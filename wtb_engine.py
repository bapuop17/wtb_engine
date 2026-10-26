import os
import sys
import re
import math
import wave
import json
import time
import base64
import random
import asyncio
import hashlib
import traceback
import subprocess
import urllib.parse
from datetime import datetime, timedelta
import requests
import feedparser
import numpy as np
import cv2
import edge_tts
from gtts import gTTS
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
os.environ["SDL_AUDIODRIVER"] = "dummy"

try:
    from moviepy.editor import VideoClip, VideoFileClip, AudioFileClip, CompositeAudioClip, concatenate_videoclips
    MOVIEPY_V2 = False
except ImportError:
    from moviepy import VideoClip, VideoFileClip, AudioFileClip, CompositeAudioClip, concatenate_videoclips
    MOVIEPY_V2 = True

os.makedirs("temp", exist_ok=True)
os.makedirs("output", exist_ok=True)

for fn in os.listdir("temp"):
    try:
        os.remove(os.path.join("temp", fn))
    except Exception:
        pass

HEADERS_WEB = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9"
}
HEADERS_WIKI = {
    "User-Agent": "WorldTalkBriefMultiAPIEngine/50.0 (https://github.com/bapuop17/wtb_engine; editorial@worldtalkbrief.org)"
}

HISTORY_FILE = "published_history.json"

# ==============================================================================
# 1. ALL 8 CONTENT PILLARS WITH DEEPGRAM AURA-2 ULTRA-HUMAN VOICES & PLAYLISTS
# ==============================================================================
ORDERED_PILLARS = [
    "WORLD",
    "TECHNOLOGY",
    "MIND_BLOWING_FACTS",
    "SCIENCE",
    "BUSINESS",
    "HEALTH",
    "SPORTS",
    "ENTERTAINMENT"
]

CATEGORY_VOICE_CAST = {
    "WORLD": (["aura-2-apollo-en", "aura-orion-en", "aura-asteria-en"], "en-US-AndrewMultilingualNeural", "+3%"),
    "TECHNOLOGY": (["aura-2-aries-en", "aura-arcas-en", "aura-orion-en"], "en-US-BrianMultilingualNeural", "+4%"),
    "MIND_BLOWING_FACTS": (["aura-2-thalia-en", "aura-asteria-en", "aura-luna-en"], "en-US-AvaMultilingualNeural", "+3%"),
    "SCIENCE": (["aura-2-hermes-en", "aura-helios-en", "aura-arcas-en"], "en-US-BrianMultilingualNeural", "+3%"),
    "BUSINESS": (["aura-2-zeus-en", "aura-perseus-en", "aura-orion-en"], "en-US-AndrewMultilingualNeural", "+4%"),
    "HEALTH": (["aura-2-helena-en", "aura-luna-en", "aura-asteria-en"], "en-US-AvaMultilingualNeural", "+3%"),
    "SPORTS": (["aura-2-draco-en", "aura-angus-en", "aura-arcas-en"], "en-US-BrianMultilingualNeural", "+5%"),
    "ENTERTAINMENT": (["aura-2-andromeda-en", "aura-stella-en", "aura-asteria-en"], "en-US-EmmaMultilingualNeural", "+4%")
}

CATEGORY_FEEDS = {
    "WORLD": {
        "yt_category_id": "25",
        "playlist_title": "World Talk Brief • Global Geopolitics & World News",
        "badge_color": (220, 20, 45),
        "accent_color": (0, 230, 255),
        "hook_tag": "GEOPOLITICAL DEEP DIVE",
        "bgm_mood": "dark_geopolitics",
        "reddit_subs": "worldnews+geopolitics",
        "search_query": "world news geopolitics summit military",
        "feeds": [
            ("Al Jazeera World", "https://www.aljazeera.com/xml/rss/all.xml"),
            ("BBC World", "http://feeds.bbci.co.uk/news/world/rss.xml"),
            ("The Guardian World", "https://www.theguardian.com/world/rss"),
            ("DW World", "https://rss.dw.com/rdf/rss-en-world"),
            ("France24 World", "https://www.france24.com/en/rss")
        ]
    },
    "TECHNOLOGY": {
        "yt_category_id": "28",
        "playlist_title": "World Talk Brief • AI, Robotics, Gaming & Future Tech",
        "badge_color": (0, 130, 255),
        "accent_color": (0, 240, 255),
        "hook_tag": "FUTURE TECH & AI",
        "bgm_mood": "cyberpunk_tech",
        "reddit_subs": "technology+robotics+artificial+singularity",
        "search_query": "artificial intelligence humanoid robot gaming nvidia technology",
        "feeds": [
            ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
            ("BBC Technology", "http://feeds.bbci.co.uk/news/technology/rss.xml"),
            ("The Guardian Tech", "https://www.theguardian.com/uk/technology/rss"),
            ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index")
        ]
    },
    "MIND_BLOWING_FACTS": {
        "yt_category_id": "27",
        "playlist_title": "World Talk Brief • Mind-Blowing Facts & World Mysteries",
        "badge_color": (165, 25, 220),
        "accent_color": (0, 235, 255),
        "hook_tag": "UNBELIEVABLE REALITY",
        "bgm_mood": "cosmic_mystery",
        "reddit_subs": "Damnthatsinteresting+interestingasfuck+space",
        "search_query": "unbelievable facts scientific mystery mind blowing discovery",
        "feeds": [
            ("SciTechDaily Discoveries", "https://scitechdaily.com/feed/"),
            ("Phys.org Breakthroughs", "https://phys.org/rss-feed/")
        ]
    },
    "SCIENCE": {
        "yt_category_id": "28",
        "playlist_title": "World Talk Brief • Space, NASA & Future Science",
        "badge_color": (105, 40, 225),
        "accent_color": (0, 235, 255),
        "hook_tag": "SPACE & SCIENCE",
        "bgm_mood": "cosmic_mystery",
        "reddit_subs": "space+science+astronomy",
        "search_query": "space nasa spacex astronomy quantum discovery",
        "feeds": [
            ("Space.com", "https://www.space.com/feeds/all"),
            ("NASA Breaking News", "https://www.nasa.gov/news-release/feed/"),
            ("The Guardian Science", "https://www.theguardian.com/science/rss")
        ]
    },
    "BUSINESS": {
        "yt_category_id": "25",
        "playlist_title": "World Talk Brief • Business, Markets & Global Economy",
        "badge_color": (12, 160, 105),
        "accent_color": (0, 235, 255),
        "hook_tag": "MONEY & MARKETS",
        "bgm_mood": "high_stakes_finance",
        "reddit_subs": "economics+business+finance",
        "search_query": "global economy stock market business billionaire trade",
        "feeds": [
            ("CNBC Business", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147"),
            ("BBC Business", "http://feeds.bbci.co.uk/news/business/rss.xml"),
            ("The Guardian Business", "https://www.theguardian.com/uk/business/rss")
        ]
    },
    "HEALTH": {
        "yt_category_id": "28",
        "playlist_title": "World Talk Brief • Health, Biotech & Medical Science",
        "badge_color": (10, 155, 145),
        "accent_color": (0, 235, 255),
        "hook_tag": "MEDICAL BREAKTHROUGH",
        "bgm_mood": "inspiring_science",
        "reddit_subs": "science+health+medicine",
        "search_query": "medical breakthrough human brain health longevity",
        "feeds": [
            ("SciTechDaily Health", "https://scitechdaily.com/news/health/feed/"),
            ("MedicalXpress", "https://medicalxpress.com/rss-feed/")
        ]
    },
    "SPORTS": {
        "yt_category_id": "17",
        "playlist_title": "World Talk Brief • Global Sports Arena",
        "badge_color": (230, 80, 10),
        "accent_color": (0, 235, 255),
        "hook_tag": "SPORTS SHOWDOWN",
        "bgm_mood": "stadium_action",
        "reddit_subs": "sports+soccer+formula1+Cricket",
        "search_query": "cricket football champions league formula 1 sports",
        "feeds": [
            ("BBC Sport", "http://feeds.bbci.co.uk/sport/rss.xml"),
            ("The Guardian Sport", "https://www.theguardian.com/uk/sport/rss"),
            ("ESPN Top News", "https://www.espn.com/espn/rss/news")
        ]
    },
    "ENTERTAINMENT": {
        "yt_category_id": "24",
        "playlist_title": "World Talk Brief • Cinema, Gaming & Pop Culture",
        "badge_color": (210, 25, 115),
        "accent_color": (0, 235, 255),
        "hook_tag": "CINEMA & GAMING",
        "bgm_mood": "stadium_action",
        "reddit_subs": "movies+gaming+entertainment",
        "search_query": "movies box office gaming marvel gta entertainment",
        "feeds": [
            ("BBC Entertainment & Arts", "http://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml"),
            ("The Guardian Film", "https://www.theguardian.com/uk/film/rss"),
            ("Hollywood Reporter", "https://www.hollywoodreporter.com/feed/")
        ]
    }
}

# ==============================================================================
# 2. MULTI-API AI DIRECTOR BRAIN (Groq Llama-3.3-70B + HuggingFace Qwen-72B + Pollinations)
# ==============================================================================
def parse_json_safely(raw_text):
    if not raw_text:
        return None
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text.strip(), flags=re.I)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip())
    try:
        return json.loads(cleaned)
    except Exception:
        m = re.search(r"\{.*\}", cleaned, flags=re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
    return None

def call_multi_api_ai_brain_json(system_prompt, user_prompt):
    groq_key = os.environ.get("GROQ_API_KEY", "").strip()
    if groq_key:
        for g_model in ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]:
            try:
                r = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                    json={
                        "model": g_model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "response_format": {"type": "json_object"},
                        "temperature": 0.65,
                        "max_tokens": 3800
                    },
                    timeout=28
                )
                if r.status_code == 200:
                    content = r.json()["choices"][0]["message"]["content"]
                    parsed = parse_json_safely(content)
                    if parsed:
                        return parsed
                else:
                    print(f"⚠️ Groq HTTP {r.status_code} ({g_model}):", r.text[:120], flush=True)
            except Exception as e:
                print(f"⚠️ Groq ({g_model}) exception:", str(e)[:80], flush=True)

    hf_token = os.environ.get("HF_TOKEN", "").strip()
    if hf_token:
        for hf_model in ["Qwen/Qwen2.5-72B-Instruct", "meta-llama/Llama-3.3-70B-Instruct"]:
            try:
                r = requests.post(
                    "https://router.huggingface.co/v1/chat/completions",
                    headers={"Authorization": f"Bearer {hf_token}", "Content-Type": "application/json"},
                    json={
                        "model": hf_model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "max_tokens": 3200,
                        "temperature": 0.65
                    },
                    timeout=26
                )
                if r.status_code == 200:
                    txt = r.json()["choices"][0]["message"]["content"]
                    parsed = parse_json_safely(txt)
                    if parsed:
                        return parsed
            except Exception:
                pass

    for _ in range(2):
        try:
            r = requests.post(
                "https://text.pollinations.ai/",
                json={
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "model": "openai",
                    "jsonMode": True,
                    "seed": random.randint(1, 99999)
                },
                headers={"Content-Type": "application/json"},
                timeout=25
            )
            if r.status_code == 200 and r.text:
                parsed = parse_json_safely(r.text)
                if parsed:
                    return parsed
        except Exception:
            time.sleep(1.0)
    return None

def ai_direct_complete_video_package(dossier, is_short=True, top_channel_hits=None):
    pillar = dossier.get("pillar", "WORLD")
    raw_title = dossier["title"]
    raw_facts = dossier["raw_facts"][:16]
    num_scenes = 6 if is_short else 9
    words_per_scene = "22 to 26 words" if is_short else "55 to 70 words (3 to 4 full sentences)"
    top_hits_str = ", ".join(top_channel_hits[:3]) if top_channel_hits else "High-impact mysteries, defense tech, AI breakthroughs, and geopolitical shifts"

    sys_prompt = (
        "You are an elite YouTube Documentary Director combining the investigative depth and data-driven case-study structure of Nitish Rajput, "
        "the high-energy curiosity hooks and conversational pacing of Abhi & Niyu, and the factual authority of BBC World. "
        "You NEVER copy-paste newspaper sentences. You write 100% original, spoken-English storytelling scripts that hook viewers in the first 2 seconds, "
        "explain the background, the exact mechanism, the real numbers, and end with a powerful takeaway. Output STRICT JSON only."
    )

    usr_prompt = f"""
Create a complete {'YouTube Short (45-55 seconds, 6 fast-paced scenes)' if is_short else 'YouTube Documentary Explainer (3.5 to 4.5 minutes, 9 deep-dive chapters)'} package for the category [{pillar}].

RAW SOURCE HEADLINE: {raw_title}
RAW VERIFIED FACTS:
{chr(10).join('- ' + f for f in raw_facts)}

OUR CHANNEL'S TOP PERFORMING VIDEO THEMES (Learn from these): {top_hits_str}

Return ONLY valid JSON in this exact structure:
{{
  "viral_title": "A 100% original, high-CTR YouTube title (50-75 chars, curiosity-driven, e.g. 'Why Everyone Is Talking About...' or 'How X Just Changed Y Forever')",
  "thumb_line_1": "2 TO 3 CAPS WORDS (max 15 chars, e.g. '20,000 SOLD' or 'SECRET VAULT')",
  "thumb_line_2": "2 TO 3 CAPS WORDS (max 15 chars, e.g. 'NVIDIA SHOCK' or 'THE REAL TRUTH')",
  "core_subject": "2-3 word exact physical subject (e.g. 'Nvidia Microduck Robot' or 'Prehistoric Crocodile Fossil')",
  "seo_description": "A compelling 3-paragraph YouTube SEO description summarizing the core case study.",
  "seo_tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8"],
  "scenes": [
    {{
      "scene_num": 1,
      "context_pill": "SHORT UPPERCASE BADGE (max 22 chars, ASCII only, e.g. 'THE VIRAL KEYNOTE')",
      "narration": "Engaging spoken narration ({words_per_scene}) in natural human storyteller English with contractions (here's, it's, didn't). Write out all units in full words (e.g. '1.56 million', NEVER '1.56m').",
      "news_photo_query": "Distinct 3-4 word query to find real news photos for THIS specific scene (must be different for each scene!)",
      "video_broll_query": "Distinct 2-3 word query to find real moving stock/news video footage for THIS scene",
      "ai_image_prompt": "Detailed photorealistic 8k documentary photography prompt depicting THIS exact scene (no text in image)"
    }}
  ]
}}
CRITICAL RULES:
1. Generate EXACTLY {num_scenes} scenes in "scenes".
2. Every scene MUST have a DIFFERENT `news_photo_query` and `ai_image_prompt` so visuals never repeat!
3. Every scene MUST stay 100% focused on the main story ({raw_title}).
"""
    ai_pkg = call_multi_api_ai_brain_json(sys_prompt, usr_prompt)
    if ai_pkg and isinstance(ai_pkg.get("scenes"), list) and len(ai_pkg["scenes"]) >= 4:
        print(f"🧠 [Groq Llama-3.3-70B Director] Crafted Original Title: '{ai_pkg.get('viral_title')}' ({len(ai_pkg['scenes'])} Scenes)", flush=True)
        return ai_pkg
    return None

# ==============================================================================
# 3. 30-TRACK MOOD-ADAPTIVE STUDIO INSTRUMENTAL ALBUM ENGINE
# ==============================================================================
STUDIO_ALBUM_30_TRACKS = {
    "dark_geopolitics": [
        ("Track 01 • Kremlin Shadow", [110.0, 130.81, 146.83, 164.81], 92, [0, 2, 1, 3]),
        ("Track 02 • Red Sea Radar", [98.0, 116.54, 130.81, 146.83], 96, [0, 1, 3, 2]),
        ("Track 03 • Diplomatic Standoff", [123.47, 146.83, 164.81, 185.0], 88, [0, 3, 1, 2]),
        ("Track 04 • Iron Corridor", [87.31, 103.83, 116.54, 130.81], 100, [0, 2, 3, 1]),
        ("Track 05 • Brink of History", [110.0, 123.47, 146.83, 164.81], 94, [0, 1, 2, 3])
    ],
    "cyberpunk_tech": [
        ("Track 06 • Neural Horizon", [146.83, 174.61, 220.0, 196.0], 112, [0, 2, 3, 1]),
        ("Track 07 • Silicon Pulse", [130.81, 164.81, 196.0, 220.0], 118, [0, 1, 2, 3]),
        ("Track 08 • Quantum Grid", [164.81, 196.0, 246.94, 220.0], 115, [0, 3, 2, 1]),
        ("Track 09 • Deep Algorithm", [138.59, 164.81, 207.65, 185.0], 110, [0, 2, 1, 3]),
        ("Track 10 • Autonomous Future", [146.83, 185.0, 220.0, 246.94], 120, [0, 1, 3, 2])
    ],
    "cosmic_mystery": [
        ("Track 11 • Mariana Abyss", [110.0, 164.81, 130.81, 196.0], 82, [0, 3, 1, 2]),
        ("Track 12 • Voyager Interstellar", [130.81, 196.0, 164.81, 220.0], 86, [0, 2, 3, 1]),
        ("Track 13 • Subglacial Secret", [98.0, 146.83, 130.81, 174.61], 80, [0, 1, 2, 3]),
        ("Track 14 • Event Horizon", [116.54, 174.61, 146.83, 220.0], 84, [0, 2, 1, 3]),
        ("Track 15 • Ancient Mechanism", [123.47, 185.0, 146.83, 220.0], 88, [0, 3, 2, 1])
    ],
    "high_stakes_finance": [
        ("Track 16 • Wall Street Bell", [130.81, 164.81, 146.83, 196.0], 104, [0, 1, 2, 3]),
        ("Track 17 • Trillion Dollar Pivot", [146.83, 185.0, 164.81, 220.0], 108, [0, 2, 1, 3]),
        ("Track 18 • Global Supply Chain", [123.47, 146.83, 185.0, 164.81], 102, [0, 3, 1, 2]),
        ("Track 19 • Central Bank Calculus", [110.0, 146.83, 164.81, 196.0], 100, [0, 1, 3, 2]),
        ("Track 20 • Market Shockwave", [138.59, 164.81, 185.0, 207.65], 106, [0, 2, 3, 1])
    ],
    "inspiring_science": [
        ("Track 21 • Biotech Dawn", [130.81, 164.81, 196.0, 261.63], 96, [0, 1, 2, 3]),
        ("Track 22 • Cellular Breakthrough", [146.83, 185.0, 220.0, 293.66], 98, [0, 2, 1, 3]),
        ("Track 23 • Orbital Telescope", [164.81, 196.0, 246.94, 329.63], 94, [0, 3, 2, 1]),
        ("Track 24 • Longevity Code", [130.81, 174.61, 196.0, 220.0], 92, [0, 1, 3, 2]),
        ("Track 25 • Planetary Frontier", [146.83, 196.0, 220.0, 261.63], 100, [0, 2, 3, 1])
    ],
    "stadium_action": [
        ("Track 26 • Pole Position Grid", [146.83, 196.0, 220.0, 293.66], 124, [0, 2, 1, 3]),
        ("Track 27 • El Clasico Arena", [130.81, 164.81, 196.0, 261.63], 126, [0, 1, 3, 2]),
        ("Track 28 • Championship Lap", [164.81, 220.0, 246.94, 329.63], 128, [0, 3, 1, 2]),
        ("Track 29 • Box Office Premiere", [138.59, 185.0, 207.65, 277.18], 118, [0, 1, 2, 3]),
        ("Track 30 • Final Whistle", [146.83, 174.61, 220.0, 261.63], 122, [0, 2, 3, 1])
    ]
}

def build_30_track_mood_adaptive_album_bgm(filename, duration, beat_switch_times, mood="dark_geopolitics", track_seed=0):
    tracks = STUDIO_ALBUM_30_TRACKS.get(mood, STUDIO_ALBUM_30_TRACKS["dark_geopolitics"])
    track_name, root_freqs, bpm, arp_order = tracks[track_seed % len(tracks)]
    print(f"   🎵 [30-Track Studio BGM Album] Selected '{track_name}' (Mood: {mood} | {bpm} BPM)", flush=True)

    sr = 22050
    n_samples = max(int(sr * duration), sr)
    t = np.linspace(0, duration, n_samples, endpoint=False)

    beat_len = 60.0 / float(bpm)
    bar_len = beat_len * 4.0

    bar_idx = (t // bar_len).astype(int)
    chord_roots = np.array([root_freqs[i % len(root_freqs)] for i in bar_idx], dtype=np.float32)

    phase_root = 2.0 * np.pi * np.cumsum(chord_roots) / float(sr)
    pad_wave = (
        0.50 * np.sin(phase_root)
        + 0.28 * np.sin(phase_root * 1.498)
        + 0.15 * np.sin(phase_root * 2.0)
    )
    pad_env = 0.70 + 0.30 * np.sin(2.0 * np.pi * (t / bar_len))
    pad_layer = pad_wave * pad_env * 0.45

    note_len = beat_len / 2.0
    note_idx = (t // note_len).astype(int)
    note_local_t = t % note_len
    arp_mults = np.array([1.0, 1.25, 1.498, 2.0], dtype=np.float32)
    chosen_mults = np.array([arp_mults[arp_order[i % len(arp_order)]] for i in note_idx], dtype=np.float32)
    note_freqs = chord_roots * 2.0 * chosen_mults
    note_phase = 2.0 * np.pi * note_freqs * note_local_t
    attack_env = np.minimum(1.0, note_local_t / 0.015)
    decay_env = np.exp(-note_local_t * 5.5)
    pluck_wave = (
        0.65 * np.sin(note_phase)
        + 0.22 * np.sin(note_phase * 2.0) * np.exp(-note_local_t * 9.0)
        + 0.08 * np.sin(note_phase * 3.0) * np.exp(-note_local_t * 14.0)
    )
    arp_layer = pluck_wave * attack_env * decay_env * 0.42

    beat_local_t = t % beat_len
    kick_freq_sweep = 95.0 * np.exp(-beat_local_t * 18.0) + 42.0
    kick_env = np.exp(-beat_local_t * 14.0)
    kick_layer = 0.35 * np.sin(2.0 * np.pi * kick_freq_sweep * beat_local_t) * kick_env

    music = pad_layer + arp_layer + kick_layer
    max_m = max(float(np.max(np.abs(music))), 1e-4)
    audio = (music / max_m) * 0.075

    for bt in beat_switch_times:
        idx = int(bt * sr)
        if 0 < idx < n_samples:
            slen = min(int(0.24 * sr), n_samples - idx)
            st_t = np.linspace(0, slen / float(sr), slen, endpoint=False)
            whoosh_env = np.sin(np.pi * (st_t / (slen / float(sr)))) * np.exp(-st_t * 8.0)
            whoosh = 0.038 * np.sin(2.0 * np.pi * (180.0 - 70.0 * st_t) * st_t) * whoosh_env
            audio[idx:idx + slen] += whoosh

    audio_int16 = np.int16(np.clip(audio, -1.0, 1.0) * 32767)
    with wave.open(filename, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(audio_int16.tobytes())
    return filename

# ==============================================================================
# 4. COMPLETE WORLD GEOPOLITICAL DATABASE
# ==============================================================================
COUNTRY_GEO_DB = {
    "UNITED STATES": ("US", "USA", "Washington, D.C.", "335 million", "North America", 38.895, -77.036),
    "RUSSIA": ("RU", "RUS", "Moscow", "144 million", "Eurasia", 55.755, 37.617),
    "CHINA": ("CN", "CHN", "Beijing", "1.41 billion", "East Asia", 39.904, 116.407),
    "ISRAEL": ("IL", "ISR", "Jerusalem", "9.8 million", "Middle East", 31.768, 35.213),
    "IRAN": ("IR", "IRN", "Tehran", "89 million", "Middle East", 35.689, 51.389),
    "INDIA": ("IN", "IND", "New Delhi", "1.43 billion", "South Asia", 28.613, 77.209),
    "PAKISTAN": ("PK", "PAK", "Islamabad", "241 million", "South Asia", 33.684, 73.047),
    "UKRAINE": ("UA", "UKR", "Kyiv", "38 million", "Eastern Europe", 50.450, 30.523),
    "BULGARIA": ("BG", "BGR", "Sofia", "6.4 million", "Southeastern Europe", 42.697, 23.321),
    "UZBEKISTAN": ("UZ", "UZB", "Tashkent", "36 million", "Central Asia", 41.299, 69.240),
    "UGANDA": ("UG", "UGA", "Kampala", "48 million", "East Africa", 0.347, 32.582),
    "SOUTH KOREA": ("KR", "KOR", "Seoul", "51.7 million", "East Asia", 37.566, 126.978),
    "NORTH KOREA": ("KP", "PRK", "Pyongyang", "26 million", "East Asia", 39.039, 125.762),
    "JAPAN": ("JP", "JPN", "Tokyo", "124 million", "East Asia", 35.676, 139.650),
    "GERMANY": ("DE", "DEU", "Berlin", "84.5 million", "Europe", 52.520, 13.405),
    "FRANCE": ("FR", "FRA", "Paris", "68 million", "Europe", 48.856, 2.352),
    "UNITED KINGDOM": ("GB", "GBR", "London", "67.7 million", "Europe", 51.507, -0.127),
    "ITALY": ("IT", "ITA", "Rome", "58.9 million", "Europe", 41.902, 12.496),
    "SAUDI ARABIA": ("SA", "SAU", "Riyadh", "36.9 million", "Middle East", 24.713, 46.675),
    "TURKEY": ("TR", "TUR", "Ankara", "85.3 million", "Eurasia", 39.933, 32.859),
    "CANADA": ("CA", "CAN", "Ottawa", "40.1 million", "North America", 45.421, -75.697),
    "BRAZIL": ("BR", "BRA", "Brasilia", "203 million", "South America", -15.797, -47.891),
    "AUSTRALIA": ("AU", "AUS", "Canberra", "26.6 million", "Oceania", -35.280, 149.130),
    "MEXICO": ("MX", "MEX", "Mexico City", "129 million", "North America", 19.432, -99.133),
    "LEBANON": ("LB", "LBN", "Beirut", "5.3 million", "Middle East", 33.893, 35.501),
    "SYRIA": ("SY", "SYR", "Damascus", "23.2 million", "Middle East", 33.513, 36.276),
    "YEMEN": ("YE", "YEM", "Sanaa", "34.4 million", "Middle East", 15.369, 44.191),
    "SUDAN": ("SD", "SDN", "Khartoum", "48 million", "Northeast Africa", 15.500, 32.559),
    "GAZA": ("PS", "PSE", "Gaza City", "2.1 million", "Middle East", 31.501, 34.466),
    "PALESTINE": ("PS", "PSE", "Ramallah", "5.4 million", "Middle East", 31.902, 35.206),
    "TAIWAN": ("TW", "TWN", "Taipei", "23.5 million", "East Asia", 25.033, 121.565),
    "POLAND": ("PL", "POL", "Warsaw", "37.6 million", "Europe", 52.229, 21.012),
    "ALBANIA": ("AL", "ALB", "Tirana", "2.8 million", "Balkans / Europe", 41.327, 19.818),
    "SERBIA": ("RS", "SRB", "Belgrade", "6.6 million", "Balkans / Europe", 44.786, 20.448),
    "GREECE": ("GR", "GRC", "Athens", "10.4 million", "Europe", 37.983, 23.727),
    "SPAIN": ("ES", "ESP", "Madrid", "48.3 million", "Europe", 40.416, -3.703),
    "NORWAY": ("NO", "NOR", "Oslo", "5.5 million", "Europe", 59.913, 10.752),
    "SWITZERLAND": ("CH", "CHE", "Bern", "8.8 million", "Europe", 46.948, 7.447),
    "MOROCCO": ("MA", "MAR", "Rabat", "37.8 million", "North Africa", 34.020, -6.841),
    "EGYPT": ("EG", "EGY", "Cairo", "112 million", "North Africa", 30.044, 31.235),
    "SOUTH AFRICA": ("ZA", "ZAF", "Pretoria", "60 million", "Southern Africa", -25.747, 28.229),
    "NIGERIA": ("NG", "NGA", "Abuja", "223 million", "West Africa", 9.076, 7.398),
    "KENYA": ("KE", "KEN", "Nairobi", "55 million", "East Africa", -1.292, 36.821),
    "DR CONGO": ("CD", "COD", "Kinshasa", "102 million", "Central Africa", -4.441, 15.266)
}

DEMONYM_TO_COUNTRY = {
    "morocco": "MOROCCO", "moroccan": "MOROCCO", "casablanca": "MOROCCO",
    "barcelona": "SPAIN", "real madrid": "SPAIN", "la liga": "SPAIN", "madrid": "SPAIN", "spanish": "SPAIN",
    "england": "UNITED KINGDOM", "scotland": "UNITED KINGDOM", "wales": "UNITED KINGDOM", "nhs": "UNITED KINGDOM",
    "northern ireland": "UNITED KINGDOM", "antrim": "UNITED KINGDOM", "tyrone": "UNITED KINGDOM",
    "british": "UNITED KINGDOM", "london": "UNITED KINGDOM", "starmer": "UNITED KINGDOM", "uk ": "UNITED KINGDOM",
    "congo": "DR CONGO", "kinshasa": "DR CONGO",
    "uganda": "UGANDA", "ugandan": "UGANDA", "kampala": "UGANDA", "entebbe": "UGANDA",
    "bulgaria": "BULGARIA", "bulgarian": "BULGARIA", "sofia": "BULGARIA",
    "uzbekistan": "UZBEKISTAN", "uzbek": "UZBEKISTAN", "samarkand": "UZBEKISTAN", "tashkent": "UZBEKISTAN",
    "saudi": "SAUDI ARABIA", "riyadh": "SAUDI ARABIA",
    "houthi": "YEMEN", "yemen": "YEMEN", "sanaa": "YEMEN", "taiz": "YEMEN",
    "zelensky": "UKRAINE", "zelenskyy": "UKRAINE", "ukrainian": "UKRAINE", "ukrainians": "UKRAINE", "kyiv": "UKRAINE", "kiev": "UKRAINE",
    "alberta": "CANADA", "canadian": "CANADA", "ottawa": "CANADA", "carney": "CANADA",
    "oslo": "NORWAY", "norwegian": "NORWAY",
    "french": "FRANCE", "paris": "FRANCE", "macron": "FRANCE", "lecornu": "FRANCE", "france": "FRANCE",
    "american": "UNITED STATES", "u.s.": "UNITED STATES", "washington": "UNITED STATES", "white house": "UNITED STATES",
    "russian": "RUSSIA", "moscow": "RUSSIA", "kremlin": "RUSSIA", "putin": "RUSSIA",
    "chinese": "CHINA", "beijing": "CHINA",
    "israeli": "ISRAEL", "jerusalem": "ISRAEL", "tel aviv": "ISRAEL", "netanyahu": "ISRAEL",
    "iranian": "IRAN", "tehran": "IRAN",
    "indian": "INDIA", "new delhi": "INDIA", "modi": "INDIA", "india": "INDIA", "kerala": "INDIA", "assam": "INDIA",
    "pakistani": "PAKISTAN", "islamabad": "PAKISTAN",
    "german": "GERMANY", "berlin": "GERMANY",
    "italian": "ITALY", "rome": "ITALY",
    "brazilian": "BRAZIL", "brasilia": "BRAZIL", "lula": "BRAZIL", "bolsonaro": "BRAZIL", "brazil": "BRAZIL",
    "palestinian": "PALESTINE", "gaza": "GAZA",
    "kenyan": "KENYA", "nairobi": "KENYA",
    "sudanese": "SUDAN", "khartoum": "SUDAN",
    "south african": "SOUTH AFRICA", "pretoria": "SOUTH AFRICA", "durban": "SOUTH AFRICA",
    "nigerian": "NIGERIA", "nigeria": "NIGERIA", "abuja": "NIGERIA",
    "japanese": "JAPAN", "tokyo": "JAPAN"
}

BANNED_IMAGE_SOURCES = [
    "alamy", "dreamstime", "freepik", "shutterstock", "gettyimages", "istockphoto",
    "123rf", "depositphotos", "vecteezy", "canstock", "bigstock", "sputnik",
    "ytimg", "youtube", "cartoon", "clipart", "meme", "watermark", "agefotostock", "pond5",
    "etsy", "redbubble", "zazzle", "teespring", "cafepress", "pinterest", "shopify", "ebay"
]

PERSON_WIKI_MAP = {
    "earhart": ("Amelia Earhart", "AVIATION PIONEER AMELIA EARHART", "UNITED STATES"),
    "hamilton": ("Lewis Hamilton", "FERRARI F1 STAR LEWIS HAMILTON", "UNITED KINGDOM"),
    "russell": ("George Russell (racing driver)", "MERCEDES DRIVER GEORGE RUSSELL", "UNITED KINGDOM"),
    "verstappen": ("Max Verstappen", "RED BULL CHAMPION MAX VERSTAPPEN", "NETHERLANDS"),
    "leclerc": ("Charles Leclerc", "FERRARI DRIVER CHARLES LECLERC", "ITALY"),
    "antonelli": ("Andrea Kimi Antonelli", "MERCEDES F1 DRIVER KIMI ANTONELLI", "ITALY"),
    "trump": ("Donald Trump", "U.S. PRESIDENT DONALD TRUMP", "UNITED STATES"),
    "putin": ("Vladimir Putin", "RUSSIAN PRESIDENT VLADIMIR PUTIN", "RUSSIA"),
    "zelensky": ("Volodymyr Zelenskyy", "UKRAINIAN PRESIDENT ZELENSKYY", "UKRAINE"),
    "zelenskyy": ("Volodymyr Zelenskyy", "UKRAINIAN PRESIDENT ZELENSKYY", "UKRAINE"),
    "witkoff": ("Steve Witkoff", "U.S. SPECIAL ENVOY STEVE WITKOFF", "UNITED STATES"),
    "biden": ("Joe Biden", "U.S. PRESIDENT JOE BIDEN", "UNITED STATES"),
    "netanyahu": ("Benjamin Netanyahu", "ISRAELI PM BENJAMIN NETANYAHU", "ISRAEL"),
    "macron": ("Emmanuel Macron", "FRENCH PRESIDENT EMMANUEL MACRON", "FRANCE"),
    "starmer": ("Keir Starmer", "UK PM KEIR STARMER", "UNITED KINGDOM"),
    "modi": ("Narendra Modi", "INDIAN PM NARENDRA MODI", "INDIA"),
    "xi": ("Xi Jinping", "CHINESE PRESIDENT XI JINPING", "CHINA"),
    "lula": ("Luiz Inácio Lula da Silva", "BRAZILIAN PRESIDENT LULA", "BRAZIL"),
    "bolsonaro": ("Jair Bolsonaro", "BRAZILIAN LEADER BOLSONARO", "BRAZIL"),
    "carney": ("Mark Carney", "CANADIAN PM MARK CARNEY", "CANADA"),
    "erdogan": ("Recep Tayyip Erdoğan", "TURKISH PRESIDENT ERDOGAN", "TURKEY"),
    "khamenei": ("Ali Khamenei", "IRANIAN SUPREME LEADER KHAMENEI", "IRAN"),
    "salman": ("Mohammed bin Salman", "SAUDI CROWN PRINCE MBS", "SAUDI ARABIA"),
    "musk": ("Elon Musk", "TECH LEADER ELON MUSK", "UNITED STATES"),
    "dorsey": ("Jack Dorsey", "BLOCK FOUNDER JACK DORSEY", "UNITED STATES"),
    "altman": ("Sam Altman", "OPENAI CEO SAM ALTMAN", "UNITED STATES"),
    "huang": ("Jensen Huang", "NVIDIA CEO JENSEN HUANG", "UNITED STATES"),
    "zuckerberg": ("Mark Zuckerberg", "META CEO MARK ZUCKERBERG", "UNITED STATES"),
    "cook": ("Tim Cook", "APPLE CEO TIM COOK", "UNITED STATES"),
    "pichai": ("Sundar Pichai", "GOOGLE CEO SUNDAR PICHAI", "UNITED STATES"),
    "nadella": ("Satya Nadella", "MICROSOFT CEO SATYA NADELLA", "UNITED STATES"),
    "mbappe": ("Kylian Mbappé", "REAL MADRID FORWARD MBAPPE", "SPAIN"),
    "vinicius": ("Vinícius Júnior", "REAL MADRID STAR VINICIUS JR", "SPAIN"),
    "yamal": ("Lamine Yamal", "BARCELONA WING LAMINE YAMAL", "SPAIN"),
    "lewandowski": ("Robert Lewandowski", "BARCELONA STRIKER LEWANDOWSKI", "SPAIN")
}

CONCRETE_WIKI_PROPS = {
    "crocodile": ("PREHISTORIC CROCODILE FOSSIL", "Crocodilia", "prehistoric crocodile fossil paleontology skull"),
    "crocodiles": ("ANCIENT CROCODILE SPECIES", "Crocodilia", "ancient crocodile fossil skeleton"),
    "microduck": ("NVIDIA MICRODUCK ROBOTS", "Robotics", "Nvidia Jensen Huang Microduck robot Hugging Face"),
    "microducks": ("NVIDIA MICRODUCK ROBOTS", "Robotics", "Nvidia Microduck robot Pollen Robotics"),
    "pollen robotics": ("POLLEN ROBOTICS & HUGGING FACE", "Robotics", "Pollen Robotics Reachy robot"),
    "electra": ("LOCKHEED ELECTRA AIRCRAFT", "Lockheed Model 10 Electra", "Lockheed Model 10 Electra Amelia Earhart aircraft"),
    "cattle": ("SMART DAIRY FARMING", "Dairy farming", "dairy cows automated milking farm"),
    "farming": ("AI PRECISION AGRICULTURE", "Precision agriculture", "modern agriculture tractor drone technology"),
    "agriculture": ("SMART AGRICULTURE TECH", "Agricultural technology", "precision farming technology tractor"),
    "comcast": ("COMCAST MEDIA & TECH", "Comcast", "Comcast NBCUniversal headquarters building"),
    "peacock": ("PEACOCK STREAMING", "Peacock (streaming service)", "Peacock NBCUniversal streaming television"),
    "grok": ("XAI GROK MODEL", "Grok (chatbot)", "Grok xAI Elon Musk artificial intelligence"),
    "chatgpt": ("OPENAI CHATGPT", "ChatGPT", "ChatGPT OpenAI artificial intelligence"),
    "openai": ("OPENAI & GPT MODELS", "OpenAI", "OpenAI Sam Altman artificial intelligence"),
    "mclaren": ("MCLAREN FORMULA 1", "McLaren", "McLaren Formula 1 race car"),
    "pole": ("FORMULA 1 POLE POSITION", "Formula One car", "Formula 1 racing car grid pole position"),
    "grand prix": ("FORMULA 1 GRAND PRIX", "United States Grand Prix", "Formula 1 Grand Prix Circuit of the Americas race"),
    "ferrari": ("SCUDERIA FERRARI F1", "Scuderia Ferrari", "Ferrari Formula 1 car race track"),
    "mercedes": ("MERCEDES-AMG PETRONAS F1", "Mercedes-Benz in Formula One", "Mercedes AMG Formula 1 car race"),
    "red bull": ("RED BULL RACING F1", "Red Bull Racing", "Red Bull Racing Formula 1 car"),
    "el clasico": ("EL CLASICO RIVALRY", "El Clásico", "Barcelona vs Real Madrid El Clasico football match"),
    "barcelona": ("FC BARCELONA", "FC Barcelona", "FC Barcelona football match Camp Nou"),
    "real madrid": ("REAL MADRID CF", "Real Madrid CF", "Real Madrid football match Bernabeu"),
    "swift": ("NASA SWIFT OBSERVATORY", "Neil Gehrels Swift Observatory", "NASA Neil Gehrels Swift Observatory satellite"),
    "gamma-ray": ("GAMMA-RAY BURST COSMOS", "Gamma-ray burst", "gamma ray burst astronomy NASA space"),
    "supernova": ("SUPERNOVA EXPLOSION", "Supernova", "supernova explosion telescope NASA"),
    "banana": ("CAVENDISH BANANA CROP", "Cavendish banana", "Cavendish banana plantation agriculture"),
    "cat": ("FELINE BIOLOGY STUDY", "Cat", "domestic cat pet owner science"),
    "cats": ("FELINE BEHAVIOR & BIOLOGY", "Cat", "domestic cat close up pet owner"),
    "falcon 9": ("FALCON 9 ROCKET", "Falcon 9", "SpaceX Falcon 9 rocket launch pad"),
    "starlink": ("STARLINK SATELLITES", "Starlink", "SpaceX Starlink satellite orbit"),
    "starship": ("SPACEX STARSHIP", "SpaceX Starship", "SpaceX Starship rocket"),
    "spacex": ("SPACEX LAUNCH SYSTEM", "SpaceX", "SpaceX Falcon 9 launch"),
    "robot": ("HUMANOID ROBOTICS", "Humanoid robot", "humanoid robot artificial intelligence"),
    "robots": ("ADVANCED ROBOTICS", "Robotics", "autonomous robot technology"),
    "voice model": ("AI SPEECH SYNTHESIS", "Speech synthesis", "artificial intelligence audio waveform neural network"),
    "ai model": ("AI NEURAL ARCHITECTURE", "Large language model", "artificial intelligence neural network server"),
    "ai": ("ARTIFICIAL INTELLIGENCE", "Artificial intelligence", "AI data center supercomputer chips"),
    "nvidia": ("NVIDIA AI & ROBOTICS", "Nvidia", "Nvidia Jensen Huang keynote robotics"),
    "gpu": ("NVIDIA GPU ARCHITECTURE", "Graphics processing unit", "Nvidia GPU graphics card hardware"),
    "macbook": ("APPLE SILICON M4 MAX", "MacBook Pro", "Apple MacBook Pro M4 laptop hardware"),
    "chip": ("SEMICONDUCTOR CHIP", "Semiconductor device fabrication", "semiconductor silicon wafer microchip"),
    "chips": ("AI SEMICONDUCTORS", "Integrated circuit", "microchip semiconductor factory"),
    "gaming": ("GAMING & ESPORTS", "Video game", "gaming console esports arena"),
    "playstation": ("PLAYSTATION GAMING", "PlayStation 5", "Sony PlayStation gaming"),
    "xbox": ("XBOX GAMING", "Xbox", "Microsoft Xbox gaming"),
    "cyber": ("CYBERSECURITY OPS", "Computer security", "cybersecurity network server"),
    "nasa": ("NASA SPACE MISSION", "NASA", "NASA rocket launch space telescope"),
    "astronaut": ("ORBITAL SPACEFLIGHT", "International Space Station", "astronaut space station orbit"),
    "astronauts": ("ISS ASTRONAUT CREW", "International Space Station", "astronauts spacewalk International Space Station"),
    "space station": ("INTERNATIONAL SPACE STATION", "International Space Station", "International Space Station orbit Earth"),
    "moon": ("LUNAR EXPLORATION", "Moon", "lunar lander moon surface"),
    "mars": ("MARS EXPLORATION", "Mars", "Mars rover planet surface"),
    "galaxy": ("DEEP SPACE DISCOVERY", "Galaxy", "James Webb Space Telescope galaxy nebula"),
    "black hole": ("COSMIC MYSTERY", "Black hole", "supermassive black hole space astronomy"),
    "satellite": ("ORBITAL SATELLITE", "Communications satellite", "satellite earth orbit"),
    "satellites": ("SATELLITE CONSTELLATION", "Communications satellite", "satellites orbit space Earth"),
    "quantum": ("QUANTUM COMPUTING", "Quantum computing", "quantum computer cryostat lab"),
    "vaccine": ("MEDICAL RESEARCH", "Vaccine", "medical laboratory vaccine research vial"),
    "virus": ("INFECTIOUS DISEASE LAB", "Virology", "medical laboratory microscope doctor"),
    "hospital": ("HOSPITAL & HEALTHCARE", "Hospital", "modern hospital medical doctors"),
    "cancer": ("ONCOLOGY BREAKTHROUGH", "Cancer research", "cancer research laboratory microscope"),
    "brain": ("NEUROSCIENCE LAB", "Human brain", "brain scan medical neuroscience"),
    "dna": ("GENETICS & BIOTECH", "DNA", "DNA genetics CRISPR laboratory"),
    "stock": ("GLOBAL STOCK MARKETS", "New York Stock Exchange", "stock market trading floor screens"),
    "markets": ("FINANCIAL MARKETS", "Financial market", "stock exchange wall street trading"),
    "tariff": ("GLOBAL TRADE & TARIFFS", "Container ship", "cargo container ship port cranes"),
    "bitcoin": ("CRYPTO & DIGITAL ASSETS", "Bitcoin", "Bitcoin cryptocurrency trading"),
    "oil": ("GLOBAL ENERGY MARKETS", "Oil refinery", "oil refinery tanker energy"),
    "champions league": ("UEFA CHAMPIONS LEAGUE", "UEFA Champions League", "Champions League football stadium"),
    "cricket": ("INTERNATIONAL CRICKET", "Cricket", "cricket stadium match pitch"),
    "formula 1": ("FORMULA 1 GRAND PRIX", "Formula One", "Formula 1 race car circuit"),
    "fighter": ("FIGHTER JET DEPLOYMENT", "Eurofighter Typhoon", "Eurofighter Typhoon fighter jet"),
    "drone": ("MILITARY DRONE / UAV", "Unmanned combat aerial vehicle", "military combat drone UAV"),
    "missile": ("BALLISTIC MISSILE SYSTEM", "MIM-104 Patriot", "Patriot missile defense launcher")
}

GLOBAL_OPEN_VCLIPS = []

try:
    FACE_CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
except Exception:
    FACE_CASCADE = None

def get_font(size):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"]:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()

def wrap_lines(draw, text, font, max_w):
    words = str(text).split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textbbox((0, 0), test, font=font)[2] <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines if lines else [""]

def build_wtb_watermark(width=130, height=76):
    logo = Image.new("RGBA", (260, 156), (255, 255, 255, 245))
    d = ImageDraw.Draw(logo)
    d.polygon([(24, 10), (242, 10), (242, 44), (232, 54), (14, 54), (14, 20)], fill=(12, 56, 118, 255))
    d.text((34, 14), "WORLD", fill=(255, 255, 255, 255), font=get_font(34))
    d.rectangle([(14, 58), (242, 108)], fill=(204, 18, 36, 255))
    d.text((32, 62), "TALK", fill=(255, 255, 255, 255), font=get_font(42), stroke_width=2, stroke_fill=(255, 255, 255, 255))
    d.polygon([(96, 112), (242, 112), (242, 136), (234, 144), (96, 144)], fill=(12, 56, 118, 255))
    d.text((112, 114), "BRIEF", fill=(255, 255, 255, 255), font=get_font(26))
    d.rectangle([(14, 149), (242, 153)], fill=(204, 18, 36, 255))
    resample_mode = getattr(Image, "Resampling", Image).LANCZOS
    return logo.resize((width, height), resample_mode)

# ==============================================================================
# 5. FULL YOUTUBE DATA API v3 INTELLIGENCE + ALL 8 PLAYLISTS PRE-CREATION
# ==============================================================================
def sync_all_8_playlists_and_organize_channel(yt):
    playlist_map = {}
    try:
        pl_resp = yt.playlists().list(part="snippet,contentDetails", mine=True, maxResults=50).execute()
        for item in pl_resp.get("items", []):
            t_existing = item.get("snippet", {}).get("title", "").strip()
            playlist_map[t_existing.lower()] = item["id"]

        for pillar in ORDERED_PILLARS:
            p_cfg = CATEGORY_FEEDS[pillar]
            target_pl_title = p_cfg["playlist_title"]
            if target_pl_title.lower() not in playlist_map:
                try:
                    create_resp = yt.playlists().insert(
                        part="snippet,status",
                        body={
                            "snippet": {
                                "title": target_pl_title,
                                "description": f"Official {target_pl_title} deep-dive case studies and shorts by World Talk Brief."
                            },
                            "status": {"privacyStatus": "public"}
                        }
                    ).execute()
                    pl_id = create_resp.get("id")
                    if pl_id:
                        playlist_map[target_pl_title.lower()] = pl_id
                        print(f"📂 [YouTube API Auto-Created Playlist] '{target_pl_title}' -> ID: {pl_id}", flush=True)
                except Exception as ce:
                    print(f"⚠️ Playlist creation note ({target_pl_title}): {str(ce)[:80]}", flush=True)
    except Exception as e:
        print("⚠️ Playlist sync note:", str(e)[:90], flush=True)
    return playlist_map

def run_youtube_api_full_intelligence():
    default_viral_kws = ["ancient", "lake", "antarctic", "fighter", "jets", "missile", "drone", "ai", "robot", "nvidia", "openai", "nasa", "spacex", "starlink", "discovery"]
    token_b64 = os.environ.get("YOUTUBE_TOKEN_JSON_B64", "").strip()
    if not token_b64:
        return default_viral_kws, [], {}, []

    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        t_file = "temp/analytics_token.json"
        with open(t_file, "wb") as tf:
            tf.write(base64.b64decode(token_b64))
        creds = Credentials.from_authorized_user_file(t_file)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        yt = build("youtube", "v3", credentials=creds)

        playlist_map = sync_all_8_playlists_and_organize_channel(yt)

        winning_kws = []
        viral_yt_tags = []
        top_channel_hits = []
        stop_w = {"why", "how", "the", "and", "for", "with", "from", "changes", "next", "move", "shorts", "says", "stated", "after", "briefing", "news", "video", "live", "today"}

        try:
            ch_resp = yt.channels().list(part="contentDetails,statistics,snippet", mine=True).execute()
            items = ch_resp.get("items", [])
            if items:
                ch_stats = items[0].get("statistics", {})
                print(f"📊 [YouTube Channel API] Views: {ch_stats.get('viewCount', 0)} | Subs: {ch_stats.get('subscriberCount', 0)} | Videos: {ch_stats.get('videoCount', 0)}", flush=True)
                uploads_pl = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
                pl_items = yt.playlistItems().list(part="contentDetails,snippet", playlistId=uploads_pl, maxResults=45).execute().get("items", [])
                vid_ids = [it["contentDetails"]["videoId"] for it in pl_items]
                if vid_ids:
                    v_stats = yt.videos().list(part="snippet,contentDetails,statistics,status", id=",".join(vid_ids)).execute().get("items", [])
                    scored_vids = []
                    for v in v_stats:
                        views = int(v.get("statistics", {}).get("viewCount", 0))
                        likes = int(v.get("statistics", {}).get("likeCount", 0))
                        comments = int(v.get("statistics", {}).get("commentCount", 0))
                        title = v.get("snippet", {}).get("title", "")
                        scored_vids.append((views + likes * 12 + comments * 20, views, likes, title))
                    scored_vids.sort(reverse=True)
                    if scored_vids:
                        print(f"🏆 [Our #1 Hit Video] '{scored_vids[0][3][:60]}' ({scored_vids[0][1]} Views, {scored_vids[0][2]} Likes)", flush=True)
                        top_channel_hits = [sv[3] for sv in scored_vids[:5]]
                    for _, _, _, t_str in scored_vids[:10]:
                        for w in re.findall(r"[a-z]{4,}", t_str.lower()):
                            if w not in stop_w and w not in winning_kws:
                                winning_kws.append(w)
        except Exception as ce:
            print("⚠️ Channel stats note:", str(ce)[:80], flush=True)

        pub_after = (datetime.utcnow() - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
        discovered_ids = []
        for cat_key, c_cfg in CATEGORY_FEEDS.items():
            try:
                s_resp = yt.search().list(
                    part="id,snippet",
                    q=c_cfg["search_query"],
                    type="video",
                    order="viewCount",
                    publishedAfter=pub_after,
                    relevanceLanguage="en",
                    maxResults=10
                ).execute()
                for it in s_resp.get("items", []):
                    vid = it.get("id", {}).get("videoId")
                    if vid and vid not in discovered_ids:
                        discovered_ids.append(vid)
            except Exception:
                pass

        for i in range(0, len(discovered_ids), 45):
            chunk_ids = discovered_ids[i:i + 45]
            if not chunk_ids:
                continue
            try:
                tr_stats = yt.videos().list(part="snippet,contentDetails,statistics", id=",".join(chunk_ids)).execute().get("items", [])
                for tv in tr_stats:
                    t_title = tv.get("snippet", {}).get("title", "")
                    t_tags = tv.get("snippet", {}).get("tags", [])
                    for tg in t_tags[:5]:
                        tg_clean = re.sub(r"[^A-Za-z0-9\s]", "", tg).strip()
                        if 3 <= len(tg_clean) <= 28 and tg_clean not in viral_yt_tags:
                            if not any(non_en in tg_clean.lower() for non_en in ["telugu", "tamil", "hindi", "malayalam", "kannada", "kids"]):
                                viral_yt_tags.append(tg_clean)
                    for w in re.findall(r"[a-z]{4,}", t_title.lower()):
                        if w not in stop_w and w not in winning_kws:
                            winning_kws.append(w)
            except Exception:
                pass

        for dkw in default_viral_kws:
            if dkw not in winning_kws:
                winning_kws.append(dkw)
        return winning_kws[:25], viral_yt_tags[:18], playlist_map, top_channel_hits
    except Exception:
        return default_viral_kws, [], {}, []

def add_video_to_category_playlist_and_comment(yt, video_id, pillar, summary_takeaway, playlist_map):
    if not video_id:
        return
    p_cfg = CATEGORY_FEEDS.get(pillar, CATEGORY_FEEDS["WORLD"])
    target_pl_title = p_cfg.get("playlist_title", f"World Talk Brief • {pillar.title()}")

    try:
        playlist_id = playlist_map.get(target_pl_title.lower())
        if not playlist_id:
            pl_resp = yt.playlists().list(part="snippet", mine=True, maxResults=50).execute()
            for item in pl_resp.get("items", []):
                if item.get("snippet", {}).get("title", "").strip().lower() == target_pl_title.lower():
                    playlist_id = item["id"]
                    break

        if playlist_id:
            yt.playlistItems().insert(
                part="snippet",
                body={
                    "snippet": {
                        "playlistId": playlist_id,
                        "resourceId": {"kind": "youtube#video", "videoId": video_id}
                    }
                }
            ).execute()
            print(f"✅ [Added to Playlist] Video {video_id} -> '{target_pl_title}'", flush=True)
    except Exception as pe:
        print(f"ℹ️ [Playlist Add Note]: {str(pe)[:90]}", flush=True)

    try:
        yt.commentThreads().insert(
            part="snippet",
            body={
                "snippet": {
                    "videoId": video_id,
                    "topLevelComment": {
                        "snippet": {
                            "textOriginal": f"📌 KEY TAKEAWAY: {summary_takeaway}\nWhat is your perspective on this? Share your thoughts below! 👇"
                        }
                    }
                }
            }
        ).execute()
        print(f"💬 [YouTube API Engagement Comment Posted] on Video {video_id}", flush=True)
    except Exception:
        pass

# ==============================================================================
# 6. STRICT TOPIC-COHERENCE FILTER & UNIT EXPANDER (`1.56m` -> `1.56 million`!)
# ==============================================================================
def load_published_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {
                    "published_keys": set(data.get("published_keys", [])),
                    "event_fingerprints": data.get("event_fingerprints", []),
                    "last_categories": data.get("last_categories", []),
                    "last_sources": data.get("last_sources", []),
                    "round_robin_idx": int(data.get("round_robin_idx", 0)),
                    "bgm_track_counter": int(data.get("bgm_track_counter", 0))
                }
        except Exception:
            pass
    return {"published_keys": set(), "event_fingerprints": [], "last_categories": [], "last_sources": [], "round_robin_idx": 0, "bgm_track_counter": 0}

def save_published_history(hist_obj):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "updated_at": datetime.utcnow().isoformat(),
                "round_robin_idx": int(hist_obj.get("round_robin_idx", 0)),
                "bgm_track_counter": int(hist_obj.get("bgm_track_counter", 0)),
                "published_keys": list(hist_obj["published_keys"])[-500:],
                "event_fingerprints": hist_obj["event_fingerprints"][-250:],
                "last_categories": hist_obj["last_categories"][-30:],
                "last_sources": hist_obj["last_sources"][-30:]
            }, f, indent=2)
    except Exception:
        pass

def make_story_key(title):
    words = re.findall(r"[a-z0-9]+", title.lower())
    return "_".join(words[:6])

def extract_event_fingerprint(title, first_fact=""):
    stop_w = {"the", "and", "for", "with", "from", "over", "after", "into", "says", "said", "amid", "new", "how", "why", "what", "that", "this", "are", "was", "were", "stands", "brink", "history", "takes", "weekend"}
    comb = f"{title} {first_fact[:120]}"
    tokens = sorted(list({w.lower() for w in re.findall(r"[a-zA-Z]{4,}", comb) if w.lower() not in stop_w}))
    return tokens

def check_semantic_duplicate_or_update(title, first_fact, hist_obj):
    st_key = make_story_key(title)
    if st_key in hist_obj["published_keys"]:
        return ("DUPLICATE", None)

    cur_fp = set(extract_event_fingerprint(title, first_fact))
    if not cur_fp:
        return ("NEW_STORY", None)

    for past in hist_obj["event_fingerprints"]:
        past_fp = set(past.get("tokens", []))
        if not past_fp:
            continue
        overlap = len(cur_fp.intersection(past_fp)) / float(min(len(cur_fp), len(past_fp)))
        if overlap >= 0.38:
            return ("DUPLICATE", None)

    return ("NEW_STORY", None)

BANNED_ARTICLE_TITLES = [
    "uti", "utis", "urinary", "bladder", "bowel", "diarrhea", "constipation", "erectile", "sexually transmitted",
    "ovaries", "ovary", "menopause", "menstrual", "pregnancy", "fertility", "cosmetic surgery", "butt lift",
    "bbl", "botox", "lip filler", "vampire facial", "nathan fielder", "kill switch", "lance oppenheim",
    "indiewire", "cyberselfish", "techno-libertarianism", "book returns", "author takes aim",
    "birthday sale", "percent off", "% off", "sitewide", "promo code", "coupon", "best deals",
    "buying guide", "gift guide", "review:", "we tested", "horoscope", "wordle", "crossword", "sudoku",
    "live updates", "as it happened", "in pictures", "at a glance", "podcast", "quiz", "bandcamp",
    "synth-pop", "album review", "song review", "obsessed with scammers", "how to watch", "tv channel",
    "live stream", "prediction, team news", "power partnership", "ai-griculture"
]

BANNED_PHRASES = [
    "https://", "http://", "https/", "http/", "www.", ".gov", ".org/", ".com/",
    "when you purchase through links", "earn a small commission", "editorial independence",
    "enjoy it as a palate cleanser", "hard to watch this video without ordering",
    "subscribe to smithsonian", "free tote", "special projects editor", "ellen wexler",
    "zoom interview", "told me in a", "do you want to talk", "i started knocking",
    "my agent picked me up", "i grew up in", "i was just listening", "i knew no sector",
    "i just fell into it", "narcissistic", "wait a minute, what's going on",
    "for more information on", "visit https", "explore langley", "communications strategist",
    "turning what if into what will be", "popular on variety", "popular on ", "related:", "read more:",
    "also read:", "external ", "weeing lava", "need a wee", "vampire facials involve",
    "dermal micro-coring involves", "chemical peels are", "founder summit", "buy one",
    "get a second for free", "get your pass", "bring someone with you", "50% off", "register now",
    "ticket", "how to follow:", "where: camp", "when: sunday", "when: saturday",
    "will bring you all the build-up", "enter your email below", "send confirmation",
    "sign you up to our newsletter", "by submitting your information", "confirm you are aged 16",
    "read our privacy policy", "read ourprivacy policy", "agree to the terms", "terms & conditions",
    "latest space missions, discoveries and exploration updates", "here's a video of", "here is a video of",
    "watch the video below", "dw asked people on the ground", "asked people on the ground what life is like",
    "take this one, for example, shared by", "you have got to listen to these", "you've got to listen to these",
    "percent off sitewide", "wired-staff favorite", "birthday girl is feeling generous", "bandcamp page",
    "saxophone solos", "you don't have permission to access", "what is this page",
    "website you are visiting is protected", "for security reasons this page cannot be displayed",
    "access denied", "403 forbidden", "error 404", "enable javascript", "enable cookies", "cloudflare",
    "please verify you are a human", "some readers may find this article distressing",
    "warning: this article contains", "continue reading", "sign up for our newsletter", "all rights reserved",
    "photograph:", "image source:", "getty images", "tells the bbc", "tells bbc", "the bbc joins",
    "send us your questions", "share your story", "tell us what you think", "contact us",
    "have you been affected", "tap here to", "click here to", "listen to our podcast",
    "is seen on monday", "is seen on tuesday", "is seen on wednesday", "is seen on thursday",
    "is seen on friday", "is seen on saturday", "is seen on sunday", "is seen in this",
    "pictured in this", "in this file photo", "lecturer in", "professor of", "associate professor",
    "fellow at the", "sound bite of", "archived recording", "npr's ", "abc news' ", "cbs news' ",
    "nbc news' ", "talks with ", "speaks with ", "is a french journalist, writer"
]

def clean_fact(text):
    """
    Fixes the `abmsuXDGiEA` bug where `1.56m` was read as '1.56 meters'!
    Expands both lowercase and uppercase `1.56m` -> `1.56 million`, `2.4bn` -> `2.4 billion`!
    """
    if not text:
        return ""
    repl = {"\u2011": "-", "\u2013": "-", "\u2014": " - ", "\u2018": "'", "\u2019": "'", "\u201c": "", "\u201d": "", '"': "", "\u00a0": " "}
    for k, v in repl.items():
        text = text.replace(k, v)

    if "|" in text:
        return ""
    if re.search(r"\b(I|me|my|mine|myself|we've|I've|I'm|I'd|our articles)\b", text, flags=re.I):
        return ""
    if len(re.findall(r"\b(WHO|WHAT|WHERE|WHEN|HOW TO FOLLOW)\s*:", text)) >= 2:
        return ""
    if re.search(r"(https?:|www\.|\.gov\b|\.org\b|\.com\b)", text, flags=re.I):
        return ""

    text = re.sub(r"(?i)\bPopular on [A-Za-z]+\b", "", text)
    text = re.sub(r"(?i)\bexternal\b", "", text)
    text = re.sub(r"[A-Z][A-Z\s\.\-]{3,},\s*(HOST|BYLINE|CORRESPONDENT|ANCHOR|REPORTER)\s*:\s*", "", text)
    text = re.sub(r"(?i)^by\s+[A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+and\s+[A-Z][a-z]+\s+[A-Z][a-z]+)?\s*", "", text)
    text = re.sub(r"^[A-Z\s,\.]{3,28}\s*(\([A-Za-z\s]+\))?\s*(?:--|—|-)\s*", "", text)
    text = re.sub(r",\s*writes\s+[A-Z][a-z]+\s+[A-Z][a-z]+\.?$", ".", text)

    text = re.sub(r",\s*(?:an?\s+)?[A-Za-z\s]{2,25}\s+(?:spokesperson|director|official|researcher|professor|investigator)\s+(?:said|stated|noted|added|told\s+[A-Za-z]+)\.?", ".", text, flags=re.I)
    text = re.sub(r",\s*according to\s+[A-Za-z\s]{2,25}\.?", ".", text, flags=re.I)
    text = re.sub(r"\bhe said\b|\bshe said\b|\bthey said\b|\bsaid in a tweet\b", "", text, flags=re.I)

    text = re.sub(r"\s*\([^)]{1,45}\)", "", text)
    text = re.sub(r"(\d+)\s*km/h\b", r"\1 kilometers per hour", text, flags=re.I)
    # Fix `1.56m` -> `1.56 million` and `1.39bn` -> `1.39 billion` so TTS NEVER says "1.56 meters"!
    text = re.sub(r"(\d+\.\d+)\s*[mM]\b", r"\1 million", text)
    text = re.sub(r"(\d+(?:\.\d+)?)\s*bn\b", r"\1 billion", text, flags=re.I)
    text = re.sub(r"(\d+)\s*M\b", r"\1 million", text)

    text = re.sub(r"\bKhartoum\b", "Khar-toom", text)
    text = re.sub(r"\bTaiz\b", "Ta-iz", text)
    text = re.sub(r"\bSanaa\b", "Sa-naa", text)

    text = re.sub(r"(?i)\b(BBC World Service|BBC World|BBC News|BBC|DW|Wired|Al Jazeera Sport|Al Jazeera|IndieWire|Variety|Smithsonian)\b", "official reports", text)
    text = re.sub(r"\[([^\]]+)\]", r"\1", text)
    text = re.sub(r"[^\x20-\x7E]", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    low = text.lower()
    for bp in BANNED_PHRASES:
        if bp in low:
            return ""

    if text.endswith("...") or text.endswith(".."):
        return ""
    words_check = [re.sub(r"[^a-zA-Z]", "", w).lower() for w in text.split()]
    words_check = [w for w in words_check if w]
    if len(words_check) < 6:
        return ""
    dangling_endings = {"a", "an", "the", "to", "in", "on", "of", "for", "with", "and", "or", "by", "at", "from", "that", "which", "as", "into"}
    if words_check[-1] in dangling_endings:
        return ""

    return text

def split_into_complete_sentences(paragraph_text):
    protected = re.sub(r"\b(U\.S|U\.K|U\.N|E\.U|Oct|Nov|Dec|Jan|Feb|Mar|Apr|Aug|Sept|Mr|Mrs|Ms|Dr|Prof|St|Gen|Col|Sen|Rep|S)\.", r"\1<DOT>", paragraph_text)
    raw_sents = re.split(r"(?<=[.!?])\s+", protected)
    return [s.replace("<DOT>", ".") for s in raw_sents]

def is_semantically_similar_claim(new_claim, existing_claims, headline_title=""):
    stop_c = {"the", "and", "for", "with", "from", "that", "this", "have", "has", "had", "were", "was", "are", "said", "says"}
    new_words = {w.lower() for w in re.findall(r"[a-zA-Z]{4,}", new_claim) if w.lower() not in stop_c}
    if len(new_words) < 4:
        return True

    if headline_title:
        title_words = {w.lower() for w in re.findall(r"[a-zA-Z]{4,}", headline_title) if w.lower() not in stop_c}
        if title_words:
            t_overlap = len(new_words.intersection(title_words)) / float(min(len(new_words), len(title_words)))
            if t_overlap >= 0.42:
                return True

    for old_c in existing_claims:
        old_words = {w.lower() for w in re.findall(r"[a-zA-Z]{4,}", old_c["text"]) if w.lower() not in stop_c}
        if not old_words:
            continue
        overlap = len(new_words.intersection(old_words)) / float(min(len(new_words), len(old_words)))
        if overlap >= 0.38:
            return True
    return False

def is_claim_strictly_on_topic(candidate_sent, core_topic_tokens):
    if not core_topic_tokens:
        return True
    s_tokens = {w.lower() for w in re.findall(r"[a-zA-Z0-9]{4,}", candidate_sent)}
    return len(s_tokens.intersection(core_topic_tokens)) >= 1

HEADLINE_STOP_VERBS_ADJS = {
    "have", "has", "had", "what", "when", "where", "while", "after", "before", "under", "inside",
    "amid", "with", "from", "why", "how", "first", "rapid", "changes", "scientists", "find",
    "found", "finally", "save", "says", "said", "new", "major", "global", "world", "report",
    "reports", "study", "shows", "reveals", "could", "would", "should", "make", "made", "makes",
    "obsessed", "unhinged", "surprising", "connection", "owners", "share", "way", "risk", "market",
    "popular", "unexpected", "catch", "warn", "leaves", "behind", "bonanza", "ends", "sounds",
    "eerily", "human", "preview", "predictions", "teams", "block", "blocks", "model", "takes",
    "weekend", "win", "title", "italian", "dutchman", "affect", "millions", "discover", "discovered",
    "that", "this", "these", "those", "something", "doing", "decades", "forced", "pick", "picks",
    "chooses", "launch", "power", "partnership", "between", "through", "their", "there", "about",
    "tighter", "rules", "planned", "protect", "people", "goes", "badly", "wrong", "stands", "brink",
    "history", "beats", "expectations", "offsets", "weakness", "researchers", "claimed", "blurry",
    "object", "very", "likely", "holds", "author", "changing", "bizarre", "million", "billion",
    "trillion", "ancient", "adorable", "hottest", "secretly", "scary", "tiny", "little", "year",
    "years", "predator", "rewriting", "know", "plays", "sell", "sold", "left", "alone", "nothing",
    "started", "playing", "slashes", "cost", "rules", "markups", "extortion", "hiding", "behind",
    "narrative"
}

def extract_primary_topic_anchor(dossier):
    low = f"{dossier['title']} {' '.join(dossier['raw_facts'][:2])}".lower()
    for word_key, (_, wiki_exact, _) in CONCRETE_WIKI_PROPS.items():
        if re.search(rf"\b{re.escape(word_key)}\b", low):
            return wiki_exact

    for p_key, (wiki_page, _, _) in PERSON_WIKI_MAP.items():
        if re.search(rf"\b{re.escape(p_key)}\b", low):
            return wiki_name if 'wiki_name' in locals() else wiki_page

    content_nouns = [
        w for w in re.findall(r"[A-Za-z]{4,}", dossier["title"])
        if w.lower() not in HEADLINE_STOP_VERBS_ADJS
    ]
    return " ".join(content_nouns[:2]).title() if content_nouns else "Global Case Study"

def build_100_percent_original_youtube_title(raw_title, pillar, c_prof, topic_anchor):
    anchor_clean = topic_anchor.strip()
    if len(raw_title) <= 75 and not any(b in raw_title.lower() for b in ["dw ", "bbc", "reuters"]):
        return f"{raw_title} | {pillar.replace('_', ' ').title()} Explained"[:95]
    if pillar == "MIND_BLOWING_FACTS":
        return f"The Untold Science of {anchor_clean} | Case Study Explained"[:95]
    if pillar == "TECHNOLOGY":
        return f"Inside {anchor_clean}: How It Changes the Future of Tech"[:95]
    if pillar == "SCIENCE":
        return f"The {anchor_clean} Discovery That Surprised Scientists"[:95]
    return raw_title[:95]

def paraphrase_into_original_creator_voice(raw_fact, beat_idx=0):
    s = raw_fact.strip().rstrip(".")
    rewrites = [
        (r"(?i)^in a study of\b", "When researchers analyzed"),
        (r"(?i)^according to\b", "Verified data from"),
        (r"(?i)\bmounted a stunning comeback\b", "pulled off a historic turnaround"),
        (r"(?i)\bholds off far right\b", "secured a decisive victory"),
        (r"(?i)\bmore than (\d+)", r"over \1"),
        (r"(?i)\bapproximately (\d+)", r"nearly \1"),
        (r"(?i)\bit is\b", "it's"),
        (r"(?i)\bthat is\b", "that's"),
        (r"(?i)\bthere is\b", "there's"),
        (r"(?i)\bdo not\b", "don't"),
        (r"(?i)\bdoes not\b", "doesn't"),
        (r"(?i)\bdid not\b", "didn't"),
        (r"(?i)\bcannot\b", "can't"),
        (r"(?i)\bhas not\b", "hasn't"),
        (r"(?i)\bhave not\b", "haven't")
    ]
    for pat, rep in rewrites:
        s = re.sub(pat, rep, s)

    s = re.sub(r"\s+", " ", s).strip().rstrip(",;:")
    if not s:
        return ""
    s = s[0].upper() + s[1:]
    return f"{s}."

def extract_story_entities(dossier):
    if dossier.get("visual_anchors"):
        return dossier["visual_anchors"]

    text = f"{dossier['title']} {' '.join(dossier['raw_facts'][:3])}"
    c_prof = dossier["country_profile"]
    pillar = dossier.get("pillar", "WORLD")
    ents = []
    if dossier.get("wiki_hook_entity"):
        ents.append(dossier["wiki_hook_entity"])

    low = text.lower()
    for word_key, (_, wiki_exact, _) in CONCRETE_WIKI_PROPS.items():
        if re.search(rf"\b{re.escape(word_key)}\b", low) and wiki_exact not in ents:
            ents.append(wiki_exact)

    for k, (wiki_name, _, _) in PERSON_WIKI_MAP.items():
        if re.search(rf"\b{re.escape(k)}\b", low):
            if wiki_name not in ents:
                ents.append(wiki_name)

    anchor = extract_primary_topic_anchor(dossier)
    if anchor and anchor not in ents:
        ents.append(anchor)

    if pillar == "WORLD" and not c_prof.get("is_global_topic"):
        for fb in [c_prof["capital"], c_prof["name"].title()]:
            if fb not in ents:
                ents.append(fb)
    return ents[:8] if ents else ["Global Case Study"]

def fetch_wikipedia_article_media_gallery(wiki_page_title):
    gallery_urls = []
    try:
        m_url = f"https://en.wikipedia.org/api/rest_v1/page/media-list/{urllib.parse.quote(wiki_page_title)}"
        r = requests.get(m_url, headers=HEADERS_WIKI, timeout=6).json()
        for item in r.get("items", []):
            if item.get("type") == "image":
                srcset = item.get("srcset", [])
                u = srcset[-1].get("src", "") if srcset else ""
                if u.startswith("//"):
                    u = "https:" + u
                if u and u.lower().endswith((".jpg", ".jpeg", ".png")) and not any(b in u.lower() for b in ["icon", "logo", "symbol", "flag", "commons-logo", "map"]):
                    gallery_urls.append(u)
    except Exception:
        pass
    return gallery_urls[:14]

def build_mind_blowing_fact_dossier(hist_obj):
    curated_mysteries = [
        ("Kola Superdeep Borehole", "Why Scientists Sealed the Deepest Hole Ever Drilled Into Earth", "RUSSIA", ["Kola Superdeep Borehole", "Drilling rig", "Earth crust", "Geology", "Murmansk", "Seismic wave"]),
        ("Point Nemo", "The Secret Ocean Graveyard Where Space Agencies Crash Dying Spacecraft", "INTERNATIONAL", ["Point Nemo", "Spacecraft cemetery", "Pacific Ocean", "Mir", "International Space Station", "Atmospheric entry"]),
        ("Svalbard Global Seed Vault", "Inside the Doomsday Vault Hidden Deep Inside an Arctic Mountain", "NORWAY", ["Svalbard Global Seed Vault", "Spitsbergen", "Permafrost", "Seed", "Arctic", "Glacier"]),
        ("Mariana Trench", "What Deep-Sea Submarines Discovered at the Bottom of the Mariana Trench", "INTERNATIONAL", ["Mariana Trench", "Challenger Deep", "Bathyscaphe Trieste", "Deep sea", "Submersible", "Oceanic trench"]),
        ("Voyager 1", "What NASA's Voyager 1 Just Detected Beyond the Edge of Our Solar System", "UNITED STATES", ["Voyager 1", "Voyager Golden Record", "Heliosphere", "Pale Blue Dot", "Jet Propulsion Laboratory", "Interstellar medium"]),
        ("Large Hadron Collider", "Inside the 27-Kilometer Machine Recreating the First Second of the Universe", "SWITZERLAND", ["Large Hadron Collider", "CERN", "Particle accelerator", "Higgs boson", "ATLAS experiment", "Superconducting magnet"]),
        ("Darvaza gas crater", "Why This Giant Crater in the Desert Has Been Burning for Over 50 Years", "INTERNATIONAL", ["Darvaza gas crater", "Karakum Desert", "Natural gas", "Methane", "Crater", "Turkmenistan"]),
        ("Antikythera mechanism", "The 2,000-Year-Old Ancient Greek Computer That Baffled Modern Scientists", "GREECE", ["Antikythera mechanism", "Antikythera wreck", "Ancient Greece", "Astronomical clock", "Gear", "National Archaeological Museum, Athens"]),
        ("James Webb Space Telescope", "The Impossible Galaxy Discovered by the James Webb Space Telescope", "UNITED STATES", ["James Webb Space Telescope", "Carina Nebula", "Pillars of Creation", "Deep field", "Galaxy", "Hubble Space Telescope"]),
        ("Chernobyl Exclusion Zone", "How Wildlife Is Thriving Inside the Most Radioactive Forest on Earth", "UKRAINE", ["Chernobyl Exclusion Zone", "Prypiat", "Red Forest", "Chernobyl New Safe Confinement", "Przewalski's horse", "Geiger counter"]),
        ("Bering Strait", "Why Two Islands Separated by Just 4 Kilometers Are 21 Hours Apart in Time", "UNITED STATES", ["Diomede Islands", "Bering Strait", "International Date Line", "Alaska", "Siberia", "Sea ice"]),
        ("Quantum entanglement", "The Spooky Quantum Physics Phenomenon That Einstein Refused to Believe", "INTERNATIONAL", ["Quantum entanglement", "Albert Einstein", "Photon", "Laser", "Quantum computing", "Optical table"])
    ]
    random.shuffle(curated_mysteries)

    for wiki_page, viral_title, c_key, visual_anchors in curated_mysteries:
        st_key = make_story_key(viral_title)
        if st_key in hist_obj["published_keys"]:
            continue
        try:
            s_api = "https://en.wikipedia.org/w/api.php"
            ex_r = requests.get(
                s_api,
                params={"action": "query", "prop": "extracts", "exintro": 0, "exchars": 4500, "explaintext": 1, "titles": wiki_page, "format": "json"},
                headers=HEADERS_WIKI, timeout=6
            ).json()
            deep_sents = []
            for pg in ex_r.get("query", {}).get("pages", {}).values():
                for raw_s in split_into_complete_sentences(pg.get("extract", "")):
                    cs = clean_fact(raw_s)
                    if 45 <= len(cs) <= 210 and "== " not in cs:
                        deep_sents.append(cs if cs[-1] in ".!?" else cs + ".")

            w_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(wiki_page)}"
            r = requests.get(w_url, headers=HEADERS_WIKI, timeout=6).json()
            lead_im = r.get("originalimage", {}).get("source") or r.get("thumbnail", {}).get("source")
            page_url = r.get("content_urls", {}).get("desktop", {}).get("page", f"https://en.wikipedia.org/wiki/{urllib.parse.quote(wiki_page)}")

            if len(deep_sents) >= 6:
                pub_d = datetime.utcnow().strftime("%Y-%m-%d")
                claims = [{"text": s, "source_url": page_url, "source_name": "Verified Encyclopedia", "published_date": pub_d} for s in deep_sents[:16]]
                c_prof = build_country_dict_from_db(c_key, is_global_topic=(c_key == "INTERNATIONAL")) if c_key in COUNTRY_GEO_DB else resolve_country_or_domain_profile(viral_title, deep_sents, pillar_name="MIND_BLOWING_FACTS")
                wiki_gal = fetch_wikipedia_article_media_gallery(wiki_page)
                return {
                    "score": 999,
                    "pillar": "MIND_BLOWING_FACTS",
                    "yt_category_id": "27",
                    "story_key": st_key,
                    "event_tokens": extract_event_fingerprint(viral_title, deep_sents[0]),
                    "is_followup_update": False,
                    "previous_event_title": None,
                    "title": viral_title,
                    "original_yt_title": f"{viral_title} | Case Study Explained",
                    "topic_anchor": wiki_page,
                    "wiki_hook_entity": wiki_page,
                    "visual_anchors": visual_anchors,
                    "article_video_urls": [],
                    "category": "cosmic_mystery",
                    "source_url": page_url,
                    "published_date": pub_d,
                    "source_name": "Verified Science & History",
                    "verified_claims": claims,
                    "raw_facts": [c["text"] for c in claims],
                    "lead_img": lead_im,
                    "wiki_gallery_urls": wiki_gal,
                    "country_profile": c_prof,
                    "wb_data": None
                }
        except Exception:
            pass
    return None

def resolve_country_or_domain_profile(title, raw_facts_list, pillar_name="WORLD"):
    headline_low = title.lower()
    body_low = " ".join(raw_facts_list[:3]).lower()

    best_match = None
    best_pos = 9999
    for dem, c_mapped in DEMONYM_TO_COUNTRY.items():
        pos = headline_low.find(dem)
        if pos != -1 and pos < best_pos:
            best_pos = pos
            best_match = c_mapped
    for c_name in COUNTRY_GEO_DB.keys():
        m = re.search(rf"\b{re.escape(c_name.lower())}\b", headline_low)
        if m and m.start() < best_pos:
            best_pos = m.start()
            best_match = c_name

    if best_match and pillar_name in ["WORLD", "BUSINESS", "SPORTS", "HEALTH"]:
        return build_country_dict_from_db(best_match, is_global_topic=False)

    if pillar_name == "WORLD":
        for dem, c_mapped in DEMONYM_TO_COUNTRY.items():
            if re.search(rf"\b{re.escape(dem.strip())}\b", body_low):
                return build_country_dict_from_db(c_mapped, is_global_topic=False)
        for c_name in COUNTRY_GEO_DB.keys():
            if re.search(rf"\b{re.escape(c_name.lower())}\b", body_low):
                return build_country_dict_from_db(c_name, is_global_topic=False)

    hub_names = {
        "MIND_BLOWING_FACTS": ("MIND-BLOWING FACT", "Global Discovery", "World Wonders"),
        "TECHNOLOGY": ("GLOBAL TECH & AI", "Silicon Valley", "Global Tech Sector"),
        "SCIENCE": ("SPACE & SCIENCE", "Global Research", "Scientific Community"),
        "HEALTH": ("MEDICAL SCIENCE", "Global Health", "Biotech & Medicine"),
        "BUSINESS": ("GLOBAL MARKETS", "Wall Street", "Global Economy"),
        "SPORTS": ("SPORTS ARENA", "International Arena", "Global Sports"),
        "ENTERTAINMENT": ("GLOBAL CINEMA", "Hollywood", "Entertainment Industry"),
        "WORLD": ("INTERNATIONAL", "United Nations", "Global Affairs")
    }
    h_name, h_cap, h_reg = hub_names.get(pillar_name, ("GLOBAL BRIEFING", "International Hub", "Global"))
    return {
        "name": h_name,
        "iso2": "UN",
        "iso3": "USA",
        "capital": h_cap,
        "population": "8 billion",
        "region": h_reg,
        "lat": 37.386,
        "lon": -122.083,
        "flag_img": None,
        "is_global_topic": True
    }

def build_country_dict_from_db(c_name, is_global_topic=False):
    iso2, iso3, cap, pop, reg, lat, lon = COUNTRY_GEO_DB.get(c_name, COUNTRY_GEO_DB["UNITED STATES"])
    c_prof = {
        "name": c_name, "iso2": iso2, "iso3": iso3, "capital": cap,
        "population": pop, "region": reg, "lat": lat, "lon": lon,
        "flag_img": None, "is_global_topic": is_global_topic
    }
    try:
        fr = requests.get(f"https://flagcdn.com/w160/{iso2.lower()}.png", headers=HEADERS_WEB, timeout=5)
        if fr.status_code == 200 and len(fr.content) > 500:
            fp = f"temp/flag_{iso2}.png"
            with open(fp, "wb") as f:
                f.write(fr.content)
            c_prof["flag_img"] = Image.open(fp).convert("RGBA")
    except Exception:
        pass
    return c_prof

def normalize_pub_date(raw_date):
    if not raw_date:
        return datetime.utcnow().strftime("%Y-%m-%d")
    cleaned = re.sub(r"\s+", " ", str(raw_date)).strip()
    return cleaned[:25]

def classify_story_mood_and_category(title, claims_text, pillar_name="WORLD"):
    p_cfg = CATEGORY_FEEDS.get(pillar_name, CATEGORY_FEEDS["WORLD"])
    return p_cfg.get("bgm_mood", "dark_geopolitics")

def fetch_verified_world_bank_gdp(iso3):
    try:
        wb_u = f"https://api.worldbank.org/v2/country/{iso3}/indicator/NY.GDP.MKTP.KD.ZG?format=json&per_page=8"
        wbr = requests.get(wb_u, headers=HEADERS_WEB, timeout=6).json()
        if isinstance(wbr, list) and len(wbr) > 1 and wbr[1]:
            pts = [(str(row["date"]), round(float(row["value"]), 1)) for row in wbr[1] if row.get("value") is not None][:5]
            if len(pts) >= 3:
                pts.reverse()
                return ([p[0] for p in pts], [p[1] for p in pts])
    except Exception:
        pass
    return None

def discover_dossier_for_pillar(pillar, hist_obj, winning_keywords, batch_fingerprints):
    if pillar == "MIND_BLOWING_FACTS":
        mb = build_mind_blowing_fact_dossier(hist_obj)
        if mb is not None:
            return mb

    p_cfg = CATEGORY_FEEDS.get(pillar, CATEGORY_FEEDS["WORLD"])
    candidates = []

    for src, url in p_cfg["feeds"]:
        try:
            r_feed = requests.get(url, headers=HEADERS_WEB, timeout=9)
            if r_feed.status_code != 200:
                continue
            feed = feedparser.parse(r_feed.content)
        except Exception:
            continue

        for entry in feed.entries[:15]:
            raw_t = entry.title.rsplit(" - ", 1)[0]
            low_raw_t = raw_t.lower()
            if any(bt in low_raw_t for bt in BANNED_ARTICLE_TITLES):
                continue

            title = clean_fact(raw_t)
            if len(title) < 24:
                continue

            link = getattr(entry, "link", "").strip()
            if any(b_url in link.lower() for b_url in ["/deals/", "/shopping/", "/coupons/", "/reviews/", "/podcasts/", "/video/", "/music/"]):
                continue

            pub_date = normalize_pub_date(getattr(entry, "published", "") or getattr(entry, "updated", ""))
            if not link or not pub_date:
                continue

            raw_sum = BeautifulSoup(getattr(entry, "summary", ""), "html.parser").get_text(separator=" ")
            summary = clean_fact(raw_sum)

            dup_status, _ = check_semantic_duplicate_or_update(title, summary, hist_obj)
            if dup_status == "DUPLICATE":
                continue

            cur_fp_set = set(extract_event_fingerprint(title, summary))
            if any(len(cur_fp_set.intersection(bfp)) / float(max(1, min(len(cur_fp_set), len(bfp)))) >= 0.38 for bfp in batch_fingerprints):
                continue

            core_topic_tokens = {
                w.lower() for w in re.findall(r"[A-Za-z0-9]{4,}", f"{title} {summary}")
                if w.lower() not in HEADLINE_STOP_VERBS_ADJS and w.lower() not in {"the", "and", "for", "with", "from", "that", "this"}
            }

            rss_img = None
            if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
                rss_img = entry.media_thumbnail[0].get("url")
                if rss_img and "bbci.co.uk" in rss_img:
                    rss_img = re.sub(r"/standard/\d+/", "/standard/1024/", rss_img)
            elif hasattr(entry, "media_content") and entry.media_content:
                rss_img = entry.media_content[0].get("url")

            og_img = None
            article_video_urls = []
            verified_claims = []

            for s in split_into_complete_sentences(summary):
                cs = clean_fact(s)
                if 40 <= len(cs) <= 200 and not is_semantically_similar_claim(cs, verified_claims, headline_title=title):
                    if cs[-1] not in ".!?":
                        cs += "."
                    verified_claims.append({
                        "text": cs,
                        "source_url": link,
                        "source_name": src,
                        "published_date": pub_date
                    })

            try:
                r = requests.get(link, headers=HEADERS_WEB, timeout=7)
                if r.status_code == 200 and "permission to access" not in r.text.lower() and "visiting is protected" not in r.text.lower():
                    soup = BeautifulSoup(r.text, "html.parser")
                    m_og = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "twitter:image"})
                    if m_og and m_og.get("content"):
                        og_img = m_og["content"]

                    for m_vid in re.findall(r"(https?://[^\s\"'<>]+?\.(?:mp4|webm))", r.text, flags=re.I):
                        if not any(b in m_vid.lower() for b in ["ad", "banner", "tracker", "pixel", "logo"]) and m_vid not in article_video_urls:
                            article_video_urls.append(m_vid)

                    for p in soup.find_all("p"):
                        if p.find_parent("figcaption") or p.find_parent("figure") or p.find_parent("footer") or p.find_parent("aside") or p.find_parent("form") or p.find_parent("nav"):
                            continue
                        p_txt = p.get_text(separator=" ").strip()
                        if any(stop_m in p_txt.lower() for stop_m in ["when you purchase through links", "earn a small commission", "related articles", "more from techcrunch", "recommended for you"]):
                            break
                        for rs in split_into_complete_sentences(p_txt):
                            cs = clean_fact(rs)
                            if 45 <= len(cs) <= 210 and is_claim_strictly_on_topic(cs, core_topic_tokens) and not is_semantically_similar_claim(cs, verified_claims, headline_title=title):
                                if cs[-1] not in ".!?":
                                    cs += "."
                                verified_claims.append({
                                    "text": cs,
                                    "source_url": link,
                                    "source_name": src,
                                    "published_date": pub_date
                                })
                                if len(verified_claims) >= 18:
                                    break
                        if len(verified_claims) >= 18:
                            break
            except Exception:
                pass

            if len(verified_claims) < 14:
                try:
                    kw_q = " ".join(list(core_topic_tokens)[:4])
                    if kw_q:
                        b_rss = f"https://www.bing.com/news/search?q={urllib.parse.quote(kw_q)}&format=rss"
                        br = requests.get(b_rss, headers=HEADERS_WEB, timeout=6)
                        b_feed = feedparser.parse(br.content)
                        for b_ent in b_feed.entries[:12]:
                            b_desc = clean_fact(BeautifulSoup(getattr(b_ent, "summary", ""), "html.parser").get_text(separator=" "))
                            for bs in split_into_complete_sentences(b_desc):
                                cbs = clean_fact(bs)
                                if 45 <= len(cbs) <= 205 and is_claim_strictly_on_topic(cbs, core_topic_tokens) and not is_semantically_similar_claim(cbs, verified_claims, headline_title=title):
                                    if cbs[-1] not in ".!?":
                                        cbs += "."
                                    verified_claims.append({
                                        "text": cbs,
                                        "source_url": link,
                                        "source_name": src,
                                        "published_date": pub_date
                                    })
                                    if len(verified_claims) >= 18:
                                        break
                except Exception:
                    pass

            if len(verified_claims) < 5:
                continue

            raw_facts = [c["text"] for c in verified_claims]
            c_prof = resolve_country_or_domain_profile(title, raw_facts, pillar_name=pillar)
            wb_data = fetch_verified_world_bank_gdp(c_prof["iso3"]) if not c_prof.get("is_global_topic") else None
            mood_cat = classify_story_mood_and_category(title, " ".join(raw_facts[:4]), pillar_name=pillar)

            temp_d = {"title": title, "raw_facts": raw_facts, "country_profile": c_prof, "pillar": pillar}
            t_anchor = extract_primary_topic_anchor(temp_d)
            orig_yt_title = build_100_percent_original_youtube_title(title, pillar, c_prof, t_anchor)

            comb = f"{title} {' '.join(raw_facts[:3])}".lower()
            analytics_boost = sum(7 for w_kw in winning_keywords if re.search(rf"\b{re.escape(w_kw)}\b", comb))
            trend_score = len(verified_claims) * 4 + analytics_boost

            candidates.append({
                "score": trend_score,
                "pillar": pillar,
                "yt_category_id": p_cfg["yt_category_id"],
                "story_key": make_story_key(title),
                "event_tokens": list(cur_fp_set),
                "is_followup_update": False,
                "previous_event_title": None,
                "title": title,
                "original_yt_title": orig_yt_title,
                "topic_anchor": t_anchor,
                "article_video_urls": article_video_urls[:4],
                "category": mood_cat,
                "source_url": link,
                "published_date": pub_date,
                "source_name": src,
                "verified_claims": verified_claims,
                "raw_facts": raw_facts,
                "lead_img": og_img or rss_img,
                "wiki_gallery_urls": [],
                "country_profile": c_prof,
                "wb_data": wb_data
            })
            if len(candidates) >= 5:
                break
        if len(candidates) >= 5:
            break

    if not candidates:
        return None
    candidates.sort(key=lambda x: x["score"], reverse=True)
    chosen = candidates[0]
    batch_fingerprints.append(set(chosen["event_tokens"]))
    return chosen

# ==============================================================================
# 7. STRICT VIDEO FRAME VALIDATOR (Blocks NASA Text Slates, SMPTE Red Leader & Black Frames!)
# ==============================================================================
def is_valid_cinematic_video_frame(frame_rgb):
    """
    Blocks:
      1. Solid black frames (`black_px > 0.45`) like in `abmsuXDGiEA` (`1:36`)
      2. Solid white/text slides (`white_px > 0.25`) like `#AskNASA` in `X5WKTfvBgeQ` (`0:52`)
      3. Red SMPTE Universal Leader countdowns (`red_dom > 0.35`) like in `X5WKTfvBgeQ` (`0:57`)!
    """
    arr = np.asarray(Image.fromarray(frame_rgb).resize((120, 120)), dtype=np.float32)
    white_px = np.sum((arr[:, :, 0] > 225) & (arr[:, :, 1] > 225) & (arr[:, :, 2] > 225)) / float(120 * 120)
    black_px = np.sum((arr[:, :, 0] < 28) & (arr[:, :, 1] < 28) & (arr[:, :, 2] < 28)) / float(120 * 120)
    red_dom = np.sum((arr[:, :, 0] > 170) & (arr[:, :, 1] < 65) & (arr[:, :, 2] < 65)) / float(120 * 120)
    if white_px > 0.24 or black_px > 0.42 or red_dom > 0.32:
        return False
    return True

def download_and_transcode_mp4_url(cand_u, used_video_urls, tag_id, label_str):
    if not cand_u or cand_u in used_video_urls:
        return None
    try:
        raw_local = f"temp/{tag_id}_raw.mp4"
        clean_mp4 = f"temp/{tag_id}_{len(used_video_urls)}.mp4"

        with requests.get(cand_u, headers=HEADERS_WEB, stream=True, timeout=12) as vr:
            if vr.status_code != 200:
                return None
            bytes_read = 0
            with open(raw_local, "wb") as vf:
                for chunk in vr.iter_content(chunk_size=262144):
                    if not chunk:
                        break
                    vf.write(chunk)
                    bytes_read += len(chunk)
                    if bytes_read >= 5500000:
                        break

        if not os.path.exists(raw_local) or os.path.getsize(raw_local) < 35000:
            return None

        # Skip the first 1.5 seconds (`-ss 1.5`) so any opening title slate is automatically cut off!
        cmd = [
            "ffmpeg", "-y",
            "-ss", "1.5",
            "-i", raw_local,
            "-t", "5.5",
            "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1",
            "-r", "24", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast",
            clean_mp4
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=18, check=False)
        if os.path.exists(clean_mp4) and os.path.getsize(clean_mp4) > 30000:
            vc = VideoFileClip(clean_mp4)
            GLOBAL_OPEN_VCLIPS.append(vc)
            if vc.duration >= 1.8:
                f1 = vc.get_frame(min(0.4, vc.duration * 0.2))
                f2 = vc.get_frame(min(1.2, vc.duration * 0.6))
                if is_valid_cinematic_video_frame(f1) and is_valid_cinematic_video_frame(f2):
                    used_video_urls.add(cand_u)
                    print("   🎬 [SHOWCASE VIDEO LOCKED]:", label_str, f"({round(vc.duration, 1)}s)", flush=True)
                    return {
                        "vclip": vc,
                        "start_t": 0.0,
                        "label": f"LIVE SHOWCASE - {label_str.upper()[:18]}"
                    }
    except Exception:
        pass
    return None

def fetch_and_transcode_real_video_broll(wiki_target, dossier, used_video_urls, tag_id="vclip"):
    topic_anchor = dossier.get("topic_anchor") or extract_primary_topic_anchor(dossier)
    pillar = dossier.get("pillar", "WORLD")
    p_cfg = CATEGORY_FEEDS.get(pillar, CATEGORY_FEEDS["WORLD"])
    subreddits = p_cfg.get("reddit_subs", "worldnews+technology")

    clean_subj = re.sub(r"[^a-zA-Z0-9\s]", " ", f"{wiki_target} {topic_anchor}").strip()
    subj_words = []
    for w in re.findall(r"[A-Za-z0-9]{3,}", clean_subj):
        wl = w.lower()
        if wl not in HEADLINE_STOP_VERBS_ADJS and wl not in subj_words:
            subj_words.append(wl)

    query_str = " ".join(subj_words[:3]) if subj_words else topic_anchor

    # 1. Article Native MP4/WebM Showcase Videos
    for art_v in dossier.get("article_video_urls", []):
        res = download_and_transcode_mp4_url(art_v, used_video_urls, f"{tag_id}_art", query_str)
        if res is not None:
            return res

    # 2. Reddit Subreddit-Targeted HD Showcase Video Search (`v.redd.it` MP4s)
    for r_vq in [query_str, topic_anchor]:
        if not r_vq:
            continue
        try:
            rd_url = f"https://www.reddit.com/r/{subreddits}/search.json?q={urllib.parse.quote(r_vq)}&restrict_sr=1&sort=relevance&t=all&limit=10"
            rr = requests.get(rd_url, headers=HEADERS_WIKI, timeout=6).json()
            for child in rr.get("data", {}).get("children", []):
                post = child.get("data", {})
                if post.get("over_18"):
                    continue
                rv = (post.get("secure_media") or post.get("media") or {}).get("reddit_video", {})
                fb_u = rv.get("fallback_url", "")
                if fb_u and ".mp4" in fb_u:
                    res = download_and_transcode_mp4_url(fb_u, used_video_urls, f"{tag_id}_rd", query_str)
                    if res is not None:
                        return res
        except Exception:
            pass

    # 3. Global Reddit Video Search
    try:
        rd_url2 = f"https://www.reddit.com/search.json?q={urllib.parse.quote(query_str)}&sort=relevance&t=year&limit=10"
        rr2 = requests.get(rd_url2, headers=HEADERS_WIKI, timeout=6).json()
        for child in rr2.get("data", {}).get("children", []):
            post = child.get("data", {})
            if post.get("over_18"):
                continue
            rv = (post.get("secure_media") or post.get("media") or {}).get("reddit_video", {})
            fb_u = rv.get("fallback_url", "")
            if fb_u and ".mp4" in fb_u:
                res = download_and_transcode_mp4_url(fb_u, used_video_urls, f"{tag_id}_rdg", query_str)
                if res is not None:
                    return res
    except Exception:
        pass

    # 4. Wikimedia Commons Video Archive (Strict Title Filter: No SMPTE, No Podcast, No AskNASA!)
    if subj_words:
        wm_q = " ".join(subj_words[:2])
        banned_video_words = [
            "vlog", "webcam", "stream", "gaming", "twitch", "minecraft", "cartoon", "user", "test",
            "lecture", "interview", "golf", "tree", "park", "pronunciation", "spoken", "audio",
            "session", "recorded", "wikidata", "conference", "talk", "presentation", "isolated",
            "slate", "lawrence", "tutorial", "screen", "backpulver", "rakete", "voa", "voice of america",
            "migrant", "newscast", "anchor", "trooper", "police", "kamala", "harris", "senator", "governor",
            "smpte", "leader", "countdown", "asknasa", "podcast", "virology", "rubins"
        ]
        try:
            api = "https://commons.wikimedia.org/w/api.php"
            params = {
                "action": "query", "generator": "search",
                "gsrsearch": f"filetype:video {wm_q}",
                "gsrnamespace": "6", "gsrlimit": 6,
                "prop": "videoinfo|imageinfo", "viprop": "url|size|derivatives", "iiprop": "url|size", "format": "json"
            }
            r = requests.get(api, params=params, headers=HEADERS_WIKI, timeout=6).json()
            for pg in r.get("query", {}).get("pages", {}).values():
                v_title = pg.get("title", "").lower()
                if any(bw in v_title for bw in banned_video_words):
                    continue
                if subj_words[0] not in v_title:
                    continue
                vi = (pg.get("videoinfo") or pg.get("imageinfo") or [{}])[0]
                for d in vi.get("derivatives", []):
                    du = d.get("src", "")
                    if du.endswith((".webm", ".mp4", ".ogv")) and any(res in du for res in ["480p", "360p", "720p"]):
                        res = download_and_transcode_mp4_url(du, used_video_urls, f"{tag_id}_wm", wm_q)
                        if res is not None:
                            return res
        except Exception:
            pass

    return None

# ==============================================================================
# 9. ZERO-REPETITION MULTI-API PHOTO HARVESTER (Bing News + GDELT + HF FLUX.1-schnell!)
# ==============================================================================
def validate_and_enhance_1080p(im, existing_hashes, min_w=400, min_h=250):
    im = im.convert("RGB")
    w, h = im.size
    if w < min_w or h < min_h:
        return None
    if h > w * 1.12:
        return None

    im = im.crop((int(w * 0.05), int(h * 0.05), int(w * 0.95), int(h * 0.92)))

    arr = np.asarray(im.resize((80, 80)), dtype=np.float32)
    c_box = arr[28:52, 28:52]
    red_px = np.sum((c_box[:, :, 0] > 195) & (c_box[:, :, 1] < 45) & (c_box[:, :, 2] < 45))
    if (red_px / float(24 * 24)) > 0.15:
        return None

    white_px = np.sum((arr[:, :, 0] > 235) & (arr[:, :, 1] > 235) & (arr[:, :, 2] > 235))
    if (white_px / float(80 * 80)) > 0.22:
        return None

    rg_diff = np.mean(np.abs(arr[:, :, 0] - arr[:, :, 1]))
    gb_diff = np.mean(np.abs(arr[:, :, 1] - arr[:, :, 2]))
    if rg_diff < 6.0 and gb_diff < 6.0:
        return None

    quant = (arr // 32).astype(int)
    flat = quant[:, :, 0] * 64 + quant[:, :, 1] * 8 + quant[:, :, 2]
    _, counts = np.unique(flat, return_counts=True)
    if (counts.max() / float(80 * 80)) > 0.34:
        return None

    gray_cv = cv2.cvtColor(np.array(im.resize((320, 200))), cv2.COLOR_RGB2GRAY)
    blur_score = cv2.Laplacian(gray_cv, cv2.CV_64F).var()
    if blur_score < 30.0 or im.entropy() < 6.4:
        return None

    gray = im.convert("L").resize((13, 12))
    dh = (np.asarray(gray, dtype=np.int16)[:, 1:] > np.asarray(gray, dtype=np.int16)[:, :-1]).flatten()
    for old_h in existing_hashes:
        if int(np.sum(dh != old_h)) < 14:
            return None
    existing_hashes.append(dh)

    if im.size[0] < 1600:
        scale = 1920.0 / float(im.size[0])
        resample_mode = getattr(Image, "Resampling", Image).LANCZOS
        im = im.resize((1920, int(im.size[1] * scale)), resample_mode)

    im = im.filter(ImageFilter.UnsharpMask(radius=1.5, percent=125, threshold=3))
    im = ImageEnhance.Contrast(im).enhance(1.06)
    return im

def fetch_huggingface_or_pollinations_1080p_scene(ai_prompt, existing_hashes, tag_id="ai_scene"):
    if not ai_prompt or len(ai_prompt) < 5:
        return None
    full_p = f"{ai_prompt}, photorealistic documentary photography, dramatic cinematic lighting, 8k, no text, no watermark"
    hf_token = os.environ.get("HF_TOKEN", "").strip()
    if hf_token:
        try:
            hf_url = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"
            r = requests.post(
                hf_url,
                headers={"Authorization": f"Bearer {hf_token}", "Content-Type": "application/json"},
                json={"inputs": full_p},
                timeout=16
            )
            if r.status_code == 200 and len(r.content) > 20000:
                p = f"temp/{tag_id}_hfflux.jpg"
                with open(p, "wb") as f:
                    f.write(r.content)
                vim = validate_and_enhance_1080p(Image.open(p), existing_hashes)
                if vim is not None:
                    print("   🎨 [HuggingFace FLUX.1 1080p Visual Generated]:", ai_prompt[:45], flush=True)
                    return vim
        except Exception:
            pass

    try:
        seed = random.randint(100, 999999)
        u = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(full_p)}?width=1920&height=1080&seed={seed}&nologo=true"
        r = requests.get(u, headers=HEADERS_WEB, timeout=14)
        if r.status_code == 200 and len(r.content) > 25000:
            p = f"temp/{tag_id}_flux.jpg"
            with open(p, "wb") as f:
                f.write(r.content)
            vim = validate_and_enhance_1080p(Image.open(p), existing_hashes)
            if vim is not None:
                print("   🎨 [Pollinations Flux 1080p Scene Generated]:", ai_prompt[:45], flush=True)
                return vim
    except Exception:
        pass
    return None

def extract_speaker_or_prop_for_beat(beat_text, dossier, entities, beat_idx):
    """
    Constructs a UNIQUE beat-specific query (`beat_specific_q`) from the actual words spoken in `beat_text`
    so Beat 1, Beat 2, Beat 3, Beat 4 NEVER search the exact same query!
    """
    low = beat_text.lower()
    pillar = dossier.get("pillar", "WORLD")
    topic_anchor = dossier.get("topic_anchor") or extract_primary_topic_anchor(dossier)

    matched_people = []
    for p_key, (wiki_page, badge_lbl, _) in PERSON_WIKI_MAP.items():
        m = re.search(rf"\b{re.escape(p_key)}\b", low)
        if m and (pillar in ["WORLD", "BUSINESS", "SPORTS", "TECHNOLOGY"] or p_key in dossier["title"].lower()):
            matched_people.append((m.start(), badge_lbl, wiki_page))
    if matched_people:
        matched_people.sort(reverse=True)
        _, badge_lbl, wiki_page = matched_people[0]
        return badge_lbl, wiki_page, f"{wiki_page} {topic_anchor}", True

    beat_words = [
        w for w in re.findall(r"[A-Za-z]{4,}", beat_text)
        if w.lower() not in HEADLINE_STOP_VERBS_ADJS and w.lower() not in {"their", "there", "which", "would", "could", "should", "about", "these", "those", "where"}
    ]
    specific_Mod = " ".join(beat_words[:2]) if beat_words else entities[beat_idx % len(entities)]

    for word_key, (prop_badge, wiki_exact, news_q) in CONCRETE_WIKI_PROPS.items():
        if re.search(rf"\b{re.escape(word_key)}\b", low):
            return prop_badge, wiki_exact, f"{topic_anchor} {specific_Mod} {wiki_exact}", False

    chosen_ent = entities[beat_idx % len(entities)]
    return f"{pillar.replace('_', ' ')} - {topic_anchor.upper()[:18]}", chosen_ent, f"{topic_anchor} {specific_Mod}", False

def fetch_verified_news_or_wiki_visual(wiki_exact_title, news_query, dossier, existing_hashes, failed_queries, tag_id="beat", used_image_urls=None):
    if used_image_urls is None:
        used_image_urls = set()
    topic_anchor = dossier.get("topic_anchor") or extract_primary_topic_anchor(dossier)
    c_prof = dossier["country_profile"]
    loc_str = "" if c_prof.get("is_global_topic") else f" {c_prof['name']}"

    news_angles = [
        news_query,
        f"{topic_anchor} {wiki_exact_title}",
        f"{dossier['title'][:45]} {wiki_exact_title}",
        f"{topic_anchor}{loc_str}"
    ]
    for nq in news_angles:
        if not nq or len(nq) < 3:
            continue
        try:
            rss_u = f"https://www.bing.com/news/search?q={urllib.parse.quote(nq)}&format=rss"
            r = requests.get(rss_u, headers=HEADERS_WEB, timeout=6)
            for u in re.findall(r"<News:Image>(https?://[^<]+)</News:Image>", r.text)[:20]:
                u_clean = u.replace("&amp;", "&")
                if u_clean in used_image_urls:
                    continue
                if "bing.com/th" in u_clean:
                    u_clean = u_clean.split("&")[0] + "&w=1920&h=1080&c=7&rs=1"
                ir = requests.get(u_clean, headers=HEADERS_WEB, timeout=6)
                if ir.status_code == 200 and len(ir.content) > 10000:
                    p = f"temp/{tag_id}_bnews.jpg"
                    with open(p, "wb") as f:
                        f.write(ir.content)
                    vim = validate_and_enhance_1080p(Image.open(p), existing_hashes)
                    if vim is not None:
                        used_image_urls.add(u_clean)
                        return vim
        except Exception:
            pass

    try:
        gd_q = " ".join(re.findall(r"[A-Za-z0-9]{3,}", news_query)[:3])
        if gd_q:
            gd_u = f"https://api.gdeltproject.org/api/v2/doc/doc?query={urllib.parse.quote(gd_q)}&mode=ArtList&maxrecords=10&format=json"
            gr = requests.get(gd_u, headers=HEADERS_WEB, timeout=6).json()
            for art in gr.get("articles", []):
                im_u = art.get("socialimage", "")
                if im_u and im_u.startswith("http") and im_u not in used_image_urls and not any(b in im_u.lower() for b in BANNED_IMAGE_SOURCES):
                    ir = requests.get(im_u, headers=HEADERS_WEB, timeout=5)
                    if ir.status_code == 200 and len(ir.content) > 12000:
                        p = f"temp/{tag_id}_gdelt.jpg"
                        with open(p, "wb") as f:
                            f.write(ir.content)
                        vim = validate_and_enhance_1080p(Image.open(p), existing_hashes)
                        if vim is not None:
                            used_image_urls.add(im_u)
                            return vim
    except Exception:
        pass

    for gal_u in dossier.get("wiki_gallery_urls", []):
        if gal_u in used_image_urls:
            continue
        try:
            ir = requests.get(gal_u, headers=HEADERS_WIKI, timeout=5)
            if ir.status_code == 200 and len(ir.content) > 14000:
                p = f"temp/{tag_id}_wgal.jpg"
                with open(p, "wb") as f:
                    f.write(ir.content)
                vim = validate_and_enhance_1080p(Image.open(p), existing_hashes)
                if vim is not None:
                    used_image_urls.add(gal_u)
                    return vim
        except Exception:
            pass

    for cm_q in [wiki_exact_title, topic_anchor]:
        if not cm_q:
            continue
        try:
            api = "https://commons.wikimedia.org/w/api.php"
            params = {
                "action": "query", "generator": "search",
                "gsrsearch": f"filetype:bitmap {cm_q}",
                "gsrnamespace": "6", "gsrlimit": 12,
                "prop": "imageinfo", "iiprop": "url", "iiurlwidth": 1920, "format": "json"
            }
            r = requests.get(api, params=params, headers=HEADERS_WIKI, timeout=6).json()
            for pg in r.get("query", {}).get("pages", {}).values():
                t_low = pg.get("title", "").lower()
                if any(b in t_low for b in ["map", "diagram", "logo", "icon", "flag", "coat", "chart", "japanese", "kanji", "plaque", "stamp", "coin"]):
                    continue
                ii = pg.get("imageinfo", [{}])[0]
                u = ii.get("thumburl") or ii.get("url")
                if u and u not in used_image_urls and u.lower().endswith((".jpg", ".jpeg", ".png")):
                    ir = requests.get(u, headers=HEADERS_WIKI, timeout=6)
                    if ir.status_code == 200 and len(ir.content) > 14000:
                        p = f"temp/{tag_id}_comm.jpg"
                        with open(p, "wb") as f:
                            f.write(ir.content)
                        vim = validate_and_enhance_1080p(Image.open(p), existing_hashes)
                        if vim is not None:
                            used_image_urls.add(u)
                            return vim
        except Exception:
            pass

    failed_queries.append(news_query)
    return None

def build_prop_driven_storyboard_1080p(
    sections_list, dossier, entities, W, H, tag_prefix="short",
    shared_hashes=None, shared_video_urls=None, start_beat_offset=0, shared_photo_pool=None, shared_image_urls=None
):
    planned_beats = []
    existing_hashes = shared_hashes if shared_hashes is not None else []
    used_video_urls = shared_video_urls if shared_video_urls is not None else set()
    used_image_urls = shared_image_urls if shared_image_urls is not None else set()
    unique_real_photos = shared_photo_pool if shared_photo_pool is not None else []
    failed_queries = []
    reused_photo_beats = 0
    moving_video_beats = 0

    if start_beat_offset == 0 and dossier.get("lead_img") and not any(b in dossier["lead_img"].lower() for b in BANNED_IMAGE_SOURCES):
        try:
            r = requests.get(dossier["lead_img"], headers=HEADERS_WEB, timeout=6)
            if r.status_code == 200 and len(r.content) > 12000:
                p = f"temp/{tag_prefix}_lead_0.jpg"
                with open(p, "wb") as f:
                    f.write(r.content)
                vim = validate_and_enhance_1080p(Image.open(p), existing_hashes)
                if vim is not None:
                    unique_real_photos.append(vim)
                    used_image_urls.add(dossier["lead_img"])
        except Exception:
            pass

    global_beat_idx = start_beat_offset
    max_video_clips_for_block = 6 if W < H else 3

    for sec_idx, sec in enumerate(sections_list):
        narration = sec["narration"]
        sec_dur = sec["duration"]
        word_timings = sec["word_timings"]
        sec_headline = sec.get("headline") or sec.get("chapter_title") or make_clean_context_headline(dossier["title"])
        sec_role = sec.get("role", "THE REAL STORY")
        claim_meta = sec.get("claim_meta") or dossier["verified_claims"][0]

        ai_photo_q = sec.get("ai_news_photo_query", "")
        ai_video_q = sec.get("ai_video_broll_query", "")
        ai_img_prompt = sec.get("ai_image_prompt", "")

        target_beat_len = 2.6 if W < H else 3.0
        num_beats = max(2, int(round(sec_dur / target_beat_len)))
        beat_dur = sec_dur / float(num_beats)
        words = narration.split()
        w_per_b = max(1, int(math.ceil(len(words) / float(num_beats))))

        for b_i in range(num_beats):
            b_txt = " ".join(words[b_i * w_per_b:(b_i + 1) * w_per_b]) or narration
            prop_badge, wiki_target, search_q, _ = extract_speaker_or_prop_for_beat(b_txt, dossier, entities, global_beat_idx)
            if ai_photo_q and b_i == 0:
                search_q = f"{ai_photo_q} {b_txt[:25]}"
            if sec.get("role"):
                prop_badge = sec["role"]
            low_b = b_txt.lower()

            vseg = None
            if (b_i % 2 == 1 or re.search(r"\b(video|playing|walk|waddling|launch|race|robot|robots|action)\b", low_b)) and moving_video_beats < max_video_clips_for_block:
                v_target = ai_video_q if ai_video_q else wiki_target
                vseg = fetch_and_transcode_real_video_broll(
                    v_target, dossier, used_video_urls, tag_id=f"{tag_prefix}_vc_{global_beat_idx}"
                )

            if vseg is not None:
                b_type = "VIDEO_BROLL_BEAT"
                moving_video_beats += 1
                beat_im = unique_real_photos[-1] if unique_real_photos else Image.new("RGB", (1920, 1080), (12, 18, 32))
                stage_1 = build_clean_1080p_stage(beat_im, W, H)
            else:
                if global_beat_idx == 0 and unique_real_photos:
                    beat_im = unique_real_photos[0]
                else:
                    beat_im = fetch_verified_news_or_wiki_visual(
                        wiki_target, search_q, dossier, existing_hashes, failed_queries,
                        tag_id=f"{tag_prefix}_b{global_beat_idx}", used_image_urls=used_image_urls
                    )
                    # If news search didn't yield a brand-new image, generate a brand-new 1080p visual via HuggingFace FLUX.1 / Pollinations so photos NEVER repeat!
                    if beat_im is None:
                        custom_prompt = ai_img_prompt if (ai_img_prompt and b_i == 0) else f"{dossier['title']}, {b_txt}"
                        beat_im = fetch_huggingface_or_pollinations_1080p_scene(
                            custom_prompt, existing_hashes, tag_id=f"{tag_prefix}_ai_{global_beat_idx}"
                        )
                    if beat_im is not None:
                        unique_real_photos.append(beat_im)
                    elif unique_real_photos:
                        base_p = unique_real_photos[global_beat_idx % len(unique_real_photos)]
                        beat_im = base_p.transpose(Image.FLIP_LEFT_RIGHT) if (global_beat_idx % 2 == 1) else base_p
                        reused_photo_beats += 1
                    else:
                        beat_im = Image.new("RGB", (1920, 1080), (12, 18, 32))

                if re.search(r"\b(versus|contrast|between|ahead of|beat|rival)\b", low_b) and len(unique_real_photos) >= 2 and b_i == 1:
                    b_type = "SPLIT_COMPARE_BEAT"
                else:
                    b_type = "CINEMA_HERO_ZOOM"

                stage_1 = build_clean_1080p_stage(beat_im, W, H)

            secondary_im = unique_real_photos[(len(unique_real_photos) - 2) % len(unique_real_photos)] if len(unique_real_photos) >= 2 else beat_im
            prev_stage = planned_beats[-1]["stage_1"] if planned_beats else None

            planned_beats.append({
                "section_idx": sec_idx,
                "beat_in_section": b_i,
                "beat_type": b_type,
                "camera_mode": global_beat_idx % 6,
                "pan_dir": 1 if (global_beat_idx % 2 == 0) else -1,
                "duration": round(beat_dur, 3),
                "beat_excerpt": b_txt,
                "section_role": sec_role,
                "section_headline": sec_headline,
                "full_section_narration": narration,
                "word_timings": word_timings,
                "section_duration": sec_dur,
                "section_elapsed_before": round(b_i * beat_dur, 3),
                "stage_1": stage_1,
                "prev_stage": prev_stage,
                "primary_im": beat_im,
                "primary_lbl": prop_badge,
                "secondary_im": secondary_im,
                "vseg": vseg,
                "claim_meta": claim_meta,
                "story": dossier
            })
            global_beat_idx += 1

    stats = {
        "run_status": "PASS",
        "total_beats": len(planned_beats),
        "unique_real_photos": len(unique_real_photos),
        "moving_video_beats": moving_video_beats,
        "reused_photo_beats": reused_photo_beats,
        "failed_queries_count": len(failed_queries),
        "failed_queries": failed_queries[:8]
    }
    print("📊 [AUDIT]", tag_prefix.upper(), "| Beats:", stats["total_beats"], "| Unique Photos:", stats["unique_real_photos"], "| Moving Videos:", stats["moving_video_beats"], flush=True)
    return planned_beats, unique_real_photos, stats

async def render_and_upload_short_unit(short_dossier, unit_num, watermark, voice_sub_dir, hist_obj, winning_keywords, viral_yt_tags, playlist_map, top_channel_hits):
    pillar = short_dossier.get("pillar", "WORLD")
    short_sections, short_entities = build_ai_directed_sections(short_dossier, is_short=True, top_channel_hits=top_channel_hits)
    print(f"\n📱 [SHORT #{unit_num} - {pillar}] Building AI-Directed 1080p Short on: {short_dossier['original_yt_title']}", flush=True)

    for idx, sec in enumerate(short_sections):
        ap = f"temp/s{unit_num}_voice_{idx}.mp3"
        vc, dur, w_timings = await voice_sub_dir.synthesize_with_word_boundaries(sec["narration"], ap, pillar=pillar)
        sec["audio_clip"] = vc
        sec["duration"] = dur
        sec["word_timings"] = w_timings

    s_beats, s_unique_photos, s_stats = build_prop_driven_storyboard_1080p(
        short_sections, short_dossier, short_entities, 1080, 1920, tag_prefix=f"short_{unit_num}"
    )

    short_clips = []
    beat_switch_times_s = []
    cur_t = 0.0
    for sec_idx, sec in enumerate(short_sections):
        sec_beats = [b for b in s_beats if b["section_idx"] == sec_idx]
        for b in sec_beats:
            beat_switch_times_s.append(round(cur_t, 2))
            cur_t += b["duration"]
        clip = make_section_clip_from_beats(sec_beats, watermark, voice_sub_dir, sec["duration"], 1080, 1920, is_short=True)
        clip = clip.with_audio(sec["audio_clip"]) if MOVIEPY_V2 else clip.set_audio(sec["audio_clip"])
        short_clips.append(clip)

    final_short = concatenate_videoclips(short_clips, method="compose")
    track_seed = hist_obj.get("bgm_track_counter", 0) + unit_num
    hist_obj["bgm_track_counter"] = track_seed
    bgm_s = AudioFileClip(build_30_track_mood_adaptive_album_bgm(
        f"temp/bgm_s{unit_num}.wav", final_short.duration, beat_switch_times_s,
        mood=short_dossier["category"], track_seed=track_seed
    ))
    final_short = final_short.with_audio(CompositeAudioClip([final_short.audio, bgm_s])) if MOVIEPY_V2 else final_short.set_audio(CompositeAudioClip([final_short.audio, bgm_s]))
    out_short = "output/WTB_1080p_Short_9x16.mp4" if unit_num == 1 else f"output/WTB_1080p_Short_{unit_num}_9x16.mp4"
    final_short.write_videofile(out_short, fps=24, codec="libx264", audio_codec="aac", bitrate="8000k", preset="ultrafast", threads=4, logger=None)

    thumb_out = "output/WTB_1080p_Short_Thumb.jpg" if unit_num == 1 else f"output/WTB_1080p_Short_{unit_num}_Thumb.jpg"
    short_pkg = create_signature_wtb_brand_thumbnail(short_dossier, short_entities, s_unique_photos, watermark, out_path=thumb_out)

    short_hashtags_str = " ".join(short_pkg["hashtags"] + ["#Shorts", "#Explained"])
    short_seo_desc = (
        f"{short_dossier['original_yt_title']}\n\n"
        f"World Talk Brief [{pillar.replace('_', ' ')}] original #Shorts case study.\n\n"
        f"KEY ENTITIES: {', '.join(short_entities[:5])}\n\n"
        f"{short_hashtags_str}"
    )
    ai_tags = short_dossier.get("ai_seo_tags", [])
    short_seo_tags = [
        "World Talk Brief", pillar.replace("_", " ").title(), "Case Study Explained", "YouTube Shorts",
        short_dossier["country_profile"]["name"].title()
    ] + ai_tags[:6] + short_entities[:4] + winning_keywords[:4] + viral_yt_tags[:4]

    try_youtube_auto_upload(
        out_short, short_dossier["original_yt_title"], short_seo_desc, short_seo_tags,
        category_id=short_dossier.get("yt_category_id", "25"), pillar=pillar, is_short=True,
        thumbnail_path=short_pkg["selected_thumbnail"], playlist_map=playlist_map,
        summary_takeaway=short_sections[-1]["narration"]
    )
    hist_obj["published_keys"].add(short_dossier["story_key"])
    hist_obj["event_fingerprints"].append({"title": short_dossier["title"], "tokens": short_dossier["event_tokens"]})
    hist_obj["last_categories"].append(pillar)
    hist_obj["last_sources"].append(short_dossier["source_name"])
    return s_stats

async def render_and_upload_long_unit(lead_long_dossier, unit_num, watermark, voice_sub_dir, hist_obj, winning_keywords, viral_yt_tags, playlist_map, top_channel_hits):
    pillar = lead_long_dossier.get("pillar", "WORLD")
    long_chapters, lead_long_entities = build_ai_directed_sections(lead_long_dossier, is_short=False, top_channel_hits=top_channel_hits)
    print(f"\n📺 [LONG #{unit_num} - {pillar}] Building AI-Directed Case Study on: {lead_long_dossier['original_yt_title']}", flush=True)

    for idx, ch in enumerate(long_chapters):
        ap = f"temp/l{unit_num}_voice_{idx}.mp3"
        vc, dur, w_timings = await voice_sub_dir.synthesize_with_word_boundaries(ch["narration"], ap, pillar=pillar)
        ch["audio_clip"] = vc
        ch["duration"] = dur
        ch["word_timings"] = w_timings
        ch["dossier"] = lead_long_dossier
        ch["chapter_title"] = ch["headline"]

    long_clips = []
    beat_switch_times_l = []
    shared_long_photos = []
    long_stats_list = []
    shared_long_hashes = []
    shared_long_video_urls = set()
    shared_long_image_urls = set()
    running_beat_offset = 0
    cur_lt = 0.0

    for ch_idx, ch in enumerate(long_chapters):
        ch_beats, _, ch_st = build_prop_driven_storyboard_1080p(
            [ch], lead_long_dossier, lead_long_entities, 1920, 1080, tag_prefix=f"long_{unit_num}_ch{ch_idx+1}",
            shared_hashes=shared_long_hashes, shared_video_urls=shared_long_video_urls,
            start_beat_offset=running_beat_offset, shared_photo_pool=shared_long_photos,
            shared_image_urls=shared_long_image_urls
        )
        running_beat_offset += len(ch_beats)
        long_stats_list.append(ch_st)
        for b in ch_beats:
            beat_switch_times_l.append(round(cur_lt, 2))
            cur_lt += b["duration"]
        clip = make_section_clip_from_beats(ch_beats, watermark, voice_sub_dir, ch["duration"], 1920, 1080, is_short=False)
        clip = clip.with_audio(ch["audio_clip"]) if MOVIEPY_V2 else clip.set_audio(ch["audio_clip"])
        long_clips.append(clip)

    final_long = concatenate_videoclips(long_clips, method="compose")
    track_seed = hist_obj.get("bgm_track_counter", 0) + unit_num + 10
    hist_obj["bgm_track_counter"] = track_seed
    bgm_l = AudioFileClip(build_30_track_mood_adaptive_album_bgm(
        f"temp/bgm_l{unit_num}.wav", final_long.duration, beat_switch_times_l,
        mood=lead_long_dossier["category"], track_seed=track_seed
    ))
    final_long = final_long.with_audio(CompositeAudioClip([final_long.audio, bgm_l])) if MOVIEPY_V2 else final_long.set_audio(CompositeAudioClip([final_long.audio, bgm_l]))
    out_long = "output/WTB_1080p_Long_16x9.mp4" if unit_num == 1 else f"output/WTB_1080p_Long_{unit_num}_16x9.mp4"
    final_long.write_videofile(out_long, fps=20, codec="libx264", audio_codec="aac", bitrate="8000k", preset="ultrafast", threads=4, logger=None)

    thumb_out = "output/WTB_1080p_Thumb_1.jpg" if unit_num == 1 else f"output/WTB_1080p_Thumb_{unit_num}.jpg"
    pkg_report = create_signature_wtb_brand_thumbnail(lead_long_dossier, lead_long_entities, shared_long_photos, watermark, out_path=thumb_out)

    chap_lines = []
    t_acc = 0
    for ch in long_chapters:
        mm = int(t_acc) // 60
        ss = int(t_acc) % 60
        chap_lines.append(f"{mm:02d}:{ss:02d} - {ch['chapter_title']}")
        t_acc += ch.get("duration", 16)

    long_hashtags_str = " ".join(pkg_report["hashtags"] + ["#CaseStudy", "#DeepDive"])
    long_seo_desc = (
        f"{pkg_report['selected_title']}\n\n"
        f"World Talk Brief [{pillar.replace('_', ' ')}] presents an original deep-dive case study.\n\n"
        f"CHAPTER TIMESTAMPS:\n" + "\n".join(chap_lines) + "\n\n"
        f"KEY SUBJECTS & ENTITIES: {', '.join(lead_long_entities[:8])}\n\n"
        f"{long_hashtags_str}"
    )
    ai_tags = lead_long_dossier.get("ai_seo_tags", [])
    long_seo_tags = [
        "World Talk Brief", pillar.replace("_", " ").title(), "Documentary Case Study",
        lead_long_dossier["country_profile"]["name"].title()
    ] + ai_tags[:6] + lead_long_entities[:4] + winning_keywords[:4] + viral_yt_tags[:4]

    try_youtube_auto_upload(
        out_long, pkg_report["selected_title"], long_seo_desc, long_seo_tags,
        category_id=lead_long_dossier.get("yt_category_id", "25"), pillar=pillar, is_short=False,
        thumbnail_path=pkg_report["selected_thumbnail"], playlist_map=playlist_map,
        summary_takeaway=long_chapters[-1]["narration"]
    )
    hist_obj["published_keys"].add(lead_long_dossier["story_key"])
    hist_obj["event_fingerprints"].append({"title": lead_long_dossier["title"], "tokens": lead_long_dossier["event_tokens"]})
    hist_obj["last_categories"].append(pillar)
    hist_obj["last_sources"].append(lead_long_dossier["source_name"])
    return pkg_report

async def main():
    try:
        watermark = build_wtb_watermark(width=130, height=76)
        voice_sub_dir = VoiceAndSubtitleEngine()
        hist_obj = load_published_history()
        winning_keywords, viral_yt_tags, playlist_map, top_channel_hits = run_youtube_api_full_intelligence()

        rr_idx = hist_obj.get("round_robin_idx", 0)
        batch_fingerprints = []
        selected_dossiers = []

        for step in range(len(ORDERED_PILLARS) * 2):
            pillar = ORDERED_PILLARS[(rr_idx + step) % len(ORDERED_PILLARS)]
            d = discover_dossier_for_pillar(pillar, hist_obj, winning_keywords, batch_fingerprints)
            if d is not None:
                selected_dossiers.append(d)
                if len(selected_dossiers) >= 4:
                    hist_obj["round_robin_idx"] = (rr_idx + step + 1) % len(ORDERED_PILLARS)
                    break

        if len(selected_dossiers) < 4:
            hist_obj["published_keys"].clear()
            hist_obj["event_fingerprints"].clear()
            for pillar in ORDERED_PILLARS:
                d = discover_dossier_for_pillar(pillar, hist_obj, winning_keywords, batch_fingerprints)
                if d is not None:
                    selected_dossiers.append(d)
                    if len(selected_dossiers) >= 4:
                        break

        s1_dossier = selected_dossiers[0]
        l1_lead = selected_dossiers[1] if len(selected_dossiers) > 1 else selected_dossiers[0]
        s2_dossier = selected_dossiers[2] if len(selected_dossiers) > 2 else selected_dossiers[0]
        l2_lead = selected_dossiers[3] if len(selected_dossiers) > 3 else selected_dossiers[1]

        # 1. Short Video #1 (Pillar #1)
        s1_stats = await render_and_upload_short_unit(s1_dossier, 1, watermark, voice_sub_dir, hist_obj, winning_keywords, viral_yt_tags, playlist_map, top_channel_hits)
        # 2. Long Documentary #1 (Pillar #2)
        pkg_1 = await render_and_upload_long_unit(l1_lead, 1, watermark, voice_sub_dir, hist_obj, winning_keywords, viral_yt_tags, playlist_map, top_channel_hits)
        # 3. Short Video #2 (Pillar #3)
        s2_stats = await render_and_upload_short_unit(s2_dossier, 2, watermark, voice_sub_dir, hist_obj, winning_keywords, viral_yt_tags, playlist_map, top_channel_hits)
        # 4. Long Documentary #2 (Pillar #4)
        pkg_2 = await render_and_upload_long_unit(l2_lead, 2, watermark, voice_sub_dir, hist_obj, winning_keywords, viral_yt_tags, playlist_map, top_channel_hits)

        save_published_history(hist_obj)

        with open("output/wtb_1080p_report.json", "w") as f:
            json.dump({
                "videos_produced_in_run": 4,
                "ai_director_enabled": True,
                "deepgram_aura_2_enabled": bool(os.environ.get("DEEPGRAM_API_KEY")),
                "groq_llama70b_enabled": bool(os.environ.get("GROQ_API_KEY")),
                "hf_flux_enabled": bool(os.environ.get("HF_TOKEN")),
                "next_round_robin_index": hist_obj.get("round_robin_idx", 0),
                "playlists_synced": len(playlist_map),
                "analytics_winning_keywords": winning_keywords,
                "viral_youtube_tags_discovered": viral_yt_tags,
                "short_1": {"title": s1_dossier["original_yt_title"], "pillar": s1_dossier["pillar"], "audit": s1_stats},
                "long_1": {"title": l1_lead["original_yt_title"], "pillar": l1_lead["pillar"], "packaging": pkg_1},
                "short_2": {"title": s2_dossier["original_yt_title"], "pillar": s2_dossier["pillar"], "audit": s2_stats},
                "long_2": {"title": l2_lead["original_yt_title"], "pillar": l2_lead["pillar"], "packaging": pkg_2}
            }, f, indent=2)

        print("✅ [6/6] GITHUB CLOUD MULTI-API MASTER ENGINE (GROQ + DEEPGRAM AURA-2 + HF FLUX + YOUTUBE) COMPLETE!", flush=True)
    finally:
        for vc in GLOBAL_OPEN_VCLIPS:
            try:
                vc.close()
            except Exception:
                pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print("❌ CRITICAL ERROR DETAILS:", flush=True)
        traceback.print_exc()
        sys.exit(1)
