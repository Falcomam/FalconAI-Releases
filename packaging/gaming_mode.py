"""Explicit, reversible gaming mode for Falcon's one-chat local AI.

When selected by the user, game mode blocks new chat/Developer Mode work and
asks local Ollama to unload Falcon's already-loaded models. It does not change
GPU clocks, game processes, drivers, or other programs' permissions. Model
unload is best-effort; the user must verify actual performance on their PC.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import urllib.request

ROOT = Path(os.getenv("LOCALAPPDATA") or Path.home()) / "FalconAI"
SETTINGS = ROOT / "gaming_mode.json"
LOCAL_PS = "http://127.0.0.1:11434/api/ps"
LOCAL_GENERATE = "http://127.0.0.1:11434/api/generate"
MAX_RESPONSE = 256_000


class GamingModeError(RuntimeError):
    """A user-facing configuration or local Ollama error."""


def enabled():
    """Return true only for a valid explicitly saved bool; never infer intent."""
    try:
        value = json.loads(SETTINGS.read_text(encoding="utf-8"))
        return isinstance(value, dict) and value.get("enabled") is True
    except (OSError, ValueError, TypeError):
        return False


def set_enabled(value):
    """Persist a user-controlled pause with atomic replace, not registry edits."""
    if type(value) is not bool:
        raise GamingModeError("Gaming mode must be on or off")
    ROOT.mkdir(parents=True, exist_ok=True)
    temporary = SETTINGS.with_suffix(".tmp")
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            json.dump({"enabled": value}, handle)
        temporary.replace(SETTINGS)
    except OSError as exc:
        raise GamingModeError("Could not save gaming-mode setting: " + str(exc)[:120]) from exc
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
    return value


def _local_request(url, *, payload=None, opener=None):
    """Loopback only, no proxies, bounded response and small fixed timeouts."""
    if url not in (LOCAL_PS, LOCAL_GENERATE):
        raise GamingModeError("Unsupported local Ollama endpoint")
    if opener is None:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({})).open
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url, data=data, headers={"Accept": "application/json",
                                 "Content-Type": "application/json",
                                 "User-Agent": "FalconAi-GamingMode/1.0"})
    try:
        with opener(request, timeout=4) as response:
            raw = response.read(MAX_RESPONSE + 1)
        if len(raw) > MAX_RESPONSE:
            raise GamingModeError("Ollama response is too large")
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise GamingModeError("Unexpected Ollama response")
        return result
    except (OSError, TimeoutError, ValueError) as exc:
        raise GamingModeError("Local Ollama unavailable: " + str(exc)[:120]) from exc


def loaded_models(*, opener=None):
    """Read the names Ollama currently reports loaded, not all installed models."""
    result = _local_request(LOCAL_PS, opener=opener)
    items = result.get("models")
    if not isinstance(items, list):
        raise GamingModeError("Ollama did not provide a running-model list")
    names = set()
    for item in items:
        if isinstance(item, dict):
            name = item.get("name") or item.get("model")
            if isinstance(name, str) and name:
                names.add(name)
    return names


def unload_falcon_models(models, *, opener=None):
    """Unload selected Falcon models only if already loaded.

    Ollama is shared by other clients. This explicit command may also unload
    the same model being used by another Ollama client; it does not stop the
    Ollama service or affect games. Never request a new model load.
    """
    import engine_manager
    requested = set()
    for name in models:
        if not engine_manager.valid_model(name):
            raise GamingModeError("Invalid selected Falcon model name")
        requested.add(name)
    before = loaded_models(opener=opener)
    targets = sorted(before & requested)
    failed = []
    for model in targets:
        try:
            _local_request(LOCAL_GENERATE,
                           payload={"model": model, "keep_alive": 0},
                           opener=opener)
        except GamingModeError:
            failed.append(model)
    try:
        remaining = sorted(loaded_models(opener=opener) & requested)
        verified = not remaining and not failed
    except GamingModeError:
        remaining = []
        verified = False
    return {"requested": tuple(targets), "failed": tuple(failed),
            "remaining": tuple(remaining), "verified": verified}
