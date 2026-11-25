"""Scene timing and caption primitives for original Falcon Shorts.

Dependency-free, offline, no model-supplied code or shell execution.
"""
from __future__ import annotations
import hashlib
import json
import math
import re
import wave
from pathlib import Path

FPS = 30
MIN_SECONDS = 12
MAX_SECONDS = 59

def story_key(story):
    """Exact normalized narration fingerprint; not a plagiarism detector."""
    normalized = re.sub(r"[^a-z0-9 ]", "", " ".join(story["lines"]).lower())
    normalized = " ".join(normalized.split())
    return hashlib.sha256(normalized.encode()).hexdigest()

def distinct_story(story, root, current):
    key = story_key(story)
    for path in Path(root).glob("????-??-??/story.json"):
        if path.parent == Path(current):
            continue
        old = json.loads(path.read_text(encoding="utf-8"))
        if story_key(old) == key:
            raise ValueError("Duplicate narration from an earlier draft")
    return key

def scene_frames(wav_path):
    with wave.open(str(wav_path), "rb") as audio:
        seconds = audio.getnframes() / audio.getframerate()
    if not 0.3 <= seconds <= 18:
        raise ValueError("Individual narration duration out of bounds")
    return math.ceil((seconds + .18) * FPS)

def timestamps(frame):
    ms = round(frame * 1000 / FPS)
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def timeline(lines, frames):
    if len(lines) != 6 or len(frames) != 6:
        raise ValueError("Exactly six scenes required")
    if any(type(n) is not int or not 10 <= n <= 550 for n in frames):
        raise ValueError("Invalid frame count")
    if not MIN_SECONDS*FPS <= sum(frames) <= MAX_SECONDS*FPS:
        raise ValueError("Short duration out of bounds")
    cursor = 0
    cues = []
    for index, (line, count) in enumerate(zip(lines, frames), 1):
        if not isinstance(line, str) or not re.fullmatch(r"[A-Za-z0-9 ,.!?'\-]{1,120}", line):
            raise ValueError("Unsafe caption text")
        cues.append(f"{index}\n{timestamps(cursor)} --> {timestamps(cursor+count)}\n{line}\n")
        cursor += count
    return "\n".join(cues)

def scene_theme(key, index):
    """Derive a different original motion palette per story and scene."""
    h = hashlib.sha256(f"{key}:{index}".encode()).digest()
    dark = tuple(12 + x % 40 for x in h[:3])
    bright = tuple(100 + x % 145 for x in h[3:6])
    return ("0x" + bytes(dark).hex(), "0x" + bytes(bright).hex())
