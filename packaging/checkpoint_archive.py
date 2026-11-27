"""Archive an explicitly selected checkpoint on Windows.

Recovery normally requires the Windows account and machine that wrote the archive.
The database is a local copy of a handoff and does not preserve the workspace or
the running process. Each distinct payload receives an immutable sequence and
keyed ID. The change feed exposes that metadata for a future transfer adapter.
The capacity limit covers the main SQLite file. A rollback journal can use
additional space while a transaction is in progress.
"""

import argparse
from contextlib import closing
import ctypes
from ctypes import wintypes
from functools import cache
import hmac
import json
import os
from pathlib import Path
import sqlite3
import sys
from tempfile import NamedTemporaryFile
import zlib


APPLICATION_ID = 0x46414C43
FORMAT_VERSION = 1
MAX_INPUT_BYTES = 256 * 1024
MIN_CAPACITY_BYTES = 32 * 1024
DEFAULT_CAPACITY_BYTES = 8 * 1024 * 1024
MAX_CAPACITY_BYTES = 64 * 1024 * 1024
MAX_SEQUENCE = 2**63 - 1
CRYPTPROTECT_UI_FORBIDDEN = 0x01


class ArchiveError(ValueError):
    pass


class DataBlob(ctypes.Structure):
    _fields_ = [("size", wintypes.DWORD), ("data", ctypes.c_void_p)]


@cache
def dpapi_functions():
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    protect = crypt32.CryptProtectData
    unprotect = crypt32.CryptUnprotectData
    for operation in (protect, unprotect):
        operation.argtypes = [ctypes.POINTER(DataBlob), ctypes.c_void_p, ctypes.c_void_p,
                              ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD,
                              ctypes.POINTER(DataBlob)]
        operation.restype = wintypes.BOOL
    free = kernel32.LocalFree
    free.argtypes = [ctypes.c_void_p]
    free.restype = ctypes.c_void_p
    return protect, unprotect, free


def dpapi(data, *, decrypt=False):
    protect, unprotect, free = dpapi_functions()
    source = ctypes.create_string_buffer(data, len(data))
    incoming = DataBlob(len(data), ctypes.addressof(source))
    outgoing = DataBlob()
    operation = unprotect if decrypt else protect
    try:
        if not operation(ctypes.byref(incoming), None, None, None, None,
                         CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(outgoing)):
            if decrypt:
                raise ArchiveError("Windows DPAPI could not authenticate or unlock the archive in this profile")
            raise ArchiveError(f"Windows DPAPI could not protect data (error {ctypes.get_last_error()})")
        return ctypes.string_at(outgoing.data, outgoing.size)
    finally:
        ctypes.memset(incoming.data, 0, incoming.size)
        if outgoing.data:
            if decrypt:
                ctypes.memset(outgoing.data, 0, outgoing.size)
            free(outgoing.data)


def local_path(value):
    path = Path(value).absolute()
    if os.name != "nt":
        raise ArchiveError("Checkpoint archives require Windows DPAPI")
    if path.drive.startswith("\\\\"):
        raise ArchiveError("Use a local Windows path")
    return path


def connect(path, *, write=False):
    mode = "rwc" if write else "ro"
    return sqlite3.connect(f"{path.as_uri()}?mode={mode}", uri=True, timeout=2)


def page_info(db):
    page_size, = db.execute("PRAGMA page_size").fetchone()
    page_count, = db.execute("PRAGMA page_count").fetchone()
    return page_size, page_count


def settings(db):
    app_id, = db.execute("PRAGMA application_id").fetchone()
    version, = db.execute("PRAGMA user_version").fetchone()
    if (app_id, version) != (APPLICATION_ID, FORMAT_VERSION):
        raise ArchiveError("This file is not a supported checkpoint archive")
    row = db.execute("SELECT max_pages, protected_key FROM settings WHERE singleton = 1").fetchone()
    if row is None:
        raise ArchiveError("Checkpoint archive settings are missing")
    max_pages, protected_key = row
    page_size, page_count = page_info(db)
    if (type(max_pages) is not int or max_pages < page_count
            or not MIN_CAPACITY_BYTES <= max_pages * page_size <= MAX_CAPACITY_BYTES):
        raise ArchiveError("Checkpoint archive capacity settings are invalid")
    return max_pages, protected_key


def unlock(protected_key):
    if not isinstance(protected_key, bytes) or not protected_key:
        raise ArchiveError("Checkpoint archive key is invalid")
    key = dpapi(protected_key, decrypt=True)
    if len(key) != 32:
        raise ArchiveError("Checkpoint archive key is invalid")
    return key


def initialize(db, max_pages, key):
    db.execute(f"PRAGMA application_id = {APPLICATION_ID}")
    db.execute(f"PRAGMA user_version = {FORMAT_VERSION}")
    db.execute("""CREATE TABLE settings (
        singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
        max_pages INTEGER NOT NULL,
        protected_key BLOB NOT NULL
    )""")
    db.execute("""CREATE TABLE checkpoints (
        seq INTEGER PRIMARY KEY CHECK (seq > 0),
        id BLOB UNIQUE NOT NULL CHECK (length(id) = 32),
        sealed BLOB NOT NULL,
        tag BLOB NOT NULL CHECK (length(tag) = 32)
    )""")
    db.execute("INSERT INTO settings VALUES (1, ?, ?)", (max_pages, dpapi(key)))


def content_id(key, data):
    return hmac.digest(key, b"checkpoint-id-v1\x00" + data, "sha256")


def record_tag(key, sequence, identifier, sealed):
    return hmac.digest(key, b"checkpoint-record-v1\x00" + sequence.to_bytes(8, "big")
                       + identifier + sealed, "sha256")


def authenticate_record(key, sequence, identifier, sealed, tag):
    if (not isinstance(sealed, bytes) or not isinstance(tag, bytes)
            or not hmac.compare_digest(tag, record_tag(key, sequence, identifier, sealed))):
        raise ArchiveError("Checkpoint record failed its integrity check")


def record_info(sequence, identifier, sealed_bytes):
    return {"sequence": sequence, "id": identifier.hex(), "sealed_bytes": sealed_bytes}


def archive_checkpoint(database, source, capacity_bytes=None):
    database, source = local_path(database), local_path(source)
    if not source.is_file():
        raise ArchiveError("Select one existing checkpoint file")
    if database.exists() and os.path.samefile(database, source):
        raise ArchiveError("The archive itself cannot be a checkpoint input")
    with source.open("rb") as stream:
        data = stream.read(MAX_INPUT_BYTES + 1)
    if not 0 < len(data) <= MAX_INPUT_BYTES:
        raise ArchiveError(f"Checkpoint size must be between 1 and {MAX_INPUT_BYTES} bytes")
    if capacity_bytes is not None and not MIN_CAPACITY_BYTES <= capacity_bytes <= MAX_CAPACITY_BYTES:
        raise ArchiveError(f"Capacity must be between {MIN_CAPACITY_BYTES} and {MAX_CAPACITY_BYTES} bytes")

    try:
        with closing(connect(database, write=True)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            page_size, _ = page_info(db)
            # BEGIN IMMEDIATE temporarily allocates page 1 even on an empty file.
            # Check the committed file after requesting the writer lock.
            new_archive = database.stat().st_size == 0
            if not new_archive:
                max_pages, protected_key = settings(db)
                if capacity_bytes is not None and capacity_bytes // page_size != max_pages:
                    raise ArchiveError("Capacity is set when the archive is created")
                key = unlock(protected_key)
            else:
                max_pages = (capacity_bytes or DEFAULT_CAPACITY_BYTES) // page_size
                key = os.urandom(32)
            db.execute(f"PRAGMA max_page_count = {max_pages}").fetchone()
            if new_archive:
                initialize(db, max_pages, key)

            identifier = content_id(key, data)
            existing = db.execute("SELECT seq, sealed, tag FROM checkpoints WHERE id = ?",
                                  (identifier,)).fetchone()
            if existing is not None:
                sequence, sealed, tag = existing
                authenticate_record(key, sequence, identifier, sealed, tag)
                return dict(record_info(sequence, identifier, len(sealed)), added=False)

            sequence, = db.execute("SELECT COALESCE(MAX(seq), 0) + 1 FROM checkpoints").fetchone()
            sealed = dpapi(zlib.compress(data, level=1))
            tag = record_tag(key, sequence, identifier, sealed)
            db.execute("INSERT INTO checkpoints VALUES (?, ?, ?, ?)", (sequence, identifier, sealed, tag))
            return dict(record_info(sequence, identifier, len(sealed)), added=True)
    except sqlite3.Error as error:
        if error.sqlite_errorcode == sqlite3.SQLITE_FULL:
            raise ArchiveError("Archive capacity reached or disk is full") from error
        raise


def restore_checkpoint(database, checkpoint_id, destination):
    database, destination = local_path(database), local_path(destination)
    identifier = bytes.fromhex(checkpoint_id)
    if len(identifier) != 32 or len(checkpoint_id) != 64:
        raise ArchiveError("Provide the 64-character checkpoint ID")
    with closing(connect(database)) as db:
        _, protected_key = settings(db)
        row = db.execute("SELECT seq, sealed, tag FROM checkpoints WHERE id = ?", (identifier,)).fetchone()
    if row is None:
        raise ArchiveError("Checkpoint ID was not found in the archive")
    sequence, sealed, tag = row
    key = unlock(protected_key)
    authenticate_record(key, sequence, identifier, sealed, tag)
    compressed = dpapi(sealed, decrypt=True)
    decompressor = zlib.decompressobj()
    data = decompressor.decompress(compressed, MAX_INPUT_BYTES + 1)
    if (not decompressor.eof or decompressor.unused_data or not 0 < len(data) <= MAX_INPUT_BYTES
            or not hmac.compare_digest(identifier, content_id(key, data))):
        raise ArchiveError("Checkpoint content failed its integrity check")

    # Windows rename fails when the destination exists, including if it appeared
    # after authentication. Flush the temporary file before making it visible.
    temporary = None
    try:
        with NamedTemporaryFile(dir=destination.parent, prefix=".checkpoint-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.rename(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return record_info(sequence, identifier, len(sealed))


def archive_status(database):
    with closing(connect(local_path(database))) as db:
        max_pages, _ = settings(db)
        page_size, page_count = page_info(db)
        count, last = db.execute("SELECT COUNT(*), COALESCE(MAX(seq), 0) FROM checkpoints").fetchone()
    return {"format_version": FORMAT_VERSION, "checkpoints": count, "last_sequence": last,
            "database_bytes": page_count * page_size, "capacity_bytes": max_pages * page_size}


def list_changes(database, after, limit):
    if not 0 <= after <= MAX_SEQUENCE or not 1 <= limit <= 100:
        raise ArchiveError("Use a nonnegative sequence and a page size from 1 to 100")
    with closing(connect(local_path(database))) as db:
        settings(db)
        rows = db.execute("""SELECT seq, id, length(sealed) FROM checkpoints
                             WHERE seq > ? ORDER BY seq LIMIT ?""", (after, limit))
        checkpoints = [record_info(*row) for row in rows]
    next_after = checkpoints[-1]["sequence"] if checkpoints else after
    return {"format_version": FORMAT_VERSION, "checkpoints": checkpoints, "next_after": next_after}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0],
                                     epilog="Recovery uses the original Windows account and normally the original machine.")
    parser.add_argument("--db", required=True, type=Path, help="local SQLite archive file")
    commands = parser.add_subparsers(dest="command", required=True)
    archive = commands.add_parser("archive", help="archive one explicitly selected file")
    archive.add_argument("source", type=Path)
    archive.add_argument("--capacity-bytes", type=int,
                         help="database size cap rounded down to whole pages, set at creation")
    restore = commands.add_parser("restore", help="authenticate and restore to a new file")
    restore.add_argument("checkpoint_id")
    restore.add_argument("destination", type=Path)
    commands.add_parser("status", help="show usage and capacity")
    changes = commands.add_parser("changes", help="list opaque checkpoint IDs in sequence order")
    changes.add_argument("--after", type=int, default=0)
    changes.add_argument("--limit", type=int, default=50)

    arguments = vars(parser.parse_args(argv))
    operation = {"archive": archive_checkpoint, "restore": restore_checkpoint,
                 "status": archive_status, "changes": list_changes}[arguments.pop("command")]
    database = arguments.pop("db")
    try:
        result = operation(database, **arguments)
    except (ValueError, OSError, sqlite3.Error, zlib.error) as error:
        print(f"Checkpoint archive: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
