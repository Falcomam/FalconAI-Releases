"""Regression tests for inert Falcon self-improvement proposals."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import self_improve_proposals as sip


class SelfImproveProposalTests(unittest.TestCase):
    def setUp(self):
        self.change = {"falcon/features.py": {"before": "def value():\n    return 1\n",
                                              "after": "def value():\n    return 2\n"}}

    def test_review_is_inert_and_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("builtins.open", side_effect=AssertionError("read/write forbidden")):
                result = sip.review(self.change)
            self.assertEqual(result["status"], "review_only_not_tested")
            self.assertFalse(result["execution_allowed"])
            self.assertFalse(result["installation_allowed"])
            self.assertIn("+    return 2", result["files"][0]["diff"])
            self.assertEqual(result["fingerprint"], sip.review(self.change)["fingerprint"])
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_fingerprint_changes_with_proposal(self):
        modified = copy.deepcopy(self.change)
        modified["falcon/features.py"]["after"] = "def value():\n    return 3\n"
        self.assertNotEqual(sip.review(self.change)["fingerprint"], sip.review(modified)["fingerprint"])

    def test_unsafe_paths_blocked(self):
        for name in ("../attack.py", "/absolute.py", "C:/attack.py", "src\\attack.py",
                     ".github/workflows/release.yml", ".git/config.txt", "build/tool.py",
                     "src/../../attack.py", "src//attack.py", "src/./attack.py",
                     "x.exe", "run.ps1", "requirements.txt", "CON.py", "secret.env"):
            with self.subTest(name=name), self.assertRaises(sip.ProposalError):
                sip.review({name: {"before": "x", "after": "y"}})

    def test_invalid_syntax_and_noops_blocked(self):
        for replacement in ("def broken(:\n", "def value():\n    return 1\n"):
            with self.assertRaises(sip.ProposalError):
                sip.review({"x.py": {"before": "def value():\n    return 1\n",
                                     "after": replacement}})
        with self.assertRaises(sip.ProposalError):
            sip.review({"x.json": {"before": "{}", "after": "{broken"}})

    def test_collisions_and_size_caps(self):
        with self.assertRaises(sip.ProposalError):
            sip.review({"X.txt": {"before": "a", "after": "b"},
                        "x.txt": {"before": "a", "after": "b"}})
        with self.assertRaises(sip.ProposalError):
            sip.review({"x.txt": {"before": "a", "after": "b" * (sip.MAX_FILE_BYTES + 1)}})
        with self.assertRaises(sip.ProposalError):
            sip.review({f"file{i}.txt": {"before": "a", "after": "b"} for i in range(sip.MAX_FILES + 1)})


if __name__ == "__main__":
    unittest.main()
