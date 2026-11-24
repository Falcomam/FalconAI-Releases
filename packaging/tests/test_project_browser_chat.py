"""Falcon's real staged main chat can navigate saved projects without executing them."""
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str((ROOT / "build/Falcon_Ai_Browser_Candidate").resolve()))
import developer_workspace as dev
import developer_chat as chat
import project_browser as browser

REAL_LIST = browser.list_saved_projects
REAL_OPEN = browser.open_saved_project
REAL_SHOW = browser.show_saved_file


class App:
    def __init__(self):
        self.root = types.SimpleNamespace(after=lambda _, f: f())
        self.busy = False
        self.messages = []
        self.status = None

    def append(self, role, body):
        self.messages.append((role, body))

    def set_status(self, status):
        self.status = status


class ChatProjectBrowserTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.workspace = Path(self.tmp.name) / "saved"
        p = {"name": "falcon_project", "kind": "python",
             "files": {"main.py": "print('🦅')\n",
                       "README.md": "Falcon generated project\n"}}
        dev.save_approved(p, dev.review_proposal(p)["fingerprint"],
                          workspace=self.workspace)
        self.app = App()
        self.chat = chat.ChatFeatures(self.app)

    def routes(self):
        return [patch.object(browser, "list_saved_projects",
                             side_effect=lambda: REAL_LIST(workspace=self.workspace)),
                patch.object(browser, "open_saved_project",
                             side_effect=lambda name, **kwargs: REAL_OPEN(name,workspace=self.workspace)),
                patch.object(browser, "show_saved_file",
                             side_effect=lambda name,path,fp,**kwargs:
                             REAL_SHOW(name,path,fp,workspace=self.workspace))]

    def test_command_routing_and_catalog(self):
        self.assertEqual(chat.route("/project list"), ("project_list", ""))
        self.assertEqual(chat.route("/project open falcon_project"),
                         ("project_open", "falcon_project"))
        self.assertEqual(chat.route("/project open a b"), ("project_help", ""))
        self.assertEqual(chat.route("/project open"), ("project_help", ""))
        self.assertEqual(chat.route("/project show main.py"), ("project_show", "main.py"))
        with self.routes()[0]:
            self.assertTrue(self.chat.dispatch("/project list"))
        self.assertIn("falcon_project", self.app.messages[-1][1])
        self.assertIsNone(self.chat.opened)

    def test_open_and_show_saved_source_with_single_chat(self):
        a, b, c = self.routes()
        with a, b, c:
            self.chat.dispatch("/project open falcon_project")
            self.assertEqual(self.chat.opened["name"], "falcon_project")
            self.assertIn("Read-only", self.app.messages[-1][1])
            self.chat.dispatch("/project show main.py")
            self.assertIn("SAVED FILE: falcon_project/main.py", self.app.messages[-1][1])
            self.assertIn("nothing executed", self.app.messages[-1][1])
        self.assertNotIn("tkinter", Path(chat.__file__).read_text(encoding="utf-8"))

    def test_stale_disk_edits_refused(self):
        _, b, c = self.routes()
        with b, c:
            self.chat.dispatch("/project open falcon_project")
            (self.workspace / "falcon_project/README.md").write_text("I changed this\n")
            self.chat.dispatch("/project show main.py")
        self.assertIn("changed", self.app.messages[-1][1])
        self.assertEqual((self.workspace / "falcon_project/README.md").read_text(),
                         "I changed this\n")

    def test_proposal_conflict_is_not_clobbered(self):
        _, b, _ = self.routes()
        self.chat.pending = {"plan": {}, "review": {}, "reviewed": False}
        with b as mocked:
            self.chat.dispatch("/project open falcon_project")
        mocked.assert_not_called()
        self.assertIn("pending project", self.app.messages[-1][1])
        self.assertIsNone(self.chat.opened)

    def test_path_traversal_and_no_auto_approval(self):
        _, b, c = self.routes()
        with b, c:
            self.chat.dispatch("/project open falcon_project")
            self.chat.dispatch("/project show ../secrets.txt")
        self.assertIn("Cannot preview", self.app.messages[-1][1])
        self.assertIsNone(self.chat.pending)
        self.assertEqual((self.workspace / "falcon_project/main.py").read_text(encoding="utf-8"),
                         "print('🦅')\n")

    def test_reject_forgets_open_snapshot(self):
        _, b, _ = self.routes()
        with b:
            self.chat.dispatch("/project open falcon_project")
        self.chat.dispatch("/project reject")
        self.assertIsNone(self.chat.opened)
        self.assertIsNone(self.chat.pending)


if __name__ == "__main__":
    unittest.main()
