"""Stage Falcon's Aider/OpenCode-inspired, original project coding agent.

Development only. Builds on exact V14.0.0 source, preserves all existing
review, diff, explicit approval and rollback controls; does not publish,
install, execute proposed projects, access arbitrary user files or change GPU.
"""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "build" / "Falcon_Ai_V14_Candidate"
TARGET = ROOT / "build" / "Falcon_Ai_CodingAgent_Candidate"
BASE_RUNTIME = ROOT / "build" / "falcon_app_v14_runtime"
RUNTIME = ROOT / "build" / "falcon_app_coding_agent_runtime"

if (BASE / "RELEASE_VERSION.txt").read_text(encoding="utf-8").strip() != "14.0.0":
    raise RuntimeError("The verified Falcon V14.0.0 foundation is required")
for folder in (TARGET, RUNTIME):
    if folder.exists():
        shutil.rmtree(folder)
shutil.copytree(BASE, TARGET, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".venv"))
shutil.copytree(BASE_RUNTIME, RUNTIME,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".venv"))
shutil.copy2(ROOT / "packaging" / "project_coding_agent.py", TARGET / "project_coding_agent.py")


def patch(path, old, new):
    file = TARGET / path
    contents = file.read_text(encoding="utf-8")
    if contents.count(old) != 1:
        raise RuntimeError("Coding agent integration anchor mismatch: " + path
                           + " occurrences=" + str(contents.count(old)) + " anchor=" + repr(old[:130]))
    file.write_text(contents.replace(old, new, 1), encoding="utf-8")


patch("developer_chat.py",
      "import project_targeted_edits as targeted\n",
      "import project_targeted_edits as targeted\nimport project_coding_agent as coding_agent\n")

patch("developer_chat.py",
      '    "/project edit-small <saved_name> <request>\\n"\n',
      '    "/project edit-small <saved_name> <request>\\n"\n'
      '    "/project map <saved_name>  •  /project agent <saved_name> <goal>\\n"\n')

patch("developer_chat.py",
      '        if rest.lower().startswith("edit-small "):\n',
      '''        if rest.lower().startswith("map "):
            args = rest.split()
            if len(args) == 2:
                return "project_map", args[1]
            return "project_help", ""
        if rest.lower().startswith("agent "):
            args = rest.split(None, 2)
            if len(args) == 3 and 8 <= len(args[2].strip()) <= 1100:
                return "project_agent", (args[1], args[2].strip())
            return "project_help", ""
        if rest.lower().startswith("edit-small "):
''')

patch("developer_chat.py",
      '("project_new", "project_edit", "project_edit_small")',
      '("project_new", "project_edit", "project_edit_small", "project_agent")')

patch("developer_chat.py",
      '''        elif action == "project_edit_small":
            self._edit_small(*payload)
''',
      '''        elif action == "project_edit_small":
            self._edit_small(*payload)
        elif action == "project_map":
            self._map_saved(payload)
        elif action == "project_agent":
            self._agent_edit(*payload)
''')

patch("developer_chat.py",
      "    def _edit_small(self, name, goal):\n",
      '''    def _map_saved(self, name):
        if self._running or self.app.busy:
            self.say("Finish or STOP the current task before inspecting the map.")
            return
        try:
            base = revisions.load_project(name)
            text = coding_agent.repository_map(
                base, "Review this project's structure and available source files")
        except (OSError, projects.ProjectError) as exc:
            self.say("Cannot show project map: " + str(exc)[:240])
            return
        self.say("READ-ONLY PROJECT MAP: " + name + "\\n" + text +
                 "\\nNo model called, source executed, or files changed.")

    def _agent_edit(self, name, goal):
        if self.app.busy or self._running:
            self.say("Falcon is already working. Press STOP first.")
            return
        if self.pending:
            self.say("Review or reject the pending source proposal before starting an agent edit.")
            return
        try:
            # Safe snapshot and complete fingerprint must precede model calls.
            base = revisions.load_project(name)
            coding_agent.repository_map(base, goal)
        except (OSError, projects.ProjectError) as exc:
            self.say("Cannot prepare project agent: " + str(exc)[:250])
            return

        def work(cancel):
            status = engine_manager.probe(timeout=3)
            if not status["online"]:
                raise RuntimeError("Ollama is offline. Type /engine start.")
            coder = engine_manager.saved_coding_model()
            chat = engine_manager.saved_chat_model()
            model = coder if coder in status["models"] else chat
            if model not in status["models"]:
                raise RuntimeError("Neither coding nor chat model is installed. Type /engine list.")
            if cancel.is_set():
                return None
            import agent
            return coding_agent.generate_reviewed_edit(
                base, goal, model=model, cancel=cancel, ask=agent.ask_ollama)

        def complete(output):
            if output is None:
                return
            plan = output["plan"]
            self.pending = {
                "mode": "edit", "plan": plan, "base": base,
                "review": projects.review_proposal(plan),
                "revision": output["revision"], "reviewed": False,
            }
            self.opened = None
            self.app.set_status("Ready • Agent coding proposal")
            self.say("Project-aware coding proposal ready (NOT saved or executed).\\n"
                     "Project: " + name +
                     "\\nArchitect: " + output["architect_summary"] +
                     "\\nPlanned files: " + ", ".join(output["architect_files"]) +
                     "\\nRead-only source inspections: " + str(len(output["planner_reads"])) +
                     "\\nProposed changed files: " +
                     ", ".join(output["revision"]["changed"]) +
                     "\\nNothing was executed, tested, downloaded, or approved. "
                     "Use /project diff to review, then /project approve "
                     "to save with a backup or /project reject.")

        self._launch("Planning and editing saved source locally…", work, complete)

    def _edit_small(self, name, goal):
''')

# Enhanced new-project path: architecture first, then strict source generation.
# This route is OPT-IN; existing /project website/python behavior is untouched.
patch("developer_chat.py",
      '    "/project map <saved_name>  •  /project agent <saved_name> <goal>\\n"\\n',
      '    "/project map <saved_name>  •  /project agent <saved_name> <goal>\\n"\\n'
      '    "/project architect <website|python|fabric_mod> <goal>\\n"\\n')
patch("developer_chat.py",
      '        if rest.lower().startswith("map "):\\n',
      '''        if rest.lower().startswith("architect "):
            args = rest.split(None, 2)
            if len(args) == 3 and args[1] in projects.ALLOWED_KINDS and 8 <= len(args[2].strip()) <= 1100:
                return "project_architect", (args[1], args[2].strip())
            return "project_help", ""
        if rest.lower().startswith("map "):
''')
patch("developer_chat.py",
      '("project_new", "project_edit", "project_edit_small", "project_agent")',
      '("project_new", "project_edit", "project_edit_small", "project_agent", "project_architect")')
patch("developer_chat.py",
      '''        elif action == "project_agent":
            self._agent_edit(*payload)
''',
      '''        elif action == "project_agent":
            self._agent_edit(*payload)
        elif action == "project_architect":
            self._architect_new(*payload)
''')
patch("developer_chat.py",
      "    def _map_saved(self, name):\\n",
      '''    def _architect_new(self, kind, goal):
        if self.app.busy or self._running:
            self.say("Falcon is already working. Press STOP first.")
            return
        if self.pending:
            self.say("Review or reject the pending project before starting another.")
            return
        try:
            proposal_messages(kind, goal)  # Existing length/kind validation.
        except projects.ProjectError as exc:
            self.say("Cannot prepare architect: " + str(exc)[:250])
            return

        def work(cancel):
            status = engine_manager.probe(timeout=3)
            if not status["online"]:
                raise RuntimeError("Ollama is offline. Type /engine start.")
            coder = engine_manager.saved_coding_model()
            chat = engine_manager.saved_chat_model()
            model = coder if coder in status["models"] else chat
            if model not in status["models"]:
                raise RuntimeError("Neither coding nor chat model is installed. Type /engine list.")
            if cancel.is_set():
                return None
            import agent
            return coding_agent.generate_new_project_with_architect(
                kind, goal, model=model, cancel=cancel, ask=agent.ask_ollama)

        def complete(output):
            if output is None:
                return
            plan = output["plan"]
            self.pending = {"plan": plan, "review": output["review"],
                            "reviewed": False}
            self.opened = None
            review = output["review"]
            warnings = review.get("quality_warnings", ())
            self.app.set_status("Ready • Architect project proposal")
            self.say("Architect-first source project ready (NOT saved, executed, or tested).\\n"
                     "Architecture: " + output["blueprint"]["summary"] +
                     "\\nPlanned features: " + "; ".join(output["blueprint"]["features"]) +
                     "\\nProposed files: " + ", ".join(review["files"]) +
                     ("\\nStatic quality warnings: " + "; ".join(warnings) if warnings else "") +
                     "\\nUse /project review to read the complete source, "
                     "/project approve to save after full review, or /project reject.")

        self._launch("Architecting and generating source locally…", work, complete)

    def _map_saved(self, name):
''')

# Expose discoverable user-facing shortcuts in the *existing* Commands menu.
# Only inserts commands into the chat textbox. Existing completion order is
# preserved by appending to the end of the Coding & Projects group.
palette = TARGET / "command_palette.py"
raw = palette.read_text(encoding="utf-8")
mark = '        Command("Make a Python code draft", "/build "),\n'
if raw.count(mark) != 1:
    raise RuntimeError("Coding command palette anchor changed")
raw = raw.replace(
    mark, mark +
    '        Command("Read saved project map", "/project map "),\n'
    '        Command("Plan + edit a saved project (review first)", "/project agent "),\n',
    1)
palette.write_text(raw, encoding="utf-8")
raw = palette.read_text(encoding="utf-8")
mark = '        Command("Plan + edit a saved project (review first)", "/project agent "),\\n'
if raw.count(mark) != 1:
    raise RuntimeError("Architect new-project menu anchor changed")
palette.write_text(raw.replace(
    mark, mark + '        Command("Architect-first new project", "/project architect "),\\n', 1),
    encoding="utf-8")

(TARGET / "PROJECT_AGENT_DEVELOPMENT_ONLY.txt").write_text(
    "Local two-stage read-only architect and targeted source editor. "
    "At most 5 planning turns / 2 file reads; no arbitrary tool actions. "
    "All changes require the existing /project diff then /project approve "
    "permission gate. Not installed or published.\n", encoding="utf-8")
print("Staged project-aware Falcon coding agent with no new execution rights")
