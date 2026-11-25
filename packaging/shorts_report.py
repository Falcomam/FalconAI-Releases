"""Read-only, local Shorts status report. No models, network, or uploads."""
import datetime as dt
import json
import os
from pathlib import Path
import shutil
from ltx_video import daily_enabled

ROOT = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "FalconAI"

def report(root=ROOT, day=None, *, gaming=False):
    root=Path(root)
    day=day or dt.date.today()
    folder=root/"shorts"/day.isoformat()
    ledger=folder/"upload_attempt.json"
    state="No draft yet"
    upload="Not uploaded"
    if (folder/"FAILED.txt").exists():
        state="Failed or interrupted; inspect draft folder"
    elif (folder/"REVIEW_REQUIRED.txt").is_file() and (folder/"draft.mp4").is_file():
        state="Video ready for review"
    elif folder.exists():
        state="Reserved or incomplete draft"
    if ledger.exists():
        try:
            data=json.loads(ledger.read_text(encoding="utf-8"))
            if data.get("state")=="manual_handoff":
                upload="Manual Studio handoff recorded; upload not verified"
            elif data.get("state")=="uploaded" and data.get("video_id"):
                upload="Upload receipt saved; public visibility not verified"
            else:
                upload="Upload uncertain; check YouTube Studio before retrying"
        except (OSError, ValueError, AttributeError):
            upload="Unreadable upload receipt; check YouTube Studio"
    missing=[name for name in ("ffmpeg","ffprobe","powershell.exe") if not shutil.which(name)]
    try:
        automatic=json.loads((root/"shorts_preferences.json").read_text(encoding="utf-8")).get("daily_drafts") is True
    except (OSError, ValueError, AttributeError):
        automatic=False
    lines=["FALCON MONEY MODE — DAILY SHORTS REPORT",
           "Date: "+day.isoformat(), "Daily target: 1 original brainrot Short",
           "Draft: "+state, "YouTube: "+upload,
           "Daily visuals: "+("LTX-Video 2B" if daily_enabled(root) else "Illustrated"),
           "Gaming Mode: "+("ON (paused)" if gaming else "OFF"),
           "STOP: "+("Active" if (root/"shorts"/"STOP").exists() else "Not active"),
           "Media tools: "+("Missing "+", ".join(missing) if missing else "Found on PATH"),
           "Daily drafts: "+("ON (4 PM or later while Falcon is open)" if automatic else "OFF"),
           "Publication: target 6 PM; unattended publishing not enabled.",
           "Draft folder: "+str(folder),
           "Next action: "+("Review today's video." if state=="Video ready for review" else
                            "Check the status above before using /shorts draft."),
           "No video was generated or uploaded by this report."]
    return "\n".join(lines)
