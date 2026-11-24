"""Integration checks for project-search commands in Falcon's one main chat."""
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str((REPO / "build/Falcon_Ai_ProjectSearch_Candidate").resolve()))
import developer_workspace as workspace
import developer_chat as chat
import project_browser as browser
import project_search as search

_REAL_OPEN = browser.open_saved_project
_REAL_SEARCH = search.find_source


class FakeApp:
    def __init__(self):
        self.root = types.SimpleNamespace(after=lambda _, cb: cb())
        self.busy = False
        self.messages = []
        self.status = "Ready"
    def append(self, role, text):
        self.messages.append((role, text))
    def set_status(self, value):
        self.status = value


class ChatProjectSearchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name) / "saved"
        p = {"name": "falcon_site", "kind": "python",
             "files": {"main.py": "print('Falcon ready')\n# FALCON TODO\n",
                       "README.md": "Falcon search sample\n"}}
        workspace.save_approved(p, workspace.review_proposal(p)["fingerprint"],
                                workspace=self.base)
        self.app = FakeApp()
        self.chat = chat.ChatFeatures(self.app)

    def access(self):
        return (patch.object(browser, "open_saved_project",
                             side_effect=lambda name, **kwargs: _REAL_OPEN(
                                 name, workspace=self.base)),
                patch.object(search, "find_source",
                             side_effect=lambda name, needle, fingerprint:
                             _REAL_SEARCH(name, needle, fingerprint,
                                          workspace=self.base)))

    def test_find_requires_explicit_open_and_never_executes(self):
        self.assertEqual(chat.route("/project search Falcon"),
                         ("project_search", "Falcon"))
        self.chat.dispatch("/project search Falcon")
        self.assertIn("Open a saved developer project", self.app.messages[-1][1])
        a, b = self.access()
        with a, b:
            self.chat.dispatch("/project open falcon_site")
            self.chat.dispatch("/project search Falcon")
        message = self.app.messages[-1][1]
        self.assertIn("READ-ONLY PROJECT SEARCH", message)
        self.assertIn("main.py:1", message)
        self.assertIn("README.md:1", message)
        self.assertIn("No project files were changed or executed", message)
        self.assertIsNone(self.chat.pending)

    def test_refuses_stale_opened_project(self):
        a, b = self.access()
        with a, b:
            self.chat.dispatch("/project open falcon_site")
            (self.base / "falcon_site/main.py").write_text("print('edited')\n")
            self.chat.dispatch("/project search Falcon")
        self.assertIn("changed", self.app.messages[-1][1])

    def test_pending_approval_is_not_replaced_by_search(self):
        a, b = self.access()
        with a, b:
            self.chat.dispatch("/project open falcon_site")
            self.chat.pending = {"plan": {}, "reviewed": False}
            self.chat.dispatch("/project search Falcon")
        self.assertIn("pending source proposal", self.app.messages[-1][1])
        self.assertEqual(self.chat.pending["reviewed"], False)

    def test_single_chat_and_command_dropdown(self):
        self.assertNotIn("tkinter", Path(chat.__file__).read_text(encoding="utf-8"))
        palette = (REPO / "build/Falcon_Ai_ProjectSearch_Candidate"
                   / "command_palette.py").read_text(encoding="utf-8")
        self.assertIn('"/project search "', palette)


if __name__ == "__main__":
    unittest.main()
