"""Compatibility import for scripts run from the checkout root."""
from pathlib import Path
from runpy import run_path

_adapter = run_path(str(Path(__file__).parent / "packaging" / "comfy_video.py"))
ComfyVideo = _adapter["ComfyVideo"]
VideoJobFailed = _adapter["VideoJobFailed"]
check_active = _adapter["check_active"]
