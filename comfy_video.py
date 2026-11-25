"""Compatibility import for scripts run from the checkout root."""
from pathlib import Path
from runpy import run_path

ComfyVideo = run_path(str(Path(__file__).parent / "packaging" / "comfy_video.py"))["ComfyVideo"]
