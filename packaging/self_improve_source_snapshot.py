"""Bounded source snapshots from an explicitly supplied Falcon development checkout.

Only for a trusted checkout chosen by development tooling. This module does not
prove repository authenticity, run code, modify any file, or inspect the
installed application. Never pass a model-supplied root directory.
"""
from __future__ import annotations

import os
from pathlib import Path
import stat

import self_improve_proposals as proposals

MAX_SOURCE_FILES = 12
MAX_SOURCE_BYTES = 600_000
MARKER = "FALCON_DEVELOPMENT_BACKLOG.md"


def _redirected(path):
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )


def _check_root(root):
    if not isinstance(root, (str, os.PathLike)):
        raise proposals.ProposalError("Explicit trusted checkout root required")
    folder = Path(root).absolute()
    try:
        if not folder.is_dir() or _redirected(folder):
            raise proposals.ProposalError("Checkout root is missing or redirected")
        marker = folder / MARKER
        if not marker.is_file() or _redirected(marker):
            raise proposals.ProposalError("Falcon development checkout marker missing")
    except (OSError, ValueError) as exc:
        raise proposals.ProposalError("Cannot inspect development checkout") from exc
    return folder


def read_snapshot(root, paths):
    """Read only a bounded list of explicit relative files from a trusted checkout.

    Rejects redirecting directory components, symlink files, special files,
    hardlinked files and oversized sources. No directory crawling, globbing,
    file writes or subprocesses. Results are in-memory plain-text snapshots.
    A separate pinned revision verification must precede use in release CI.
    """
    if not isinstance(paths, (list, tuple)) or not 1 <= len(paths) <= MAX_SOURCE_FILES:
        raise proposals.ProposalError("Expected 1 to 12 explicit source paths")
    folder = _check_root(root)
    snapshot = {}
    folded = set()
    total = 0
    for name in paths:
        path = proposals._path(name)
        key = path.casefold()
        if key in folded:
            raise proposals.ProposalError("Duplicate requested source path")
        folded.add(key)
        target = folder
        try:
            for segment in path.split("/")[:-1]:
                target = target / segment
                if not target.is_dir() or _redirected(target):
                    raise proposals.ProposalError("Redirected or missing source directory")
            target = target / path.split("/")[-1]
            info = target.lstat()
            if (_redirected(target) or not stat.S_ISREG(info.st_mode)
                    or info.st_nlink > 1 or info.st_size > proposals.MAX_FILE_BYTES):
                raise proposals.ProposalError("Unsafe or oversized source file")
            # O_NOFOLLOW provides additional protection on platforms where available.
            flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
            fd = os.open(target, flags)
            with os.fdopen(fd, "rb") as stream:
                actual = os.fstat(stream.fileno())
                if (not stat.S_ISREG(actual.st_mode) or actual.st_nlink > 1
                        or actual.st_size > proposals.MAX_FILE_BYTES
                        or (actual.st_dev, actual.st_ino) != (info.st_dev, info.st_ino)):
                    raise proposals.ProposalError("Source changed or was redirected")
                raw = stream.read(proposals.MAX_FILE_BYTES + 1)
            if len(raw) > proposals.MAX_FILE_BYTES:
                raise proposals.ProposalError("Source exceeded size limit")
            total += len(raw)
            if total > MAX_SOURCE_BYTES:
                raise proposals.ProposalError("Too much source requested")
            try:
                content = raw.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise proposals.ProposalError("Source must be valid UTF-8") from exc
            snapshot[path] = content
        except (OSError, UnicodeError) as exc:
            raise proposals.ProposalError("Cannot safely read source: " + path) from exc
    return snapshot
