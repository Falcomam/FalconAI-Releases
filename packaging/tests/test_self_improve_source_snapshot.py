"""Source snapshot loader never executes, writes or follows redirected paths."""
from pathlib import Path
import hashlib
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import self_improve_source_snapshot as snapshots
import self_improve_proposals as proposals
import self_improve_review_bridge as bridge


class SourceSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "checkout"
        (self.root / "packaging").mkdir(parents=True)
        (self.root / snapshots.MARKER).write_text("# Falcon backlog", encoding="utf-8")
        (self.root / "packaging" / "engine.py").write_bytes(b"def speed():\n    return 1\n")

    def test_safe_read_and_proposal_baseline(self):
        snapshot = snapshots.read_snapshot(self.root, ["packaging/engine.py"])
        self.assertEqual(snapshot["packaging/engine.py"], "def speed():\n    return 1\n")
        changes = {"packaging/engine.py": {"before": snapshot["packaging/engine.py"],
                                            "after": "def speed():\n    return 2\n"}}
        self.assertTrue(bridge.prepare(changes, snapshot)["fingerprint"])

    def test_end_to_end_review_and_recheck_detects_source_edit(self):
        changes = {"packaging/engine.py": {
            "before": "def speed():\n    return 1\n",
            "after": "def speed():\n    return 2\n",
        }}
        reviewed = bridge.prepare_from_checkout(changes, trusted_checkout=self.root)
        verified = bridge.verify_from_checkout(
            changes, trusted_checkout=self.root,
            reviewed_fingerprint=reviewed["fingerprint"])
        self.assertTrue(verified["source_snapshot_verified"])
        self.assertFalse(verified["installation_allowed"])
        (self.root / "packaging" / "engine.py").write_bytes(
            b"def speed():\n    return 10\n")
        with self.assertRaisesRegex(proposals.ProposalError, "Stale or fabricated"):
            bridge.verify_from_checkout(
                changes, trusted_checkout=self.root,
                reviewed_fingerprint=reviewed["fingerprint"])

    def test_pinned_snapshot_accepts_exact_digest_and_rejects_mismatch(self):
        before = (self.root / "packaging" / "engine.py").read_bytes()
        digest = hashlib.sha256(before).hexdigest()
        path = "packaging/engine.py"
        pinned = snapshots.read_pinned_snapshot(self.root, {path: digest})
        self.assertEqual(pinned[path].encode("utf-8"), before)
        changes = {path: {"before": pinned[path],
                          "after": "def speed():\n    return 2\n"}}
        review = bridge.prepare_pinned_from_checkout(
            changes, trusted_checkout=self.root, trusted_sha256={path: digest})
        result = bridge.verify_pinned_from_checkout(
            changes, trusted_checkout=self.root, trusted_sha256={path: digest},
            reviewed_fingerprint=review["fingerprint"])
        self.assertTrue(result["source_snapshot_verified"])
        with self.assertRaisesRegex(proposals.ProposalError, "digest mismatch"):
            snapshots.read_pinned_snapshot(self.root, {path: "0" * 64})
        with self.assertRaises(proposals.ProposalError):
            snapshots.read_pinned_snapshot(self.root, {path: "untrusted"})
        with self.assertRaises(proposals.ProposalError):
            bridge.prepare_pinned_from_checkout(
                changes, trusted_checkout=self.root,
                trusted_sha256={"unrelated.py": digest})

    def test_unknown_checkout_without_marker_rejected(self):
        (self.root / snapshots.MARKER).unlink()
        with self.assertRaises(proposals.ProposalError):
            snapshots.read_snapshot(self.root, ["packaging/engine.py"])

    def test_symlink_file_and_directory_rejected(self):
        outside = Path(self.tmp.name) / "outside.py"
        outside.write_text("pass\n")
        link = self.root / "packaging" / "link.py"
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks unavailable")
        with self.assertRaises(proposals.ProposalError):
            snapshots.read_snapshot(self.root, ["packaging/link.py"])
        redirected = self.root / "redirect"
        try:
            redirected.symlink_to(self.root / "packaging", target_is_directory=True)
        except (OSError, NotImplementedError):
            return
        with self.assertRaises(proposals.ProposalError):
            snapshots.read_snapshot(self.root, ["redirect/engine.py"])

    def test_redirecting_checkout_ancestor_rejected(self):
        alias = Path(self.tmp.name) / "checkout_alias"
        try:
            alias.symlink_to(self.root, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Directory symlinks unavailable")
        indirect = alias / "packaging"
        with self.assertRaises(proposals.ProposalError):
            snapshots.read_snapshot(indirect.parent, ["packaging/engine.py"])

    def test_paths_limits_and_missing_file(self):
        for requested in (["../escape.py"], ["packaging/missing.py"],
                          ["packaging/engine.py", "PACKAGING/ENGINE.PY"],
                          [f"a{i}.py" for i in range(13)]):
            with self.subTest(requested=requested), self.assertRaises(proposals.ProposalError):
                snapshots.read_snapshot(self.root, requested)

    def test_oversized_and_invalid_encoding_rejected(self):
        target = self.root / "packaging" / "engine.py"
        target.write_bytes(b"x" * (proposals.MAX_FILE_BYTES + 1))
        with self.assertRaises(proposals.ProposalError):
            snapshots.read_snapshot(self.root, ["packaging/engine.py"])
        target.write_bytes(b"\xff")
        with self.assertRaises(proposals.ProposalError):
            snapshots.read_snapshot(self.root, ["packaging/engine.py"])

    def test_read_only_no_subprocess_or_writes(self):
        with patch("subprocess.run", side_effect=AssertionError("execution forbidden")), \
             patch("subprocess.Popen", side_effect=AssertionError("execution forbidden")):
            self.assertEqual(len(snapshots.read_snapshot(self.root, ["packaging/engine.py"])), 1)


if __name__ == "__main__":
    unittest.main()
