"""Generate a real, review-only LTX clip with installed weights and check for motion."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ltx_video import LTXVideo

PROMPT = ("A small peregrine falcon with silver feathers and a violet silk scarf opens its wings atop "
          "an antique brass observatory. The bird leans forward and lifts off into the purple dawn. "
          "Its wingtips catch warm rim light as the camera tracks it from the side. A softly glowing "
          "skyline passes behind it, cel-shaded original animation, clean silhouettes and fluid motion.")


def verify(output, *, compact=False):
    from shorts_mode import paused, OUT
    stop = lambda: (OUT / "STOP").exists()
    engine = LTXVideo.connect(stop, paused)
    opts = dict(width=192, height=320, frames=25, steps=10) if compact else {}
    clip = engine.render(PROMPT, output, stop, paused, preview=True, seed=21125,
                         progress=lambda s: print(s, flush=True), **opts)
    data = subprocess.check_output(["ffmpeg", "-v", "error", "-i", str(clip), "-map", "0:v:0",
                                    "-f", "framemd5", "-"], text=True, timeout=120)
    frames = [s.rsplit(",", 1)[-1].strip() for s in data.splitlines() if s and not s.startswith("#")]
    if len(set(frames)) < 2:
        raise ValueError("Rendered frames have no detectable change")
    with clip.open("rb") as f:
        digest = hashlib.file_digest(f, "sha256").hexdigest()
    result = {"checkpoint": engine.checkpoint, "encoder": engine.encoder,
              "frames": len(frames), "distinct_frames": len(set(frames)), "sha256": digest}
    (clip.parent / "verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result), "\n", clip)
    return clip


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()
    verify(args.output, compact=args.compact)
