import base64
import html
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from .common import ROOT, StudioError, digest, load_json, save_json


def description(plan,dossier,beats,assets,credits_url,linked_long=None):
    lines=[plan["summary"],"", "World Talk Brief | Global documentary analysis", ""]
    elapsed=0
    seen=set()
    for b in beats:
        if b["chapter"] not in seen:
            seconds=int(elapsed);lines.append(f"{seconds//60:02}:{seconds%60:02} {b['chapter']}")
            seen.add(b["chapter"])
        elapsed+=b["duration"]
    if linked_long:lines += ["", "Full documentary: "+linked_long]
    lines += ["", "Research sources:"]
    lines += [f"{s['id']} {s['url']}" for s in dossier["sources"]]
    lines += ["", "Complete media credits, licenses and research: "+credits_url,
              "Archive and stock images are labeled as context; they are not authenticated footage of the reported event.",
              "Narration is synthesized. Graphics are explanatory. AI-assisted evidence checks can make mistakes."]
    text="\n".join(lines)
    if len(text)>4900:raise StudioError("Description exceeds safe metadata length; shorten source list")
    return text


def credits_page(plan,dossier,assets,slug,video_id=None,music_credit=""):
    path=ROOT/"docs"/"articles"/(slug+".html")
    e=html.escape
    sources="".join(f'<li><a href="{e(s["url"],quote=True)}">{e(s["title"])}</a> — {e(s["published"])}</li>' for s in dossier["sources"])
    unique={a["url"]:a for a in assets}
    credits="".join(f'<li><a href="{e(a["page_url"],quote=True)}">{e(a["caption"][:180])}</a><br>'
        f'{e(a["creator"])} · <a href="{e(a["license_url"],quote=True)}">{e(a["license"])}</a>'
        f'<br>Changes: {e(a["changes"])}. Context label: {e(a["label"])}.</li>' for a in unique.values())
    paragraphs="".join(f'<p>{e(b["narration"])}</p>' for b in plan["beats"])
    video=f'<p><a href="https://youtu.be/{e(video_id,quote=True)}">Watch on YouTube</a></p>' if video_id else "<p>Production credits; video publication pending.</p>"
    page=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(plan['title'])} — World Talk Brief</title><style>body{{background:#0c131e;color:#f2efe4;font:18px/1.65 system-ui;max-width:900px;margin:60px auto;padding:24px}}a{{color:#5fd3c8}}h1{{line-height:1.15}}li{{margin:24px 0}}small{{color:#97a7b6}}</style>
<small>WORLD TALK BRIEF / SOURCES & MEDIA CREDITS</small><h1>{e(plan['title'])}</h1>{video}
<p>{e(plan['summary'])}</p><h2>Research sources</h2><ol>{sources}</ol><h2>Media credits</h2><ul>{credits}</ul>
<p>{e(music_credit)}</p><p>Archive and stock material illustrates context. Synthesized narration; original explanatory graphics.
Automated checks are not independent journalistic verification. Source descriptions and sampled image frames are checked; authenticity is not guaranteed.</p>
<h2>Narration</h2>{paragraphs}</html>'''
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(page,encoding="utf-8")
    repo=os.getenv("GITHUB_REPOSITORY","bapuop17/wtb_engine").split("/")
    return f"https://{repo[0]}.github.io/{repo[-1]}/articles/{slug}.html"


def upload(video,thumbnail,title,desc,tags,cfg,qc,key,state):
    if qc.get("passed") is not True:raise StudioError("Publication requires a passing QC report")
    if not os.getenv("YOUTUBE_TOKEN_JSON_B64"):raise StudioError("YOUTUBE_TOKEN_JSON_B64 secret missing")
    receipts=state.setdefault("uploads",{})
    if receipts.get(key,{}).get("video_id"):return receipts[key]["video_id"]
    if receipts.get(key,{}).get("status")=="uploading":
        raise StudioError("A previous upload has an ambiguous result. Check YouTube before clearing its pending receipt")
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    info=json.loads(base64.b64decode(os.environ["YOUTUBE_TOKEN_JSON_B64"]))
    creds=Credentials.from_authorized_user_info(info)
    if creds.expired and creds.refresh_token:creds.refresh(Request())
    yt=build("youtube","v3",credentials=creds,cache_discovery=False)
    if os.getenv("YOUTUBE_CHANNEL_ID"):
        channel=yt.channels().list(part="id",mine=True).execute().get("items",[])
        if not any(c["id"]==os.environ["YOUTUBE_CHANNEL_ID"] for c in channel):raise StudioError("OAuth token belongs to a different channel")
    if cfg["privacy"] not in {"private","unlisted","public"}:raise StudioError("Invalid privacy setting")
    body={"snippet":{"title":title[:100],"description":desc,"tags":tags[:10],"categoryId":"25",
                     "defaultLanguage":"en","defaultAudioLanguage":"en"},
          "status":{"privacyStatus":cfg["privacy"],"selfDeclaredMadeForKids":False,
                    "containsSyntheticMedia":bool(cfg["contains_synthetic_media"])}}
    receipts[key]={"status":"uploading","title":title,"started_utc":datetime.now(timezone.utc).isoformat()}
    save_json(ROOT/"studio_history.json",state)
    # One channel/token; never rotate credentials to bypass quota or upload limits.
    req=yt.videos().insert(part="snippet,status",body=body,
        media_body=MediaFileUpload(str(video),chunksize=8*1024*1024,resumable=True,mimetype="video/mp4"))
    response=None
    while response is None:
        _,response=req.next_chunk(num_retries=3)
    video_id=response["id"]
    receipts[key]={"status":"uploaded","video_id":video_id,"title":title,"uploaded_utc":datetime.now(timezone.utc).isoformat()}
    save_json(ROOT/"studio_history.json",state)
    if thumbnail:
        try:
            yt.thumbnails().set(videoId=video_id,media_body=MediaFileUpload(str(thumbnail),mimetype="image/jpeg")).execute()
        except Exception:
            receipts[key]["thumbnail_warning"]="Video uploaded; thumbnail update failed. Set it in YouTube Studio."
            save_json(ROOT/"studio_history.json",state)
    return video_id
