"""Stage no-approval local website preview on the existing V14 coding-agent candidate.

Developer-only staging: not an installed release or standalone installer.
"""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "build" / "Falcon_Ai_CodingAgent_Candidate"
TARGET = ROOT / "build" / "Falcon_Ai_WebsitePreview_Candidate"
if (SOURCE / "RELEASE_VERSION.txt").read_text(encoding="utf-8").strip() != "14.0.0":
    raise RuntimeError("Expected staged Falcon V14 coding-agent candidate")
if TARGET.exists():
    shutil.rmtree(TARGET)
shutil.copytree(SOURCE, TARGET, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".venv"))
shutil.copy2(ROOT / "packaging" / "website_preview.py", TARGET / "website_preview.py")


def patch(path, old, new):
    file = TARGET / path
    data = file.read_text(encoding="utf-8")
    if data.count(old) != 1:
        raise RuntimeError("Preview integration anchor mismatch: " + path + " " + repr(old[:100]))
    file.write_text(data.replace(old, new, 1), encoding="utf-8")


patch("developer_chat.py",
      "import project_coding_agent as coding_agent\n",
      "import project_coding_agent as coding_agent\nimport website_preview\n")
patch("developer_chat.py",
      '    "/project architect <website|python|fabric_mod> <goal>\\n"\n',
      '    "/project architect <website|python|fabric_mod> <goal>\\n"\n'
      '    "/project preview <saved_website_name>  (no extra approval)\\n"\n')
patch("developer_chat.py",
      '        if rest.lower().startswith("architect "):\n',
      '''        if rest.lower().startswith("preview "):
            args = rest.split()
            if len(args) == 2:
                return "project_preview", args[1]
            return "project_help", ""
        if rest.lower().startswith("architect "):
''')
patch("developer_chat.py",
      '''        elif action == "project_architect":
            self._architect_new(*payload)
''',
      '''        elif action == "project_architect":
            self._architect_new(*payload)
        elif action == "project_preview":
            self._preview_saved_website(payload)
''')
patch("developer_chat.py",
      "    def _map_saved(self, name):\n",
      '''    def _preview_saved_website(self, name):
        # Opening an already-reviewed local HTML entry page is a permitted
        # preview operation; saving/editing/executing code still needs approval.
        if self.app.busy or self._running:
            self.say("Finish or STOP the current task before previewing the website.")
            return
        try:
            website_preview.open_website(name)
        except (OSError, projects.ProjectError) as exc:
            self.say("Cannot preview website: " + str(exc)[:250])
            return
        self.say("Opened saved website preview in your default browser: " + name +
                 "/index.html. No project files changed. Browser HTML/JS may run "
                 "under your browser's local-file policy.")

    def _map_saved(self, name):
''')
patch("command_palette.py",
      '        Command("Architect-first new project", "/project architect "),\n',
      '        Command("Architect-first new project", "/project architect "),\n'
      '        Command("Preview saved website in browser", "/project preview "),\n')
(TARGET / "PREVIEW_DEVELOPMENT_ONLY.txt").write_text(
    "No-approval browser preview for approved website projects only. "
    "This source candidate is not installed or published.\n", encoding="utf-8")
print("Staged opt-in Falcon website preview command.")
