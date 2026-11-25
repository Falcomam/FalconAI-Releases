"""Regression tests for Falcon's bounded read-only project agent harness."""
from pathlib import Path
import json
import sys
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import developer_workspace as workspace
import project_revision as revisions
import project_coding_agent as agent


def snapshot(files=None):
    plan = {"name": "lostfalcon_test", "kind": "python",
            "files": files or {
                "main.py": "from helpers import greeting\n\ndef main():\n    print(greeting())\n",
                "helpers.py": "def greeting():\n    return 'hello'\n",
                "README.md": "This project prints a greeting.\n",
            }}
    return {"plan": plan, "fingerprint": revisions._snapshot_fingerprint(plan)}


GOAL = "Improve the greeting output on the main entry point and keep helper functions."
PLAN = {"action": "plan",
        "summary": "Improve the greeting output while preserving the entry point.",
        "files": ["main.py"],
        "steps": ["Update the greeting printed by the main function.",
                  "Preserve the old project structure."]}


class MockModel:
    def __init__(self, outputs):
        self.outputs = iter(outputs)
        self.calls = []
    def __call__(self, messages, *, model, fmt, limit, timeout, cancel):
        self.calls.append({"messages": messages, "model": model, "fmt": fmt,
                           "limit": limit, "timeout": timeout})
        return next(self.outputs)


class CodingAgentTests(unittest.TestCase):
    def setUp(self):
        self.base = snapshot()
        self.cancel = threading.Event()

    def test_repository_map_is_bounded_and_read_only(self):
        output = agent.repository_map(self.base, GOAL)
        self.assertIn("main.py", output)
        self.assertIn("function main", output)
        self.assertIn("function greeting", output)
        self.assertNotIn("print(greeting())", output)
        self.assertLess(len(output), agent.MAX_MAP_CHARS)

    def test_two_round_read_then_editor_produces_inert_review(self):
        new_main = "from helpers import greeting\n\ndef main():\n    print('Hi ' + greeting())\n"
        model = MockModel([
            json.dumps({"action": "read_file", "path": "main.py"}),
            json.dumps(PLAN),
            json.dumps({"changes": {"main.py": new_main}}),
        ])
        output = agent.generate_reviewed_edit(
            self.base, GOAL, model="qwen2.5-coder:7b",
            cancel=self.cancel, ask=model)
        self.assertFalse(output["execution_allowed"])
        self.assertEqual(output["planner_reads"], ("main.py",))
        self.assertEqual(output["plan"]["files"]["README.md"],
                         self.base["plan"]["files"]["README.md"])
        self.assertEqual(output["plan"]["files"]["main.py"], new_main)
        self.assertIn("main.py", output["revision"]["changed"])
        self.assertEqual(len(model.calls), 3)
        self.assertEqual(model.calls[0]["fmt"], "json")
        self.assertEqual(model.calls[0]["limit"], 950)
        # Model cannot gain access to unrelated OS files.
        text = "\n".join(str(v) for call in model.calls for msg in call["messages"]
                         for v in msg.values())
        self.assertNotIn("C:\\Users", text)

    def test_model_read_traversal_and_tool_escalation_denied(self):
        for action in (
            {"action": "read_file", "path": "../private.txt"},
            {"action": "shell", "command": "whoami"},
            {"action": "write_file", "path": "main.py", "content": "oops"},
        ):
            with self.subTest(action=action):
                model = MockModel([json.dumps(action), json.dumps(action)])
                with self.assertRaises(agent.AgentError):
                    agent.generate_reviewed_edit(
                        self.base, GOAL, model="qwen3:4b",
                        cancel=threading.Event(), ask=model)
                self.assertEqual(len(model.calls), 2)

    def test_planning_unknown_target_rejected_and_no_editor(self):
        bad = dict(PLAN, files=["../outside.py"])
        model = MockModel([json.dumps(bad), json.dumps(bad)])
        with patch.object(agent.targeted, "generate_targeted_with_one_retry",
                          side_effect=AssertionError("no edits")):
            with self.assertRaises(agent.AgentError):
                agent.generate_reviewed_edit(
                    self.base, GOAL, model="coder:7b",
                    cancel=self.cancel, ask=model)

    def test_stop_before_any_model_call(self):
        self.cancel.set()
        model = MockModel([])
        self.assertIsNone(agent.generate_reviewed_edit(
            self.base, GOAL, model="coder:7b", cancel=self.cancel, ask=model))
        self.assertEqual(model.calls, [])

    def test_stop_after_planning_prevents_editor_request(self):
        cancel = threading.Event()
        def ask(messages, **kwargs):
            cancel.set()
            return json.dumps(PLAN)
        self.assertIsNone(agent.generate_reviewed_edit(
            self.base, GOAL, model="coder:7b", cancel=cancel, ask=ask))

    def test_large_source_file_is_not_exposed_through_read_tool(self):
        files = {"main.py": "x" * 9000, "README.md": "A test sample"}
        base = snapshot(files)
        model = MockModel([
            json.dumps({"action": "read_file", "path": "main.py"}),
            json.dumps(PLAN)
        ])
        with patch.object(agent.targeted, "generate_targeted_with_one_retry",
                          return_value={"plan": base["plan"],
                                        "revision": {"changed": ("main.py",)},
                                        "execution_allowed": False}):
            result = agent.generate_reviewed_edit(
                base, GOAL, model="coder:7b", cancel=self.cancel, ask=model)
        self.assertFalse(result["execution_allowed"])
        self.assertIn("exceeds read limit", model.calls[1]["messages"][-1]["content"])
        self.assertNotIn("x" * 200, str(model.calls))

    def test_model_unexpected_plan_shape_is_rejected(self):
        response = dict(PLAN, execute=True)
        with self.assertRaises(agent.AgentError):
            agent._parse_action(json.dumps(response), self.base)

    def test_duplicate_json_keys_fail_closed(self):
        raw = '{"action":"plan","action":"shell","files":["main.py"],"steps":["test it now"],"summary":"A detailed description"}'
        with self.assertRaises(agent.AgentError):
            agent._parse_action(raw, self.base)

    def test_invalid_model_timeout_and_context_rejected(self):
        with self.assertRaises(agent.AgentError):
            agent.generate_reviewed_edit(self.base, GOAL, model="coder:7b",
                                         cancel=self.cancel, ask=lambda *_a, **_k: "",
                                         total_timeout=301)
        with self.assertRaises(agent.AgentError):
            agent.repository_map(self.base, GOAL, max_chars=100_000)


if __name__ == "__main__":
    unittest.main()
