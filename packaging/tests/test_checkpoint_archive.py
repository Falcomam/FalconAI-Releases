import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "checkpoint_archive.py"


@unittest.skipUnless(os.name == "nt", "Uses Windows DPAPI")
class CheckpointArchiveTests(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.database = self.root / "archive.sqlite3"
        self.source = self.root / "private-input-name.json"
        self.destination = self.root / "recovered.json"

    def command(self, *arguments):
        return subprocess.run(
            [sys.executable, "-B", str(SCRIPT), "--db", str(self.database), *map(str, arguments)],
            text=True, capture_output=True, timeout=8,
        )

    def success(self, *arguments):
        result = self.command(*arguments)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_reopens_protected_checkpoint_and_restores_exact_bytes(self):
        data = b'{"checkpoint":"distinct synthetic checkpoint phrase"}\r\n'
        self.source.write_bytes(data)
        saved = self.success("archive", self.source)
        stored = self.database.read_bytes()
        self.assertNotIn(b"distinct synthetic checkpoint phrase", stored)
        self.assertNotIn(self.source.name.encode(), stored)
        self.assertNotIn(hashlib.sha256(data).digest(), stored)
        self.assertNotIn(hashlib.sha256(data).hexdigest().encode(), stored)

        self.success("restore", saved["id"], self.destination)

        self.assertEqual(self.destination.read_bytes(), data)

    def test_duplicate_reuses_record_and_changes_can_resume_after_sequence(self):
        self.source.write_bytes(b"synthetic first checkpoint")
        first = self.success("archive", self.source)
        duplicate = self.success("archive", self.source)
        self.source.write_bytes(b"synthetic second checkpoint")
        second = self.success("archive", self.source)

        self.assertEqual(first["id"], duplicate["id"])
        self.assertEqual(first["sequence"], duplicate["sequence"])
        self.assertFalse(duplicate["added"])
        self.assertEqual(self.success("status")["checkpoints"], 2)
        self.assertEqual(self.success("changes", "--limit", 1)["next_after"], first["sequence"])
        later = self.success("changes", "--after", first["sequence"])
        self.assertEqual([entry["id"] for entry in later["checkpoints"]], [second["id"]])
        self.assertEqual(later["next_after"], second["sequence"])

    def test_compresses_repetitive_checkpoint_before_encryption(self):
        self.source.write_bytes(b"synthetic checkpoint line\n" * 2_000)
        saved = self.success("archive", self.source)

        self.assertLess(saved["sealed_bytes"], 4096)

    def test_tampered_ciphertext_cannot_be_restored_or_accepted_as_duplicate(self):
        self.source.write_bytes(b"synthetic stable checkpoint")
        saved = self.success("archive", self.source)
        database = sqlite3.connect(self.database)
        self.addCleanup(database.close)
        with database:
            payload, = database.execute("SELECT sealed FROM checkpoints").fetchone()
            damaged = payload[:20] + bytes([payload[20] ^ 1]) + payload[21:]
            database.execute("UPDATE checkpoints SET sealed = ?", (damaged,))

        result = self.command("restore", saved["id"], self.destination)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("integrity", result.stderr.lower())
        self.assertFalse(self.destination.exists())
        self.assertNotEqual(self.command("archive", self.source).returncode, 0)

    def test_record_authentication_binds_the_sequence(self):
        self.source.write_bytes(b"synthetic checkpoint with sequence")
        saved = self.success("archive", self.source)
        database = sqlite3.connect(self.database)
        self.addCleanup(database.close)
        with database:
            database.execute("UPDATE checkpoints SET seq = seq + 10")

        result = self.command("restore", saved["id"], self.destination)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("integrity", result.stderr.lower())
        self.assertFalse(self.destination.exists())

    def test_capacity_is_enforced_on_reopen_without_losing_previous_record(self):
        self.source.write_bytes(b"small synthetic payload")
        saved = self.success("archive", self.source, "--capacity-bytes", 32768)
        self.source.write_bytes(os.urandom(40_000))

        result = self.command("archive", self.source)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("capacity", result.stderr.lower())
        status = self.success("status")
        self.assertEqual(status["capacity_bytes"], 32768)
        self.assertEqual(status["checkpoints"], 1)
        self.assertLessEqual(self.database.stat().st_size, 32768)
        self.success("restore", saved["id"], self.destination)
        self.assertEqual(self.destination.read_bytes(), b"small synthetic payload")

    def test_restore_can_never_overwrite_existing_output(self):
        self.source.write_bytes(b"synthetic checkpoint")
        saved = self.success("archive", self.source)
        self.destination.write_bytes(b"preserve this")

        result = self.command("restore", saved["id"], self.destination)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.destination.read_bytes(), b"preserve this")
        self.assertFalse(list(self.root.glob(".checkpoint-*")))

    def test_rejects_oversize_input_without_creating_database(self):
        self.source.write_bytes(b"x" * (256 * 1024 + 1))

        self.assertNotEqual(self.command("archive", self.source).returncode, 0)
        self.assertFalse(self.database.exists())

    def test_status_does_not_create_archive(self):
        self.assertNotEqual(self.command("status").returncode, 0)
        self.assertFalse(self.database.exists())


if __name__ == "__main__":
    unittest.main()
