"""Exercise real staged Falcon one-chat coding agent, mocks only local Ollama."""
from pathlib import Path
import json
import sys
import tempfile
import threading
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str((ROOT / "build/Falcon_Ai_CodingAgent_Candidate").resolve()))
import developer_chat as chat
import developer_workspace as workspace
import project_coding_agent as agent
import project_revision as revisions


class App:
    def __init__(self):
        self.messages = []
        self.busy = False
        self.status = ""
        self.root = types.SimpleNamespace(after=lambda delay, action: action())
    def append(self, role, value):
        self.messages.append((role, value))
    def set_status(self, value):
        self.status = value


class CodingAgentChatTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name) / "saved"
        self.project = {"name": "lostfalcon_agent", "kind": "python",
                        "files": {
                            "main.py": "from helper import greeting\nprint(greeting())\n",
                            "helper.py": "def greeting():\n    return 'Hello'\n",
                            "README.md": "Demo greeting source\n",
                        }}
        workspace.save_approved(
            self.project, workspace.review_proposal(self.project)["fingerprint"],
            workspace=self.workspace)
        self.app = App()
        self.chat = chat.ChatFeatures(self.app)

    def direct(self, label, work, done):
        done(work(threading.Event()))

    def test_routes_are_discoverable_without_executing(self):
        goal = "Make the output nicer, and keep the program working."
        self.assertEqual(chat.route("/project map lostfalcon_agent"),
                         ("project_map", "lostfalcon_agent"))
        self.assertEqual(chat.route("/project agent lostfalcon_agent " + goal),
                         ("project_agent", ("lostfalcon_agent", goal)))
        self.assertEqual(chat.route("/project agent lostfalcon_agent"),
                         ("project_help", ""))
        self.assertIn("project_agent", Path(chat.__file__).read_text(encoding="utf-8"))

    def test_read_only_map_no_llm_or_disk_changes(self):
        loader = revisions.load_project
        with patch.object(revisions, "load_project",
                          side_effect=lambda name: loader(name, workspace=self.workspace)), \
             patch.object(self.chat, "_launch", side_effect=AssertionError("no AI")):
            self.chat.dispatch("/project map lostfalcon_agent")
        self.assertIn("READ-ONLY PROJECT MAP", self.app.messages[-1][1])
        self.assertIn("main.py", self.app.messages[-1][1])
        self.assertIn("No model called", self.app.messages[-1][1])
        self.assertIsNone(self.chat.pending)

    def test_architect_and_editor_require_diff_before_approval(self):
        loader = revisions.load_project
        calls = []
        goal = "Improve main.py to add a fun greeting while keeping the helper."
        planned = {"action": "plan", "summary":
                   "Improve greeting in main program without changing helper functions.",
                   "files": ["main.py"],
                   "steps": ["Change print output in main.py to be more expressive."]}
        revised = "from helper import greeting\nprint('Falcon: ' + greeting())\n"
        replies = iter([json.dumps({"action": "read_file", "path": "main.py"}),
                        json.dumps(planned),
                        json.dumps({"changes": {"main.py": revised}})])
        def ask(*a, **kw):
            calls.append(kw["model"])
            return next(replies)
        with patch.object(self.chat, "_launch", side_effect=self.direct), \
             patch.object(revisions, "load_project",
                          side_effect=lambda name: loader(name, workspace=self.workspace)), \
             patch.object(chat.engine_manager, "probe",
                          return_value={"online": True, "models": ("qwen2.5-coder:7b",)}), \
             patch.object(chat.engine_manager, "saved_chat_model", return_value="qwen3:4b"), \
             patch.object(chat.engine_manager, "saved_coding_model",
                          return_value="qwen2.5-coder:7b"), \
             patch.dict(sys.modules, {"agent": types.SimpleNamespace(ask_ollama=ask)}):
            self.chat.dispatch("/project agent lostfalcon_agent " + goal)
        self.assertEqual(len(calls), 3)
        self.assertEqual(calls, ["qwen2.5-coder:7b"] * 3)
        self.assertEqual(self.chat.pending["mode"], "edit")
        self.assertFalse(self.chat.pending["reviewed"])
        self.assertIn("Architect", self.app.messages[-1][1])
        self.assertEqual((self.workspace / "lostfalcon_agent/main.py").read_text(),
                         self.project["files"]["main.py"])
        self.chat.dispatch("/project approve")
        self.assertIn("Review", self.app.messages[-1][1])
        self.chat.dispatch("/project diff")
        self.assertTrue(self.chat.pending["reviewed"])
        original = revisions.save_revision_approved
        with patch.object(revisions, "save_revision_approved",
                          side_effect=lambda base, plan, fingerprint:
                          original(base, plan, fingerprint, workspace=self.workspace)):
            self.chat.dispatch("/project approve")
        self.assertEqual((self.workspace / "lostfalcon_agent/main.py").read_text(), revised)
        self.assertEqual((self.workspace / "lostfalcon_agent/helper.py").read_text(),
                         self.project["files"]["helper.py"])

    def test_gaming_mode_denies_generation_but_not_project_map(self):
        with patch.object(chat.gaming_mode, "enabled", return_value=True), \
             patch.object(self.chat, "_agent_edit",
                          side_effect=AssertionError("never generate")):
            self.chat.dispatch("/project agent lostfalcon_agent change the greeting safely")
        self.assertIn("Gaming Mode", self.app.messages[-1][1])

    def test_pending_source_not_clobbered(self):
        self.chat.pending = {"mode": "edit", "plan": self.project}
        with patch.object(self.chat, "_launch", side_effect=AssertionError("no model")):
            self.chat.dispatch("/project agent lostfalcon_agent change the greeting safely")
        self.assertIn("pending source proposal", self.app.messages[-1][1])


if __name__ == "__main__":
    unittest.main()
