"""Bounded targeted edits preserve untouched source and existing review gates."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import project_targeted_edits as targeted
import project_revision as revisions
import developer_workspace as projects


class TargetedEditsTests(unittest.TestCase):
    def setUp(self):
        plan = {"name": "falcon_project", "kind": "python",
                "files": {"main.py": "import helpers\nprint(helpers.answer())\n",
                          "helpers.py": "def answer():\n    return 1\n",
                          "README.md": "# Sample project\n",
                          "src/notes.txt": "do not touch this file\n"}}
        self.base = {"plan": plan,
                     "fingerprint": revisions._snapshot_fingerprint(plan)}

    def test_select_and_merge_only_relevant_files(self):
        context = targeted.select_context(
            self.base, "Update helpers.py so answer returns 2", max_files=1)
        self.assertIn("helpers.py", context["selected_files"])
        changes = json.dumps({"changes": {"helpers.py": "def answer():\n    return 2\n"}})
        with patch.object(revisions, "save_revision_approved",
                          side_effect=AssertionError("no write")):
            output = targeted.parse_targeted_changes(self.base, changes, context)
        self.assertEqual(output["revision"]["changed"], ("helpers.py",))
        self.assertEqual(output["plan"]["files"]["main.py"],
                         self.base["plan"]["files"]["main.py"])
        self.assertFalse(output["execution_allowed"])

    def test_explicit_oversized_file_cannot_be_silently_skipped(self):
        original = self.base["plan"]["files"]["helpers.py"]
        self.base["plan"]["files"]["helpers.py"] = "x" * 30000
        self.base["fingerprint"] = revisions._snapshot_fingerprint(self.base["plan"])
        with self.assertRaisesRegex(projects.ProjectError, "too large"):
            targeted.select_context(
                self.base, "Update helpers.py so answer returns 2", max_chars=12000)
        self.base["plan"]["files"]["helpers.py"] = original

    def test_unselected_source_changes_refused(self):
        context = targeted.select_context(
            self.base, "Update helpers.py so answer returns 2", max_files=1)
        raw = json.dumps({"changes": {"main.py": "print('tampered')\n"}})
        with self.assertRaisesRegex(projects.ProjectError, "outside selected"):
            targeted.parse_targeted_changes(self.base, raw, context)

    def test_additions_require_existing_revision_review(self):
        context = targeted.select_context(
            self.base, "Update helpers.py and add a new helper test file")
        raw = json.dumps({"changes": {"tests/test_helpers.py": "assert True\n"}})
        output = targeted.parse_targeted_changes(self.base, raw, context)
        self.assertIn("tests/test_helpers.py", output["revision"]["added"])
        self.assertIn("/dev/null", output["revision"]["diff"])

    def test_path_traversal_and_duplicate_keys_refused(self):
        context = targeted.select_context(self.base, "Improve helper function")
        for raw in (
            '{"changes":{"../evil.py":"pass"}}',
            '{"changes":{"main.py":"pass","main.py":"print(1)"}}',
            '{"changes":{"main.py":NaN}}',
        ):
            with self.subTest(raw=raw), self.assertRaises(projects.ProjectError):
                targeted.parse_targeted_changes(self.base, raw, context)

    def test_stale_context_or_model_hallucinated_source_refused(self):
        context = targeted.select_context(self.base, "Improve helper function")
        context["selected_files"]["helpers.py"] = "fake original"
        with self.assertRaises(projects.ProjectError):
            targeted.parse_targeted_changes(
                self.base, '{"changes":{"helpers.py":"pass"}}', context)

    def test_no_change_blocked_and_fenced_json_supported(self):
        context = targeted.select_context(self.base, "Improve helper function")
        unchanged = json.dumps({"changes": {"helpers.py": self.base["plan"]["files"]["helpers.py"]}})
        with self.assertRaisesRegex(projects.ProjectError, "did not change"):
            targeted.parse_targeted_changes(self.base, unchanged, context)
        raw = "```json\n" + json.dumps({"changes": {
            "helpers.py": "def answer():\n    return 5\n"}}) + "\n```"
        result = targeted.parse_targeted_changes(self.base, raw, context)
        self.assertIn("helpers.py", result["revision"]["updated"])


if __name__ == "__main__":
    unittest.main()
