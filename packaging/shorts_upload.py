"""Review-gated YouTube upload adapter for Falcon Shorts, standalone CLI.

No saved access tokens. Browser OAuth for each upload; credentials supplied
locally by the owner, never committed. No background publishing.
"""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import subprocess
import math

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.readonly"]

def digest(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()

def validate_media(data):
    streams = data.get("streams", [])
    video = [s for s in streams if s.get("codec_type") == "video"]
    audio = [s for s in streams if s.get("codec_type") == "audio"]
    duration = float(data["format"]["duration"])
    if len(video) != 1 or len(audio) != 1 or not math.isfinite(duration) or not 12 <= duration <= 60:
        raise ValueError("Expected one video, one audio, and 12-60 seconds")
    if (video[0].get("width"), video[0].get("height")) != (720,1280):
        raise ValueError("Expected vertical 720x1280 video")
    return duration

def probe(path):
    result = subprocess.run(["ffprobe","-v","error","-show_streams",
                             "-show_format","-of","json",str(path)],
                            capture_output=True, check=True, timeout=30)
    return validate_media(json.loads(result.stdout))

def metadata(title, description, visibility, kids, synthetic, category, publish_at=None):
    if not isinstance(title,str) or not title.strip() or len(title)>100 or any(c in title for c in "<>"):
        raise ValueError("Invalid title")
    if not isinstance(description,str) or len(description.encode())>5000 or any(c in description for c in "<>"):
        raise ValueError("Invalid description")
    if visibility not in ("private","unlisted","public") or type(kids) is not bool or type(synthetic) is not bool:
        raise ValueError("Explicit audience, disclosure and visibility required")
    if not re.fullmatch(r"[0-9]{1,4}",category):
        raise ValueError("Invalid category")
    status = {"privacyStatus":visibility,"selfDeclaredMadeForKids":kids,
              "containsSyntheticMedia":synthetic}
    if publish_at is not None:
        if visibility != "private" or publish_at.tzinfo is None or publish_at <= dt.datetime.now(dt.timezone.utc):
            raise ValueError("Scheduling requires private visibility and a future aware time")
        status["publishAt"] = publish_at.astimezone(dt.timezone.utc).isoformat().replace("+00:00","Z")
    return {"snippet":{"title":title,"description":description,"categoryId":category},"status":status}

def channel(service):
    items = service.channels().list(part="id,snippet",mine=True,maxResults=50).execute(num_retries=0).get("items",[])
    if len(items)!=1 or not items[0].get("id"):
        raise ValueError("Expected exactly one authorized channel")
    return items[0]["id"],items[0]["snippet"]["title"]

def upload(service, folder, expected_channel, body, approved_digest, media_factory, paused):
    folder=Path(folder)
    path=folder/"draft.mp4"
    if not (folder/"REVIEW_REQUIRED.txt").is_file() or (folder/"FAILED.txt").exists():
        raise ValueError("Draft not ready for review")
    if paused() or channel(service)[0]!=expected_channel:
        raise RuntimeError("Paused or wrong channel")
    if digest(path)!=approved_digest:
        raise ValueError("Video changed since review")
    # Never retry an ambiguous upload by starting another insert.
    # Exclusive marker also prevents two concurrent uploads of this draft.
    ledger=folder/"upload_attempt.json"
    with ledger.open("x",encoding="utf-8") as out:
        json.dump({"state":"pending_or_uncertain","channel":expected_channel,
                   "sha256":approved_digest},out)
    request=service.videos().insert(part="snippet,status",body=body,
                                    media_body=media_factory(str(path)))
    response=None
    while response is None:
        if paused():
            raise RuntimeError("Paused during upload; reconcile in YouTube Studio")
        _,response=request.next_chunk(num_retries=0)
    if not response.get("id"):
        raise RuntimeError("Missing upload receipt; reconcile in YouTube Studio")
    receipt={"state":"uploaded","video_id":response["id"],"channel":expected_channel,
             "sha256":approved_digest}
    temp=folder/"upload_receipt.tmp"
    temp.write_text(json.dumps(receipt),encoding="utf-8")
    temp.replace(ledger)
    return receipt

def main():
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from shorts_mode import OUT, paused as gaming_paused
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--client-secrets",required=True,type=Path)
    p.add_argument("--date",required=True,type=dt.date.fromisoformat)
    args=p.parse_args()
    folder=OUT/args.date.isoformat()
    path=folder/"draft.mp4"
    if (folder/"upload_attempt.json").exists():
        raise RuntimeError("Existing upload attempt; check YouTube Studio before proceeding")
    print("Media:",path,"Duration:",probe(path))
    review_hash=digest(path)
    if input("Open the exact video locally and review it. Type REVIEWED to continue: ")!="REVIEWED":
        return
    print("By proceeding you agree to YouTube's Terms of Service https://www.youtube.com/t/terms and must respect copyright and privacy. Google Privacy Policy: https://policies.google.com/privacy")
    flow=InstalledAppFlow.from_client_secrets_file(str(args.client_secrets),SCOPES)
    creds=flow.run_local_server(host="127.0.0.1",port=0,open_browser=True)
    service=build("youtube","v3",credentials=creds,cache_discovery=False)
    channel_id, name=channel(service)
    print("Authorized channel:",name,channel_id)
    if input("Confirm channel ID: ")!=channel_id:
        return
    suggested=json.loads((folder/"story.json").read_text(encoding="utf-8"))["title"]
    print("Suggested title:",suggested)
    title=input("Final title: ")
    description=input("Final description: ")
    visibility=input("Visibility (private/unlisted/public): ")
    kids=input("Made for kids? (yes/no): ")
    synthetic=input("Contains realistic altered/synthetic media requiring disclosure? (yes/no): ")
    category=input("Category ID (e.g. 23 for comedy): ")
    if kids not in ("yes","no") or synthetic not in ("yes","no"):
        raise ValueError("Explicit yes/no required")
    body=metadata(title,description,visibility,kids=="yes",synthetic=="yes",category)
    print(json.dumps(body,indent=2))
    if input("Certify that this exact video complies with YouTube Community Guidelines and you have rights to all assets. Type CERTIFY: ")!="CERTIFY":
        return
    if input("Type UPLOAD to send the reviewed video to this channel now: ")!="UPLOAD":
        return
    result=upload(service,folder,channel_id,body,review_hash,
                  lambda name:MediaFileUpload(name,mimetype="video/mp4",chunksize=1024*1024,resumable=True),
                  lambda:gaming_paused() or (OUT/"STOP").exists())
    print("Upload receipt:",result["video_id"])

if __name__=="__main__":
    main()
