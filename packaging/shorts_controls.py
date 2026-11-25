"""Money Mode controls for the existing Falcon window.

No extra AI window or automatic upload. A local draft schedule is opt-in.
"""
from __future__ import annotations
import datetime as dt
import json
import os
from pathlib import Path
import tempfile
import tkinter as tk
from shorts_schedule import due
from shorts_report import ROOT

def enabled(root=ROOT):
    try:
        return json.loads((Path(root)/"shorts_preferences.json").read_text(encoding="utf-8")).get("daily_drafts") is True
    except (OSError, ValueError, AttributeError):
        return False

def set_enabled(value, root=ROOT):
    if type(value) is not bool:
        raise ValueError("Expected boolean preference")
    root=Path(root)
    root.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix="shorts_preferences_",suffix=".tmp",dir=root)
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as out:
            json.dump({"daily_drafts":value},out)
        Path(name).replace(root/"shorts_preferences.json")
    finally:
        Path(name).unlink(missing_ok=True)

def ready_video(root=ROOT, day=None):
    root=Path(root)
    folder=root/"shorts"/(day or dt.date.today()).isoformat()
    video=folder/"draft.mp4"
    if ((folder/"FAILED.txt").exists() or not (folder/"REVIEW_REQUIRED.txt").is_file()
            or not video.is_file() or video.is_symlink() or video.stat().st_size==0):
        return None
    if not video.resolve().is_relative_to(root.resolve()):
        return None
    return video

class MoneyControls:
    def __init__(self, features, root=ROOT):
        self.features=features
        self.root=Path(root)
        self.window=features.app.root
        self.last_attempt=None
        self.choice=tk.BooleanVar(master=self.window,value=enabled(self.root))
        menu_name=self.window.cget("menu")
        if menu_name:
            bar=self.window.nametowidget(str(menu_name))
        else:
            bar=tk.Menu(self.window)
            self.window.configure(menu=bar)
        self.menu=tk.Menu(bar,tearoff=False)
        self.menu.add_command(label="Daily report",command=features._shorts_status)
        self.menu.add_command(label="Generate today's video",command=features._shorts_draft)
        self.menu.add_command(label="Preview today's video",command=self.preview)
        self.menu.add_checkbutton(label="Generate daily at 4 PM while Falcon is open",
                                   variable=self.choice,command=self.toggle)
        self.menu.add_command(label="Pause daily generation and stop current work",command=self.pause)
        bar.add_cascade(label="Money Mode",menu=self.menu)
        self.window.after(10000,self.tick)

    def toggle(self):
        try:
            set_enabled(bool(self.choice.get()),self.root)
            self.features.say("Automatic local drafts "+("enabled" if self.choice.get() else "disabled")+
                              ". No automatic publishing.")
        except OSError:
            self.choice.set(enabled(self.root))
            self.features.say("Could not save Shorts preferences.")

    def pause(self):
        self.choice.set(False)
        self.toggle()
        self.features.stop()

    def preview(self):
        try:
            path=ready_video(self.root)
            if path is None:
                self.features.say("No completed video ready for preview today.")
                return
            os.startfile(str(path))
        except (OSError,AttributeError):
            self.features.say("Could not open the video with the Windows default player.")

    def tick(self):
        try:
            import gaming_mode
            now=dt.datetime.now().astimezone()
            day=now.date()
            if (not self.features.app.busy and not self.features._running and
                self.last_attempt!=day and due(now,self.root/"shorts",
                    enabled=enabled(self.root),
                    paused=gaming_mode.enabled() or (self.root/"shorts"/"STOP").exists())):
                self.last_attempt=day
                self.features._shorts_draft()
        finally:
            self.window.after(60000,self.tick)
