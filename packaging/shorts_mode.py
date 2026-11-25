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
        (folder/"story.json").write_text(json.dumps(story,indent=2),encoding="utf-8")
        # Windows installed speech voices; text passed via file, never interpolated.
        (folder/"speak.ps1").write_text("""Add-Type -AssemblyName System.Speech
$s=New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.Rate=-1
$s.SetOutputToWaveFile((Join-Path (Get-Location) 'voice.wav'))
$s.Speak([IO.File]::ReadAllText((Join-Path (Get-Location) 'narration.txt')))
$s.Dispose()
""",encoding="utf-8")
        (folder/"narration.txt").write_text(" ".join(story["lines"]),encoding="utf-8")
        run(["powershell.exe","-NoProfile","-NonInteractive","-File","speak.ps1"],folder)
        # Minimal original motion background, not AI imagery or timed subtitles.
        run(["ffmpeg","-nostdin","-y","-f","lavfi","-i",
             "gradients=s=720x1280:r=30:c0=0x10051f:c1=0x432657:speed=0.03",
             "-i","voice.wav","-map","0:v","-map","1:a","-c:v","libx264",
             "-preset","veryfast","-pix_fmt","yuv420p","-c:a","aac",
             "-shortest","-t","60","draft.mp4"],folder)
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
