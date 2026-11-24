"""Falcon Ai local Ollama engine manager (V13.8 development candidate).

This module does not grant any PC permissions to AI models. It checks only the
loopback Ollama endpoint. Starting Ollama requires an explicit confirmed click.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import urllib.error
import urllib.request

API_TAGS = "http://127.0.0.1:11434/api/tags"
DATA = Path(os.getenv("LOCALAPPDATA") or Path.home()) / "FalconAI"
CONFIG = DATA / "engine_model.json"
DEFAULT_CHAT_MODEL = "qwen3:4b"
MODEL_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._/-]{0,119}:[a-zA-Z0-9_.-]{1,48}$")
MAX_RESPONSE = 512_000


class EngineError(RuntimeError):
    """Recoverable error while checking or starting the local AI engine."""


def valid_model(name):
    return isinstance(name, str) and bool(MODEL_PATTERN.fullmatch(name))


def saved_chat_model():
    """Load only a model name, never commands or arbitrary runtime settings."""
    try:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        name = payload.get("chat_model") if isinstance(payload, dict) else None
        if valid_model(name):
            return name
    except (OSError, ValueError, TypeError):
        pass
    return DEFAULT_CHAT_MODEL


def probe(*, timeout=1.8, opener=None):
    """Check the installed local Ollama API without ever downloading a model.

    Errors are a health status, not a reason to show a fake 'Ready' indicator.
    The urllib opener explicitly excludes proxy settings for local requests.
    """
    if opener is None:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({})).open
    request = urllib.request.Request(
        API_TAGS, headers={"Accept": "application/json", "User-Agent": "FalconAi-LocalEngine/13.8"})
    try:
        with opener(request, timeout=timeout) as response:
            raw = response.read(MAX_RESPONSE + 1)
        if len(raw) > MAX_RESPONSE:
            raise EngineError("Ollama model list is larger than expected")
        data = json.loads(raw)
        if not isinstance(data, dict) or not isinstance(data.get("models"), list):
            raise EngineError("Unexpected Ollama model-list response")
        found = []
        for item in data["models"]:
            if isinstance(item, dict):
                model = item.get("name")
                if valid_model(model) and model not in found:
                    found.append(model)
        return {"online": True, "models": tuple(found), "detail": "Ollama is running locally"}
    except (OSError, TimeoutError, ValueError, TypeError, EngineError) as exc:
        detail = str(exc).strip()
        if len(detail) > 170:
            detail = detail[:170]
        return {"online": False, "models": (), "detail": detail or "Ollama is not responding"}


def saved_coding_model():
    """Prefer an explicitly selected coding model, otherwise reuse chat model."""
    try:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        name = payload.get("coding_model") if isinstance(payload, dict) else None
        if valid_model(name):
            return name
    except (OSError, ValueError, TypeError):
        pass
    return saved_chat_model()


def _save_model_field(field, name, *, installed_models):
    """Atomically update one installed-model preference without losing the other."""
    if field not in ("chat_model", "coding_model"):
        raise EngineError("Unsupported model setting")
    if not valid_model(name):
        raise EngineError("Invalid local AI model name")
    if not isinstance(installed_models, (tuple, list)) or name not in installed_models:
        raise EngineError("Install the model in Ollama before selecting it")
    try:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            payload = {}
    except (OSError, ValueError, TypeError):
        payload = {}
    # Ignore unknown config keys, preserving only independently validated models.
    values = {key: payload[key] for key in ("chat_model", "coding_model")
              if valid_model(payload.get(key))}
    values[field] = name
    DATA.mkdir(parents=True, exist_ok=True)
    temporary = CONFIG.with_suffix(".tmp")
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(values, stream, indent=2)
        temporary.replace(CONFIG)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
    return name


def save_chat_model(name, *, installed_models):
    """Select a currently installed chat model without changing the coding model."""
    return _save_model_field("chat_model", name, installed_models=installed_models)


def save_coding_model(name, *, installed_models):
    """Select an installed coding model. This does not download a model."""
    return _save_model_field("coding_model", name, installed_models=installed_models)


def start_ollama(*, confirmed=False, which=shutil.which, popen=subprocess.Popen):
    """Start local Ollama only after the user explicitly confirms in the UI.

    No shell, no arbitrary model arguments, no downloaded executable, and no
    changes to Falcon's computer-control approval or STOP policies.
    """
    if not confirmed:
        raise EngineError("Starting Ollama requires explicit user confirmation")
    if os.name != "nt":
        raise EngineError("Ollama launcher is currently supported on Windows only")
    if probe()["online"]:
        return "already_running"
    executable = which("ollama")
    if not executable or Path(executable).suffix.lower() != ".exe":
        raise EngineError("Ollama.exe was not found on PATH. Open the Ollama app manually.")
    DATA.mkdir(parents=True, exist_ok=True)
    log_path = DATA / "ollama_server.log"
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    try:
        with log_path.open("ab") as output:
            popen([executable, "serve"], cwd=str(Path(executable).parent),
                  stdin=subprocess.DEVNULL, stdout=output, stderr=output,
                  close_fds=True, creationflags=flags)
    except OSError as exc:
        raise EngineError("Could not start Ollama: " + str(exc)[:160]) from exc
    return "start_requested"
