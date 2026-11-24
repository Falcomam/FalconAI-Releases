"""Bounded targeted edits preserve untouched source and existing review gates."""
import json
import threading
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

    def test_targeted_model_retry_keeps_other_files_unchanged(self):
        calls = []
        def ask(messages, **kwargs):
            calls.append((messages, kwargs))
            if len(calls) == 1:
                return "not json"
            return json.dumps({"changes": {
                "helpers.py": "def answer():\n    return 42\n"}})
        output = targeted.generate_targeted_with_one_retry(
            self.base, "Update helpers.py so answer returns 42",
            model="qwen3:4b", cancel=threading.Event(), ask=ask)
        self.assertEqual(len(calls), 2)
        self.assertEqual(output["revision"]["changed"], ("helpers.py",))
        self.assertEqual(output["plan"]["files"]["main.py"],
                         self.base["plan"]["files"]["main.py"])
        self.assertTrue(all("all_existing_paths" in calls[0][0][1]["content"]
                            for _ in (0,)))
        self.assertFalse(output["execution_allowed"])

    def test_targeted_cancel_avoids_retry_or_write(self):
        token = threading.Event()
        calls = []
        def ask(messages, **kwargs):
            calls.append(1)
            token.set()
            return "not json"
        with patch.object(revisions, "save_revision_approved",
                          side_effect=AssertionError("unexpected save")):
            output = targeted.generate_targeted_with_one_retry(
                self.base, "Update helpers.py so answer returns 42",
                model="qwen3:4b", cancel=token, ask=ask)
        self.assertIsNone(output)
        self.assertEqual(calls, [1])

    def test_targeted_failing_model_does_not_retry_connection_errors(self):
        calls = []
        def ask(*args, **kwargs):
            calls.append(1)
            raise ConnectionError("Ollama went offline")
        with self.assertRaises(ConnectionError):
            targeted.generate_targeted_with_one_retry(
                self.base, "Update helpers.py so answer returns 42",
                model="qwen3:4b", cancel=threading.Event(), ask=ask)
        self.assertEqual(calls, [1])

    def test_targeted_two_invalid_attempts_never_save(self):
        calls = []
        def ask(*args, **kwargs):
            calls.append(1)
            return '{"changes":{"../escape.py":"pass"}}'
        with patch.object(revisions, "save_revision_approved",
                          side_effect=AssertionError("unexpected save")):
            with self.assertRaisesRegex(projects.ProjectError, "after two attempts"):
                targeted.generate_targeted_with_one_retry(
                    self.base, "Update helpers.py so answer returns 42",
                    model="qwen3:4b", cancel=threading.Event(), ask=ask)
        self.assertEqual(len(calls), 2)

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
