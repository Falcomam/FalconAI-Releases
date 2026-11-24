"""Single chat developer mode: routing, approvals and model-switch tests."""
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import developer_chat as dev
import developer_workspace as workspace


class FakeRoot:
    def after(self, delay, callback):
        callback()


class FakeApp:
    def __init__(self):
        self.root = FakeRoot()
        self.messages = []
        self.busy = False
        self.status = ""
    def append(self, name, text):
        self.messages.append((name, text))
    def set_status(self, text):
        self.status = text


def project():
    return {"name": "falcon_test", "kind": "python",
            "files": {"main.py": "print('hello')\n", "README.md": "Test sample\n"}}


class DeveloperChatTests(unittest.TestCase):
    def setUp(self):
        self.app = FakeApp()
        self.chat = dev.ChatFeatures(self.app)

    def test_one_window_commands(self):
        self.assertEqual(dev.route("/engine list"), ("engine", "list"))
        self.assertEqual(dev.route("/engine use-code qwen2.5-coder:7b"),
                         ("engine", "use-code qwen2.5-coder:7b"))
        self.assertEqual(dev.route("/project review"), ("project_review", ""))
        self.assertEqual(dev.route("/project check"), ("project_check", ""))
        self.assertEqual(dev.route("/project approve"), ("project_approve", ""))
        self.assertEqual(dev.route("/project reject"), ("project_reject", ""))
        self.assertEqual(dev.route("/project show src/main.py"), ("project_show", "src/main.py"))
        self.assertEqual(dev.route("/project website build a homepage"),
                         ("project_new", ("website", "build a homepage")))
        self.assertEqual(dev.route("Make me a website for my channel"),
                         ("project_new", ("website", "Make me a website for my channel")))
        self.assertEqual(dev.route("Create a Minecraft Fabric mod that adds falcons"),
                         ("project_new", ("fabric_mod", "Create a Minecraft Fabric mod that adds falcons")))
        self.assertIsNone(dev.route("How do I make a website?"))
        self.assertIsNone(dev.route("Tell me a joke"))
        self.assertNotIn("tkinter", Path(dev.__file__).read_text(encoding="utf-8"))
        self.assertNotIn("Toplevel", Path(dev.__file__).read_text(encoding="utf-8"))

    def test_unmatched_leaves_original_chat_in_charge(self):
        self.assertFalse(self.chat.dispatch("what is the weather"))
        self.assertTrue(self.chat.dispatch("/project"))
        self.assertIn("Developer Mode", self.app.messages[-1][1])

    def test_generation_rejects_empty_request(self):
        self.assertTrue(self.chat.dispatch("/project python hi"))
        self.assertIn("Describe the project", self.app.messages[-1][1])
        self.assertIsNone(self.chat.pending)

    def test_clipped_project_review_never_allows_approval(self):
        p = project()
        p["files"]["main.py"] = "value = '" + "A" * 7000 + "'\n"
        review = workspace.review_proposal(p)
        self.chat.pending = {"plan": p, "review": review, "reviewed": False}
        self.chat.dispatch("/project review")
        self.assertFalse(self.chat.pending["reviewed"])
        self.assertIn("Approval is BLOCKED", self.app.messages[-1][1])
        with patch.object(workspace, "save_approved",
                          side_effect=AssertionError("no file writes")):
            self.chat.dispatch("/project approve")
        self.assertIn("Review the proposed files first", self.app.messages[-1][1])

    def test_static_check_does_not_grant_review_or_execute(self):
        p = project()
        info = workspace.review_proposal(p)
        self.chat.pending = {"plan": p, "review": info, "reviewed": False}
        with patch.object(workspace, "save_approved",
                          side_effect=AssertionError("no writes")):
            self.assertTrue(self.chat.dispatch("/project check"))
        self.assertIn("PROJECT STATIC CHECK", self.app.messages[-1][1])
        self.assertIn("Executed tests: NONE", self.app.messages[-1][1])
        self.assertFalse(self.chat.pending["reviewed"])

    def test_static_check_saved_project_and_stale_snapshot(self):
        p = project()
        info = workspace.review_proposal(p)
        self.chat.opened = {"name": p["name"], "fingerprint": info["fingerprint"]}
        snapshot = {"plan": p, "fingerprint": info["fingerprint"]}
        fake_browser = types.SimpleNamespace(open_saved_project=lambda name: snapshot)
        with patch.dict(sys.modules, {"project_browser": fake_browser}):
            self.chat.dispatch("/project check")
            self.assertIn("PROJECT STATIC CHECK", self.app.messages[-1][1])
            snapshot["fingerprint"] = "0" * 64
            self.chat.dispatch("/project check")
            self.assertIn("Saved project changed", self.app.messages[-1][1])

    def test_static_check_rejects_mutated_proposal(self):
        p = project()
        info = workspace.review_proposal(p)
        self.chat.pending = {"plan": p, "review": info, "reviewed": False}
        p["files"]["main.py"] = "print('tampered')\n"
        self.chat.dispatch("/project check")
        self.assertIn("Static project check blocked", self.app.messages[-1][1])

    def test_preview_and_exact_approval_in_same_chat(self):
        p = project()
        review = workspace.review_proposal(p)
        self.chat.pending = {"plan": p, "review": review}
        self.assertTrue(self.chat.dispatch("/project review"))
        self.assertIn("main.py", self.app.messages[-1][1])
        self.assertIn("print('hello')", self.app.messages[-1][1])
        self.assertTrue(self.chat.dispatch("/project show main.py"))
        self.assertIn("print('hello')", self.app.messages[-1][1])
        with tempfile.TemporaryDirectory() as directory:
            real_save = workspace.save_approved
            def save(plan, digest):
                return real_save(plan, digest, workspace=Path(directory) / "projects")
            with patch.object(workspace, "save_approved", save):
                self.assertTrue(self.chat.dispatch("/project approve"))
                self.assertTrue((Path(directory) / "projects" / "falcon_test" / "main.py").exists())
        self.assertIsNone(self.chat.pending)
        self.assertIn("Nothing was executed", self.app.messages[-1][1])

    def test_stale_fingerprint_refused(self):
        p = project()
        review = workspace.review_proposal(p)
        self.chat.pending = {"plan": p, "review": review}
        self.chat.dispatch("/project review")
        p["files"]["main.py"] = "print('changed')\n"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "projects"
            real_save = workspace.save_approved
            with patch.object(workspace, "save_approved",
                              side_effect=lambda plan, digest: real_save(plan, digest, workspace=root)):
                self.chat.dispatch("/project approve")
            self.assertFalse(root.exists())
        self.assertIn("Saving blocked", self.app.messages[-1][1])

    def test_approval_requires_visible_review(self):
        p = project()
        self.chat.pending = {"plan": p, "review": workspace.review_proposal(p)}
        with patch.object(workspace, "save_approved") as save:
            self.chat.dispatch("/project approve")
            save.assert_not_called()
        self.assertIn("Review the proposed files first", self.app.messages[-1][1])
        self.chat.dispatch("/project review")
        self.assertTrue(self.chat.pending["reviewed"])

    def test_reject_does_not_write(self):
        self.chat.pending = {"plan": project(), "review": workspace.review_proposal(project())}
        self.assertTrue(self.chat.dispatch("/project reject"))
        self.assertIsNone(self.chat.pending)
        self.assertIn("No files were written", self.app.messages[-1][1])

    def test_generation_is_inert_until_explicit_approval(self):
        p = project()
        fake_agent = types.SimpleNamespace(ask_ollama=lambda *args, **kwargs: json.dumps(p))
        installed = {"online": True, "models": ("qwen3:4b",), "detail": "OK"}
        def instant(label, function, complete):
            complete(function(threading.Event()))
        with patch.object(self.chat, "_launch", side_effect=instant), \
             patch.object(dev.engine_manager, "probe", return_value=installed), \
             patch.object(dev.engine_manager, "saved_chat_model", return_value="qwen3:4b"), \
             patch.dict(sys.modules, {"agent": fake_agent}):
            self.chat.dispatch("/project python create a basic hello world demo")
        self.assertIsNotNone(self.chat.pending)
        self.assertIn("NOT saved", self.app.messages[-1][1])

    def test_model_selection_uses_installed_local_model(self):
        fake_falcon = types.SimpleNamespace(MODEL="qwen3:4b")
        installed = {"online": True, "models": ("qwen3:4b", "llama3.2:3b")}
        def instant(label, function, complete):
            complete(function(threading.Event()))
        with patch.object(self.chat, "_launch", side_effect=instant), \
             patch.object(dev.engine_manager, "probe", return_value=installed), \
             patch.object(dev.engine_manager, "save_chat_model", return_value="llama3.2:3b") as save, \
             patch.dict(sys.modules, {"falcon": fake_falcon}), \
             patch.dict(os.environ, {}, clear=False):
            self.chat.dispatch("/engine use llama3.2:3b")
            self.assertEqual(fake_falcon.MODEL, "llama3.2:3b")
            save.assert_called_once_with("llama3.2:3b", installed_models=installed["models"])
        self.assertIn("PC approval and STOP permissions", self.app.messages[-1][1])

    def test_failed_replacement_preserves_reviewed_draft(self):
        old = project()
        review = workspace.review_proposal(old)
        self.chat.pending = {"plan": old, "review": review, "reviewed": True}
        def fails(label, function, complete):
            with self.assertRaises(RuntimeError):
                function(threading.Event())
        with patch.object(self.chat, "_launch", side_effect=fails), \
             patch.object(dev.engine_manager, "probe",
                          return_value={"online": False, "models": ()}):
            self.chat.dispatch("/project python make a different Python utility")
        self.assertEqual(self.chat.pending["review"]["fingerprint"], review["fingerprint"])
        self.assertTrue(self.chat.pending["reviewed"])

    def test_reject_while_generating_prompts_to_stop(self):
        p = project()
        self.chat.pending = {"plan": p, "review": workspace.review_proposal(p)}
        self.chat._running = True
        self.chat.dispatch("/project reject")
        self.assertIsNotNone(self.chat.pending)
        self.assertIn("Press STOP", self.app.messages[-1][1])

    def test_concurrent_generation_cannot_discard_pending_review(self):
        p = project()
        info = workspace.review_proposal(p)
        self.chat.pending = {"plan": p, "review": info, "reviewed": True}
        self.chat._running = True
        self.app.busy = True
        self.chat.dispatch("/project python write a new simple program")
        self.assertEqual(self.chat.pending["review"]["fingerprint"], info["fingerprint"])
        self.assertIn("already working", self.app.messages[-1][1])

    def test_stop_frees_busy_state_and_ignores_stale_callbacks(self):
        token = threading.Event()
        self.chat._event = token
        self.chat._running = True
        self.app.busy = True
        serial_before = self.chat._serial
        self.chat.stop()
        self.assertTrue(token.is_set())
        self.assertFalse(self.chat._running)
        self.assertFalse(self.app.busy)
        self.assertIsNone(self.chat._event)
        self.assertIn("stopped", self.app.status.lower())
        self.assertGreater(self.chat._serial, serial_before)
        # Late completion from a cancelled generation cannot restore a draft.
        self.chat._finish(serial_before, lambda plan: setattr(
            self.chat, "pending", plan), {"unsafe": True})
        self.assertIsNone(self.chat.pending)

    def test_coding_model_is_independent_of_chat_model(self):
        installed = {"online": True, "models": ("qwen3:4b", "qwen2.5-coder:7b")}
        def instant(label, function, complete):
            complete(function(threading.Event()))
        with patch.object(self.chat, "_launch", side_effect=instant), \
             patch.object(dev.engine_manager, "probe", return_value=installed), \
             patch.object(dev.engine_manager, "save_coding_model",
                          return_value="qwen2.5-coder:7b") as save:
            self.chat.dispatch("/engine use-code qwen2.5-coder:7b")
            save.assert_called_once_with("qwen2.5-coder:7b",
                                         installed_models=installed["models"])
        self.assertIn("Chat model is unchanged", self.app.messages[-1][1])

    def test_project_generation_uses_dedicated_model_or_chat_fallback(self):
        p = project()
        selected = []
        def fake_ask(*args, **kwargs):
            selected.append(kwargs["model"])
            return json.dumps(p)
        fake_agent = types.SimpleNamespace(ask_ollama=fake_ask)
        def instant(label, function, complete):
            complete(function(threading.Event()))
        with patch.object(self.chat, "_launch", side_effect=instant), \
             patch.object(dev.engine_manager, "probe", return_value={
                 "online": True, "models": ("qwen3:4b", "qwen2.5-coder:7b")}), \
             patch.object(dev.engine_manager, "saved_chat_model",
                          return_value="qwen3:4b"), \
             patch.object(dev.engine_manager, "saved_coding_model",
                          return_value="qwen2.5-coder:7b"), \
             patch.dict(sys.modules, {"agent": fake_agent}):
            self.chat.dispatch("/project python make a sample Python application")
        self.assertEqual(selected, ["qwen2.5-coder:7b"])
        with patch.object(self.chat, "_launch", side_effect=instant), \
             patch.object(dev.engine_manager, "probe", return_value={
                 "online": True, "models": ("qwen3:4b",)}), \
             patch.object(dev.engine_manager, "saved_chat_model",
                          return_value="qwen3:4b"), \
             patch.object(dev.engine_manager, "saved_coding_model",
                          return_value="missing-coder:latest"), \
             patch.dict(sys.modules, {"agent": fake_agent}):
            self.chat.dispatch("/project python make a sample Python application")
        self.assertEqual(selected[-1], "qwen3:4b")

    def test_stop_cancels_active_work(self):
        token = threading.Event()
        self.chat._event = token
        self.chat._running = True
        self.chat.stop()
        self.assertTrue(token.is_set())
        self.assertFalse(self.chat._running)


if __name__ == "__main__":
    unittest.main()
