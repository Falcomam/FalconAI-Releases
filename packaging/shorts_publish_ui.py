"""Reviewed upload from Falcon's existing Money Mode menu.

Authorization lives only in memory for the selected upload. Never publishes
on startup, on a timer, or merely because the owner enabled daily drafts.
"""
from __future__ import annotations
import datetime as dt
import json
import os
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
import webbrowser
import shorts_upload as api

NOTICE = ("By clicking 'upload,' you certify that the content you are uploading "
          "complies with the YouTube Terms of Service (including the YouTube "
          "Community Guidelines) at https://www.youtube.com/t/terms. Please be "
          "sure not to violate others' copyright or privacy rights.")

def oauth_config(path):
    with Path(path).open('rb') as stream:
        raw = stream.read(65537)
    if len(raw)>65536:
        raise ValueError('OAuth configuration too large')
    config=json.loads(raw)
    data=config.get('installed') if isinstance(config,dict) else None
    if (not isinstance(data,dict) or data.get('auth_uri') not in
            ('https://accounts.google.com/o/oauth2/auth','https://accounts.google.com/o/oauth2/v2/auth')
            or data.get('token_uri')!='https://oauth2.googleapis.com/token'
            or not isinstance(data.get('client_id'),str)
            or not data['client_id'].endswith('.apps.googleusercontent.com')
            or not isinstance(data.get('client_secret'),str)):
        raise ValueError('Choose a Google desktop OAuth client JSON file')
    return {'installed':{k:data[k] for k in ('auth_uri','token_uri','client_id','client_secret')}}

def connect(path):
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    import google_auth_httplib2
    import httplib2
    flow=InstalledAppFlow.from_client_config(oauth_config(path),api.SCOPES,autogenerate_code_verifier=True)
    credentials=flow.run_local_server(host='127.0.0.1',port=0,open_browser=True,timeout_seconds=180)
    transport=google_auth_httplib2.AuthorizedHttp(credentials,http=httplib2.Http(timeout=30))
    return build('youtube','v3',http=transport,cache_discovery=False)

def plan_upload(title, description, visibility, kids, synthetic, category, when, certified, previewed):
    if certified is not True or previewed is not True:
        raise ValueError('Review the actual video and certify it before uploading')
    if kids not in ('yes','no') or synthetic not in ('yes','no'):
        raise ValueError('Select both audience and synthetic media disclosure')
    publish_at=dt.datetime.fromisoformat(when.strip()) if when.strip() else None
    return api.metadata(title,description,visibility,kids=='yes',synthetic=='yes',category,publish_at)

class ReviewDialog(simpledialog.Dialog):
    def __init__(self,parent,video,title,channel_id,channel_name):
        self.video=video; self.suggested=title; self.channel_id=channel_id; self.channel_name=channel_name
        self.preview_opened=False
        super().__init__(parent,title='Review and schedule YouTube Short')

    def body(self,frame):
        frame.columnconfigure(1,weight=1)
        ttk.Label(frame,text='Channel: '+self.channel_name+' ('+self.channel_id+')',wraplength=520).grid(row=0,column=0,columnspan=2,sticky='w',pady=5)
        ttk.Button(frame,text='Open exact video in player',command=self.preview).grid(row=1,column=0,columnspan=2,sticky='w',pady=5)
        self.title_var=tk.StringVar(master=self,value=self.suggested)
        self.visibility=tk.StringVar(master=self,value='private')
        self.kids=tk.StringVar(master=self,value='')
        self.synthetic=tk.StringVar(master=self,value='')
        self.category=tk.StringVar(master=self,value='23')
        self.when=tk.StringVar(master=self,value='')
        self.reviewed=tk.BooleanVar(master=self,value=False)
        self.certified=tk.BooleanVar(master=self,value=False)
        def field(row,label,var,options=None):
            ttk.Label(frame,text=label).grid(row=row,column=0,sticky='w',padx=5,pady=4)
            widget=ttk.Entry(frame,textvariable=var,width=45) if options is None else ttk.Combobox(frame,textvariable=var,values=options,state='readonly',width=42)
            widget.grid(row=row,column=1,sticky='ew',pady=4)
            return widget
        first=field(2,'Title',self.title_var)
        ttk.Label(frame,text='Description').grid(row=3,column=0,sticky='nw',padx=5)
        self.description=tk.Text(frame,width=46,height=4,wrap='word')
        self.description.grid(row=3,column=1,sticky='ew',pady=4)
        self.description.insert('1.0','Original fictional AI-assisted comedy. #Shorts')
        field(4,'Visibility',self.visibility,('private','unlisted','public'))
        field(5,'Made for kids?',self.kids,('yes','no'))
        field(6,'Realistic altered media?',self.synthetic,('yes','no'))
        field(7,'Category ID',self.category)
        field(8,'Future time (optional ISO + offset)',self.when)
        ttk.Label(frame,text='Leave blank to upload with selected visibility. Future scheduling requires private visibility, e.g. 2026-12-01T18:00:00-05:00.',wraplength=520).grid(row=9,column=0,columnspan=2,sticky='w',pady=4)
        ttk.Checkbutton(frame,text='I watched this exact video.',variable=self.reviewed).grid(row=10,column=0,columnspan=2,sticky='w')
        ttk.Label(frame,text=NOTICE,wraplength=520).grid(row=11,column=0,columnspan=2,sticky='w',pady=5)
        ttk.Checkbutton(frame,text='I certify the video complies and I have rights to its assets.',variable=self.certified).grid(row=12,column=0,columnspan=2,sticky='w')
        return first

    def buttonbox(self):
        box=ttk.Frame(self)
        ttk.Button(box,text='Upload',command=self.ok).pack(side='left',padx=5,pady=5)
        ttk.Button(box,text='Cancel',command=self.cancel).pack(side='left',padx=5,pady=5)
        self.bind('<Escape>',self.cancel)
        box.pack()

    def preview(self):
        try:
            os.startfile(str(self.video))
            self.preview_opened=True
        except (OSError,AttributeError):
            messagebox.showerror('Preview','Could not open the video. No upload performed.',parent=self)

    def validate(self):
        try:
            self.result=plan_upload(self.title_var.get(),self.description.get('1.0','end-1c'),self.visibility.get(),self.kids.get(),self.synthetic.get(),self.category.get(),self.when.get(),bool(self.certified.get()),self.preview_opened and bool(self.reviewed.get()))
            return True
        except ValueError as exc:
            messagebox.showerror('Review required',str(exc),parent=self)
            return False

class PublishUI:
    def __init__(self,controls):
        self.controls=controls; self.features=controls.features; self.window=controls.window

    def start(self):
        if self.controls.review_active:
            return
        self.controls.review_active=True
        try:
            self._start()
        finally:
            self.controls.review_active=False

    def _start(self):
        import gaming_mode
        from shorts_controls import ready_video
        if self.features.app.busy or self.features._running or gaming_mode.enabled() or (self.controls.root/'shorts'/'STOP').exists():
            self.features.say('Finish current work or disable Gaming Mode before upload.'); return
        video=ready_video(self.controls.root)
        if video is None:
            self.features.say('No completed video ready to upload.'); return
        if (video.parent/'upload_attempt.json').exists():
            self.features.say('An upload was already attempted. Check YouTube Studio; no repeat upload.'); return
        if not messagebox.askokcancel('Connect YouTube','Use the browser to sign in to your own channel. Falcon will read the channel identity and upload only after your explicit review. No credentials are stored by Falcon. YouTube Terms: https://www.youtube.com/t/terms\nGoogle Privacy Policy: https://policies.google.com/privacy',parent=self.window): return
        path=filedialog.askopenfilename(parent=self.window,title='Select your Google desktop OAuth client JSON',filetypes=[('JSON files','*.json')])
        if not path:return
        def work(cancel):
            try:
                api.probe(video); reviewed_hash=api.digest(video)
                if cancel.is_set():return None
                service=connect(path)
                if cancel.is_set():return None
                cid,name=api.channel(service)
                title=json.loads((video.parent/'story.json').read_text(encoding='utf-8'))['title']
                return service,cid,name,title,reviewed_hash
            except Exception as exc:
                return ('error',type(exc).__name__)
        def complete(value):
            self.features.app.set_status('Ready • Shorts')
            if value is None:return
            if value[0]=='error':
                self.features.say('YouTube authorization or media check failed ('+value[1]+'). No upload performed.');return
            service,cid,name,title,reviewed_hash=value
            self.controls.review_active=True
            try:
                dialog=ReviewDialog(self.window,video,title,cid,name)
                body=dialog.result
                if not body:return
                if not messagebox.askyesno('Confirm channel','Send this reviewed video to '+name+' ('+cid+') with the selected publication settings?',parent=self.window):return
                self.send(service,cid,video,body,reviewed_hash)
            finally:
                self.controls.review_active=False
        self.features._launch('Checking video and connecting YouTube…',work,complete)

    def send(self,service,cid,video,body,reviewed_hash):
        import gaming_mode
        def work(cancel):
            try:
                from googleapiclient.http import MediaFileUpload
                paused=lambda:cancel.is_set() or gaming_mode.enabled() or (self.controls.root/'shorts'/'STOP').exists()
                if paused():return ('error','Paused')
                api.probe(video)
                result=api.upload(service,video.parent,cid,body,reviewed_hash,lambda name:MediaFileUpload(name,mimetype='video/mp4',chunksize=1024*1024,resumable=True),paused)
                return ('ok',result['video_id'])
            except Exception as exc:return ('error',type(exc).__name__)
        def complete(value):
            self.features.app.set_status('Ready • Shorts')
            if value[0]=='ok':self.features.say('YouTube upload accepted: '+value[1]+'. Check Studio for processing and publication status.')
            else:self.features.say('Upload not confirmed ('+value[1]+'). If an attempt was recorded, check YouTube Studio before retrying.')
        self.features._launch('Uploading reviewed video…',work,complete)
