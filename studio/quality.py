import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from .common import StudioError, run_ff, save_json
from .voice import inspect_audio


def inspect_video(path):
    probe = os.getenv("FFPROBE_BINARY") or shutil.which("ffprobe")
    if not probe:
        raise StudioError("ffprobe is required for publication checks; install FFmpeg")
    result = subprocess.run([probe,"-v","error","-show_streams","-show_format","-of","json",str(path)],
                            capture_output=True,text=True,timeout=45)
    if result.returncode:
        raise StudioError("ffprobe could not inspect the final video")
    return json.loads(result.stdout)


def visual_gate(beats,cfg):
    total=sum(b["duration"] for b in beats)
    if total<=0:raise StudioError("No storyboard duration")
    media=sum(b["duration"] for b in beats if b.get("asset")) / total
    videos=sum(b["duration"] for b in beats if b.get("asset",{}).get("kind")=="footage") / total
    fallbacks=sum(b["duration"] for b in beats if b.get("fallback")) / total
    issues=[]
    if media<cfg["minimum_real_media_ratio"]:issues.append("Too little relevant real media")
    if videos<cfg["minimum_real_video_ratio"]:issues.append("Too little real video footage")
    if fallbacks>cfg["max_evidence_fallback_ratio"]:issues.append("Too many unavailable-media fallbacks")
    if any(b.get("asset") and not b["asset"].get("license") for b in beats):issues.append("Missing media rights record")
    return {"passed":not issues,"issues":issues,"real_media_ratio":round(media,3),
            "real_video_ratio":round(videos,3),"fallback_ratio":round(fallbacks,3)}


def check_video(path,beats,cfg,report_path,short=False):
    report={"passed":False,"file":Path(path).name,"issues":[],"checks":{}}
    try:
        probe=inspect_video(path)
        videos=[s for s in probe["streams"] if s["codec_type"]=="video"]
        audios=[s for s in probe["streams"] if s["codec_type"]=="audio"]
        if len(videos)!=1 or not audios:raise StudioError("Video/audio stream missing")
        v,a=videos[0],audios[0]
        width,height=(1080,1920) if short else (cfg["width"],cfg["height"])
        if (v["width"],v["height"])!=(width,height):raise StudioError("Incorrect output dimensions")
        num,den=map(float,v.get("avg_frame_rate","0/1").split("/"))
        if den==0 or abs(num/den-cfg["fps"])>.1:raise StudioError("Incorrect output frame rate")
        dur=float(v.get("duration",probe["format"]["duration"]))
        adur=float(a.get("duration",0))
        if abs(dur-adur)>.3:raise StudioError("Audio/video duration mismatch")
        if dur<(25 if short else cfg["minimum_long_seconds"]) or (short and dur>65):
            raise StudioError("Output duration outside publishing limits")
        if abs(dur-sum(b["duration"] for b in beats))>1:raise StudioError("Final duration differs from storyboard")
        # Decode the entire output; checking only file existence cannot detect corrupt clips.
        run_ff(["-v","error","-xerror","-i",path,"-f","null","-"],timeout=900)
        decoded=Path(path).with_suffix(".qc.wav")
        try:
            run_ff(["-i",path,"-vn","-ar","16000","-ac","1","-c:a","pcm_s16le",decoded])
            inspect_audio(decoded)
        finally:
            decoded.unlink(missing_ok=True)
        result=run_ff(["-i",path,"-vf","blackdetect=d=0.4:pix_th=0.035:pic_th=0.98",
                       "-af","silencedetect=noise=-48dB:d=4","-f","null","-"],timeout=900)
        log=result.stderr.decode(errors="replace")
        if "black_start:" in log:raise StudioError("Sustained black frames detected")
        if "silence_start:" in log:raise StudioError("Long silent gap detected")
        report["checks"].update(width=width,height=height,duration=dur,full_decode=True,audio_present=True)
        if not short:
            report["checks"]["visuals"]=visual_gate(beats,cfg)
            report["issues"]+=report["checks"]["visuals"]["issues"]
        report["passed"]=not report["issues"]
    except Exception as e:
        report["issues"].append(str(e))
    save_json(report_path,report)
    return report
