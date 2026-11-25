"""Falcon Shorts prototype: one local draft per calendar day, no auto-publish.
Run with Python 3.10+, Ollama, Windows PowerShell, and FFmpeg on PATH.
Daily visuals use the selected local renderer. LTX uses ComfyUI; illustrated drafts use Pillow.
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
import urllib.error
import socket
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

SHORTS_MODEL = "qwen3:4b-instruct-2507-q4_K_M"

def preferred_story_model(selected, installed):
    # A separate non-thinking writer, without changing the user's main chat model.
    if SHORTS_MODEL in installed:
        return SHORTS_MODEL
    if "qwen3:4b-instruct" in installed:
        return "qwen3:4b-instruct"
    return selected

def install_story_model(cancel):
    """Pull only the fixed official writer after UI confirmation; no shell."""
    import engine_manager
    state = engine_manager.probe(timeout=3)
    if not state["online"]:
        raise RuntimeError("Start Ollama using Tools > AI Engine first.")
    if preferred_story_model("", state["models"]):
        return "Shorts writer already installed."
    exe = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/Ollama/ollama.exe"
    if not exe.is_file():
        raise RuntimeError("Official Ollama installation not found. Open the Ollama app to install "+SHORTS_MODEL)
    env = dict(os.environ, OLLAMA_HOST="http://127.0.0.1:11434")
    if cancel.is_set() or paused():
        raise RuntimeError("Model download paused.")
    with subprocess.Popen([str(exe), "pull", SHORTS_MODEL], cwd=str(exe.parent),
                          env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL, creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0)) as proc:
        deadline = time.monotonic() + 3600
        try:
            while proc.poll() is None:
                if cancel.is_set() or paused() or time.monotonic() > deadline:
                    raise RuntimeError("Writer download stopped or timed out.")
                time.sleep(.5)
            if proc.returncode:
                raise RuntimeError("Ollama could not download the writer. Check network and available disk space.")
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
    if not preferred_story_model("", engine_manager.probe(timeout=3)["models"]):
        raise RuntimeError("Download finished, but Ollama did not report the writer installed.")
    return "Shorts writer installed. Generate today's video."

def story_schema():
    return {
        "type": "object", "required": ["title", "lines", "scenes"],
        "additionalProperties": False,
        "properties": {
            "title": {"type": "string", "minLength": 1, "maxLength": 90},
            "lines": {"type": "array", "minItems": 6, "maxItems": 6,
                      "items": {"type": "string", "minLength": 1, "maxLength": 120}},
            "scenes": {"type": "array", "minItems": 6, "maxItems": 6,
                       "items": {"type": "object", "required": ["setting", "action"],
                                 "additionalProperties": False, "properties": {
                                     "setting": {"enum": sorted(SETTINGS)},
                                     "action": {"enum": sorted(ACTIONS)}}}}
        }
    }

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
                data=json.dumps(dict(model=model, prompt=prompt, stream=False, think=False, format=story_schema(), keep_alive=0, options={"num_ctx":4096,"num_predict":1024,"temperature":0.55})).encode(),
                headers={"Content-Type":"application/json"})
            with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=120) as r:
                raw = r.read(128001)
            if len(raw)>128000:
                raise ValueError("Model response too large")
            result = json.loads(raw)
            if result.get("done_reason") == "length":
                raise ValueError("Narration hit the generation budget")
            return validate_story(json.loads(result["response"]))
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504):
                raise RuntimeError(f"Ollama HTTP {exc.code}; check selected model in AI Engine.") from None
            if attempt == 2:
                raise RuntimeError(f"Ollama HTTP {exc.code} after three bounded attempts. Use Money Mode > Install Shorts writer; no upload occurred.") from None
        except (urllib.error.URLError, TimeoutError, socket.timeout):
            if attempt == 2:
                raise RuntimeError("Local Ollama unavailable or timed out after three attempts. No upload occurred.") from None
        except (ValueError, KeyError, TypeError, AttributeError):
            if attempt == 2:
                raise ValueError("Qwen returned invalid narration or scenes three times. Use Money Mode > Install Shorts writer if not installed. No video was uploaded.") from None
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

def render_video(folder, story, key, frames, *, ltx=None, progress=lambda message: None):
    """Render existing six voice WAV files; reusable by offline integration tests."""
    (folder/"captions.srt").write_text(timeline(story["lines"],frames),encoding="utf-8")
    for i, count in enumerate(frames):
        check_pause()
        scene = story["scenes"][i]
        if ltx is None:
            render_scene(key,i,scene["setting"],scene["action"],folder/f"art{i}.png")
            visual = ["-loop","1","-framerate",str(FPS),"-i",f"art{i}.png"]
            video_filter = "scale=1440:2560,zoompan=z=1.04+0.0004*on:x=iw/2-iw/zoom/2:y=ih/2-ih/zoom/2:d=1:s=720x1280:fps=30"
        else:
            import ltx_video
            cancel = _CANCEL.get()
            stop = lambda: (cancel is not None and cancel.is_set()) or (OUT/"STOP").exists()
            clip = folder / f"ltx{i}.mp4"
            progress(f"Generating LTX scene {i+1} of 6")
            ltx.render(ltx_video.scene_prompt(story, i), clip, stop, paused,
                       seed=(int(key[:15], 16) + i))
            visual = ["-i", clip.name]
            speed = (count - 1) * ltx_video.FPS / ((ltx_video.FRAMES - 1) * FPS)
            video_filter = (f"setpts={speed:.9f}*PTS,fps={FPS},scale=720:1280:"
                            "force_original_aspect_ratio=increase,crop=720:1280,setsar=1,"
                            "tpad=stop_mode=clone:stop_duration=1")
        run(["ffmpeg","-nostdin","-y",*visual,
             "-i",f"voice{i}.wav","-map","0:v","-map","1:a","-vf",video_filter,
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

def create(model, day=None, *, cancel=None, progress=lambda message: None):
    """Run in an existing app worker; cancellation is scoped to that worker."""
    token = _CANCEL.set(cancel)
    try:
        return _create(model, day, progress)
    finally:
        _CANCEL.reset(token)

def _create(model, day, progress):
    check_pause()
    preflight()
    import ltx_video
    ltx = None
    if ltx_video.daily_enabled(ROOT):
        cancel = _CANCEL.get()
        progress("Checking local LTX setup")
        ltx = ltx_video.LTXVideo.connect(
            lambda: (cancel is not None and cancel.is_set()) or (OUT/"STOP").exists(), paused)
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
        render_video(folder, story, key, frames, ltx=ltx, progress=progress)
        check_pause()
        (folder/"REVIEW_REQUIRED.txt").write_text(("LTX-Video 2B" if ltx else "Illustrated") + " local draft. Review audio, duration, originality, imagery and disclosure before uploading.", encoding="utf-8")
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
