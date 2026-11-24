"""Test planning produces no executable commands and does no execution."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import self_improve_test_plan as plans
import self_improve_proposals as proposals


class TestPlanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "FALCON_DEVELOPMENT_BACKLOG.md").write_bytes(b"# Falcon source")
        (self.root / "engine.py").write_bytes(b"def answer():\n    return 1\n")
        self.changes = {"engine.py": {"before": "def answer():\n    return 1\n",
                                      "after": "def answer():\n    return 2\n"}}

    def test_planning_does_not_execute(self):
        with patch("subprocess.run", side_effect=AssertionError("not allowed")), \
             patch("subprocess.Popen", side_effect=AssertionError("not allowed")):
            result = plans.plan(self.changes, trusted_checkout=self.root)
        self.assertFalse(result["dynamic_tests_executed"])
        self.assertFalse(result["installer_built"])
        self.assertFalse(result["deployment_approved"])
        self.assertEqual(result["dynamic_tests"], "requires_approved_isolation")
        self.assertIn("python_ast_parse", result["files"][0]["static_checks"])
        self.assertEqual(len(result["proposal_sha256"]), 64)
        self.assertNotIn("commands", result)

    def test_untrusted_model_baseline_rejected(self):
        modified = {"engine.py": {"before": "def answer():\n    return 100\n",
                                   "after": "def answer():\n    return 2\n"}}
        with self.assertRaises(proposals.ProposalError):
            plans.plan(modified, trusted_checkout=self.root)

    def test_plan_line_stats(self):
        result = plans.plan(self.changes, trusted_checkout=self.root)
        self.assertEqual(result["files"][0]["line_changes"],
                         {"added_lines": 1, "removed_lines": 1})


if __name__ == "__main__":
    unittest.main()
