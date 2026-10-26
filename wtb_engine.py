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
    "User-Agent": "WorldTalkBriefMultiAPIEngine/45.0 (https://github.com/bapuop17/wtb_engine; editorial@worldtalkbrief.org)"
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

# Deepgram Aura-2 (Latest Generation Ultra-Human Voices) + Aura-1 + Edge-TTS Backup
CATEGORY_VOICE_CAST = {
    "WORLD": (["aura-2-apollo-en", "aura-orion-en"], "en-US-AndrewMultilingualNeural", "+3%"),
    "TECHNOLOGY": (["aura-2-aries-en", "aura-arcas-en"], "en-US-BrianMultilingualNeural", "+4%"),
    "MIND_BLOWING_FACTS": (["aura-2-thalia-en", "aura-asteria-en"], "en-US-AvaMultilingualNeural", "+3%"),
    "SCIENCE": (["aura-2-hermes-en", "aura-helios-en"], "en-US-BrianMultilingualNeural", "+3%"),
    "BUSINESS": (["aura-2-zeus-en", "aura-perseus-en"], "en-US-AndrewMultilingualNeural", "+4%"),
    "HEALTH": (["aura-2-helena-en", "aura-luna-en"], "en-US-AvaMultilingualNeural", "+3%"),
    "SPORTS": (["aura-2-draco-en", "aura-angus-en"], "en-US-BrianMultilingualNeural", "+5%"),
    "ENTERTAINMENT": (["aura-2-andromeda-en", "aura-stella-en"], "en-US-EmmaMultilingualNeural", "+4%")
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
# 2. MULTI-ACT GROQ LLAMA-3.3-70B AI DIRECTOR BRAIN
#    Generates 50s Shorts (6-7 scenes) & 3.5-to-5 Minute Deep Long Videos (9-10 chapters)!
# ==============================================================================
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
                        "temperature": 0.68,
                        "max_tokens": 3600
                    },
                    timeout=25
                )
                if r.status_code == 200:
                    content = r.json()["choices"][0]["message"]["content"]
                    return json.loads(content)
            except Exception as e:
                print(f"⚠️ Groq ({g_model}) note:", str(e)[:80], flush=True)

    hf_token = os.environ.get("HF_TOKEN", "").strip()
    if hf_token:
        try:
            r = requests.post(
                "https://router.huggingface.co/v1/chat/completions",
                headers={"Authorization": f"Bearer {hf_token}", "Content-Type": "application/json"},
                json={
                    "model": "Qwen/Qwen2.5-72B-Instruct",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "max_tokens": 3000,
                    "temperature": 0.65
                },
                timeout=25
            )
            if r.status_code == 200:
                txt = r.json()["choices"][0]["message"]["content"]
                m = re.search(r"\{.*\}", txt, flags=re.S)
                if m:
                    return json.loads(m.group(0))
        except Exception:
            pass

    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if gemini_key and gemini_key.startswith("AIza"):
        try:
            g_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
            payload = {
                "contents": [{"parts": [{"text": f"{system_prompt}\n\n{user_prompt}"}]}],
                "generationConfig": {"responseMimeType": "application/json", "temperature": 0.65}
            }
            r = requests.post(g_url, json=payload, timeout=20)
            if r.status_code == 200:
                txt = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(txt)
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
                m = re.search(r"\{.*\}", r.text.strip(), flags=re.S)
                if m:
                    return json.loads(m.group(0))
        except Exception:
            time.sleep(1.0)
    return None

def ai_direct_complete_video_package(dossier, is_short=True, top_channel_hits=None):
    """
    Uses Groq Llama-3.3-70B to craft:
      - For Shorts: 6 fast-paced scenes (~125-145 words = 45 to 55 seconds)
      - For Long Videos: 9 deep-dive investigative chapters (~480-650 words = 3.2 to 4.5 minutes!)
    """
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
  "seo_tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8"],
  "scenes": [
    {{
      "scene_num": 1,
      "context_pill": "SHORT UPPERCASE BADGE (max 22 chars, ASCII only, e.g. 'THE VIRAL KEYNOTE')",
      "narration": "Engaging spoken narration ({words_per_scene}) in natural human storyteller English with contractions (here's, it's, didn't) and zero robotic meta-phrases.",
      "news_photo_query": "Exact 3-4 word query to find real news photos for THIS specific sentence (e.g. 'Jensen Huang Nvidia robot')",
      "video_broll_query": "Exact 2-3 word query to find real moving stock/news video footage for THIS sentence (e.g. 'humanoid robot walking' or 'fighter jet takeoff')",
      "ai_image_prompt": "Detailed photorealistic 8k documentary photography prompt depicting THIS exact sentence (no text in image)"
    }}
  ]
}}
CRITICAL RULES:
1. Generate EXACTLY {num_scenes} scenes in "scenes".
2. Every scene MUST stay 100% focused on the main story ({raw_title}). Never drift into unrelated topics.
3. For Long videos, each scene's "narration" MUST be 3 to 4 rich, detailed sentences ({words_per_scene}) explaining the full context, history, numbers, and impact so the total video is 3.5 to 4.5 minutes long.
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
    "french": "FRANCE", "paris": "FRANCE", "macron": "FRANCE", "lecornu": "FRANCE",
    "american": "UNITED STATES", "u.s.": "UNITED STATES", "washington": "UNITED STATES", "white house": "UNITED STATES",
    "russian": "RUSSIA", "moscow": "RUSSIA", "kremlin": "RUSSIA", "putin": "RUSSIA",
    "chinese": "CHINA", "beijing": "CHINA",
    "israeli": "ISRAEL", "jerusalem": "ISRAEL", "tel aviv": "ISRAEL", "netanyahu": "ISRAEL",
    "iranian": "IRAN", "tehran": "IRAN",
    "indian": "INDIA", "new delhi": "INDIA", "modi": "INDIA",
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
# 8. 6-CAMERA DOCUMENTARY MOTION ENGINE (Fixes Repetitive Zoom-In / Zoom-Out!)
#    - Moving Video Clips (`VIDEO_BROLL_BEAT`) play at 100% NATIVE 1:1 STEADY MOTION!
#    - Still Images rotate across 6 distinct, subtle documentary camera movements!
# ==============================================================================
def extract_diverse_camera_frame_from_stage(stage_tuple, W, H, bp, camera_mode=0):
    """
    Rotates across 6 distinct documentary camera movements for still images:
      Mode 0: Ultra-Subtle 4% Documentary Push-In
      Mode 1: Pure Horizontal Tracking Glide (Left -> Right, zero zoom)
      Mode 2: Vertical Cinema Tilt (Bottom -> Top reveal, zero zoom)
      Mode 3: Pure Horizontal Tracking Glide (Right -> Left, zero zoom)
      Mode 4: Gentle 4% Documentary Pull-Back Reveal
      Mode 5: Steady Parallax Spotlight Frame
    """
    resample_mode = getattr(Image, "Resampling", Image).BILINEAR
    _, fg, _ = stage_tuple
    smooth_p = 0.5 - 0.5 * math.cos(math.pi * bp)
    fw, fh = fg.size

    if camera_mode == 0:
        # Subtle 4% Push-In centered
        cur_w = int(W + (fw - W) * (0.45 - 0.35 * smooth_p))
        cur_h = int(H + (fh - H) * (0.45 - 0.35 * smooth_p))
        ox = (fw - cur_w) // 2
        oy = (fh - cur_h) // 2
    elif camera_mode == 1:
        # Pure Left-to-Right Horizontal Tracking Shot (Constant zoom, zero zoom-in/out!)
        cur_w, cur_h = W, H
        ox = int((fw - W) * smooth_p)
        oy = (fh - H) // 2
    elif camera_mode == 2:
        # Vertical Cinema Tilt (Bottom-to-Top reveal, constant zoom)
        cur_w, cur_h = W, H
        ox = (fw - W) // 2
        oy = int((fh - H) * (1.0 - smooth_p))
    elif camera_mode == 3:
        # Pure Right-to-Left Horizontal Tracking Shot
        cur_w, cur_h = W, H
        ox = int((fw - W) * (1.0 - smooth_p))
        oy = (fh - H) // 2
    elif camera_mode == 4:
        # Gentle 4% Pull-Back Reveal
        cur_w = int(W + (fw - W) * (0.10 + 0.35 * smooth_p))
        cur_h = int(H + (fh - H) * (0.10 + 0.35 * smooth_p))
        ox = (fw - cur_w) // 2
        oy = (fh - cur_h) // 2
    else:
        # Steady Frame with subtle diagonal drift
        cur_w, cur_h = W, H
        ox = int((fw - W) * 0.3 * smooth_p)
        oy = int((fh - H) * 0.3 * smooth_p)

    frame = fg.crop((ox, oy, ox + cur_w, oy + cur_h)).resize((W, H), resample_mode).convert("RGBA")
    draw = ImageDraw.Draw(frame, "RGBA")

    top_grad_h = 140 if W < H else 100
    for y in range(0, top_grad_h):
        alpha = int(145 * (1.0 - (y / float(top_grad_h))))
        draw.line([(0, y), (W, y)], fill=(4, 7, 14, alpha))

    bot_grad_h = 460 if W < H else 230
    for y in range(H - bot_grad_h, H):
        alpha = int(210 * (((y - (H - bot_grad_h)) / float(bot_grad_h)) ** 1.25))
        draw.line([(0, y), (W, y)], fill=(4, 7, 14, alpha))
    return frame

def render_1080p_beat_frame(beat, watermark, voice_sub_dir, local_t, W, H, is_short=True):
    """
    100% CLEAN FULL-SCREEN COMPOSITOR:
    - ZERO yellow lines at the bottom (`H - 8` yellow bar completely removed!)
    - ZERO artificial zoom-in/out on Moving Video B-Roll (`VIDEO_BROLL_BEAT` plays at native 1:1 steady framing!)
    - 6 Diverse Camera Movements on Still Images (`camera_mode = beat_idx % 6`)
    """
    beat_dur = beat["duration"]
    bp = min(max(local_t / max(beat_dur, 0.1), 0.0), 1.0)
    b_type = beat["beat_type"]
    story = beat["story"]
    c_prof = story["country_profile"]
    section_t = beat["section_elapsed_before"] + local_t
    cam_mode = beat.get("camera_mode", 0)

    if b_type == "VIDEO_BROLL_BEAT" and beat.get("vseg") is not None:
        vseg = beat["vseg"]
        vc = vseg["vclip"]
        try:
            t_vid = (vseg["start_t"] + local_t) % max(vc.duration - 0.15, 0.5)
            raw_vf = Image.fromarray(vc.get_frame(t_vid)).convert("RGB")
            # NATIVE 1:1 STEADY VIDEO PLAYBACK (NO artificial zoom-in/zoom-out on moving video!)
            frame = fit_full_height_face_aware_1080p(raw_vf, W, H).convert("RGBA")
            draw = ImageDraw.Draw(frame, "RGBA")
            bot_grad_h = 440 if W < H else 220
            for y in range(H - bot_grad_h, H):
                alpha = int(205 * (((y - (H - bot_grad_h)) / float(bot_grad_h)) ** 1.25))
                draw.line([(0, y), (W, y)], fill=(4, 7, 14, alpha))
        except Exception:
            frame = extract_diverse_camera_frame_from_stage(beat["stage_1"], W, H, bp, camera_mode=cam_mode)
            draw = ImageDraw.Draw(frame, "RGBA")
    elif b_type == "SPLIT_COMPARE_BEAT":
        frame = Image.new("RGBA", (W, H), (8, 12, 22, 255))
        if is_short:
            top_im = fit_full_height_face_aware_1080p(beat["primary_im"], W, H // 2)
            bot_im = fit_full_height_face_aware_1080p(beat["secondary_im"], W, H - (H // 2))
            frame.paste(top_im, (0, 0))
            frame.paste(bot_im, (0, H // 2))
        else:
            left_im = fit_full_height_face_aware_1080p(beat["primary_im"], W // 2, H)
            right_im = fit_full_height_face_aware_1080p(beat["secondary_im"], W // 2, H)
            frame.paste(left_im, (0, 0))
            frame.paste(right_im, (W // 2, 0))
        draw = ImageDraw.Draw(frame, "RGBA")
    else:
        frame = extract_diverse_camera_frame_from_stage(beat["stage_1"], W, H, bp, camera_mode=cam_mode)
        if local_t < 0.18 and beat.get("prev_stage") is not None:
            try:
                prev_f = extract_diverse_camera_frame_from_stage(beat["prev_stage"], W, H, 1.0, camera_mode=(cam_mode - 1) % 6)
                alpha_blend = local_t / 0.18
                frame = Image.blend(prev_f, frame, alpha_blend)
            except Exception:
                pass
        draw = ImageDraw.Draw(frame, "RGBA")

    # Top-Left Compact Creator Brand Logo + Flag
    top_y = 34 if is_short else 30
    frame.paste(watermark, (38, top_y), watermark)
    if c_prof.get("flag_img"):
        fl = c_prof["flag_img"].resize((76, 48))
        frame.paste(fl, (182, top_y + 14), fl)

    # Top-Right Sleek Dark Glass Context Pill (NO yellow border!)
    raw_lbl = beat["vseg"]["label"] if (b_type == "VIDEO_BROLL_BEAT" and beat.get("vseg")) else beat["primary_lbl"]
    kicker_lbl = re.sub(r"[^\x20-\x7E]", "", str(raw_lbl)).strip()
    f_lv = get_font(20 if is_short else 22)
    lw_box = draw.textbbox((0, 0), kicker_lbl, font=f_lv)[2] + 38
    draw.rounded_rectangle([(W - lw_box - 38, top_y + 12), (W - 38, top_y + 56)], radius=22, fill=(10, 14, 24, 210), outline=(255, 255, 255, 160), width=2)
    draw.text((W - lw_box - 19, top_y + 21), kicker_lbl, fill=(255, 255, 255, 255), font=f_lv)

    # Center-Bottom Pop-Up Creator Subtitles (Zero yellow lines at bottom!)
    sub_strip = voice_sub_dir.render_exact_synced_subtitles(beat["word_timings"], section_t, W, H, is_short=is_short)
    sub_y = 1520 if is_short else (H - 150)
    frame.paste(sub_strip, (0, sub_y), sub_strip)

    return np.array(frame.convert("RGB"))

def build_prop_driven_storyboard_1080p(
    sections_list, dossier, entities, W, H, tag_prefix="short",
    shared_hashes=None, shared_video_urls=None, start_beat_offset=0, shared_photo_pool=None
):
    planned_beats = []
    existing_hashes = shared_hashes if shared_hashes is not None else []
    used_video_urls = shared_video_urls if shared_video_urls is not None else set()
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
        except Exception:
            pass

    global_beat_idx = start_beat_offset
    # High-density video B-roll allowance: up to 6 moving video clips per Short and 3 per Long chapter!
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

        target_beat_len = 2.5 if W < H else 2.8
        num_beats = max(2, int(round(sec_dur / target_beat_len)))
        beat_dur = sec_dur / float(num_beats)
        words = narration.split()
        w_per_b = max(1, int(math.ceil(len(words) / float(num_beats))))

        for b_i in range(num_beats):
            b_txt = " ".join(words[b_i * w_per_b:(b_i + 1) * w_per_b]) or narration
            prop_badge, wiki_target, search_q, _ = extract_speaker_or_prop_for_beat(b_txt, dossier, entities, global_beat_idx)
            if ai_photo_q and b_i == 0:
                search_q = ai_photo_q
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
                        wiki_target, search_q, dossier, existing_hashes, failed_queries, tag_id=f"{tag_prefix}_b{global_beat_idx}"
                    )
                    if beat_im is None and ai_img_prompt:
                        beat_im = fetch_huggingface_or_pollinations_1080p_scene(
                            ai_img_prompt, existing_hashes, tag_id=f"{tag_prefix}_ai_{global_beat_idx}"
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

def make_section_clip_from_beats(section_beats, watermark, voice_sub_dir, section_dur, W, H, is_short=True):
    def make_frame(t):
        elapsed = 0.0
        chosen_beat = section_beats[-1]
        local_t = 0.0
        for b in section_beats:
            if t <= elapsed + b["duration"] or b is section_beats[-1]:
                chosen_beat = b
                local_t = max(0.0, t - elapsed)
                break
            elapsed += b["duration"]
        return render_1080p_beat_frame(chosen_beat, watermark, voice_sub_dir, local_t, W, H, is_short=is_short)
    return VideoClip(make_frame, duration=section_dur)

# ==============================================================================
# 10. DEEPGRAM AURA-2 ULTRA-HUMAN VOICE ENGINE (`aura-2-*` + Sentence Chunking)
# ==============================================================================
class VoiceAndSubtitleEngine:
    async def synthesize_with_word_boundaries(self, text, out_path, pillar="WORLD"):
        dg_models, edge_voice, rate = CATEGORY_VOICE_CAST.get(pillar, (["aura-2-apollo-en", "aura-orion-en"], "en-US-AndrewMultilingualNeural", "+3%"))
        raw_mp3 = out_path.replace(".mp3", "_raw.mp3")
        word_timings = []
        used_deepgram = False

        dg_key = os.environ.get("DEEPGRAM_API_KEY", "").strip()
        if dg_key:
            for dg_model in dg_models:
                try:
                    dg_url = f"https://api.deepgram.com/v1/speak?model={dg_model}"
                    r = requests.post(
                        dg_url,
                        headers={"Authorization": f"Token {dg_key}", "Content-Type": "application/json"},
                        json={"text": text[:1900]},
                        timeout=18
                    )
                    if r.status_code == 200 and len(r.content) > 2000:
                        with open(raw_mp3, "wb") as f:
                            f.write(r.content)
                        used_deepgram = True
                        print(f"   🎙️ [Deepgram Aura-2 Human Voice Locked] Model: {dg_model}", flush=True)
                        break
                except Exception as de:
                    print(f"⚠️ Deepgram ({dg_model}) note:", str(de)[:80], flush=True)

        if not used_deepgram:
            for _ in range(2):
                try:
                    comm = edge_tts.Communicate(text, edge_voice, rate=rate, pitch="+0Hz")
                    word_timings = []
                    with open(raw_mp3, "wb") as audio_file:
                        async for chunk in comm.stream():
                            if chunk["type"] == "audio":
                                audio_file.write(chunk["data"])
                            elif chunk["type"] == "WordBoundary":
                                w_start = chunk["offset"] / 10_000_000.0
                                w_dur = chunk["duration"] / 10_000_000.0
                                word_timings.append({"word": chunk["text"], "start": round(w_start, 3), "end": round(w_start + max(w_dur, 0.08), 3)})
                    if os.path.exists(raw_mp3) and os.path.getsize(raw_mp3) > 1000:
                        break
                except Exception:
                    await asyncio.sleep(0.4)

        if not os.path.exists(raw_mp3) or os.path.getsize(raw_mp3) <= 1000:
            gTTS(text=text, lang="en").save(raw_mp3)

        try:
            cmd = [
                "ffmpeg", "-y", "-i", raw_mp3,
                "-af", "highpass=f=70,equalizer=f=180:width_type=o:width=1.5:g=2.0,loudnorm=I=-14:TP=-1.5:LRA=11,apad=pad_dur=0.20",
                "-ar", "48000", "-b:a", "192k", out_path
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=12, check=False)
            if not os.path.exists(out_path) or os.path.getsize(out_path) < 1000:
                os.replace(raw_mp3, out_path)
        except Exception:
            os.replace(raw_mp3, out_path)

        vc = AudioFileClip(out_path)
        total_dur = vc.duration
        if not word_timings:
            words = text.split()
            weights = []
            for w in words:
                base_w = max(len(w), 2)
                if w.endswith((".", "!", "?")):
                    base_w += 4.5
                elif w.endswith((",", ";", ":", "—", "-")):
                    base_w += 2.2
                weights.append(float(base_w))
            tot_w = max(sum(weights), 1.0)
            usable_dur = max(total_dur - 0.22, 0.5)
            cur = 0.0
            for w, wt in zip(words, weights):
                wd = (wt / tot_w) * usable_dur
                word_timings.append({"word": w, "start": round(cur, 3), "end": round(cur + wd, 3)})
                cur += wd
        return vc, total_dur, word_timings

    def render_exact_synced_subtitles(self, word_timings, section_t, W, H, is_short=True):
        if not word_timings:
            return Image.new("RGBA", (W, 240), (0, 0, 0, 0))
        chunk_sz = 4 if is_short else 6
        chunks = [word_timings[i:i + chunk_sz] for i in range(0, len(word_timings), chunk_sz)]
        active_chunk = chunks[0]
        active_word_idx = 0
        for ch in chunks:
            if ch[0]["start"] <= section_t <= (ch[-1]["end"] + 0.25):
                active_chunk = ch
                for w_i, w_obj in enumerate(ch):
                    if section_t >= w_obj["start"]:
                        active_word_idx = w_i
                break
            elif section_t > (ch[-1]["end"] + 0.25):
                active_chunk = ch
                active_word_idx = len(ch) - 1

        strip_h = 240 if is_short else 130
        strip = Image.new("RGBA", (W, strip_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(strip, "RGBA")
        font = get_font(58 if is_short else 44)
        words_str_list = [w["word"] for w in active_chunk]

        if is_short:
            lines = [words_str_list[:2], words_str_list[2:]] if len(words_str_list) > 2 else [words_str_list]
            y_cur = 16
            w_cnt = 0
            for ln in lines:
                if not ln:
                    continue
                disp = [w.upper() for w in ln]
                lw = draw.textbbox((0, 0), " ".join(disp), font=font)[2]
                x_cur = (W - lw) // 2
                for dw in disp:
                    col = (255, 225, 0, 255) if w_cnt == active_word_idx else (255, 255, 255, 255)
                    draw.text((x_cur + 4, y_cur + 4), dw, font=font, fill=(0, 0, 0, 230))
                    draw.text((x_cur, y_cur), dw, font=font, fill=col, stroke_width=8, stroke_fill=(0, 0, 0, 255))
                    x_cur += draw.textbbox((0, 0), dw + " ", font=font)[2]
                    w_cnt += 1
                y_cur += 76
        else:
            phrase = " ".join(words_str_list)
            lw = draw.textbbox((0, 0), phrase, font=font)[2]
            x_cur = (W - lw) // 2
            for idx_w, w in enumerate(words_str_list):
                col = (255, 225, 0, 255) if idx_w == active_word_idx else (255, 255, 255, 255)
                draw.text((x_cur + 3, 28), w, font=font, fill=(0, 0, 0, 230))
                draw.text((x_cur, 25), w, font=font, fill=col, stroke_width=6, stroke_fill=(0, 0, 0, 255))
                x_cur += draw.textbbox((0, 0), w + " ", font=font)[2]
        return strip

# ==============================================================================
# 11. 2026 VIRAL YOUTUBER THUMBNAIL ENGINE
# ==============================================================================
def build_meaningful_thumbnail_hook(dossier):
    if dossier.get("ai_thumb_hook"):
        return dossier["ai_thumb_hook"]
    t_anchor = (dossier.get("topic_anchor") or extract_primary_topic_anchor(dossier)).upper()
    pillar = dossier.get("pillar", "WORLD")
    impact_lines = {
        "WORLD": "THE REAL TRUTH",
        "TECHNOLOGY": "GAME CHANGER",
        "MIND_BLOWING_FACTS": "HOW IT WORKS",
        "SCIENCE": "NEW DISCOVERY",
        "BUSINESS": "MARKET SHOCK",
        "HEALTH": "NEW BREAKTHROUGH",
        "SPORTS": "HISTORIC WIN",
        "ENTERTAINMENT": "INSIDE STORY"
    }
    line_1 = t_anchor[:18]
    line_2 = impact_lines.get(pillar, "EXPLAINED")
    return line_1, line_2

def create_signature_wtb_brand_thumbnail(dossier, entities, unique_photos, watermark, out_path="output/WTB_1080p_Thumb_1.jpg"):
    W, H = 1920, 1080
    c_prof = dossier["country_profile"]
    pillar = dossier.get("pillar", "WORLD")
    p_cfg = CATEGORY_FEEDS.get(pillar, CATEGORY_FEEDS["WORLD"])
    badge_col = p_cfg["badge_color"]
    accent_col = p_cfg["accent_color"]

    face_photos = [im for im in unique_photos if has_well_framed_face(im)]
    hero_1 = face_photos[0] if face_photos else (unique_photos[0] if unique_photos else Image.new("RGB", (1920, 1080), (14, 22, 38)))

    full_im = fit_full_height_face_aware_1080p(hero_1, W, H)
    full_im = ImageEnhance.Color(ImageEnhance.Contrast(full_im).enhance(1.25)).enhance(1.22)
    canvas = full_im.convert("RGBA")
    draw = ImageDraw.Draw(canvas, "RGBA")

    for y in range(660, H):
        alpha = int(235 * (((y - 660) / 420.0) ** 1.25))
        draw.line([(0, y), (W, y)], fill=(5, 8, 18, alpha))

    canvas.paste(watermark, (54, 48), watermark)
    if c_prof.get("flag_img"):
        fl = c_prof["flag_img"].resize((104, 66))
        draw.rounded_rectangle([(198, 52), (310, 126)], radius=8, fill=(255, 255, 255, 255))
        canvas.paste(fl, (202, 56), fl)

    hook_line_1, hook_line_2 = build_meaningful_thumbnail_hook(dossier)
    f_giant = get_font(98)
    f_sub = get_font(86)

    draw.text((62, 668), hook_line_1, fill=(0, 0, 0, 245), font=f_giant)
    draw.text((54, 660), hook_line_1, fill=(255, 255, 255, 255), font=f_giant, stroke_width=8, stroke_fill=(0, 0, 0, 255))

    w_l2 = draw.textbbox((0, 0), hook_line_2, font=f_sub)[2] + 76
    poly_pts = [(54, 785), (54 + w_l2, 785), (38 + w_l2, 912), (38, 912)]
    draw.polygon([(p[0] + 10, p[1] + 10) for p in poly_pts], fill=(0, 0, 0, 225))
    draw.polygon(poly_pts, fill=badge_col + (255,), outline=(255, 255, 255, 255))
    draw.text((82, 804), hook_line_2, fill=(255, 255, 255, 255), font=f_sub)

    sub_teaser = make_clean_context_headline(dossier["original_yt_title"], max_words=7)
    draw.text((58, 942), f"> {sub_teaser}", fill=accent_col + (255,), font=get_font(34), stroke_width=3, stroke_fill=(0, 0, 0, 255))

    canvas.convert("RGB").save(out_path, quality=96)

    return {
        "selected_thumbnail": out_path,
        "thumbnail_category_style": pillar,
        "selected_title": dossier["original_yt_title"],
        "hashtags": ["#WorldTalkBrief", f"#{pillar.replace('_', '')}", f"#{c_prof['name'].replace(' ', '')}", "#Explained"]
    }

# ==============================================================================
# 12. YOUTUBE UPLOADER + AUTOMATIC PLAYLIST ASSIGNMENT + AUTO COMMENT
# ==============================================================================
def try_youtube_auto_upload(video_path, title, description, tags, category_id="25", pillar="WORLD", is_short=False, thumbnail_path=None, playlist_map=None, summary_takeaway=""):
    token_b64 = os.environ.get("YOUTUBE_TOKEN_JSON_B64", "").strip()
    if not token_b64:
        print("ℹ️ [GitHub Cloud Test Mode] No YouTube API token set yet; saved to GitHub Artifacts:", video_path, flush=True)
        return None

    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        t_file = "temp/token_upload.json"
        with open(t_file, "wb") as tf:
            tf.write(base64.b64decode(token_b64))
        creds = Credentials.from_authorized_user_file(t_file)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        yt = build("youtube", "v3", credentials=creds)

        final_title = (title[:90] + " #Shorts") if is_short and "#shorts" not in title.lower() else title[:100]
        body = {
            "snippet": {"title": final_title, "description": description, "tags": tags[:25], "categoryId": str(category_id)},
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
        }
        media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/mp4")
        req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
        resp = None
        while resp is None:
            _, resp = req.next_chunk()
        vid_id = resp["id"]
        print(f"✅ [YOUTUBE LIVE UPLOAD SUCCESS - {pillar}] https://youtu.be/{vid_id}", flush=True)
        if thumbnail_path and os.path.exists(thumbnail_path):
            try:
                yt.thumbnails().set(videoId=vid_id, media_body=MediaFileUpload(thumbnail_path)).execute()
            except Exception as te:
                print("⚠️ Thumbnail set warning:", te, flush=True)

        add_video_to_category_playlist_and_comment(yt, vid_id, pillar, summary_takeaway or title, playlist_map or {})
        return vid_id
    except Exception as e:
        print("⚠️ YouTube upload attempt failed:", str(e)[:140], flush=True)
        return None

# ==============================================================================
# 13. MODULAR RENDER FUNCTIONS
# ==============================================================================
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
    running_beat_offset = 0
    cur_lt = 0.0

    for ch_idx, ch in enumerate(long_chapters):
        ch_beats, _, ch_st = build_prop_driven_storyboard_1080p(
            [ch], lead_long_dossier, lead_long_entities, 1920, 1080, tag_prefix=f"long_{unit_num}_ch{ch_idx+1}",
            shared_hashes=shared_long_hashes, shared_video_urls=shared_long_video_urls,
            start_beat_offset=running_beat_offset, shared_photo_pool=shared_long_photos
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

# ==============================================================================
# MASTER EXECUTION
# ==============================================================================
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
