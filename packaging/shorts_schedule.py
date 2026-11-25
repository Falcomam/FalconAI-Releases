"""Opt-in daily draft scheduling primitives. No network or upload actions."""
import datetime as dt
from pathlib import Path

def due(now, root, *, enabled, paused, hour=16):
    """One attempt after local preparation hour; no previous-day catchup.

    Caller supplies aware local time. create() still reserves the date
    atomically, so concurrent ticks cannot produce two drafts.
    Failed or interrupted reservations require inspection, not auto retry.
    """
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Local timezone-aware datetime required")
    if type(hour) is not int or not 0 <= hour <= 23:
        raise ValueError("Invalid preparation hour")
    if not enabled or paused or now.hour < hour:
        return False
    return not (Path(root)/now.date().isoformat()).exists()
