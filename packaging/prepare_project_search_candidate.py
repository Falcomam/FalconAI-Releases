"""Add read-only project source search to Falcon's current unified chat.

This is post-v13.9.0 development staging. It doesn't alter the published 13.9
release, produce an installer, or request new PC permissions.
"""
from pathlib import Path
import shutil

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "build" / "Falcon_Ai_NextBundle_Candidate"
TARGET = REPO / "build" / "Falcon_Ai_ProjectSearch_Candidate"
if (SOURCE / "RELEASE_VERSION.txt").read_text(encoding="utf-8").strip() != "13.9.0":
    raise RuntimeError("Expected verified Falcon 13.9.0 source baseline")
if TARGET.exists():
    shutil.rmtree(TARGET)
shutil.copytree(SOURCE, TARGET, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".venv"))
shutil.copy2(REPO / "packaging" / "project_search.py", TARGET / "project_search.py")


def patch(path, old, new):
    file = TARGET / path
    source = file.read_text(encoding="utf-8")
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"Project search integration anchor changed in {path} ({count}): {old[:75]!r}")
    file.write_text(source.replace(old, new, 1), encoding="utf-8")


patch("developer_chat.py",
      "import project_browser as browser\n",
      "import project_browser as browser\nimport project_search as project_search\n")
patch("developer_chat.py",
      '    "/project list  •  /project open <saved_name>\\n"\n',
      '    "/project list  •  /project open <saved_name>\\n"\n'
      '    "/project search <text>  •  search opened saved project only\\n"\n')
patch("developer_chat.py",
      '        if rest.lower().startswith("open "):\n',
      '''        if rest.lower().startswith("search "):
            return "project_search", rest[7:].strip()
        if rest.lower().startswith("open "):
''')
patch("developer_chat.py",
      '''        elif action == "project_open":
            self._open_saved(payload)
''',
      '''        elif action == "project_open":
            self._open_saved(payload)
        elif action == "project_search":
            self._search_saved(payload)
''')
patch("developer_chat.py",
      '''    def _edit(self, name, goal):
''',
      '''    def _search_saved(self, phrase):
        if self.app.busy or self._running:
            self.say("Finish or STOP the current task before searching saved code.")
            return
        if self.pending:
            self.say("Review, approve or reject the pending source proposal first.")
            return
        if not self.opened:
            self.say("Open a saved developer project with /project open <name> first.")
            return
        try:
            result = project_search.find_source(
                self.opened["name"], phrase, self.opened["fingerprint"])
        except (OSError, projects.ProjectError) as exc:
            self.say("Project search blocked: " + str(exc)[:260])
            return
        if not result["matches"]:
            self.say("No saved source matches for " + result["query"] +
                     ". Nothing was executed or modified.")
            return
        lines = [
            "- " + item["path"] + ":" + str(item["line"]) + "  " + item["excerpt"]
            for item in result["matches"]
        ]
        self.say("READ-ONLY PROJECT SEARCH: " + result["name"] +
                 "\\nPhrase: " + result["query"] +
                 "\\n" + "\\n".join(lines) +
                 ("\\n[Results limited. Refine search to see more.]"
                  if result["limited"] else "") +
                 "\\nNo project files were changed or executed.")

    def _edit(self, name, goal):
''')
patch("command_palette.py",
      '        Command("Open saved project", "/project open "),\n',
      '        Command("Open saved project", "/project open "),\n'
      '        Command("Search saved project source", "/project search "),\n')
(TARGET / "POST_139_PROJECT_SEARCH_DEV_ONLY.txt").write_text(
    "Read-only source search candidate based on published v13.9.0 source. "
    "NOT a new installer, not verified on user's PC, and not released.\n",
    encoding="utf-8",
)
print("Staged Falcon v13.9 post-release project source search candidate")
