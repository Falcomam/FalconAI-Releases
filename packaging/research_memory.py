"""Local, attributable research memory for Falcon's future research agent.

Stores short public-source notes in a Falcon-owned JSON file. Does not store
credentials, prompts, page HTML, private documents or external app data. This is
a storage primitive, not a model-training feature or an autonomous research loop.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re

from developer_workspace import ProjectError

DATA = Path(os.getenv("LOCALAPPDATA") or Path.home()) / "FalconAI"
MEMORY_FILE = DATA / "research_notes.json"
MAX_NOTES = 100
MAX_BYTES = 160_000
MAX_TEXT = 1800
MAX_TITLE = 200
MAX_URL = 400
NOTE_KEY = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")


def _validate_note(note):
    if not isinstance(note, dict) or set(note) != {"key", "topic", "summary", "sources", "saved_at"}:
        raise ProjectError("Research memory must have known fields")
    key, topic, summary = note["key"], note["topic"], note["summary"]
    if not isinstance(key, str) or not NOTE_KEY.fullmatch(key):
        raise ProjectError("Invalid research note key")
    if not isinstance(topic, str) or not 1 <= len(topic.strip()) <= MAX_TITLE:
        raise ProjectError("Invalid research topic")
    if not isinstance(summary, str) or not 1 <= len(summary.strip()) <= MAX_TEXT:
        raise ProjectError("Invalid research summary")
    sources = note["sources"]
    if not isinstance(sources, list) or not 1 <= len(sources) <= 5:
        raise ProjectError("Research note needs one to five sources")
    for source in sources:
        if not isinstance(source, dict) or set(source) != {"title", "url"}:
            raise ProjectError("Invalid research source metadata")
        if (not isinstance(source["title"], str) or not 1 <= len(source["title"]) <= MAX_TITLE or
                not isinstance(source["url"], str) or not 1 <= len(source["url"]) <= MAX_URL or
                not source["url"].startswith("https://en.wikipedia.org/?curid=") or
                not source["url"].removeprefix("https://en.wikipedia.org/?curid=").isdigit()):
            raise ProjectError("Unsupported research citation URL")
    if not isinstance(note["saved_at"], str) or len(note["saved_at"]) > 40:
        raise ProjectError("Invalid research note date")
    return note


def load_notes(*, filename=MEMORY_FILE):
    file = Path(filename)
    if not file.exists():
        return ()
    if file.is_symlink() or not file.is_file() or file.stat().st_size > MAX_BYTES:
        raise ProjectError("Research memory file is unsafe or oversized")
    try:
        notes = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ProjectError("Research memory could not be read") from exc
    if not isinstance(notes, list) or len(notes) > MAX_NOTES:
        raise ProjectError("Research memory is malformed")
    for note in notes:
        _validate_note(note)
    if len({note["key"] for note in notes}) != len(notes):
        raise ProjectError("Duplicate research note keys")
    return tuple(notes)


def save_note(key, topic, summary, sources, *, filename=MEMORY_FILE):
    """Store an attributed short note after a higher-level consent decision.

    This primitive does not decide which user queries may be remembered.
    Agents must not indiscriminately retain sensitive user prompts.
    """
    if not isinstance(sources, (list, tuple)):
        raise ProjectError("Research sources must be a collection")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    note = {"key": key, "topic": topic, "summary": summary,
            "sources": [{"title": item["title"], "url": item["url"]}
                        for item in sources if isinstance(item, dict) and
                        "title" in item and "url" in item],
            "saved_at": now}
    _validate_note(note)
    file = Path(filename)
    folder = file.parent
    if folder.is_symlink() or file.is_symlink():
        raise ProjectError("Redirected research memory is not allowed")
    existing = list(load_notes(filename=file))
    existing = [old for old in existing if old["key"] != key]
    existing.append(note)
    if len(existing) > MAX_NOTES:
        existing = existing[-MAX_NOTES:]
    raw = json.dumps(existing, ensure_ascii=False, indent=2).encode("utf-8")
    if len(raw) > MAX_BYTES:
        raise ProjectError("Research memory capacity exceeded")
    folder.mkdir(parents=True, exist_ok=True)
    # Exclusive temporary creation; never follow an attacker-supplied symlink.
    temp = file.with_name(file.name + ".tmp")
    with temp.open("xb") as stream:
        stream.write(raw)
    try:
        temp.replace(file)
    finally:
        temp.unlink(missing_ok=True)
    return note


def forget_note(key, *, filename=MEMORY_FILE):
    if not isinstance(key, str) or not NOTE_KEY.fullmatch(key):
        raise ProjectError("Invalid research note key")
    existing = list(load_notes(filename=filename))
    retained = [note for note in existing if note["key"] != key]
    if len(retained) == len(existing):
        return False
    file = Path(filename)
    raw = json.dumps(retained, ensure_ascii=False, indent=2).encode("utf-8")
    temp = file.with_name(file.name + ".tmp")
    with temp.open("xb") as stream:
        stream.write(raw)
    try:
        temp.replace(file)
    finally:
        temp.unlink(missing_ok=True)
    return True
