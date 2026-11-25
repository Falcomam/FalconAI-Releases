"""Reconstruct a 14.4.0 Windows candidate from the published 14.3.2 source stages."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys

from prepare_v143_shorts_candidate import replace

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
BASE = BUILD / "Falcon_Ai_V14_3_2_Candidate"
OLD_RUNTIME = BUILD / "falcon_app_v1432_runtime"
TARGET = BUILD / "Falcon_Ai_V14_4_Candidate"
RUNTIME = BUILD / "falcon_app_v144_runtime"
STAGES = (
    "prepare", "prepare_icon_release", "prepare_engine_candidate",
    "prepare_single_chat_candidate", "prepare_v138_release", "prepare_copy_reply_candidate",
    "prepare_command_palette_candidate", "prepare_web_quality_candidate",
    "prepare_project_revision_candidate", "prepare_project_browser_candidate",
    "prepare_next_bundle_windows", "prepare_project_search_candidate",
    "prepare_quiet_powershell_candidate", "prepare_packaged_health_candidate",
    "finalize_packaged_health_release", "prepare_v14_release_candidate",
    "prepare_agent_coding_candidate", "prepare_money_mode_candidate",
    "prepare_v141_money_release_candidate", "prepare_v142_store_candidate",
    "prepare_v143_shorts_candidate",
)


def reconstruct():
    for version in ("v13.6", "v13.6.1", "v13.6.2", "v13.6.3", "v13.6.4", "v13.6.5"):
        subprocess.run([sys.executable, ROOT / "patches" / version / "apply.py"], cwd=ROOT, check=True)
    for stage in STAGES:
        subprocess.run([sys.executable, ROOT / "packaging" / (stage + ".py")], cwd=ROOT, check=True)


def main():
    if (BASE / "RELEASE_VERSION.txt").read_text().strip() != "14.3.2":
        raise RuntimeError("Expected the 14.3.2 release reconstruction")
    for src, dst in ((BASE, TARGET), (OLD_RUNTIME, RUNTIME)):
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".venv"))

    for name in ("falcon.py", "falcon_launcher.py"):
        p = TARGET / name
        raw = p.read_text(encoding="utf-8")
        if "V14.3.2" not in raw:
            raise ValueError("Missing visible version in " + name)
        p.write_text(raw.replace("V14.3.2", "V14.4.0"), encoding="utf-8")
    replace(TARGET / "RELEASE_VERSION.txt", "14.3.2", "14.4.0")
    for p in (TARGET / "release_updates.py", RUNTIME / "app_updates.py"):
        replace(p, "CURRENT_VERSION = (14, 3, 2)", "CURRENT_VERSION = (14, 4, 0)")
    foundation = TARGET / "falcon_foundation.py"
    replace(foundation, 'VERSION = "14.3.2"', 'VERSION = "14.4.0"')
    replace(foundation, 'VERSION != "14.3.2"', 'VERSION != "14.4.0"')
    replace(foundation, "Original procedural cartoon drafts, preview and reviewed upload;",
            "Illustrated or local LTX-Video drafts, preview and reviewed upload;")
    entry = RUNTIME / "app_entry.py"
    replace(entry, "CURRENT_VERSION != (14, 3, 2)", "CURRENT_VERSION != (14, 4, 0)")
    replace(entry, "strip() != '14.3.2'", "strip() != '14.4.0'")
    # Extend the existing frozen Shorts check, which also runs after installation and upgrade.
    replace(entry, "        from shorts_publish_ui import plan_upload\n",
            "        import ltx_video, video_workflow, comfy_video, developer_chat\n"
            "        graph = ltx_video.build_workflow('A falcon flies', 1)\n"
            "        if graph[ltx_video.OUTPUT_NODE]['class_type'] != 'SaveVideo' or "
            "developer_chat.route('/shorts clip a bird') != ('ltx_clip', 'a bird'):\n"
            "            raise RuntimeError('Frozen LTX integration failed')\n"
            "        from shorts_publish_ui import plan_upload\n")
    iss = RUNTIME / "Falcon_Ai.iss"
    replace(iss, '#define MyAppVersion "14.3.2"', '#define MyAppVersion "14.4.0"')
    iss.write_text(iss.read_text(encoding="utf-8").replace("falcon_app_v1432_runtime", "falcon_app_v144_runtime"),
                   encoding="utf-8")
    def app_id(path):
        return [line for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("AppId=")]
    if len(app_id(iss)) != 1 or app_id(iss) != app_id(OLD_RUNTIME / "Falcon_Ai.iss"):
        raise ValueError("Installer AppId changed")

    chat = TARGET / "developer_chat.py"
    replace(chat, '    if raw.casefold() == "/shorts draft":\n',
            '    if raw.casefold() == "/shorts clip" or raw.casefold().startswith("/shorts clip "):\n'
            '        return "ltx_clip", raw[len("/shorts clip"):].strip()\n'
            '    if raw.casefold() == "/shorts draft":\n')
    replace(chat, '        if action == "shorts_status":\n',
            '        if action == "ltx_clip":\n'
            '            controls = getattr(self, "_money_controls", None)\n'
            '            if controls is None:\n'
            '                self.say("Money Mode controls are unavailable.")\n'
            '            else:\n'
            '                controls.generate_clip(payload or None)\n'
            '        elif action == "shorts_status":\n')
    replace(chat, "folder = shorts_mode.create(model, cancel=cancel)",
            "controls = getattr(self, '_money_controls', None)\n"
            "                progress = lambda message: controls.video_status(cancel, message) if controls else None\n"
            "                folder = shorts_mode.create(model, cancel=cancel, progress=progress)")
    for path in (chat, foundation, entry):
        compile(path.read_bytes(), str(path), "exec")
    print("Staged Falcon 14.4.0 local video candidate")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reconstruct", action="store_true")
    if parser.parse_args().reconstruct:
        reconstruct()
    main()
