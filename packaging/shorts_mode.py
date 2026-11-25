"""Falcon Shorts prototype: one local draft per calendar day, no auto-publish.
Run with Python 3.10+, Ollama, Windows PowerShell, and FFmpeg on PATH.
No credentials or generated code are executed. Procedural visuals are placeholders.
"""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.request
from shorts_timing import distinct_story, scene_frames, timeline, scene_theme, FPS

ROOT = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "FalconAI"
OUT = ROOT / "shorts"

def paused():
    try:
        return json.loads((ROOT / "gaming_mode.json").read_text()).get("enabled") is True
    except FileNotFoundError:
        return False
    except (ValueError, OSError, AttributeError):
        return True

def check_pause():
    if paused() or (OUT / "STOP").exists():
        raise RuntimeError("Shorts paused by Gaming Mode or STOP")

def script(model):
    check_pause()
    prompt = ("Write a completely original absurdist comedy microstory for a brainrot-style Short. Invent a surreal fictional object-animal character, give it a ridiculous goal, escalate with unexpected visual gags, and end with a surprising punchline. "
              "Return JSON with title and lines (exactly 6 short sentences, "
              "each 8-16 words). Strong hook, rapid escalation, funny payoff. Vary the premise and setting. Do not imitate existing meme characters or voices. "
              "No real people, copyrighted characters, or factual claims.")
    req = urllib.request.Request("http://127.0.0.1:11434/api/generate",
        data=json.dumps(dict(model=model, prompt=prompt, stream=False, format="json")).encode(),
        headers={"Content-Type":"application/json"})
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=120) as r:
        raw = r.read(128001)
    if len(raw)>128000:
        raise ValueError("Model response too large")
    obj = json.loads(json.loads(raw)["response"])
    title, lines = obj["title"], obj["lines"]
    if not isinstance(title,str) or not 1<=len(title)<=90 or not isinstance(lines,list) or len(lines)!=6:
        raise ValueError("Invalid story structure")
    if any(not isinstance(x,str) or not 8<=len(x.split())<=16 or len(x)>120 or not re.fullmatch(r"[A-Za-z0-9 ,.!?'\-]+",x) for x in lines):
        raise ValueError("Invalid story lines; retry")
    return {"title":title, "lines":lines}

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

def create(model):
    check_pause()
    OUT.mkdir(parents=True,exist_ok=True)
    folder=OUT/dt.date.today().isoformat()
    # Atomic directory reservation prevents concurrent duplicate drafts.
    folder.mkdir(exist_ok=False)
    try:
        story=script(model)
        key = distinct_story(story, OUT, folder)
        (folder/"story.json").write_text(json.dumps(story,indent=2),encoding="utf-8")
        # One actual speech recording per scene, not guessed timing.
        (folder/"speak.ps1").write_text("""Add-Type -AssemblyName System.Speech
$s=New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.Rate=-1
$s.SetOutputToWaveFile((Join-Path (Get-Location) 'voice.wav'))
$s.Speak([IO.File]::ReadAllText((Join-Path (Get-Location) 'narration.txt')))
$s.Dispose()
""",encoding="utf-8")
        frames = []
        for i, line in enumerate(story["lines"]):
            check_pause()
            (folder/"narration.txt").write_text(line,encoding="utf-8")
            run(["powershell.exe","-NoProfile","-NonInteractive","-File","speak.ps1"],folder)
            voice = folder / f"voice{i}.wav"
            (folder/"voice.wav").replace(voice)
            frames.append(scene_frames(voice))
        (folder/"captions.srt").write_text(timeline(story["lines"],frames),encoding="utf-8")
        for i, count in enumerate(frames):
            check_pause()
            c0,c1 = scene_theme(key,i)
            # Distinct procedural colors; not yet character artwork.
            run(["ffmpeg","-nostdin","-y","-f","lavfi","-i",
                 f"gradients=s=720x1280:r={FPS}:c0={c0}:c1={c1}:speed=0.03",
                 "-i",f"voice{i}.wav","-map","0:v","-map","1:a",
                 "-af","apad","-t",f"{count/FPS:.6f}","-c:v","libx264",
                 "-preset","veryfast","-pix_fmt","yuv420p","-c:a","aac",
                 "-ar","48000","-ac","1",f"scene{i}.mp4"],folder)
        (folder/"segments.txt").write_text("".join(f"file scene{i}.mp4\n" for i in range(6)),encoding="ascii")
        run(["ffmpeg","-nostdin","-y","-f","concat","-safe","1","-i","segments.txt",
             "-vf","subtitles=captions.srt:force_style='FontSize=20,Alignment=2,MarginV=100'",
             "-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p",
             "-c:a","aac","-movflags","+faststart","draft.mp4"],folder)
        check_pause()
        (folder/"REVIEW_REQUIRED.txt").write_text("Private local draft. Review audio, duration, originality, imagery and disclosure before uploading. No upload performed.",encoding="utf-8")
        return folder
    except BaseException:
        (folder/"FAILED.txt").write_text("Incomplete draft. Inspect before manually removing this folder to retry.",encoding="utf-8")
        raise

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model",default="qwen3:4b")
    args=p.parse_args()
    print(create(args.model))
