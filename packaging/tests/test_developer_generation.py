"""Tests for bounded local-model correction: never runs or saves generated code."""
import json
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import developer_generation as gen
import developer_workspace as projects


class GenerationTests(unittest.TestCase):
    def setUp(self):
        self.cancel = threading.Event()
        self.messages = [{"role": "system", "content": "JSON only"},
                         {"role": "user", "content": "Make a Python app"}]
        self.valid = json.dumps({"name": "sample", "kind": "python",
                                 "files": {"main.py": "print('ok')\n"}})

    def _run(self, ask):
        return gen.generate_with_one_retry(
            kind="python", messages=self.messages, model="qwen3:4b",
            cancel=self.cancel, ask=ask)

    def test_valid_first_attempt_has_no_retry(self):
        calls = []
        def ask(messages, **kwargs):
            calls.append(messages)
            return self.valid
        result = self._run(ask)
        self.assertEqual(result["name"], "sample")
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(self.messages), 2)

    def test_invalid_json_retries_at_most_once(self):
        calls = []
        def ask(messages, **kwargs):
            calls.append(messages)
            return "not json" if len(calls) == 1 else self.valid
        with patch.object(projects, "save_approved",
                          side_effect=AssertionError("no write")):
            result = self._run(ask)
        self.assertEqual(result["kind"], "python")
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(calls[1]), len(self.messages) + 1)

    def test_wrong_kind_also_retries(self):
        wrong = json.dumps({"name": "site", "kind": "website",
                            "files": {"index.html": "<html></html>"}})
        answers = iter([wrong, self.valid])
        result = self._run(lambda *_args, **_kwargs: next(answers))
        self.assertEqual(result["kind"], "python")

    def test_after_two_bad_attempts_fails_without_write(self):
        calls = []
        def ask(*args, **kwargs):
            calls.append(1)
            return "garbage"
        with patch.object(projects, "save_approved",
                          side_effect=AssertionError("no writes")):
            with self.assertRaisesRegex(projects.ProjectError, "after 2 attempts"):
                self._run(ask)
        self.assertEqual(len(calls), 2)

    def test_stop_prevents_second_request(self):
        calls = []
        def ask(*args, **kwargs):
            calls.append(1)
            self.cancel.set()
            return "garbage"
        self.assertIsNone(self._run(ask))
        self.assertEqual(len(calls), 1)

    def test_unrelated_model_error_does_not_retry(self):
        calls = []
        def ask(*args, **kwargs):
            calls.append(1)
            raise ConnectionError("Ollama offline")
        with self.assertRaises(ConnectionError):
            self._run(ask)
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
