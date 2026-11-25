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
import ltx_video

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
        self.ltx_choice = tk.BooleanVar(master=self.window, value=ltx_video.daily_enabled(self.root))
        self.menu.add_command(label="Generate LTX preview clip…", command=self.generate_clip)
        self.menu.add_command(label="Play latest LTX preview", command=self.preview_clip)
        self.menu.add_command(label="Check LTX setup", command=self.check_ai_video)
        self.menu.add_command(label="LTX setup guide", command=self.ltx_help)
        self.menu.add_checkbutton(label="Use LTX-Video for daily drafts", variable=self.ltx_choice,
                                  command=self.toggle_ltx)
        self.menu.add_command(label="Daily report",command=features._shorts_status)
        self.menu.add_command(label="Generate today's video",command=features._shorts_draft)
        self.menu.add_command(label="Preview today's video",command=self.preview)
        from shorts_publish_ui import PublishUI
        self.publisher=PublishUI(self)
        self.menu.add_command(label="Review and upload to YouTube",command=self.publisher.start)
        self.menu.add_command(label="Open YouTube Studio (manual upload)",command=self.manual_upload)
        self.menu.add_command(label="Install Shorts writer",command=self.install_writer)
        self.menu.add_command(label="Get FFmpeg media tools",command=self.media_help)
        self.menu.add_checkbutton(label="Generate daily at 4 PM while Falcon is open",
                                   variable=self.choice,command=self.toggle)
        self.menu.add_command(label="Pause daily generation and stop current work",command=self.pause)
        bar.add_cascade(label="Money Mode",menu=self.menu)
        self.window.after(10000,self.tick)

    def ltx_help(self):
        import webbrowser
        webbrowser.open("https://github.com/Falcomam/FalconAI-Releases/blob/feature/local-ai-video/FALCON_SHORTS_SPRINT.md#local-ltx-video")

    def toggle_ltx(self):
        try:
            ltx_video.set_daily(self.ltx_choice.get(), self.root)
        except OSError:
            self.ltx_choice.set(ltx_video.daily_enabled(self.root))
            self.features.say("Could not save the daily video renderer.")
            return
        mode = "LTX-Video 2B" if self.ltx_choice.get() else "illustrated visuals"
        self.features.say("Daily drafts will use " + mode + ".")

    def _video_work(self, prompt):
        from shorts_mode import paused
        def work(cancel):
            stop = lambda: cancel.is_set() or (self.root / "shorts" / "STOP").exists()
            try:
                engine = ltx_video.LTXVideo.connect(stop, paused)
                if prompt is None:
                    return True, f"Local LTX setup found. Models: {engine.checkpoint}, {engine.encoder}."
                path = engine.render(prompt, self.root / "ltx-previews", stop, paused, preview=True,
                                     progress=lambda message: self.video_status(cancel, message))
                return True, "LTX preview ready. Choose Play latest LTX preview in Money Mode.\n" + str(path)
            except (OSError, ValueError, RuntimeError) as exc:
                return False, str(exc)[:360]
        def complete(result):
            ok, detail = result
            self.features.app.set_status("Ready • LTX-Video" if ok else "LTX-Video needs attention")
            self.features.say(detail)
        self.features._launch("Generating LTX preview…" if prompt else "Checking local LTX setup…",
                              work, complete)

    def video_status(self, cancel, message):
        def update():
            if self.features._event is cancel and not cancel.is_set():
                self.features.app.set_status(message)
        self.window.after(0, update)

    def check_ai_video(self):
        self._video_work(None)

    def generate_clip(self, prompt=None):
        from tkinter import simpledialog
        from shorts_mode import paused
        if self.features.app.busy or self.features._running or self.review_active:
            self.features.say("Finish the current task before generating a preview.")
            return
        if paused() or (self.root / "shorts" / "STOP").exists():
            self.features.say("Local video is paused by STOP or Gaming Mode.")
            return
        if prompt is None:
            self.review_active = True
            try:
                prompt = simpledialog.askstring("Local LTX-Video preview",
                    "Describe a subject, its movement, and the camera shot.", parent=self.window)
            finally:
                self.review_active = False
        if prompt is None:
            return
        if not 1 <= len(prompt.strip()) <= 1600:
            self.features.say("Describe the clip in 1–1600 characters.")
            return
        self._video_work(prompt.strip())

    def preview_clip(self):
        root = self.root / "ltx-previews"
        try:
            videos = (p for p in root.glob("ai-video-*/draft.mp4")
                      if (p.parent / "REVIEW_REQUIRED.txt").is_file()
                      and p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(root.resolve()))
            latest = max(videos, key=lambda p: p.stat().st_mtime_ns, default=None)
            if latest is None:
                self.features.say("Generate an LTX preview clip first.")
                return
            os.startfile(str(latest))
        except (OSError, AttributeError):
            self.features.say("Could not open the preview in the default player.")

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

    def install_writer(self):
        from tkinter import messagebox
        import gaming_mode
        if self.features.app.busy or self.features._running or gaming_mode.enabled():
            self.features.say("Finish current work and turn off Gaming Mode before installing the writer.")
            return
        if not messagebox.askyesno("Install local Shorts writer",
                "Download the official Qwen3 4B Instruct model through local Ollama (about 2.5 GB)? Your existing chat and coding models are unchanged.",
                parent=self.window):
            return
        def work(cancel):
            try:
                import shorts_mode
                return True, shorts_mode.install_story_model(cancel)
            except Exception as exc:
                return False, str(exc)[:240]
        def complete(result):
            ok, detail = result
            self.features.app.set_status("Ready" if ok else "Writer installation failed")
            self.features.say(detail)
        self.features._launch("Installing local Shorts writer...", work, complete)

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
