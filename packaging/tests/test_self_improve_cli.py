"""CLI runs only source review; accepts no install or execution arguments."""
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import self_improve_cli as cli


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "FALCON_DEVELOPMENT_BACKLOG.md").write_bytes(b"# Falcon")
        (self.root / "engine.py").write_bytes(b"def answer():\n    return 1\n")
        digest = hashlib.sha256((self.root / "engine.py").read_bytes()).hexdigest()
        self.pins = self.root / "pins.json"
        self.pins.write_text(json.dumps({"engine.py": digest}), encoding="utf-8")
        self.change = self.root / "changes.json"
        self.change.write_text(json.dumps({"engine.py": {
            "before": "def answer():\n    return 1\n",
            "after": "def answer():\n    return 2\n"}}), encoding="utf-8")

    def _call(self, mode):
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(io.StringIO()):
            status = cli.main([mode, "--checkout", str(self.root),
                               "--pinned-manifest", str(self.pins),
                               "--proposal", str(self.change)])
        return status, out.getvalue()

    def test_review_and_plan_are_read_only(self):
        with patch("subprocess.Popen", side_effect=AssertionError("no code execution")), \
             patch("subprocess.run", side_effect=AssertionError("no code execution")):
            status, review = self._call("review")
            self.assertEqual(status, 0)
            self.assertIn("Tests executed: NO", review)
            self.assertIn("Installed: NO", review)
            status, output = self._call("plan")
        self.assertEqual(status, 0)
        plan = json.loads(output)
        self.assertEqual(plan["dynamic_tests"], "requires_approved_isolation")
        self.assertFalse(plan["installer_built"])

    def test_rejects_wrong_pin(self):
        self.pins.write_text(json.dumps({"engine.py": "0" * 64}), encoding="utf-8")
        status, output = self._call("review")
        self.assertEqual(status, 2)
        self.assertEqual(output, "")

    def test_rejects_duplicate_json(self):
        self.change.write_bytes(b'{"engine.py":{}, "engine.py":{}}')
        status, output = self._call("review")
        self.assertEqual(status, 2)
        self.assertEqual(output, "")

    def test_too_large_proposal_rejected(self):
        self.change.write_bytes(b" " * (cli.MAX_INPUT_BYTES + 1))
        status, _ = self._call("plan")
        self.assertEqual(status, 2)


if __name__ == "__main__":
    unittest.main()
