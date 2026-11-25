"""Stage reviewed Shorts modules into a Falcon development candidate.

Only called by the existing build-time reconstruction pipeline. Does not
publish, install, touch local user data, download dependencies or run models.
"""
from pathlib import Path
import shutil

MODULES = (
    "shorts_timing.py", "shorts_schedule.py", "shorts_visuals.py",
    "shorts_upload.py", "shorts_mode.py", "shorts_report.py",
    "shorts_controls.py", "shorts_publish_ui.py",
    "comfy_video.py", "video_workflow.py", "ltx_video.py",
)

def stage_shorts(source, target):
    source, target = Path(source), Path(target)
    if not target.is_dir() or source.resolve() == target.resolve():
        raise ValueError("Expected a separate existing development candidate")
    chat = (target / "developer_chat.py").read_text(encoding="utf-8")
    for anchor in ("self.app.root.after_idle(self._setup_money_mode)",
                   "def _setup_money_mode(self):",
                   "shorts_mode.create(model, cancel=cancel)"):
        if anchor not in chat:
            raise RuntimeError("Missing staged Money Mode integration: " + anchor)
    # Validate every input before copying anything. Do not silently overwrite
    # a different existing module or follow a symlink in either tree.
    for name in MODULES:
        src, dst = source / name, target / name
        if src.is_symlink() or not src.is_file() or dst.is_symlink():
            raise RuntimeError("Missing or unsafe Shorts source: " + name)
        compile(src.read_bytes(), name, "exec")
        if dst.exists() and (not dst.is_file() or dst.read_bytes() != src.read_bytes()):
            raise RuntimeError("Conflicting staged Shorts module: " + name)
    for name in MODULES:
        src, dst = source / name, target / name
        if not dst.exists():
            shutil.copy2(src, dst)
    return MODULES
