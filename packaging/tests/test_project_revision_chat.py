"""Acceptance tests for project editing through the real staged Falcon chat module."""
import json
from pathlib import Path
import sys
import tempfile
import threading
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str((ROOT / "build/Falcon_Ai_Revision_Candidate").resolve()))
import developer_workspace as workspace
import developer_chat as chat
import project_revision as edits


class FakeApp:
    def __init__(self):
        self.root = types.SimpleNamespace(after=lambda _, callback: callback())
        self.busy = False
        self.messages = []
        self.status = None
    def append(self, author, message):
        self.messages.append((author, message))
    def set_status(self, message):
        self.status = message


class InChatRevisionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "projects"
        p = {"name": "falcon_site", "kind": "website",
             "files": {
                 "index.html": ('<!doctype html><html><head><meta charset="UTF-8">'
                                '<title>LostFalcon</title></head><body><h1>Old</h1>'
                                '</body></html>'),
                 "README.md": "LostFalcon static website\n",
             }}
        workspace.save_approved(p, workspace.review_proposal(p)["fingerprint"],
                                workspace=self.root)
        self.base = p
        self.new = {"name": "falcon_site", "kind": "website",
                    "files": dict(p["files"])}
        self.new["files"]["index.html"] = p["files"]["index.html"].replace("Old", "New")
        self.app = FakeApp()
        self.chat = chat.ChatFeatures(self.app)

    def generation_context(self, output):
        def immediate(label, work, done):
            done(work(threading.Event()))
        return (
            patch.object(edits, "load_project",
                side_effect=lambda name: _load_actual(name, self.root)),
            patch.object(chat.engine_manager, "probe",
                return_value={"online": True, "models": ("qwen3:4b",)}),
            patch.object(chat.engine_manager, "saved_chat_model",
                return_value="qwen3:4b"),
            patch.object(self.chat, "_launch", side_effect=immediate),
            patch.dict(sys.modules,
                       {"agent": types.SimpleNamespace(
                           ask_ollama=lambda *args, **kwargs: json.dumps(output))}),
        )

    def test_edit_review_approval_and_explicit_rollback(self):
        self.assertEqual(chat.route("/project edit falcon_site make it purple"),
                         ("project_edit", ("falcon_site", "make it purple")))
        controls = self.generation_context(self.new)
        with controls[0], controls[1], controls[2], controls[3], controls[4]:
            self.chat.dispatch("/project edit falcon_site update homepage text")
        self.assertEqual(self.chat.pending["mode"], "edit")
        saved = self.root / "falcon_site/index.html"
        self.assertIn("Old", saved.read_text())
        self.chat.dispatch("/project approve")
        self.assertIn("Review the proposed files first", self.app.messages[-1][1])
        self.chat.dispatch("/project diff")
        self.assertIn("-<!doctype html>", self.app.messages[-1][1])
        self.assertIn("+<!doctype html>", self.app.messages[-1][1])
        with patch.object(edits, "save_revision_approved",
                          side_effect=lambda base, plan, fp:
                          _save_actual(base, plan, fp, self.root)):
            self.chat.dispatch("/project approve")
        self.assertIsNone(self.chat.pending)
        self.assertIn("New", saved.read_text())
        result = self.app.messages[-1][1]
        self.assertIn("Backup ID:", result)
        backup_id = result.split("Backup ID: ")[1].splitlines()[0]
        with patch.object(edits, "rollback_revision",
                          side_effect=lambda name, backup:
                          _restore_actual(name, backup, self.root)):
            self.chat.dispatch("/project rollback falcon_site " + backup_id)
        self.assertIn("Old", saved.read_text())
        self.assertIn("No generated code was executed.", self.app.messages[-1][1])

    def test_edit_rejects_changed_original_files(self):
        controls = self.generation_context(self.new)
        with controls[0], controls[1], controls[2], controls[3], controls[4]:
            self.chat.dispatch("/project edit falcon_site update homepage text")
        self.chat.dispatch("/project diff")
        (self.root / "falcon_site/README.md").write_text("User wrote their own changes\n")
        with patch.object(edits, "save_revision_approved",
                          side_effect=lambda base, plan, fp:
                          _save_actual(base, plan, fp, self.root)):
            self.chat.dispatch("/project approve")
        self.assertIn("Saving edit blocked", self.app.messages[-1][1])
        self.assertIn("Old", (self.root / "falcon_site/index.html").read_text())

    def test_review_reject_does_not_modify_project(self):
        controls = self.generation_context(self.new)
        with controls[0], controls[1], controls[2], controls[3], controls[4]:
            self.chat.dispatch("/project edit falcon_site update homepage text")
        self.chat.dispatch("/project diff")
        self.chat.dispatch("/project reject")
        self.assertIsNone(self.chat.pending)
        self.assertIn("Old", (self.root / "falcon_site/index.html").read_text())

    def test_edit_and_diff_are_inline_no_windows(self):
        self.assertEqual(chat.route("/project diff"), ("project_diff", ""))
        self.assertEqual(chat.route("/project rollback falcon_site abcdef"),
                         ("project_rollback", ("falcon_site", "abcdef")))
        self.assertEqual(chat.route("/project edit falcon_site x"), ("project_help", ""))
        self.assertNotIn("tkinter", Path(chat.__file__).read_text(encoding="utf-8"))
        self.chat.dispatch("/project diff")
        self.assertIn("No pending edit", self.app.messages[-1][1])


def _load_actual(name, root):
    original = edits.load_project
    # Calling original via mock would recurse; source implementation is
    # accessed by temporarily exiting the targeted patch in generation_context.
    return _REAL_LOAD(name, workspace=root)


_REAL_LOAD = edits.load_project


def _save_actual(base, plan, fp, root):
    return _REAL_SAVE(base, plan, fp, workspace=root)


_REAL_SAVE = edits.save_revision_approved


def _restore_actual(name, backup, root):
    return _REAL_ROLLBACK(name, backup, workspace=root)


_REAL_ROLLBACK = edits.rollback_revision


if __name__ == "__main__":
    unittest.main()
