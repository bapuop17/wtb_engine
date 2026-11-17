import importlib.util
import os
import shutil
from pathlib import Path
from .common import StudioError, ffmpeg


def _resolve_yt_token():
    for k in ("YOUTUBE_TOKEN_JSON_B64", "YOUTUBE_TOKEN_JSON_B64_2", "YOUTUBE_TOKEN_JSON_B64_3", "YOUTUBE_TOKEN_JSON_B64_4"):
        if os.getenv(k):
            os.environ.setdefault("YOUTUBE_TOKEN_JSON_B64", os.environ[k])
            return os.environ[k]
    return ""


def check(publish=False):
    _resolve_yt_token()
    modules = ["requests", "PIL", "numpy", "feedparser", "trafilatura", "ddgs", "edge_tts"]
    if publish:
        modules += ["googleapiclient", "google.oauth2.credentials"]
    missing = []
    for name in modules:
        try:
            found = importlib.util.find_spec(name)
        except ModuleNotFoundError:
            found = None
        if found is None:
            missing.append(name)
    if missing:
        raise StudioError("Install requirements.txt; missing modules: " + ", ".join(missing))
    ffmpeg()
    if not (os.getenv("FFPROBE_BINARY") or shutil.which("ffprobe")):
        raise StudioError("FFmpeg's ffprobe executable is missing")
    if not any(os.getenv(k) for k in ["GEMINI_API_KEY", "GROQ_API_KEY", "OPENROUTER_API_KEY"]):
        raise StudioError("Add one writing-provider key: GEMINI_API_KEY / GROQ_API_KEY / OPENROUTER_API_KEY")
    if publish and not os.getenv("YOUTUBE_TOKEN_JSON_B64"):
        raise StudioError("Add YOUTUBE_TOKEN_JSON_B64 before publishing")
    warnings = []
    if not os.getenv("PEXELS_API_KEY"):
        warnings.append("PEXELS_API_KEY absent: real-video coverage depends on Commons availability")
    if not (os.getenv("DEEPGRAM_API_KEY") or (os.getenv("ELEVENLABS_API_KEY") and os.getenv("ELEVENLABS_VOICE_ID"))):
        warnings.append("No premium narrator configured: using Edge unless provider overridden")
    for warning in warnings:
        print("Preflight:", warning, flush=True)
    return warnings
