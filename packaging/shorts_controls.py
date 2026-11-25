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
        self.session_paused=False
        self.review_active=False
        self.choice=tk.BooleanVar(master=self.window,value=enabled(self.root))
        menu_name=self.window.cget("menu")
        if menu_name:
            bar=self.window.nametowidget(str(menu_name))
        else:
            bar=tk.Menu(self.window)
            self.window.configure(menu=bar)
        self.menu=tk.Menu(bar,tearoff=False)
        self.menu.add_command(label="Check local AI video engine",command=self.check_ai_video)
        self.menu.add_command(label="Daily report",command=features._shorts_status)
        self.menu.add_command(label="Generate today's video",command=features._shorts_draft)
        self.menu.add_command(label="Preview today's video",command=self.preview)
        from shorts_publish_ui import PublishUI
        self.publisher=PublishUI(self)
        self.menu.add_command(label="Review and upload to YouTube",command=self.publisher.start)
        self.menu.add_command(label="Open YouTube Studio (manual upload)",command=self.manual_upload)
        self.menu.add_command(label="Get FFmpeg media tools",command=self.media_help)
        self.menu.add_checkbutton(label="Generate daily at 4 PM while Falcon is open",
                                   variable=self.choice,command=self.toggle)
        self.menu.add_command(label="Pause daily generation and stop current work",command=self.pause)
        bar.add_cascade(label="Money Mode",menu=self.menu)
        self.window.after(10000,self.tick)

    def check_ai_video(self):
        import threading
        from comfy_video import ComfyVideo
        from queue import Queue, Empty
        results=Queue()
        def worker():
            try:
                ComfyVideo().available()
                results.put("Local ComfyUI is reachable. Video workflow and GPU compatibility are not yet verified.")
            except Exception as exc:
                results.put("Local ComfyUI unavailable: "+str(exc))
        def poll():
            try:
                self.features.say(results.get_nowait())
            except Empty:
                self.window.after(200,poll)
        threading.Thread(target=worker,daemon=True).start()
        self.window.after(200,poll)

    def toggle(self):
        try:
            set_enabled(bool(self.choice.get()),self.root)
            self.session_paused=not bool(self.choice.get())
            self.features.say("Automatic local drafts "+("enabled" if self.choice.get() else "disabled")+
                              ". No automatic publishing.")
        except OSError:
            self.choice.set(enabled(self.root))
            self.features.say("Could not save Shorts preferences.")

    def pause(self):
        self.session_paused=True
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

    def media_help(self):
        import webbrowser
        webbrowser.open("https://ffmpeg.org/download.html")
        self.features.say("Install FFmpeg and ffprobe from a trusted distribution linked there, then restart Falcon. No software was installed by Falcon.")

    def manual_upload(self):
        from tkinter import messagebox
        import webbrowser
        if self.features.app.busy or self.features._running or self.review_active:
            self.features.say("Finish current work before starting a manual upload.")
            return
        self.review_active=True
        try:
            video=ready_video(self.root)
            if video is None:
                self.features.say("No completed video ready for manual upload.")
                return
            ledger=video.parent/"upload_attempt.json"
            if ledger.exists():
                self.features.say("An upload or handoff was already recorded. Check YouTube Studio before uploading anything.")
                webbrowser.open("https://studio.youtube.com/")
                return
            if not messagebox.askyesno("Manual YouTube handoff",
                    "Open the draft folder and YouTube Studio? You must watch the video, check rights and the correct channel, and choose audience, disclosure and visibility in Studio. This records a manual handoff and blocks Falcon's API upload for this draft to prevent duplicates. It does not upload anything.",
                    parent=self.window):
                return
            # Same exclusive ledger as API upload; only one route may reserve it.
            with ledger.open("x",encoding="utf-8") as out:
                json.dump({"state":"manual_handoff","file":"draft.mp4"},out)
            os.startfile(str(video.parent))
            webbrowser.open("https://studio.youtube.com/")
            self.features.say("Manual handoff recorded. No upload performed by Falcon. Check Studio for final status. Video: "+str(video))
        except (OSError,AttributeError):
            self.features.say("Could not complete the manual handoff. Check the draft folder and YouTube Studio before trying another upload.")
        finally:
            self.review_active=False

    def tick(self):
        try:
            import gaming_mode
            now=dt.datetime.now().astimezone()
            day=now.date()
            if (not self.session_paused and not self.review_active and
                not self.features.app.busy and not self.features._running and
                self.last_attempt!=day and due(now,self.root/"shorts",
                    enabled=enabled(self.root),
                    paused=gaming_mode.enabled() or (self.root/"shorts"/"STOP").exists())):
                self.last_attempt=day
                self.features._shorts_draft()
        finally:
            self.window.after(60000,self.tick)
