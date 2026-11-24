"""The proposal bridge refuses stale, fabricated and tampered source."""
import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import self_improve_review_bridge as bridge
import self_improve_proposals as proposals


class ReviewBridgeTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = {"src/engine.py": "def engine():\n    return 1\n"}
        self.changes = {"src/engine.py": {"before": self.snapshot["src/engine.py"],
                                          "after": "def engine():\n    return 2\n"}}

    def test_matching_snapshot_review(self):
        with patch("builtins.open", side_effect=AssertionError("unexpected file I/O")):
            review = bridge.prepare(self.changes, self.snapshot)
            result = bridge.verify_review(self.changes, self.snapshot, review["fingerprint"])
        self.assertTrue(result["source_snapshot_verified"])
        self.assertFalse(result["execution_allowed"])
        self.assertFalse(result["installation_allowed"])

    def test_fabricated_or_missing_baselines_refused(self):
        for snapshot in ({}, {"src/engine.py": "def engine():\n    return 9\n"}, None):
            with self.subTest(snapshot=snapshot), self.assertRaises(proposals.ProposalError):
                bridge.prepare(self.changes, snapshot)

    def test_changes_after_review_refused(self):
        digest = bridge.prepare(self.changes, self.snapshot)["fingerprint"]
        changed = copy.deepcopy(self.changes)
        changed["src/engine.py"]["after"] = "def engine():\n    return 3\n"
        with self.assertRaisesRegex(proposals.ProposalError, "changed since review"):
            bridge.verify_review(changed, self.snapshot, digest)

    def test_source_edits_after_review_refused(self):
        digest = bridge.prepare(self.changes, self.snapshot)["fingerprint"]
        with self.assertRaisesRegex(proposals.ProposalError, "Stale or fabricated"):
            bridge.verify_review(self.changes, {"src/engine.py": "pass\n"}, digest)

    def test_invalid_fingerprint_refused(self):
        for value in ("", "0" * 63, None):
            with self.subTest(value=value), self.assertRaises(proposals.ProposalError):
                bridge.verify_review(self.changes, self.snapshot, value)


if __name__ == "__main__":
    unittest.main()
