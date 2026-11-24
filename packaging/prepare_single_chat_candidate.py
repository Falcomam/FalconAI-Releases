"""Add one-chat Developer Mode to Falcon Ai's tested 13.8 engine candidate.

Development-only staged build; no installer is released. Exact source anchors
make accidental UI changes fail closed.
"""
from pathlib import Path
import shutil

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "build" / "Falcon_Ai_Engine_Candidate"
TARGET = REPO / "build" / "Falcon_Ai_SingleChat_Candidate"

if (SOURCE / "RELEASE_VERSION.txt").read_text(encoding="utf-8").strip() != "13.7.1":
    raise SystemExit("Verified Falcon Ai engine candidate source required")
if TARGET.exists():
    shutil.rmtree(TARGET)
shutil.copytree(SOURCE, TARGET, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".venv"))
for file in ("developer_chat.py", "developer_generation.py",
             "developer_workspace.py", "project_static_check.py", "html_quality.py",
             "gaming_mode.py", "site_design_check.py"):
    shutil.copy2(REPO / "packaging" / file, TARGET / file)


def replace_one(path, old, new):
    file = TARGET / path
    text = file.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise RuntimeError(f"Ambiguous Falcon integration anchor {path}: {old[:85]!r}, count={text.count(old)}")
    file.write_text(text.replace(old, new, 1), encoding="utf-8")


# Central planner guard: UI pause alone is insufficient when alternate agent
# entrypoints exist. No model request may start through agent.ask_ollama in
# explicit Gaming Mode. Other applications using Ollama are unaffected.
replace_one("agent.py",
    "    check_stop(cancel)\n    if model is None:\n",
    "    check_stop(cancel)\n"
    "    import gaming_mode\n"
    "    if gaming_mode.enabled():\n"
    "        raise RuntimeError('Gaming Mode ON: Falcon AI model work is paused. Type /engine gaming off to resume.')\n"
    "    if model is None:\n")

replace_one("falcon.py",
    "import engine_manager\n",
    "import engine_manager\nimport developer_chat\n")
replace_one("falcon.py",
    "        self.workflow = unified.UnifiedChat(self)\n",
    "        self.workflow = unified.UnifiedChat(self)\n"
    "        self.dev_chat = developer_chat.ChatFeatures(self)\n")
replace_one("falcon.py",
    "        if self.workflow.dispatch(prompt):\n            return\n        self.chat_message(prompt)",
    "        if self.dev_chat.dispatch(prompt):\n            return\n"
    "        if developer_chat.gaming_mode.enabled():\n"
    "            self.append('Falcon', 'Gaming Mode ON: local AI requests are paused. Type /engine gaming off to resume.')\n"
    "            return\n"
    "        if self.workflow.dispatch(prompt):\n            return\n        self.chat_message(prompt)")
replace_one("falcon.py",
    "        if hasattr(self, 'workflow'):\n            self.workflow.stop()\n",
    "        if hasattr(self, 'workflow'):\n            self.workflow.stop()\n"
    "        if hasattr(self, 'dev_chat'):\n            self.dev_chat.stop()\n")
replace_one("falcon.py",
    "            ('Build code', lambda: self._prepare_prompt('/build ')),",
    "            ('Build code', lambda: self._prepare_prompt('/build ')),\n"
    "            ('Create multi-file project', lambda: self.submit_command('/project help')),")

# Shortcuts open the same Falcon conversation, not a second Studio window or
# a model selection dialog. The startup health indicator remains asynchronous.
replace_one("falcon.py",
    "        engine_menu.add_command(label='Check Ollama status', command=self.check_ai_engine)\n"
    "        engine_menu.add_command(label='Start Ollama (confirmation)', command=self.start_ai_engine)\n"
    "        engine_menu.add_command(label='Select installed chat model', command=self.choose_ai_model)",
    "        engine_menu.add_command(label='Check Ollama status',\n"
    "                                command=lambda: self.submit_command('/engine status'))\n"
    "        engine_menu.add_command(label='Start local Ollama',\n"
    "                                command=lambda: self.submit_command('/engine start'))\n"
    "        engine_menu.add_command(label='List/select installed models',\n"
    "                                command=lambda: self.submit_command('/engine list'))")

(TARGET / "SINGLE_CHAT_DEV_ONLY.txt").write_text(
    "Project Falcon V13.8 candidate: One main chat, no separate Developer Studio UI. "
    "No EXE/installer has been published. Untrusted project output requires review "
    "and a typed /project approve command. No generated code executes.\n",
    encoding="utf-8")
print("PASS: staged single-chat Falcon developer and model interface")
