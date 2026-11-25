"""Falcon Shorts prototype: one local draft per calendar day, no auto-publish.
Run with Python 3.10+, Ollama, Windows PowerShell, and FFmpeg on PATH.
No credentials or generated code are executed. Procedural cartoons are original artwork, not generative AI video. Pillow is required.
"""
import argparse
from contextvars import ContextVar
import datetime as dt
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.request
import time
import shutil
from shorts_upload import probe
from shorts_schedule import due
from shorts_timing import distinct_story, scene_frames, timeline, FPS
from shorts_visuals import render_scene, SETTINGS, ACTIONS

ROOT = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "FalconAI"
OUT = ROOT / "shorts"
_CANCEL = ContextVar("shorts_cancel", default=None)

def paused():
    try:
        return json.loads((ROOT / "gaming_mode.json").read_text()).get("enabled") is True
    except FileNotFoundError:
        return False
    except (ValueError, OSError, AttributeError):
        return True

def check_pause():
    cancel = _CANCEL.get()
    if (cancel is not None and cancel.is_set()) or paused() or (OUT / "STOP").exists():
        raise RuntimeError("Shorts paused by Gaming Mode or STOP")

def script(model):
    check_pause()
    prompt = ("Write a completely original absurdist comedy microstory for a brainrot-style Short. Invent a surreal fictional object-animal character, give it a ridiculous goal, escalate with unexpected visual gags, and end with a surprising punchline. "
              "Return JSON with title and lines (exactly 6 short sentences, "
              "each 8-14 words), and scenes (exactly 6 objects each with setting and action). Settings: kitchen, city, moon, gym, ocean, desert, office. Actions: stand, jump, run, panic, celebrate, fall. Match each visual to its narration. Strong hook, rapid escalation, funny payoff. Vary the premise and setting. Do not imitate existing meme characters or voices. "
              "No real people, copyrighted characters, or factual claims.")
    for attempt in range(3):
        check_pause()
        try:
            req = urllib.request.Request("http://127.0.0.1:11434/api/generate",
                data=json.dumps(dict(model=model, prompt=prompt, stream=False, format="json")).encode(),
                headers={"Content-Type":"application/json"})
            with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=120) as r:
                raw = r.read(128001)
            if len(raw)>128000:
                raise ValueError("Model response too large")
            return validate_story(json.loads(json.loads(raw)["response"]))
        except (ValueError, KeyError, TypeError):
            if attempt == 2:
                raise ValueError("Qwen returned invalid narration or scenes three times. No video was uploaded.") from None
            prompt += " Repair the output: six plain English narration sentences, 6-18 words each, no emoji or markup, six valid scene objects."
    raise AssertionError("Unreachable")

def validate_story(obj):
    if not isinstance(obj, dict):
        raise ValueError("Invalid story structure")
    title, lines = obj.get("title"), obj.get("lines")
    if not isinstance(title,str) or not 1<=len(title.strip())<=90 or not isinstance(lines,list) or len(lines)!=6:
        raise ValueError("Invalid story structure")
    clean = []
    punctuation = str.maketrans({"’":"'","‘":"'","“":"","”":"","—":"-","–":"-","…":"...","\"":"",";":",",":":","})
    for line in lines:
        if not isinstance(line,str):
            raise ValueError("Invalid story line type")
        line = " ".join(line.translate(punctuation).split())
        if not 6<=len(line.split())<=18 or not re.fullmatch(r"[A-Za-z0-9 ,.!?'\-]{1,120}",line):
            raise ValueError("Invalid story lines")
        clean.append(line)
    scenes = obj.get("scenes")
    if not isinstance(scenes,list) or len(scenes)!=6 or any(not isinstance(s,dict) or s.get("setting") not in SETTINGS or s.get("action") not in ACTIONS for s in scenes):
        raise ValueError("Invalid scene choices")
    return {"title":title.strip(), "lines":clean, "scenes":scenes}


def run(cmd, cwd):
    check_pause()
    import time
    with subprocess.Popen(cmd,cwd=cwd,stdin=subprocess.DEVNULL,
                          stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL) as p:
        deadline=time.monotonic()+180
        try:
            while p.poll() is None:
                check_pause()
                if time.monotonic()>deadline:
                    raise TimeoutError("Render step timed out")
                time.sleep(.5)
            if p.returncode:
                raise RuntimeError("Media tool failed: "+cmd[0])
        finally:
            if p.poll() is None:
                p.terminate()
                try: p.wait(timeout=5)
                except subprocess.TimeoutExpired: p.kill(); p.wait()

def preflight():
    missing = [name for name in ("ffmpeg", "ffprobe", "powershell.exe") if not shutil.which(name)]
    if missing:
        raise RuntimeError("Required tools not found on PATH: " + ", ".join(missing))

def render_video(folder, story, key, frames):
    """Render existing six voice WAV files; reusable by offline integration tests."""
    (folder/"captions.srt").write_text(timeline(story["lines"],frames),encoding="utf-8")
    for i, count in enumerate(frames):
        check_pause()
        scene = story["scenes"][i]
        render_scene(key,i,scene["setting"],scene["action"],folder/f"art{i}.png")
        run(["ffmpeg","-nostdin","-y","-loop","1","-framerate",str(FPS),"-i",f"art{i}.png",
             "-i",f"voice{i}.wav","-map","0:v","-map","1:a",
             "-vf","scale=1440:2560,zoompan=z=1.04+0.0004*on:x=iw/2-iw/zoom/2:y=ih/2-ih/zoom/2:d=1:s=720x1280:fps=30",
             "-af","apad","-t",f"{count/FPS:.6f}","-c:v","libx264",
             "-preset","veryfast","-pix_fmt","yuv420p","-c:a","aac",
             "-ar","48000","-ac","1",f"scene{i}.mp4"],folder)
    (folder/"segments.txt").write_text("".join(f"file scene{i}.mp4\n" for i in range(6)),encoding="ascii")
    run(["ffmpeg","-nostdin","-y","-f","concat","-safe","1","-i","segments.txt",
         "-vf","subtitles=captions.srt:force_style='FontSize=20,Alignment=2,MarginV=100'",
         "-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p",
         "-c:a","aac","-movflags","+faststart","draft.mp4"],folder)
    check_pause()
    duration = probe(folder/"draft.mp4")
    if abs(duration-sum(frames)/FPS)>1:
        raise ValueError("Rendered duration differs from narration timeline")
    return duration

def create(model, day=None, *, cancel=None):
    """Run in an existing app worker; cancellation is scoped to that worker."""
    token = _CANCEL.set(cancel)
    try:
        return _create(model, day)
    finally:
        _CANCEL.reset(token)

def _create(model, day=None):
    check_pause()
    preflight()
    OUT.mkdir(parents=True,exist_ok=True)
    folder=OUT/(day or dt.date.today()).isoformat()
    # Atomic directory reservation prevents concurrent duplicate drafts.
    if (folder.is_dir() and not folder.is_symlink() and
            folder.resolve().parent == OUT.resolve() and
            (folder/"FAILED.txt").is_file() and
            not (folder/"REVIEW_REQUIRED.txt").exists() and
            not (folder/"upload_attempt.json").exists()):
        # Preserve failed work; only incomplete, never-reviewed attempts qualify.
        import uuid
        archive = OUT / (".failed-" + folder.name + "-" + uuid.uuid4().hex)
        folder.rename(archive)
    folder.mkdir(exist_ok=False)
    try:
        story=script(model)
        check_pause()
        key = distinct_story(story, OUT, folder)
        (folder/"story.json").write_text(json.dumps(story,indent=2),encoding="utf-8")
        # One actual speech recording per scene, not guessed timing.
        speech_command = """$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$s=New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.Rate=-1
$s.SetOutputToWaveFile((Join-Path (Get-Location) 'voice.wav'))
$s.Speak([IO.File]::ReadAllText((Join-Path (Get-Location) 'narration.txt')))
$s.Dispose()
"""
        frames = []
        for i, line in enumerate(story["lines"]):
            check_pause()
            (folder/"narration.txt").write_text(line,encoding="utf-8")
            run(["powershell.exe","-NoProfile","-NonInteractive","-Command",speech_command],folder)
            voice = folder / f"voice{i}.wav"
            (folder/"voice.wav").replace(voice)
            frames.append(scene_frames(voice))
        render_video(folder, story, key, frames)
        check_pause()
        (folder/"REVIEW_REQUIRED.txt").write_text("Private local draft. Review audio, duration, originality, imagery and disclosure before uploading. No upload performed.",encoding="utf-8")
        return folder
    except BaseException:
        (folder/"FAILED.txt").write_text("Incomplete draft. Inspect before manually removing this folder to retry.",encoding="utf-8")
        raise

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model",default="qwen3:4b")
    p.add_argument("--watch",action="store_true",help="Explicitly run the local draft scheduler while this process stays open")
    p.add_argument("--prepare-hour",type=int,default=16,choices=range(24))
    args=p.parse_args()
    if not args.watch:
        print(create(args.model))
    else:
        print("Daily local draft watch active; Ctrl+C exits. No automatic uploads.",flush=True)
        while True:
            now=dt.datetime.now().astimezone()
            if due(now,OUT,enabled=True,paused=paused() or (OUT/"STOP").exists(),hour=args.prepare_hour):
                try:
                    print(create(args.model,now.date()),flush=True)
                except Exception as exc:
                    print("Draft attempt failed: "+type(exc).__name__,flush=True)
            time.sleep(60)
