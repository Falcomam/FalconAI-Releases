"""Stage Falcon Ai 13.8 engine manager development on the verified 13.7.1 base.

No release/publishing step. All changes are applied to a copy with exact anchors,
leaving the verified Falcon Ai 13.7.1 and its working Windows updater intact.
"""
from pathlib import Path
import shutil

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "build" / "Falcon_Ai_App_V13_7_1"
TARGET = REPO / "build" / "Falcon_Ai_Engine_Candidate"
RUNTIME = REPO / "build" / "falcon_app_1371_runtime"

if (SOURCE / "RELEASE_VERSION.txt").read_text(encoding="utf-8").strip() != "13.7.1":
    raise SystemExit("Verified Falcon Ai 13.7.1 source is required")
if TARGET.exists():
    shutil.rmtree(TARGET)
shutil.copytree(SOURCE, TARGET, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".venv"))
shutil.copy2(REPO / "packaging" / "engine_manager.py", TARGET / "engine_manager.py")


def one(path, old, new):
    file = TARGET / path
    source = file.read_text(encoding="utf-8")
    if source.count(old) != 1:
        raise RuntimeError(f"Missing or nonunique integration anchor: {path}: {old[:90]!r} ({source.count(old)})")
    file.write_text(source.replace(old, new, 1), encoding="utf-8")


one("falcon.py", "from ollama_runtime import local_model_answer",
    "from ollama_runtime import local_model_answer\nimport engine_manager")
one("falcon.py", "MODEL = 'qwen3:4b'",
    "MODEL = engine_manager.saved_chat_model()")
one("falcon.py", "        self.entry.focus_set()\n\n    def _build_command_center(self):",
    """        self.entry.focus_set()
        # Verify the actual local service asynchronously; never show a fake
        # 'Ready' status when Ollama has not started after Windows reboot.
        self.root.after(650, self.check_ai_engine)

    def _build_command_center(self):""")
one("falcon.py", """        updates = tk.Menu(self.root, tearoff=0)
""", """        engine_menu = tk.Menu(self.root, tearoff=0)
        engine_menu.add_command(label='Check Ollama status', command=self.check_ai_engine)
        engine_menu.add_command(label='Start Ollama (confirmation)', command=self.start_ai_engine)
        engine_menu.add_command(label='Select installed chat model', command=self.choose_ai_model)
        tools.add_cascade(label='AI Engine', menu=engine_menu)
        updates = tk.Menu(self.root, tearoff=0)
""")
one("falcon.py", "    def check_release_updates(self):\n",
    """    def check_ai_engine(self):
        '''Check local Ollama in a background thread; GUI updates stay on Tk.'''
        if self.busy:
            self.append('System', 'Finish the current task before checking Ollama.')
            return
        self.set_status('Checking local AI engine…')
        def work():
            state = engine_manager.probe()
            def apply():
                if self.busy:
                    return
                if not state['online']:
                    self.set_status('AI Offline • Ollama unavailable')
                    return
                selected = engine_manager.saved_chat_model()
                if selected not in state['models']:
                    self.set_status('AI Offline • Chat model not installed')
                    self.append('System', 'Ollama is online, but the selected chat model '
                                + selected + ' is not installed. Use Tools > AI Engine to select an installed model.')
                else:
                    self.set_status('Ready • ' + selected)
            self.root.after(0, apply)
        threading.Thread(target=work, daemon=True).start()

    def start_ai_engine(self):
        '''Start only a local installed Ollama executable after a user click.'''
        if self.busy:
            self.append('System', 'Finish the current task before starting Ollama.')
            return
        if not messagebox.askyesno('Start local Ollama?',
                    'Start the Ollama AI server already installed on this PC?\\n'
                    'No models will be downloaded, and PC permissions will not change.',
                    parent=self.root):
            return
        self.set_status('Starting Ollama…')
        def work():
            try:
                result = engine_manager.start_ollama(confirmed=True)
            except engine_manager.EngineError as exc:
                detail = str(exc)
                self.root.after(0, lambda: self._engine_start_failed(detail))
                return
            def complete():
                if result == 'already_running':
                    self.append('System', 'Ollama is already running.')
                else:
                    self.append('System', 'Ollama launch requested; verifying local connection.')
                self.root.after(1400, self.check_ai_engine)
            self.root.after(0, complete)
        threading.Thread(target=work, daemon=True).start()

    def _engine_start_failed(self, detail):
        self.set_status('AI Offline • Could not start Ollama')
        self.append('Error', detail)

    def choose_ai_model(self):
        '''A model name is selected only from a live Ollama /api/tags list.'''
        if self.busy:
            self.append('System', 'Finish the current task before switching models.')
            return
        def work():
            state = engine_manager.probe()
            def apply():
                global MODEL
                if self.busy:
                    return
                if not state['online']:
                    self.set_status('AI Offline • Ollama unavailable')
                    self.append('System', 'Start Ollama before selecting a local model.')
                    return
                if not state['models']:
                    self.append('System', 'Ollama has no installed local models.')
                    return
                choice = simpledialog.askstring(
                    'Select local AI model',
                    'Choose an installed model by exact name:\\n\\n' + '\\n'.join(state['models'][:24]),
                    initialvalue=engine_manager.saved_chat_model(), parent=self.root)
                if choice is None:
                    return
                try:
                    MODEL = engine_manager.save_chat_model(
                        choice.strip(), installed_models=state['models'])
                except engine_manager.EngineError as exc:
                    messagebox.showerror('Invalid chat model', str(exc), parent=self.root)
                    return
                os.environ['FALCON_CHAT_MODEL'] = MODEL
                # The PC task planner uses the same selected local model.
                # Safety and approvals remain in agent.validate_plan/run_approved.
                import agent
                agent.CHAT_MODEL = MODEL
                self.set_status('Ready • ' + MODEL)
                self.append('System', 'Local chat model set to ' + MODEL
                            + '. No additional computer permissions were granted.')
            self.root.after(0, apply)
        threading.Thread(target=work, daemon=True).start()

    def check_release_updates(self):
""")
one("falcon.py", """color = self.ui_colors['danger'] if 'error' in message.casefold() else (""",
    """color = self.ui_colors['danger'] if ('error' in message.casefold() or 'offline' in message.casefold()) else (""")
one("falcon.py",
    "'Configured local models: qwen3:4b / qwen2.5vl:3b (availability not checked)',",
    "'Configured local models: ' + MODEL + ' / ' + VISION + ' (check live status in Tools > AI Engine)',")
one("falcon.py", "        self.set_status('Error • Ready')",
    "        self.set_status('Error • AI connection needs checking')")
one("falcon.py", "        self.set_status('Ready • Local Ollama')",
    "        self.set_status('Ready • ' + MODEL)")

# Frozen entry point must load saved selection before importing agent.
app_entry = RUNTIME / "app_entry.py"
app_text = app_entry.read_text(encoding="utf-8")
old = "import sys\n\nimport app_updates"
new = """import sys
import os

import engine_manager
os.environ['FALCON_CHAT_MODEL'] = engine_manager.saved_chat_model()

import app_updates"""
if app_text.count(old) != 1:
    raise RuntimeError("Packaged entry model-selection anchor changed")
(RUNTIME / "app_entry_engine_candidate.py").write_text(
    app_text.replace(old, new, 1), encoding="utf-8")

# This stage is development only. No 13.8 tag, installer or update is published.
(TARGET / "ENGINE_CANDIDATE_NOT_RELEASED.txt").write_text(
    "Engine candidate staged for integration testing. Do not install over working Falcon Ai 13.7.1.\\n",
    encoding="utf-8")
print("Staged Falcon Ai engine-management candidate; existing 13.7.1 remains unchanged")
