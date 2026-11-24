"""Stage review-first project editing in Falcon's existing chat window.

Combines previous per-reply copy, Tab menu and HTML validation candidate.
Never publishes any binary, changes the installed version, or runs projects.
"""
from pathlib import Path
import shutil

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "build" / "Falcon_Ai_WebQuality_Candidate"
TARGET = REPO / "build" / "Falcon_Ai_Revision_Candidate"
if (SOURCE / "RELEASE_VERSION.txt").read_text(encoding="utf-8").strip() != "13.8.0":
    raise SystemExit("13.8.0 next-release candidate source expected")
if TARGET.exists():
    shutil.rmtree(TARGET)
shutil.copytree(SOURCE, TARGET, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".venv"))
shutil.copy2(REPO / "packaging" / "project_revision.py", TARGET / "project_revision.py")


def replace_one(path, old, new):
    target = TARGET / path
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Unexpected Falcon {path} source anchor: {old[:100]!r}: {count}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


replace_one(
    "developer_chat.py",
    "import developer_workspace as projects\n",
    "import developer_workspace as projects\nimport project_revision as revisions\nimport json\n",
)
replace_one(
    "developer_chat.py",
    '    "/project approve  •  /project reject\\n"\n',
    '    "/project approve  •  /project reject\\n"\n'
    '    "/project edit <saved_name> <request>  •  /project diff\\n"\n'
    '    "/project rollback <saved_name> <backup_id>\\n"\n',
)
replace_one(
    "developer_chat.py",
    '        if rest.casefold() in ("review", "approve", "reject"):\n',
    '        if rest.casefold() in ("review", "approve", "reject", "diff"):\n',
)
replace_one(
    "developer_chat.py",
    '        if rest.lower().startswith("show "):\n',
    '''        if rest.lower().startswith("edit "):
            args = rest.split(None, 2)
            if len(args) == 3 and len(args[2].strip()) >= 8:
                return "project_edit", (args[1], args[2].strip())
            return "project_help", ""
        if rest.lower().startswith("rollback "):
            args = rest.split()
            if len(args) == 3:
                return "project_rollback", (args[1], args[2])
            return "project_help", ""
        if rest.lower().startswith("show "):
''',
)
replace_one(
    "developer_chat.py",
    '\n\nclass ChatFeatures:\n',
    '''

def revision_messages(base, goal):
    if not isinstance(goal, str) or not 8 <= len(goal.strip()) <= 1100:
        raise projects.ProjectError("Describe the edit in 8–1100 characters")
    plan = base["plan"]
    # The local model sees only the explicit Falcon-owned project snapshot.
    # It cannot retrieve unrelated user files or approve writing any changes.
    return [
        {"role": "system", "content": SYSTEM + " For this revision, preserve "
         "the original project name, kind and every original file path. "
         "Return ALL complete existing files plus any new plain-text source files. "
         "You MAY add safe source files, but never delete or rename existing files. "
         "Nothing is executed and approval is always required."},
        {"role": "user", "content":
         "Edit this existing Falcon project: " + goal.strip() +
         "\\nOriginal project JSON:\\n" + json.dumps(plan, ensure_ascii=False) +
         "\\nReturn one valid JSON replacement proposal retaining all old files and optional new source files."},
    ]


class ChatFeatures:
''',
)
replace_one(
    "developer_chat.py",
    '''        elif action == "project_new":
            self._generate(*payload)
        elif action == "project_review":''',
    '''        elif action == "project_new":
            self._generate(*payload)
        elif action == "project_edit":
            self._edit(*payload)
        elif action == "project_diff":
            self._diff()
        elif action == "project_rollback":
            self._rollback(*payload)
        elif action == "project_review":''',
)
replace_one(
    "developer_chat.py",
    "    def _generate(self, kind, goal):\n",
    '''    def _edit(self, name, goal):
        try:
            base = revisions.load_project(name)
            messages = revision_messages(base, goal)
        except (OSError, projects.ProjectError) as exc:
            self.say("Cannot edit saved project: " + str(exc)[:290])
            return
        self.pending = None

        def work(cancel):
            status = engine_manager.probe(timeout=3)
            if not status["online"]:
                raise RuntimeError("Ollama is offline. Type /engine start.")
            model = engine_manager.saved_chat_model()
            if model not in status["models"]:
                raise RuntimeError("Chat model " + model + " isn't installed. Type /engine list.")
            if cancel.is_set():
                return None
            import agent
            raw = agent.ask_ollama(messages, model=model, fmt="json",
                                   limit=6500, timeout=180, cancel=cancel)
            if cancel.is_set():
                return None
            candidate = projects.parse_proposal(raw)
            plan = {"name": candidate["name"], "kind": candidate["kind"],
                    "files": candidate["files"]}
            revision = revisions.review_revision(base, plan)
            return {"base": base, "plan": plan, "revision": revision}

        def complete(output):
            if output is None:
                return
            plan = output["plan"]
            self.pending = {
                "mode": "edit", "plan": plan, "base": output["base"],
                "review": projects.review_proposal(plan),
                "revision": output["revision"], "reviewed": False,
            }
            self.app.set_status("Ready • Revision proposal")
            changed = output["revision"]["changed"]
            self.say("Project edit proposal ready (NOT saved or executed).\\n"
                     "Project: " + name +
                     "\\nChanged or added source files: " + str(len(changed)) +
                     "\\n" + "\\n".join("- " + path for path in changed) +
                     "\\nType /project diff to inspect exact changes, "
                     "/project review to inspect full files, "
                     "then /project approve to save with a backup or /project reject.")

        self._launch("Preparing local project edit…", work, complete)

    def _diff(self):
        if not self.pending or self.pending.get("mode") != "edit":
            self.say("No pending edit. Use /project edit <saved_name> <request>.")
            return
        self.pending["reviewed"] = True
        revision = self.pending["revision"]
        diff = revision["diff"]
        warnings = revision.get("quality_warnings", ())
        self.say("REVIEW REVISION: " + self.pending["plan"]["name"] +
                 "\\nSHA-256 proposal fingerprint: " + revision["new_fingerprint"] +
                 "\\nChanged/added files: " + ", ".join(revision["changed"]) +
                 "\\nSource-only diff; nothing was executed." +
                 ("\\nStatic warnings: " + "; ".join(warnings) if warnings else "") +
                 "\\n\\n" + diff[:26000] +
                 ("\\n[Diff shortened; use /project show <file> for a source preview.]"
                  if len(diff) > 26000 else "") +
                 "\\n\\nType /project approve or /project reject.")

    def _rollback(self, name, backup_id):
        if self.app.busy or self._running:
            self.say("Finish or STOP the current task before rollback.")
            return
        try:
            result = revisions.rollback_revision(name, backup_id)
        except (OSError, projects.ProjectError) as exc:
            self.say("Rollback blocked: " + str(exc)[:260])
            return
        self.pending = None
        self.say("Restored original source files for " + name +
                 "\\n" + "\\n".join("- " + f for f in result["restored"]) +
                 "\\nNo generated code was executed.")

    def _generate(self, kind, goal):
''',
)
replace_one(
    "developer_chat.py",
    '''        info = self.pending["review"]
        items = list(info["files"].items())
''',
    '''        info = self.pending["review"]
        if self.pending.get("mode") == "edit":
            self._diff()
            return
        items = list(info["files"].items())
''',
)
replace_one(
    "developer_chat.py",
    '''        info = self.pending
        try:
            result = projects.save_approved(
                info["plan"], info["review"]["fingerprint"])
''',
    '''        info = self.pending
        if info.get("mode") == "edit":
            try:
                result = revisions.save_revision_approved(
                    info["base"], info["plan"],
                    info["revision"]["new_fingerprint"])
            except (OSError, projects.ProjectError) as exc:
                self.say("Saving edit blocked: " + str(exc)[:260] +
                         "\\nNo code was executed.")
                return
            self.pending = None
            self.say("Saved reviewed changes to " + result["project"] +
                     "\\nChanged/added files: " + ", ".join(result["changed"]) +
                     "\\nBackup ID: " + result["backup_id"] +
                     "\\nTo restore, type /project rollback " +
                     info["plan"]["name"] + " " + result["backup_id"] +
                     "\\nNo generated code was executed.")
            return
        try:
            result = projects.save_approved(
                info["plan"], info["review"]["fingerprint"])
''',
)
replace_one(
    "command_palette.py",
    '        Command("Review generated files", "/project review"),\n',
    '''        Command("Edit existing saved project", "/project edit "),
        Command("Inspect code changes", "/project diff"),
        Command("Restore prior revision", "/project rollback "),
        Command("Review generated files", "/project review"),
''',
)
(TARGET / "REVISION_CANDIDATE_ONLY.txt").write_text(
    "Edit saved projects through one Falcon chat. Full-file source proposals, "
    "diff review, exact SHA-256 approval, stale-file refusal, local backup and "
    "explicit rollback. No release or user installation yet.\\n",
    encoding="utf-8",
)
print("Prepared next-bundle Falcon project edit and rollback candidate")
