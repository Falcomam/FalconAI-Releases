"""Human-visible source review remains bounded, inert and fingerprinted."""
from pathlib import Path
import hashlib
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import self_improve_chat_preview as preview
import self_improve_proposals as proposals


class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "FALCON_DEVELOPMENT_BACKLOG.md").write_bytes(b"# Falcon")
        (self.root / "engine.py").write_bytes(b"def x():\n    return 1\n")
        self.hashes = {"engine.py": hashlib.sha256((self.root/"engine.py").read_bytes()).hexdigest()}
        self.changes = {"engine.py": {"before": "def x():\n    return 1\n",
                                      "after": "def x():\n    return 2\n"}}

    def test_preview_read_only(self):
        with patch("subprocess.run", side_effect=AssertionError("run forbidden")), \
             patch("subprocess.Popen", side_effect=AssertionError("run forbidden")):
            output = preview.render(self.changes, trusted_checkout=self.root,
                                    trusted_sha256=self.hashes)
        self.assertIn("Code executed: NO", output)
        self.assertIn("DIFF:", output)
        self.assertIn("+    return 2", output)
        self.assertIn("Installed: NO", output)

    def test_preview_preserves_unicode_and_escapes_terminal_controls(self):
        value = "Falcon 🦅" + chr(27) + " safe"
        cleaned = preview._visible(value)
        self.assertIn("Falcon 🦅", cleaned)
        self.assertNotIn(chr(27), cleaned)
        self.assertIn(r"\u001b", cleaned)

    def test_bad_pin_blocked(self):
        with self.assertRaises(proposals.ProposalError):
            preview.render(self.changes, trusted_checkout=self.root,
                           trusted_sha256={"engine.py": "0" * 64})

    def test_preview_limit_enforced(self):
        with self.assertRaises(proposals.ProposalError):
            preview.render(self.changes, trusted_checkout=self.root,
                           trusted_sha256=self.hashes, preview_limit=100)


if __name__ == "__main__":
    unittest.main()
