"""Exercise all six real LTX renders and the production Shorts editor on a small CPU runner."""
import argparse
from functools import partial
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ltx_video
import shorts_mode
from shorts_timing import scene_frames, story_key

STORY = {
    "title": "The Falcon Who Delivered Sunrise",
    "lines": [
        "A silver falcon in a violet scarf carried the last sunrise.",
        "She found the city asleep beneath a blanket of purple fog.",
        "A sleepy moon refused to clock out without its breakfast.",
        "The falcon raced into a kitchen and borrowed one golden pancake.",
        "The moon took a bite and rolled behind the mountains.",
        "Sunlight spilled from her mailbag, just in time for breakfast.",
    ],
    "scenes": [
        {"setting": s, "action": a} for s, a in zip(
            ("moon", "city", "moon", "kitchen", "moon", "city"),
            ("stand", "run", "panic", "run", "fall", "celebrate"))
    ],
}


def verify(output):
    engine = ltx_video.LTXVideo.connect(lambda: (shorts_mode.OUT / "STOP").exists(), shorts_mode.paused)
    # Keep the actual production clip length/timebase, with a smaller canvas and
    # fewer denoising steps for the six independent CPU inferences.
    renderer = SimpleNamespace(render=partial(engine.render, width=192, height=320, steps=8))
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output) as tmp:
        work = Path(tmp)
        frames = []
        for index, line in enumerate(STORY["lines"]):
            wav = work / f"voice{index}.wav"
            subprocess.run(["espeak-ng", "-s", "158", "-w", str(wav), line], check=True, timeout=30)
            frames.append(scene_frames(wav))
        duration = shorts_mode.render_video(work, STORY, story_key(STORY), frames, ltx=renderer,
                                           progress=lambda message: print(message, flush=True))
        clips = [hashlib.sha256((work / f"ltx{i}.mp4").read_bytes()).hexdigest() for i in range(6)]
        if len(set(clips)) != 6:
            raise RuntimeError("Expected six distinct synthesised scene files")
        if (work / "captions.srt").read_text(encoding="utf-8").count("-->") != 6:
            raise RuntimeError("Expected six timed captions")
        subprocess.run(["ffmpeg", "-v", "error", "-xerror", "-i", str(work / "draft.mp4"),
                        "-f", "null", "-"], check=True, timeout=120)
        proof = {"duration_seconds": duration, "scene_sha256": clips, "renderer": engine.checkpoint,
                 "narration": "fixed original script / eSpeak NG test voice",
                 "scene_settings": "192x320, 49 frames, 24 fps, 8 steps",
                 "draft_sha256": hashlib.sha256((work / "draft.mp4").read_bytes()).hexdigest()}
        (work / "proof.json").write_text(json.dumps(proof, indent=2), encoding="utf-8")
        (work / "draft.mp4").replace(output / "Falcon_LTX_Six_Scene_Short.mp4")
        (work / "proof.json").replace(output / "verification.json")
        print(json.dumps(proof), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    verify(parser.parse_args().output)
