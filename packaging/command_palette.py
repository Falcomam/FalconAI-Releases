"""Falcon's single-chat command discovery and Minecraft-style Tab completion.

Suggestions only edit Falcon's existing chat input; they NEVER dispatch,
execute, approve, launch, or change model permissions on their own.
"""
from __future__ import annotations
from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Command:
    label: str
    insert: str


# Command templates are existing Falcon chat commands. Order is intentional:
# completion favors the most useful project and model commands first.
GROUPS = (
    ("AI & Models", (
        Command("Check Ollama connection", "/engine status"),
        Command("List installed models", "/engine list"),
        Command("Choose installed model", "/engine use "),
        Command("Start local Ollama", "/engine start"),
        Command("Gaming Mode ON (pause AI and release Ollama VRAM)", "/engine gaming on"),
        Command("Gaming Mode OFF (resume AI)", "/engine gaming off"),
        Command("Choose installed coding model", "/engine use-code "),
        Command("Show selected coding model", "/engine coding"),
    )),
    ("Coding & Projects", (
        Command("Create a website", "/project website "),
        Command("Create Python project", "/project python "),
        Command("Create Minecraft Fabric mod", "/project fabric_mod "),
        Command("Check project source (static only)", "/project check"),
        Command("Review generated files", "/project review"),
        Command("Inspect a source file", "/project show "),
        Command("Approve reviewed files", "/project approve"),
        Command("Reject project", "/project reject"),
        Command("Make a Python code draft", "/build "),
        # Packaged app self-patching is disabled: omit legacy /upgrade shortcut.
    )),
    ("PC & Research", (
        Command("Plan a PC task", "/do "),
        Command("Analyze current screen", "/screen"),
        Command("Research public web sources", "/research "),
    )),
    ("Help & Settings", (
        Command("List Falcon commands", "/help"),
        Command("Falcon status", "/status"),
        Command("Voice controls", "/voice"),
        Command("Notification controls", "/alerts"),
        Command("Improve status", "/progress status"),
        Command("Review core proposal", "/review"),
        Command("Approve core proposal", "/approve"),
        Command("Reject core proposal", "/reject"),
        Command("Sandbox status", "/sandbox"),
        Command("STOP current work", "/stop"),
    )),
)
COMMANDS = tuple(cmd.insert for _, entries in GROUPS for cmd in entries)
assert len(COMMANDS) == len(set(COMMANDS))


def matching_commands(text):
    """Pure suggestion provider: prefix matches only; no model or PC calls."""
    if not isinstance(text, str) or not text.startswith("/") or "\n" in text:
        return ()
    return tuple(cmd for cmd in COMMANDS if cmd.casefold().startswith(text.casefold()))


class TabCompletion:
    """State for the sequence: complete common prefix, then cycle choices."""
    def __init__(self):
        self._last = None
        self._items = ()
        self._position = -1

    def reset(self):
        self._last = None
        self._items = ()
        self._position = -1

    def complete(self, text, reverse=False):
        """Return new text or None if regular Tab navigation should be used.

        Never discards freeform content or text typed after a full command.
        Holding Shift reverses through the matching completions.
        """
        if not isinstance(text, str):
            self.reset()
            return None
        if text == self._last and self._items:
            self._position = ((self._position + (-1 if reverse else 1))
                              % len(self._items))
            result = self._items[self._position]
            self._last = result
            return result

        matches = matching_commands(text)
        if not matches:
            self.reset()
            return None

        self._items = matches
        shared = os.path.commonprefix(matches)
        # All command names are lowercase, keep canonical casing.
        if len(matches) > 1 and len(shared) > len(text):
            self._position = -1 if not reverse else len(matches) - 1
            self._last = shared
            return shared

        self._position = len(matches) - 1 if reverse else 0
        self._last = matches[self._position]
        return self._last

    def suggestion(self, text):
        matches = matching_commands(text)
        if not matches:
            return "TAB completes /commands  •  ⌘ Commands shows organized shortcuts"
        if len(matches) == 1:
            return "TAB → " + matches[0]
        head = ", ".join(matches[:3])
        if len(matches) > 3:
            head += f"  (+{len(matches) - 3} more)"
        return "TAB completes • TAB again cycles: " + head


class EntryController:
    """Bind to the existing Falcon Tk Entry, without opening another window."""
    def __init__(self, entry, hint_label):
        self.entry = entry
        self.hint_label = hint_label
        self.completion = TabCompletion()
        entry.bind("<Tab>", lambda event: self._tab(False))
        entry.bind("<Shift-Tab>", lambda event: self._tab(True))
        entry.bind("<ISO_Left_Tab>", lambda event: self._tab(True))
        entry.bind("<KeyRelease>", lambda event: self.refresh_hint())
        self.refresh_hint()

    def insert(self, template):
        if template not in COMMANDS:
            raise ValueError("Unknown command shortcut")
        self.completion.reset()
        self.entry.delete(0, "end")
        self.entry.insert(0, template)
        self.entry.icursor("end")
        self.entry.focus_set()
        self.refresh_hint()

    def refresh_hint(self):
        try:
            text = self.entry.get()
            tip = self.completion.suggestion(text)
            # Long suggestions may be visually truncated by a narrow window.
            self.hint_label.configure(text=tip[:120])
        except Exception:
            pass

    def _tab(self, backwards):
        try:
            # Never modify selected text or mid-line arguments.
            text = self.entry.get()
            if self.entry.index("insert") != len(text):
                return None
            replacement = self.completion.complete(text, reverse=backwards)
            if replacement is None:
                return None
            self.entry.delete(0, "end")
            self.entry.insert(0, replacement)
            self.entry.icursor("end")
            self.refresh_hint()
            return "break"
        except Exception:
            return None
