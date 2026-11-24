"""Stage in-chat saved project browser into next Falcon combined candidate.

Requires the tested revision candidate. Nothing is installed or released.
"""
from pathlib import Path
import shutil

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "build" / "Falcon_Ai_Revision_Candidate"
TARGET = REPO / "build" / "Falcon_Ai_Browser_Candidate"
if (SOURCE / "RELEASE_VERSION.txt").read_text(encoding="utf-8").strip() != "13.8.0":
    raise SystemExit("Expected the existing Falcon V13.8.0 revision-stage source")
if TARGET.exists():
    shutil.rmtree(TARGET)
shutil.copytree(SOURCE, TARGET, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".venv"))
shutil.copy2(REPO / "packaging" / "project_browser.py", TARGET / "project_browser.py")


def change_once(path, old, new):
    file = TARGET / path
    data = file.read_text(encoding="utf-8")
    occurrences = data.count(old)
    if occurrences != 1:
        raise RuntimeError(f"Falcon source integration anchor changed for {path} ({occurrences}): {old[:100]!r}")
    file.write_text(data.replace(old, new, 1), encoding="utf-8")


change_once("developer_chat.py", "import project_revision as revisions\n",
            "import project_revision as revisions\nimport project_browser as browser\n")
change_once("developer_chat.py",
            '    "/project rollback <saved_name> <backup_id>\\n"\n',
            '    "/project rollback <saved_name> <backup_id>\\n"\n'
            '    "/project list  •  /project open <saved_name>\\n"\n')
change_once("developer_chat.py",
            '''        if rest.casefold() in ("review", "approve", "reject", "diff"):
''',
            '''        if rest.casefold() == "list":
            return "project_list", ""
        if rest.lower().startswith("open "):
            args = rest.split()
            if len(args) == 2:
                return "project_open", args[1]
            return "project_help", ""
        if rest.casefold() in ("review", "approve", "reject", "diff"):
''')
change_once("developer_chat.py",
            '''        self.app = app
        self.pending = None
''',
            '''        self.app = app
        self.pending = None
        self.opened = None  # read-only saved project snapshot; not an approval
''')
change_once("developer_chat.py",
            '''        elif action == "project_edit":
            self._edit(*payload)
''',
            '''        elif action == "project_edit":
            self._edit(*payload)
        elif action == "project_list":
            self._list_saved()
        elif action == "project_open":
            self._open_saved(payload)
''')
change_once("developer_chat.py",
            '''    def _edit(self, name, goal):
''',
            '''    def _list_saved(self):
        try:
            names = browser.list_saved_projects()
        except (OSError, projects.ProjectError) as exc:
            self.say("Cannot list saved projects: " + str(exc)[:260])
            return
        if not names:
            self.say("No saved Falcon developer projects found. "
                     "Create one with /project website <goal> or /project python <goal>.")
            return
        self.say("Saved Falcon developer projects (read-only list):\\n" +
                 "\\n".join("- " + name for name in names) +
                 "\\nType /project open <name> to inspect its source files.")

    def _open_saved(self, name):
        if self.app.busy or self._running:
            self.say("Finish or STOP the current task before opening a project.")
            return
        if self.pending:
            self.say("Review, approve, or reject the pending project before opening another.")
            return
        try:
            snapshot = browser.open_saved_project(name)
        except (OSError, projects.ProjectError) as exc:
            self.opened = None
            self.say("Cannot open saved project: " + str(exc)[:260])
            return
        self.opened = {"name": name, "fingerprint": snapshot["fingerprint"]}
        plan = snapshot["plan"]
        self.say("OPEN SAVED PROJECT: " + plan["name"] +
                 "\\nType: " + plan["kind"] +
                 "\\nFiles:\\n" + "\\n".join("- " + f for f in plan["files"]) +
                 "\\nRead-only snapshot; nothing was executed or changed." +
                 "\\nUse /project show <file> to view source, or /project edit " +
                 name + " <request> to propose changes.")

    def _edit(self, name, goal):
''')
change_once("developer_chat.py",
            '''    def _show(self, path):
        if not self.pending:
            self.say("No proposal is pending. Type /project <type> <goal> first.")
            return
''',
            '''    def _show(self, path):
        if not self.pending:
            if not self.opened:
                self.say("No proposal or saved project is open. Type /project list "
                         "and /project open <name>.")
                return
            try:
                preview = browser.show_saved_file(
                    self.opened["name"], path, self.opened["fingerprint"])
            except (OSError, projects.ProjectError) as exc:
                self.say("Cannot preview saved file: " + str(exc)[:270])
                return
            self.say("SAVED FILE: " + preview["name"] + "/" + preview["path"] +
                     "\\n" + preview["text"] +
                     ("\\n[Source preview shortened; no file changed.]"
                      if preview["truncated"] else "") +
                     "\\nSource-only read, nothing executed.")
            return
''')
change_once("developer_chat.py",
            '''        elif action == "project_reject":
            self.pending = None
''',
            '''        elif action == "project_reject":
            self.pending = None
            self.opened = None
''')
change_once("developer_chat.py",
            '''    def _rollback(self, name, backup_id):
        if self.app.busy or self._running:
''',
            '''    def _rollback(self, name, backup_id):
        if self.app.busy or self._running:
''')
# On success of rollback or approved save, invalidate any in-chat snapshot.
change_once("developer_chat.py",
            '''        self.pending = None
        self.say("Restored original source files for " + name +
''',
            '''        self.pending = None
        self.opened = None
        self.say("Restored original source files for " + name +
''')
change_once("developer_chat.py",
            '''            self.pending = None
            self.say("Saved reviewed changes to " + result["project"] +
''',
            '''            self.pending = None
            self.opened = None
            self.say("Saved reviewed changes to " + result["project"] +
''')
change_once("command_palette.py",
            '        Command("Edit existing saved project", "/project edit "),\n',
            '''        Command("List saved projects", "/project list"),
        Command("Open saved project", "/project open "),
        Command("Edit existing saved project", "/project edit "),
''')
(TARGET / "BROWSER_CANDIDATE_ONLY.txt").write_text(
    "Read-only saved-project list/open/show through same Falcon chat. "
    "No install, no extra window, no PC execution, no release.\n",
    encoding="utf-8",
)
print("Prepared Falcon saved project catalog and single-chat open/preview candidate")
