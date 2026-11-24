"""Exercise the staged focused-edit command through Falcon's actual one-chat controller.

Only mock Ollama and saved-project reads. No installs, source execution,
implicit approvals or real project mutations.
"""
import json
from pathlib import Path
import sys
import tempfile
import threading
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str((ROOT / "build/Falcon_Ai_Browser_Candidate").resolve()))
import developer_chat as chat
import developer_workspace as projects
import project_revision as revisions


class FakeApp:
    def __init__(self):
        self.root = types.SimpleNamespace(after=lambda _, fn: fn())
        self.messages = []
        self.busy = False
        self.status = ""

    def append(self, name, text):
        self.messages.append((name, text))

    def set_status(self, text):
        self.status = text


class TargetedChatTests(unittest.TestCase):
    def setUp(self):
        self.app = FakeApp()
        self.chat = chat.ChatFeatures(self.app)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.workspace = Path(self.tmp.name) / "projects"
        self.plan = {
            "name": "falcon_target", "kind": "python",
            "files": {
                "main.py": "from helpers import answer\nprint(answer())\n",
                "helpers.py": "def answer():\n    return 1\n",
                "README.md": "# Demo\n",
            },
        }
        fp = projects.review_proposal(self.plan)["fingerprint"]
        projects.save_approved(self.plan, fp, workspace=self.workspace)

    def instant(self, label, function, complete):
        output = function(threading.Event())
        complete(output)

    def test_routing_keeps_normal_edit_available(self):
        self.assertEqual(chat.route("/project edit-small falcon_target update helpers.py"),
                         ("project_edit_small", ("falcon_target", "update helpers.py")))
        self.assertEqual(chat.route("/project edit falcon_target update helpers.py"),
                         ("project_edit", ("falcon_target", "update helpers.py")))

    def test_targeted_proposal_requires_existing_review_and_approval(self):
        def model_reply(*args, **kwargs):
            return json.dumps({"changes": {"helpers.py":
                "def answer():\n    return 5\n"}})
        local_agent = types.SimpleNamespace(ask_ollama=model_reply)
        original_loader = revisions.load_project
        def load(name):
            return original_loader(name, workspace=self.workspace)
        with patch.object(self.chat, "_launch", side_effect=self.instant), \
             patch.object(revisions, "load_project", side_effect=load), \
             patch.object(chat.engine_manager, "probe",
                          return_value={"online": True, "models": ("qwen3:4b",)}), \
             patch.object(chat.engine_manager, "saved_coding_model",
                          return_value="qwen3:4b"), \
             patch.object(chat.engine_manager, "saved_chat_model",
                          return_value="qwen3:4b"), \
             patch.dict(sys.modules, {"agent": local_agent}):
            self.chat.dispatch("/project edit-small falcon_target update helpers.py to return 5")
        self.assertEqual(self.chat.pending["mode"], "edit")
        self.assertEqual(self.chat.pending["revision"]["changed"], ("helpers.py",))
        self.assertFalse(self.chat.pending["reviewed"])
        self.chat.dispatch("/project approve")
        self.assertIn("Review", self.app.messages[-1][1])
        self.assertEqual((self.workspace/"falcon_target"/"helpers.py").read_text(),
                         "def answer():\n    return 1\n")
        self.chat.dispatch("/project diff")
        self.assertTrue(self.chat.pending["reviewed"])
        self.assertIn("+    return 5", self.app.messages[-1][1])
        self.assertEqual((self.workspace/"falcon_target"/"main.py").read_text(),
                         self.plan["files"]["main.py"])
        # No file is overwritten until a real approve command is dispatched.
        real_save = revisions.save_revision_approved
        saved = []
        def save(base, plan, digest):
            outcome = real_save(base, plan, digest, workspace=self.workspace)
            saved.append(outcome)
            return outcome
        with patch.object(revisions, "save_revision_approved", side_effect=save):
            self.chat.dispatch("/project approve")
        self.assertEqual(len(saved), 1)
        self.assertIsNone(self.chat.pending)
        self.assertEqual((self.workspace/"falcon_target"/"helpers.py").read_text(),
                         "def answer():\n    return 5\n")
        self.assertEqual((self.workspace/"falcon_target"/"main.py").read_text(),
                         self.plan["files"]["main.py"])
        real_rollback = revisions.rollback_revision
        with patch.object(revisions, "rollback_revision",
                          side_effect=lambda name, backup_id:
                          real_rollback(name, backup_id, workspace=self.workspace)):
            self.chat.dispatch("/project rollback falcon_target " + saved[0]["backup_id"])
        self.assertEqual((self.workspace/"falcon_target"/"helpers.py").read_text(),
                         "def answer():\n    return 1\n")

    def test_oversized_revision_diff_does_not_unlock_approval(self):
        snapshot = {"plan": self.plan,
                    "fingerprint": revisions._snapshot_fingerprint(self.plan)}
        replacement = {
            "name": self.plan["name"], "kind": "python",
            "files": dict(self.plan["files"]),
        }
        replacement["files"]["helpers.py"] = "huge = '" + "Z" * 28000 + "'\n"
        revision = revisions.review_revision(snapshot, replacement)
        self.chat.pending = {
            "mode": "edit", "plan": replacement, "base": snapshot,
            "review": projects.review_proposal(replacement),
            "revision": revision, "reviewed": False,
        }
        self.chat.dispatch("/project diff")
        self.assertFalse(self.chat.pending["reviewed"])
        self.assertIn("Approval BLOCKED", self.app.messages[-1][1])
        with patch.object(revisions, "save_revision_approved",
                          side_effect=AssertionError("unreviewed save forbidden")):
            self.chat.dispatch("/project approve")
        self.assertIn("Review the proposed files first", self.app.messages[-1][1])
        self.assertEqual((self.workspace/"falcon_target"/"helpers.py").read_text(),
                         "def answer():\n    return 1\n")

    def test_missing_model_prevents_write(self):
        initial = (self.workspace/"falcon_target"/"helpers.py").read_bytes()
        original_loader = revisions.load_project
        def load(name):
            return original_loader(name, workspace=self.workspace)
        with patch.object(self.chat, "_launch",
                          side_effect=lambda label, function, complete:
                          self.assertRaises(RuntimeError, function, threading.Event())), \
             patch.object(revisions, "load_project", side_effect=load), \
             patch.object(chat.engine_manager, "probe",
                          return_value={"online": False, "models": ()}):
            self.chat.dispatch("/project edit-small falcon_target update helpers.py to return 5")
        self.assertIsNone(self.chat.pending)
        self.assertEqual((self.workspace/"falcon_target"/"helpers.py").read_bytes(), initial)


if __name__ == "__main__":
    unittest.main()
