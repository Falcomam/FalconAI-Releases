"""Stage Shorts on top of the exact V14.2 Payhip release reconstruction."""
from pathlib import Path
import shutil
from stage_shorts import stage_shorts

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"build/Falcon_Ai_V14_2_Candidate"
BASE_RUNTIME=ROOT/"build/falcon_app_v142_runtime"
TARGET=ROOT/"build/Falcon_Ai_V14_3_2_Candidate"
RUNTIME=ROOT/"build/falcon_app_v1432_runtime"

def replace(path, old, new):
    text=path.read_text(encoding="utf-8")
    if text.count(old)!=1:
        raise RuntimeError("V14.3 ambiguous anchor: "+str(path)+" "+repr(old[:120]))
    path.write_text(text.replace(old,new,1),encoding="utf-8")

def main():
    if (BASE/"RELEASE_VERSION.txt").read_text(encoding="utf-8").strip()!="14.2.0":
        raise RuntimeError("Expected reconstructed V14.2 source")
    if "CURRENT_VERSION = (14, 2, 0)" not in (BASE_RUNTIME/"app_updates.py").read_text(encoding="utf-8"):
        raise RuntimeError("Expected V14.2 updater")
    for directory in (TARGET,RUNTIME):
        if directory.exists():
            shutil.rmtree(directory)
    shutil.copytree(BASE,TARGET,ignore=shutil.ignore_patterns("__pycache__","*.pyc",".venv"))
    shutil.copytree(BASE_RUNTIME,RUNTIME,ignore=shutil.ignore_patterns("__pycache__","*.pyc",".venv"))
    chat=TARGET/"developer_chat.py"
    replace(chat,"    def say(self, message):\n",
        "        self.app.root.after_idle(self._setup_money_mode)\n\n    def say(self, message):\n")
    replace(chat,'    raw = text.strip()\n',
        '    raw = text.strip()\n    if raw.casefold() in ("/shorts", "/shorts status"):\n        return "shorts_status", ""\n    if raw.casefold() == "/shorts draft":\n        return "shorts_draft", ""\n')
    replace(chat,'        if action == "foundation":\n',
        '        if action == "shorts_status":\n            self._shorts_status()\n        elif action == "shorts_draft":\n            self._shorts_draft()\n        elif action == "foundation":\n')
    replace(chat,"    def _engine(self, payload):\n",SHORTS_METHODS+"    def _engine(self, payload):\n")
    compile(chat.read_bytes(),str(chat),"exec")
    stage_shorts(ROOT/"packaging",TARGET)
    requirements=TARGET/"requirements.txt"
    text=requirements.read_text(encoding="utf-8")
    for dep in ("google-api-python-client>=2.150,<3","google-auth-oauthlib>=1.2,<2","google-auth-httplib2>=0.2,<1"):
        if dep not in text.splitlines():
            text=text.rstrip()+"\n"+dep+"\n"
    requirements.write_text(text,encoding="utf-8")
    for name in ("falcon.py","falcon_launcher.py"):
        file=TARGET/name
        text=file.read_text(encoding="utf-8")
        if "V14.2.0" not in text:
            raise RuntimeError("Missing prior GUI version")
        file.write_text(text.replace("V14.2.0","V14.3.2"),encoding="utf-8")
    replace(TARGET/"RELEASE_VERSION.txt","14.2.0","14.3.2")
    replace(TARGET/"release_updates.py","CURRENT_VERSION = (14, 2, 0)","CURRENT_VERSION = (14, 3, 2)")
    replace(RUNTIME/"app_updates.py","CURRENT_VERSION = (14, 2, 0)","CURRENT_VERSION = (14, 3, 2)")
    entry=RUNTIME/"app_entry.py"
    replace(entry,"CURRENT_VERSION != (14, 2, 0)","CURRENT_VERSION != (14, 3, 2)")
    replace(entry,"version_file.read_text(encoding='utf-8').strip() != '14.2.0'","version_file.read_text(encoding='utf-8').strip() != '14.3.2'")
    replace(entry,"    if '--falcon-store-self-test' in sys.argv:\n",FROZEN_GATE+"    if '--falcon-store-self-test' in sys.argv:\n")
    iss=RUNTIME/"Falcon_Ai.iss"
    replace(iss,'#define MyAppVersion "14.2.0"','#define MyAppVersion "14.3.2"')
    text=iss.read_text(encoding="utf-8")
    if "falcon_app_v142_runtime" not in text:
        raise RuntimeError("Expected prior runtime icon path")
    iss.write_text(text.replace("falcon_app_v142_runtime","falcon_app_v1432_runtime"),encoding="utf-8")
    def app_id(file):
        return [line for line in file.read_text(encoding="utf-8").splitlines() if line.startswith("AppId=")]
    if len(app_id(iss))!=1 or app_id(iss)!=app_id(BASE_RUNTIME/"Falcon_Ai.iss"):
        raise RuntimeError("Installer identity changed")
    foundation=TARGET/"falcon_foundation.py"
    replace(foundation,'VERSION = "14.2.0"','VERSION = "14.3.2"')
    replace(foundation,'if VERSION != "14.2.0":','if VERSION != "14.3.2":')
    anchor='    Capability("trusted_updates", "Verified Windows updates", "available",'
    replace(foundation,anchor,'    Capability("shorts", "Daily local Shorts drafts", "limited",\n               "Original procedural cartoon drafts, preview and reviewed upload; requires local media tools and account authorization."),\n'+anchor)
    (TARGET/"README_FALCON_AI_V14_3_2.txt").write_text(
        "Falcon 14.3.2 - Shorts Money Mode\n"
        "Open Money Mode for startup report, daily local drafts, preview, reviewed upload or manual Studio handoff.\n"
        "Requires local Ollama and FFmpeg/ffprobe on PATH; actual YouTube authorization and commercial-use voice rights are the owner's responsibility.\n"
        "No automatic public uploads, revenue guarantee or AI diffusion animation. Retains V14.2 features.\n",encoding="utf-8")
    print("Staged V14.3 candidate; no install or publication.")

FROZEN_GATE = '''    if '--falcon-shorts-self-test' in sys.argv:
        import shorts_mode, shorts_controls, shorts_publish_ui, shorts_report
        import google_auth_oauthlib.flow, googleapiclient.discovery, google_auth_httplib2
        from shorts_publish_ui import plan_upload
        body = plan_upload('Fixture', '', 'private', 'no', 'no', '23', '', True, True)
        if body['status']['privacyStatus'] != 'private':
            raise RuntimeError('Frozen Shorts metadata self-test failed')
        if not callable(shorts_controls.MoneyControls.manual_upload):
            raise RuntimeError('Manual upload handoff unavailable')
        print('FALCON V14.3 SHORTS SELF-TEST PASSED')
        return 0
'''

SHORTS_METHODS = "    def _setup_money_mode(self):\n        if getattr(self, \"_money_controls\", None) is not None:\n            return\n        self._shorts_status()\n        try:\n            import shorts_controls\n            self._money_controls = shorts_controls.MoneyControls(self)\n        except (ImportError, AttributeError, RuntimeError, OSError) as exc:\n            self.say(\"Money Mode controls unavailable: \" + str(exc)[:160])\n\n    def _shorts_status(self):\n        try:\n            import shorts_report\n            self.say(shorts_report.report(gaming=gaming_mode.enabled()))\n        except (ImportError, OSError, ValueError):\n            self.say(\"Shorts report unavailable in this build. No video was generated or uploaded.\")\n\n    def _shorts_draft(self):\n        if gaming_mode.enabled():\n            self.say(\"Gaming Mode is ON. Shorts generation is paused.\")\n            return\n\n        def work(cancel):\n            try:\n                import shorts_mode\n                status = engine_manager.probe(timeout=3)\n                model = shorts_mode.preferred_story_model(engine_manager.saved_chat_model(), status[\"models\"])\n                if not status[\"online\"] or model not in status[\"models\"]:\n                    raise RuntimeError(\"Selected Ollama chat model is unavailable.\")\n                folder = shorts_mode.create(model, cancel=cancel)\n                return True, str(folder)\n            except Exception as exc:\n                return False, str(exc)[:300]\n\n        def complete(result):\n            ok, detail = result\n            self.app.set_status(\"Ready • Shorts\" if ok else \"Error • Shorts\")\n            self.say((\"Local draft ready for review. No upload performed.\\n\" if ok else\n                      \"Shorts draft not completed; partial files may exist.\\n\") + detail)\n\n        self._launch(\"Rendering local Short…\", work, complete)\n\n"

if __name__ == '__main__':
    main()
