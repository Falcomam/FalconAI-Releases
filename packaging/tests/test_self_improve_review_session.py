"""Ephemeral self-improvement review sessions never authorize installation."""
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import self_improve_review_session as sessions
import self_improve_proposals as proposals


class ReviewSessionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "FALCON_DEVELOPMENT_BACKLOG.md").write_bytes(b"# Source")
        (self.root / "engine.py").write_bytes(b"def run():\n    return 1\n")
        self.pins = {"engine.py": hashlib.sha256(
            (self.root / "engine.py").read_bytes()).hexdigest()}
        self.changes = {"engine.py": {
            "before": "def run():\n    return 1\n",
            "after": "def run():\n    return 2\n"}}
        self.session = sessions.ReviewSession(
            trusted_checkout=self.root, trusted_sha256=self.pins)

    def test_consent_requires_visible_review_and_exact_token(self):
        draft = self.session.submit(self.changes)
        with self.assertRaises(proposals.ProposalError):
            self.session.record_user_test_consent(
                review_token="bad", fingerprint=draft["fingerprint"])
        shown = self.session.show_review()
        self.assertIn("Tests executed: NO", shown["text"])
        with self.assertRaises(proposals.ProposalError):
            self.session.record_user_test_consent(
                review_token="wrong", fingerprint=shown["fingerprint"])
        with self.assertRaises(proposals.ProposalError):
            self.session.record_user_test_consent(
                review_token=shown["review_token"], fingerprint="0" * 64)
        approved = self.session.record_user_test_consent(
            review_token=shown["review_token"], fingerprint=shown["fingerprint"])
        self.assertEqual(approved["scope"], "request_isolated_tests_only")
        self.assertFalse(approved["tests_executed"])
        self.assertFalse(approved["deployment_approved"])
        self.assertTrue(self.session.test_plan()["user_test_consent_recorded"])

    def test_changed_proposal_clears_review_and_consent(self):
        self.session.submit(self.changes)
        shown = self.session.show_review()
        self.session.record_user_test_consent(
            review_token=shown["review_token"], fingerprint=shown["fingerprint"])
        newer = {"engine.py": {"before": self.changes["engine.py"]["before"],
                               "after": "def run():\n    return 3\n"}}
        self.session.submit(newer)
        self.assertEqual(self.session.state, "draft")
        with self.assertRaises(proposals.ProposalError):
            self.session.record_user_test_consent(
                review_token=shown["review_token"], fingerprint=shown["fingerprint"])

    def test_source_edit_blocks_consent(self):
        self.session.submit(self.changes)
        shown = self.session.show_review()
        (self.root / "engine.py").write_bytes(b"def run():\n    return 99\n")
        with self.assertRaises(proposals.ProposalError):
            self.session.record_user_test_consent(
                review_token=shown["review_token"], fingerprint=shown["fingerprint"])
        self.assertEqual(self.session.state, "reviewed")

    def test_truncated_review_cannot_issue_consent_token(self):
        large = {"engine.py": {
            "before": self.changes["engine.py"]["before"],
            "after": "def run():\n    return '" + "x" * 28000 + "'\n",
        }}
        self.session.submit(large)
        shown = self.session.show_review()
        self.assertFalse(shown["review_complete"])
        self.assertIsNone(shown["review_token"])
        with self.assertRaises(proposals.ProposalError):
            self.session.record_user_test_consent(
                review_token="", fingerprint=shown["fingerprint"])

    def test_stop_or_rejection_irreversibly_revokes(self):
        self.session.submit(self.changes)
        shown = self.session.show_review()
        self.session.reject()
        self.assertEqual(self.session.state, "stopped")
        with self.assertRaises(proposals.ProposalError):
            self.session.record_user_test_consent(
                review_token=shown["review_token"], fingerprint=shown["fingerprint"])
        with self.assertRaises(proposals.ProposalError):
            self.session.submit(self.changes)

    def test_audit_trail_excludes_source_and_review_tokens(self):
        self.session.submit(self.changes)
        shown = self.session.show_review()
        self.session.record_user_test_consent(
            review_token=shown["review_token"],
            fingerprint=shown["fingerprint"])
        self.session.stop()
        events = self.session.audit()
        self.assertEqual([e["event"] for e in events], [
            "proposal_submitted", "review_displayed",
            "test_consent_recorded", "session_stopped"])
        self.assertTrue(events[-1]["consent_revoked"])
        text = str(events)
        self.assertNotIn(shown["review_token"], text)
        self.assertNotIn("def run", text)
        events[0]["event"] = "tampered"
        self.assertEqual(self.session.audit()[0]["event"], "proposal_submitted")

    def test_never_executes_untrusted_code(self):
        with patch("subprocess.run", side_effect=AssertionError("unsafe")), \
             patch("subprocess.Popen", side_effect=AssertionError("unsafe")):
            self.session.submit(self.changes)
            self.session.show_review()
            self.assertEqual(self.session.test_plan()["dynamic_tests_executed"], False)


if __name__ == "__main__":
    unittest.main()
