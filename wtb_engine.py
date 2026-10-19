import os
import sys
import re
import math
import wave
import json
import base64
import asyncio
import traceback
import urllib.parse
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
    from moviepy.editor import VideoClip, AudioFileClip, CompositeAudioClip, concatenate_videoclips
    MOVIEPY_V2 = False
except ImportError:
    from moviepy import VideoClip, AudioFileClip, CompositeAudioClip, concatenate_videoclips
    MOVIEPY_V2 = True

os.makedirs("temp", exist_ok=True)
os.makedirs("output", exist_ok=True)

HEADERS_WEB = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
}
HEADERS_WIKI = {
    "User-Agent": "WorldTalkBriefGitHubCloud/9.5 (https://github.com/bapuop17/wtb_engine; editorial@worldtalkbrief.org)"
}

COUNTRY_GEO_DB = {
    "UNITED STATES": ("US", "USA", "Washington, D.C.", "335M", "North America", 38.895, -77.036),
    "RUSSIA": ("RU", "RUS", "Moscow", "144M", "Eurasia", 55.755, 37.617),
    "CHINA": ("CN", "CHN", "Beijing", "1.41B", "East Asia", 39.904, 116.407),
    "ISRAEL": ("IL", "ISR", "Jerusalem", "9.8M", "Middle East", 31.768, 35.213),
    "IRAN": ("IR", "IRN", "Tehran", "89M", "Middle East", 35.689, 51.389),
    "INDIA": ("IN", "IND", "New Delhi", "1.43B", "South Asia", 28.613, 77.209),
    "PAKISTAN": ("PK", "PAK", "Islamabad", "241M", "South Asia", 33.684, 73.047),
    "UKRAINE": ("UA", "UKR", "Kyiv", "38M", "Eastern Europe", 50.450, 30.523),
    "SOUTH KOREA": ("KR", "KOR", "Seoul", "51.7M", "East Asia", 37.566, 126.978),
    "NORTH KOREA": ("KP", "PRK", "Pyongyang", "26M", "East Asia", 39.039, 125.762),
    "JAPAN": ("JP", "JPN", "Tokyo", "124M", "East Asia", 35.676, 139.650),
    "GERMANY": ("DE", "DEU", "Berlin", "84.5M", "Europe", 52.520, 13.405),
    "FRANCE": ("FR", "FRA", "Paris", "68M", "Europe", 48.856, 2.352),
    "UNITED KINGDOM": ("GB", "GBR", "London", "67.7M", "Europe", 51.507, -0.127),
    "ITALY": ("IT", "ITA", "Rome", "58.9M", "Europe", 41.902, 12.496),
    "SAUDI ARABIA": ("SA", "SAU", "Riyadh", "36.9M", "Middle East", 24.713, 46.675),
    "TURKEY": ("TR", "TUR", "Ankara", "85.3M", "Eurasia", 39.933, 32.859),
    "CANADA": ("CA", "CAN", "Ottawa", "40.1M", "North America", 45.421, -75.697),
    "BRAZIL": ("BR", "BRA", "Brasilia", "203M", "South America", -15.797, -47.891),
    "AUSTRALIA": ("AU", "AUS", "Canberra", "26.6M", "Oceania", -35.280, 149.130),
    "MEXICO": ("MX", "MEX", "Mexico City", "129M", "North America", 19.432, -99.133),
    "LEBANON": ("LB", "LBN", "Beirut", "5.3M", "Middle East", 33.893, 35.501),
    "SYRIA": ("SY", "SYR", "Damascus", "23.2M", "Middle East", 33.513, 36.276),
    "YEMEN": ("YE", "YEM", "Sanaa", "34.4M", "Middle East", 15.369, 44.191),
    "SUDAN": ("SD", "SDN", "Khartoum", "48M", "Northeast Africa", 15.500, 32.559),
    "GAZA": ("PS", "PSE", "Gaza City", "2.1M", "Middle East", 31.501, 34.466)
}

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

def build_wtb_watermark(width=140, height=82):
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

BANNED_PHRASES = [
    "some readers may find this article distressing",
    "warning: this article contains",
    "continue reading",
    "live updates",
    "sign up for our newsletter",
    "all rights reserved",
    "photograph:",
    "image source:",
    "getty images",
    "tells the bbc",
    "tells bbc",
    "the bbc joins"
]

def clean_fact(text):
    if not text:
        return ""
    repl = {"\u2011": "-", "\u2013": "-", "\u2014": " - ", "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u00a0": " "}
    for k, v in repl.items():
        text = text.replace(k, v)
    text = re.sub(r"([a-z])([A-Z])", r"\1. \2", text)
    text = re.sub(r"(?i)\bthe bbc joins\b", "Correspondents join", text)
    text = re.sub(r"(?i)\btells the bbc\b", "stated", text)
    text = re.sub(r"(?i)\btells bbc\b", "stated", text)
    text = re.sub(r"(?i)\b(Financial Times|Bloomberg\.com|Bloomberg|Reuters|CNN|BBC News|BBC|Al Jazeera|The Guardian|Associated Press)\b", "", text)
    text = re.sub(r"(?i)\(\s*(centre|center|left|right|pictured|file|ap|reuters|afp|getty)[^)]*\)", "", text)
    text = re.sub(r"\[([^\]]+)\]", r"\1", text)
    text = re.sub(r"[^\x20-\x7E]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    low = text.lower()
    for bp in BANNED_PHRASES:
        if bp in low:
            return ""
    return text

def discover_and_build_dossiers():
    print("📡 [1/6] Scanning Global News Feeds (GitHub Cloud Resilient Mode)...", flush=True)
    feeds = [
        ("BBC World", "http://feeds.bbci.co.uk/news/world/rss.xml"),
        ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
        ("The Guardian", "https://www.theguardian.com/world/rss"),
        ("Global News", "https://news.google.com/rss/headlines/section/topic/WORLD?hl=en-US&gl=US&ceid=US:en")
    ]
    impact_terms = [
        "president", "prime minister", "china", "iran", "israel", "russia", "ukraine",
        "military", "summit", "un", "nato", "missile", "sanctions", "oil", "economy",
        "trade", "tariff", "parliament", "election", "court", "intelligence", "treaty"
    ]
    dossiers = []
    seen = set()

    for src, url in feeds:
        try:
            r_feed = requests.get(url, headers=HEADERS_WEB, timeout=10)
            feed = feedparser.parse(r_feed.content)
        except Exception:
            continue

        for entry in feed.entries[:20]:
            raw_t = entry.title.rsplit(" - ", 1)[0]
            if any(skip in raw_t.lower() for skip in ["live", "latest updates", "as it happened", "at a glance", "in pictures", "quiz"]):
                continue
            title = clean_fact(raw_t)
            if len(title) < 20 or title.lower() in seen:
                continue
            seen.add(title.lower())

            link = getattr(entry, "link", "")
            raw_sum = BeautifulSoup(getattr(entry, "summary", ""), "html.parser").get_text()
            summary = clean_fact(raw_sum)

            rss_img = None
            if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
                rss_img = entry.media_thumbnail[0].get("url")
                if rss_img and "bbci.co.uk" in rss_img:
                    rss_img = re.sub(r"/standard/\d+/", "/standard/1024/", rss_img)
            elif hasattr(entry, "media_content") and entry.media_content:
                rss_img = entry.media_content[0].get("url")

            og_img, raw_facts = None, []
            seen_fk = set()
            for s in re.split(r"(?<=[.!?])\s+", summary):
                cs = clean_fact(s)
                if len(cs) >= 25 and cs.lower() != title.lower():
                    if cs[-1] not in ".!?":
                        cs += "."
                    seen_fk.add(re.sub(r"[^a-z0-9]", "", cs.lower())[:40])
                    raw_facts.append(cs)

            if link and "news.google.com" not in link:
                try:
                    r = requests.get(link, headers=HEADERS_WEB, timeout=6)
                    soup = BeautifulSoup(r.text, "html.parser")
                    m_og = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "twitter:image"})
                    if m_og and m_og.get("content"):
                        og_img = m_og["content"]
                    for p in soup.find_all("p"):
                        if p.find_parent("figcaption") or p.find_parent("figure") or p.find_parent("footer"):
                            continue
                        for rs in re.split(r"(?<=[.!?])\s+", p.get_text()):
                            cs = clean_fact(rs)
                            if 40 <= len(cs) <= 210:
                                if cs[-1] not in ".!?":
                                    cs += "."
                                fk = re.sub(r"[^a-z0-9]", "", cs.lower())[:40]
                                if fk not in seen_fk:
                                    seen_fk.add(fk)
                                    raw_facts.append(cs)
                                    if len(raw_facts) >= 8:
                                        break
                        if len(raw_facts) >= 8:
                            break
                except Exception:
                    pass

            comb = f"{title} {' '.join(raw_facts[:3])}".lower()
            detected_country = "UNITED STATES"
            for c in COUNTRY_GEO_DB.keys():
                if re.search(rf"\b{re.escape(c.lower())}\b", comb):
                    detected_country = c
                    break

            iso2, iso3, cap, pop, reg, lat, lon = COUNTRY_GEO_DB[detected_country]
            c_prof = {"name": detected_country, "iso2": iso2, "iso3": iso3, "capital": cap, "population": pop, "region": reg, "lat": lat, "lon": lon, "flag_img": None}

            # If direct article HTML was blocked by firewall on GitHub Cloud, enrich facts via Bing News RSS!
            if len(raw_facts) < 3:
                try:
                    kw_q = " ".join(re.findall(r"[A-Za-z]{4,}", title)[:4])
                    b_rss = f"https://www.bing.com/news/search?q={urllib.parse.quote(kw_q)}&format=rss"
                    br = requests.get(b_rss, headers=HEADERS_WEB, timeout=6)
                    for desc_m in re.findall(r"<description>(.*?)</description>", br.text)[1:6]:
                        cd = clean_fact(BeautifulSoup(desc_m, "html.parser").get_text())
                        if len(cd) > 35:
                            if cd[-1] not in ".!?":
                                cd += "."
                            raw_facts.append(cd)
                except Exception:
                    pass

            while len(raw_facts) < 3:
                raw_facts.append(f"Officials in {cap} and diplomatic observers across {reg} are closely tracking the fallout from {title}.")
                raw_facts.append(f"With a population of {pop}, policy shifts in {detected_country.title()} carry immediate security and economic weight.")

            try:
                fr = requests.get(f"https://flagcdn.com/w160/{iso2.lower()}.png", headers=HEADERS_WEB, timeout=5)
                if fr.status_code == 200 and len(fr.content) > 500:
                    fp = f"temp/flag_{iso2}.png"
                    with open(fp, "wb") as f:
                        f.write(fr.content)
                    c_prof["flag_img"] = Image.open(fp).convert("RGBA")
            except Exception:
                pass

            wb_years, wb_vals = ["2020", "2021", "2022", "2023", "2024"], [1.8, 4.7, 3.2, 2.6, 3.1]
            try:
                wb_u = f"https://api.worldbank.org/v2/country/{iso3}/indicator/NY.GDP.MKTP.KD.ZG?format=json&per_page=6"
                wbr = requests.get(wb_u, headers=HEADERS_WEB, timeout=5).json()
                if isinstance(wbr, list) and len(wbr) > 1 and wbr[1]:
                    pts = [(str(row["date"]), round(float(row["value"]), 1)) for row in wbr[1] if row.get("value") is not None][:5]
                    if len(pts) >= 3:
                        pts.reverse()
                        wb_years = [p[0] for p in pts]
                        wb_vals = [p[1] for p in pts]
            except Exception:
                pass

            score = sum(3 for kw in impact_terms if re.search(rf"\b{re.escape(kw)}\b", comb)) + len(raw_facts)
            dossiers.append({
                "score": score,
                "title": title,
                "raw_facts": raw_facts,
                "lead_img": og_img or rss_img,
                "country_profile": c_prof,
                "wb_data": (wb_years, wb_vals),
                "source": src
            })
            if len(dossiers) >= 6:
                break
        if len(dossiers) >= 6:
            break

    dossiers.sort(key=lambda x: x["score"], reverse=True)
    return dossiers

def extract_story_entities(dossier):
    text = f"{dossier['title']} {' '.join(dossier['raw_facts'][:5])}"
    c_prof = dossier["country_profile"]
    known = {
        "trump": "Donald Trump", "putin": "Vladimir Putin", "zelensky": "Volodymyr Zelenskyy",
        "zelenskyy": "Volodymyr Zelenskyy", "biden": "Joe Biden", "netanyahu": "Benjamin Netanyahu",
        "macron": "Emmanuel Macron", "starmer": "Keir Starmer", "modi": "Narendra Modi",
        "xi jinping": "Xi Jinping", "lula": "Luiz Inácio Lula da Silva", "bolsonaro": "Jair Bolsonaro",
        "wang yi": "Wang Yi", "crosetto": "Guido Crosetto", "kremlin": "Moscow Kremlin",
        "white house": "White House", "congress": "United States Capitol", "pentagon": "The Pentagon",
        "nato": "NATO", "united nations": "United Nations",
        "european union": "European Parliament", "amazon": "Amazon rainforest",
        "donbas": "Donbas", "gaza": "Gaza Strip", "west bank": "West Bank"
    }
    ents = []
    low = text.lower()
    for k, v in known.items():
        if re.search(rf"\b{re.escape(k)}\b", low) and v not in ents:
            ents.append(v)

    proper_phrases = re.findall(r"\b[A-Z][a-z]{3,}(?:\s+[A-Z][a-z]{3,})+\b", text)
    stop_words = {
        "The", "And", "For", "With", "From", "After", "Before", "Over", "Into", "While",
        "Meanwhile", "Inside", "Here", "When", "This", "That", "What", "Where", "One",
        "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
        "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
    }
    for pp in proper_phrases:
        if not any(w in stop_words for w in pp.split()) and pp not in ents:
            ents.append(pp)

    for fb in [c_prof["capital"], c_prof["name"].title(), f"{c_prof['name'].title()} parliament", "United Nations"]:
        if fb not in ents:
            ents.append(fb)
    return ents[:10]

def polish_journalistic_sentence(raw_fact, c_prof, role="BODY"):
    s = raw_fact.strip().rstrip(".")
    s = re.sub(r",\s*(police|officials|ministry|authorities|sources|reports|his office)\s+(say|said|reported|stated)$", "", s, flags=re.I)
    s = re.sub(r"^(police|officials|authorities|reports)\s+(say|said|state|stated)\s+(that\s+)?", "", s, flags=re.I)
    if not s:
        return ""
    s = s[0].upper() + s[1:]
    if role == "HOOK":
        return f"A major shift is unfolding in {c_prof['capital']}: {s}."
    elif role == "CONTEXT":
        return f"Behind the scenes, {s[0].lower() + s[1:]}."
    elif role == "PAYOFF":
        return f"Crucially, {s[0].lower() + s[1:]}."
    return f"{s}."

def build_short_script(dossier):
    c_prof = dossier["country_profile"]
    ents = extract_story_entities(dossier)
    facts = dossier["raw_facts"]
    title = dossier["title"]

    f0 = facts[0] if len(facts) > 0 else title
    f1 = facts[1] if len(facts) > 1 else f"Decision-makers in {c_prof['capital']} are moving rapidly to secure leverage."
    f2 = facts[2] if len(facts) > 2 else f"Regional powers across {c_prof['region']} are closely watching the fallout."

    sections = [
        {
            "role": "HOOK",
            "voice_style": "urgent",
            "headline": title.upper()[:52],
            "narration": f"{title}. Here is why this sudden move in {c_prof['capital']} changes the global calculation right now."
        },
        {
            "role": "WHAT_HAPPENED",
            "voice_style": "clear",
            "headline": f"INSIDE {c_prof['capital'].upper()}'S DECISION",
            "narration": polish_journalistic_sentence(f0, c_prof, role="BODY")
        },
        {
            "role": "CONTEXT",
            "voice_style": "analytical",
            "headline": f"THE WIDER STAKES IN {c_prof['region'].upper()}",
            "narration": polish_journalistic_sentence(f1, c_prof, role="CONTEXT")
        },
        {
            "role": "PAYOFF",
            "voice_style": "serious",
            "headline": "THE CRITICAL TEST AHEAD",
            "narration": f"{polish_journalistic_sentence(f2, c_prof, role='PAYOFF')} How do you see this playing out next?"
        }
    ]
    return sections, ents

def build_long_documentary_script(dossiers):
    lead = dossiers[0]
    c_prof = lead["country_profile"]
    ents = extract_story_entities(lead)
    facts = lead["raw_facts"]

    f0 = facts[0] if len(facts) > 0 else lead["title"]
    f1 = facts[1] if len(facts) > 1 else f"Officials in {c_prof['capital']} have confirmed high-level talks are underway."
    f2 = facts[2] if len(facts) > 2 else f"Months of diplomatic pressure across {c_prof['region']} set the stage for this moment."
    f3 = facts[3] if len(facts) > 3 else f"International allies and rivals alike are now recalibrating their posture."

    chapters = [
        {
            "chapter_num": 1,
            "chapter_title": "THE FLASHPOINT",
            "role": "HOOK",
            "voice_style": "urgent",
            "dossier": lead,
            "narration": f"{lead['title']}. While the initial headlines broke just hours ago from {c_prof['capital']}, the deeper story reveals a decisive turning point. {polish_journalistic_sentence(f0, c_prof, 'BODY')}"
        },
        {
            "chapter_num": 2,
            "chapter_title": "THE VERIFIED RECORD",
            "role": "EVIDENCE",
            "voice_style": "clear",
            "dossier": lead,
            "narration": f"Look at the specifics confirmed on the ground. {polish_journalistic_sentence(f1, c_prof, 'BODY')}"
        },
        {
            "chapter_num": 3,
            "chapter_title": "THE GEOGRAPHIC FAULT LINE",
            "role": "GEOGRAPHY",
            "voice_style": "analytical",
            "dossier": lead,
            "narration": f"Geography explains why international observers are paying such close attention. Centered around {c_prof['capital']}, {c_prof['name'].title()} anchors a vital corridor in {c_prof['region']}, where any policy shift reverberates across neighboring borders."
        },
        {
            "chapter_num": 4,
            "chapter_title": "HOW WE REACHED THIS POINT",
            "role": "TIMELINE",
            "voice_style": "analytical",
            "dossier": lead,
            "narration": f"This confrontation did not appear overnight. {polish_journalistic_sentence(f2, c_prof, 'CONTEXT')} Step by step, earlier diplomatic off-ramps narrowed until key actors reached this crossroads."
        },
        {
            "chapter_num": 5,
            "chapter_title": "THE COMPETING CALCULATIONS",
            "role": "COMPARISON",
            "voice_style": "serious",
            "dossier": lead,
            "narration": f"Now two competing strategic calculations are colliding. {polish_journalistic_sentence(f3, c_prof, 'BODY')}"
        }
    ]

    if len(dossiers) > 1:
        sec_d = dossiers[1]
        sc_prof = sec_d["country_profile"]
        sf0 = sec_d["raw_facts"][0] if sec_d["raw_facts"] else sec_d["title"]
        sf1 = sec_d["raw_facts"][1] if len(sec_d["raw_facts"]) > 1 else f"Authorities in {sc_prof['capital']} are closely monitoring the fallout."
        chapters.append({
            "chapter_num": 6,
            "chapter_title": f"GLOBAL BRIEFING: {sc_prof['name']}",
            "role": "WIDER_CONTEXT",
            "voice_style": "clear",
            "dossier": sec_d,
            "narration": f"Meanwhile, a major parallel development is unfolding in {sc_prof['name'].title()}: {sec_d['title']}. {polish_journalistic_sentence(sf0, sc_prof, 'BODY')} {polish_journalistic_sentence(sf1, sc_prof, 'BODY')}"
        })

    chapters.append({
        "chapter_num": len(chapters) + 1,
        "chapter_title": "THE ROAD AHEAD",
        "role": "PAYOFF",
        "voice_style": "serious",
        "dossier": lead,
        "narration": f"Watch the next seventy-two hours closely. Whether {ents[0] if ents else c_prof['name'].title()} opts for calibrated de-escalation or doubles down on leverage will determine if this remains contained or reshapes {c_prof['region']} for years to come."
    })

    return chapters

def validate_and_enhance_1080p(im, existing_hashes):
    im = im.convert("RGB")
    w, h = im.size
    if w < 300 or h < 200:
        return None

    im = im.crop((int(w * 0.08), int(h * 0.06), int(w * 0.92), int(h * 0.86)))

    arr = np.asarray(im.resize((80, 80)), dtype=np.float32)
    c_box = arr[28:52, 28:52]
    red_px = np.sum((c_box[:, :, 0] > 195) & (c_box[:, :, 1] < 45) & (c_box[:, :, 2] < 45))
    if (red_px / float(24 * 24)) > 0.15:
        return None

    white_px = np.sum((arr[:, :, 0] > 240) & (arr[:, :, 1] > 240) & (arr[:, :, 2] > 240))
    if (white_px / float(80 * 80)) > 0.35:
        return None
    if im.entropy() < 6.0:
        return None

    gray = im.convert("L").resize((13, 12))
    dh = (np.asarray(gray, dtype=np.int16)[:, 1:] > np.asarray(gray, dtype=np.int16)[:, :-1]).flatten()
    for old_h in existing_hashes:
        if int(np.sum(dh != old_h)) < 16:
            return None
    existing_hashes.append(dh)

    if im.size[0] < 1600:
        scale = 1920.0 / float(im.size[0])
        resample_mode = getattr(Image, "Resampling", Image).LANCZOS
        im = im.resize((1920, int(im.size[1] * scale)), resample_mode)

    im = im.filter(ImageFilter.UnsharpMask(radius=1.6, percent=135, threshold=3))
    im = ImageEnhance.Contrast(im).enhance(1.08)
    return im

def build_real_openstreetmap_1080p(c_prof, zoom=5, W=1920, H=1080):
    lat, lon = c_prof["lat"], c_prof["lon"]
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    xtile = int((lon + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)

    stitched = Image.new("RGB", (256 * 4, 256 * 3), (18, 28, 44))
    tiles_loaded = 0
    for dx in [-1, 0, 1, 2]:
        for dy in [-1, 0, 1]:
            tx = (xtile + dx) % int(n)
            ty = max(0, min(int(n) - 1, ytile + dy))
            u = f"https://tile.openstreetmap.org/{zoom}/{tx}/{ty}.png"
            try:
                r = requests.get(u, headers=HEADERS_WIKI, timeout=5)
                if r.status_code == 200 and len(r.content) > 1000:
                    p = f"temp/osm_{zoom}_{tx}_{ty}.png"
                    with open(p, "wb") as f:
                        f.write(r.content)
                    tim = Image.open(p).convert("RGB")
                    stitched.paste(tim, ((dx + 1) * 256, (dy + 1) * 256))
                    tiles_loaded += 1
            except Exception:
                pass

    resample_mode = getattr(Image, "Resampling", Image).LANCZOS
    map_img = stitched.resize((W, H), resample_mode)
    if tiles_loaded > 0:
        map_img = map_img.filter(ImageFilter.UnsharpMask(radius=1.5, percent=125, threshold=3))
        map_img = ImageEnhance.Contrast(map_img).enhance(1.35)
        map_img = ImageEnhance.Brightness(map_img).enhance(0.65)
    return map_img

def harvest_datacenter_safe_1080p_photos(dossier, entities, target_count=14, tag="hd"):
    c_prof = dossier["country_profile"]
    title = dossier["title"]
    print(f"📸 [1080p Cloud Harvester] Collecting 14+ Real HD Photos for: {title[:55]}...", flush=True)

    photo_bank = []
    hashes = []

    def add_hd(im, label, kw_str):
        vim = validate_and_enhance_1080p(im, hashes)
        if vim is not None:
            photo_bank.append({
                "asset_id": f"{tag}_hd_{len(photo_bank)}",
                "image": vim,
                "label": label,
                "keywords": kw_str.lower(),
                "used_count": 0
            })
            return True
        return False

    if dossier.get("lead_img"):
        try:
            r = requests.get(dossier["lead_img"], headers=HEADERS_WEB, timeout=7)
            if r.status_code == 200 and len(r.content) > 8000:
                p = f"temp/{tag}_lead.jpg"
                with open(p, "wb") as f:
                    f.write(r.content)
                add_hd(Image.open(p), f"DISPATCH • {c_prof['name']}", title)
        except Exception:
            pass

    rss_queries = [
        title,
        f"{entities[0]} {c_prof['name']}",
        f"{entities[1] if len(entities)>1 else c_prof['capital']} {c_prof['name']}",
        f"{c_prof['capital']} government",
        f"{c_prof['name']} economy trade",
        f"{c_prof['name']} military security"
    ]
    for nq in rss_queries:
        if len(photo_bank) >= target_count:
            break
        try:
            rss_u = f"https://www.bing.com/news/search?q={urllib.parse.quote(nq)}&format=rss"
            r = requests.get(rss_u, headers=HEADERS_WEB, timeout=7)
            for u in re.findall(r"<News:Image>(https?://[^<]+)</News:Image>", r.text)[:10]:
                if len(photo_bank) >= target_count:
                    break
                u_clean = u.replace("&amp;", "&")
                if "bing.com/th" in u_clean:
                    u_clean = u_clean.split("&")[0] + "&w=1920&h=1080"
                ir = requests.get(u_clean, headers=HEADERS_WEB, timeout=6)
                if ir.status_code == 200 and len(ir.content) > 8000:
                    p = f"temp/{tag}_bnews_{len(photo_bank)}.jpg"
                    with open(p, "wb") as f:
                        f.write(ir.content)
                    add_hd(Image.open(p), f"PRESS REPORT • {c_prof['name']}", nq)
        except Exception:
            pass

    for ent in entities:
        if len(photo_bank) >= target_count:
            break
        try:
            w_api = "https://en.wikipedia.org/w/api.php"
            params = {
                "action": "query", "generator": "search", "gsrsearch": ent, "gsrlimit": 4,
                "prop": "pageimages", "piprop": "original|thumbnail", "pithumbsize": 1920, "format": "json"
            }
            r = requests.get(w_api, params=params, headers=HEADERS_WIKI, timeout=6).json()
            for pg in r.get("query", {}).get("pages", {}).values():
                if len(photo_bank) >= target_count:
                    break
                img_u = pg.get("original", {}).get("source") or pg.get("thumbnail", {}).get("source")
                if img_u and img_u.lower().endswith((".jpg", ".jpeg", ".png")):
                    ir = requests.get(img_u, headers=HEADERS_WIKI, timeout=6)
                    if ir.status_code == 200 and len(ir.content) > 10000:
                        p = f"temp/{tag}_wikihd_{len(photo_bank)}.jpg"
                        with open(p, "wb") as f:
                            f.write(ir.content)
                        add_hd(Image.open(p), f"ARCHIVE • {ent.upper()[:24]}", ent)
        except Exception:
            pass

    for ent in entities[:8]:
        if len(photo_bank) >= target_count:
            break
        try:
            api = "https://commons.wikimedia.org/w/api.php"
            params = {
                "action": "query", "generator": "search", "gsrsearch": f"filetype:bitmap {ent}",
                "gsrlimit": 5, "prop": "imageinfo", "iiprop": "url", "iiurlwidth": 1920, "format": "json"
            }
            r = requests.get(api, params=params, headers=HEADERS_WIKI, timeout=7).json()
            for pg in r.get("query", {}).get("pages", {}).values():
                if len(photo_bank) >= target_count:
                    break
                ii = pg.get("imageinfo", [{}])[0]
                u = ii.get("thumburl") or ii.get("url")
                if u and u.lower().endswith((".jpg", ".jpeg")):
                    ir = requests.get(u, headers=HEADERS_WIKI, timeout=6)
                    if ir.status_code == 200 and len(ir.content) > 10000:
                        p = f"temp/{tag}_commhd_{len(photo_bank)}.jpg"
                        with open(p, "wb") as f:
                            f.write(ir.content)
                        add_hd(Image.open(p), f"COMMONS HD • {ent.upper()[:22]}", ent)
        except Exception:
            pass

    osm_regional = build_real_openstreetmap_1080p(c_prof, zoom=5, W=1920, H=1080)
    osm_capital = build_real_openstreetmap_1080p(c_prof, zoom=8, W=1920, H=1080)
    if len(photo_bank) < 6:
        photo_bank.append({"asset_id": f"{tag}_osm_reg", "image": osm_regional, "label": f"GEO-MAP • {c_prof['region'].upper()}", "keywords": c_prof["region"].lower(), "used_count": 0})
        photo_bank.append({"asset_id": f"{tag}_osm_cap", "image": osm_capital, "label": f"GEO-MAP • {c_prof['capital'].upper()}", "keywords": c_prof["capital"].lower(), "used_count": 0})

    print(f"   ✅ [{tag.upper()}] Locked {len(photo_bank)} 1080p HD Visuals!", flush=True)
    return photo_bank, osm_regional

def detect_faces_and_build_1080p_stage(im, W, H):
    resample_mode = getattr(Image, "Resampling", Image).LANCZOS
    iw, ih = im.size

    faces = []
    if FACE_CASCADE is not None:
        try:
            small_w = 480
            small_h = max(int(ih * (480.0 / iw)), 270)
            gray_small = cv2.cvtColor(np.array(im.resize((small_w, small_h))), cv2.COLOR_RGB2GRAY)
            faces = FACE_CASCADE.detectMultiScale(gray_small, scaleFactor=1.12, minNeighbors=5, minSize=(32, 32))
        except Exception:
            faces = []

    if W < H:
        if len(faces) >= 2:
            faces_sorted = sorted(faces, key=lambda b: b[0])
            f_left, f_right = faces_sorted[0], faces_sorted[-1]
            if abs((f_right[0] + f_right[2] / 2) - (f_left[0] + f_left[2] / 2)) > (480 * 0.28):
                stage_canvas = Image.new("RGBA", (int(W * 1.08), int(H * 1.04)), (8, 12, 22, 255))
                tw, th = stage_canvas.size
                half_h = th // 2
                left_half = im.crop((0, 0, iw // 2, ih)).resize((tw, half_h), resample_mode)
                right_half = im.crop((iw // 2, 0, iw, ih)).resize((tw, half_h), resample_mode)
                stage_canvas.paste(left_half, (0, 0))
                stage_canvas.paste(right_half, (0, half_h))
                d_s = ImageDraw.Draw(stage_canvas, "RGBA")
                d_s.line([(0, half_h), (tw, half_h)], fill=(255, 214, 10, 255), width=6)
                return ("FULL_BLEED_STAGE", stage_canvas, None)

        bg = im.copy().resize((W, H), resample_mode).filter(ImageFilter.GaussianBlur(radius=28))
        bg = ImageEnhance.Brightness(bg).enhance(0.32)
        canvas = bg.convert("RGBA")

        hero_w, hero_h = int(W * 1.10), 960
        target_r = hero_w / float(hero_h)
        fg = im.copy()
        if (iw / float(ih)) > target_r:
            nw = int(ih * target_r)
            if len(faces) == 1:
                fx_center = (faces[0][0] + faces[0][2] / 2.0) / 480.0
                left = int(max(0, min(iw - nw, iw * fx_center - nw / 2.0)))
            else:
                left = (iw - nw) // 2
            fg = fg.crop((left, 0, left + nw, ih))
        else:
            nh = int(iw / target_r)
            top = int((ih - nh) * 0.20)
            fg = fg.crop((0, top, iw, top + nh))
        fg = fg.resize((hero_w, hero_h), resample_mode)
        return ("SHORT_STAGE", canvas, fg)
    else:
        over_w, over_h = int(W * 1.08), int(H * 1.08)
        target_r = over_w / float(over_h)
        fg = im.copy()
        if (iw / float(ih)) > target_r:
            nw = int(ih * target_r)
            left = (iw - nw) // 2
            fg = fg.crop((left, 0, left + nw, ih))
        else:
            nh = int(iw / target_r)
            top = int((ih - nh) * 0.22)
            fg = fg.crop((0, top, iw, top + nh))
        fg = fg.resize((over_w, over_h), resample_mode)
        return ("FULL_BLEED_STAGE", fg, None)

def extract_animated_frame_from_stage(stage_tuple, W, H, bp, pan_dir=1):
    mode_tag, base_a, base_b = stage_tuple
    if mode_tag == "SHORT_STAGE":
        canvas = base_a.copy()
        fg = base_b
        fw, fh = fg.size
        win_w, win_h = W, 920
        max_dx = max(fw - win_w, 0)
        max_dy = max(fh - win_h, 0)
        ox = int(max_dx * (bp if pan_dir == 1 else (1.0 - bp)))
        oy = int(max_dy * 0.5)
        slice_fg = fg.crop((ox, oy, ox + win_w, oy + win_h))
        canvas.paste(slice_fg, (0, 200))

        draw = ImageDraw.Draw(canvas, "RGBA")
        for y in range(0, 200):
            draw.line([(0, y), (W, y)], fill=(6, 9, 18, int(175 * (1.0 - y / 200.0))))
        for y in range(1120, H):
            draw.line([(0, y), (W, y)], fill=(6, 9, 18, int(235 * min(1.0, (y - 1120) / 260.0))))
        draw.line([(0, 200), (W, 200)], fill=(255, 214, 10, 220), width=3)
        draw.line([(0, 1120), (W, 1120)], fill=(255, 214, 10, 220), width=3)
        return canvas
    else:
        fg = base_a
        fw, fh = fg.size
        max_dx = max(fw - W, 0)
        max_dy = max(fh - H, 0)
        ox = int(max_dx * (bp if pan_dir == 1 else (1.0 - bp)))
        oy = int(max_dy * (0.2 + 0.6 * bp))
        frame = fg.crop((ox, oy, ox + W, oy + H)).convert("RGBA")
        draw = ImageDraw.Draw(frame, "RGBA")
        for y in range(0, 180):
            draw.line([(0, y), (W, y)], fill=(4, 7, 14, int(160 * (1.0 - y / 180.0))))
        for y in range(H - 360, H):
            draw.line([(0, y), (W, y)], fill=(4, 7, 14, int(238 * ((y - (H - 360)) / 360.0) ** 1.15)))
        return frame

def has_strict_economic_context(text):
    low = text.lower()
    if any(prison_w in low for prison_w in ["jailed", "prison", "sentenced", "murder", "killed", "court", "police"]):
        return False
    if re.search(r"\b(\d+(\.\d+)?%|\$\d+|\d+\s*(billion|trillion))\b", low):
        return True
    econ_terms = ["gdp", "inflation", "economy", "economic", "market", "trade", "tariff", "cost", "budget", "growth", "debt", "financial", "bank"]
    return any(re.search(rf"\b{re.escape(t)}\b", low) for t in econ_terms)

def classify_beat_mode(clause_text, sec_role, used_in_sec):
    low = clause_text.lower()
    if has_strict_economic_context(clause_text) and "DATA_CHART_BEAT" not in used_in_sec:
        return "DATA_CHART_BEAT"
    if (sec_role == "GEOGRAPHY" or re.search(r"\b(map|border|region|capital|territory|corridor|across|geography|neighbors|anchors)\b", low)) and "MAP_LOCATOR_BEAT" not in used_in_sec:
        return "MAP_LOCATOR_BEAT"
    if (sec_role == "TIMELINE" or re.search(r"\b(timeline|history|months|previously|since|before|step by step|overnight|earlier|september|october)\b", low)) and "TIMELINE_GRAPH_BEAT" not in used_in_sec:
        return "TIMELINE_GRAPH_BEAT"
    if (sec_role == "COMPARISON" or re.search(r"\b(versus|while|competing|rivals|choice|between|either|standoff|clash|calculations|colliding)\b", low)) and "SPLIT_COMPARE_BEAT" not in used_in_sec:
        return "SPLIT_COMPARE_BEAT"
    if (sec_role == "EVIDENCE" or re.search(r"\b(said|stated|warned|announced|reported|official|record|document|law|order|bill|statement|specifics)\b", low)) and "HEADLINE_EVIDENCE_BEAT" not in used_in_sec:
        return "HEADLINE_EVIDENCE_BEAT"
    return "PHOTO_BEAT"

def build_storyboard_beats_1080p(sections_list, dossier, photo_bank, osm_map, W, H):
    planned = []
    p_cursor = 0
    osm_stage = detect_faces_and_build_1080p_stage(osm_map, W, H)

    for sec_idx, sec in enumerate(sections_list):
        narration = sec["narration"]
        sec_dur = sec["duration"]
        word_timings = sec["word_timings"]
        sec_role = sec.get("role", "BODY")
        sec_headline = sec.get("headline") or sec.get("chapter_title") or dossier["title"]

        num_beats = max(2, int(math.ceil(sec_dur / 3.2)))
        beat_dur = sec_dur / float(num_beats)
        words = narration.split()
        w_per_b = max(1, int(math.ceil(len(words) / float(num_beats))))
        used_in_sec = set()

        for b_i in range(num_beats):
            b_txt = " ".join(words[b_i * w_per_b:(b_i + 1) * w_per_b]) or narration
            b_type = classify_beat_mode(b_txt, sec_role, used_in_sec)
            used_in_sec.add(b_type)

            p_item_1 = photo_bank[p_cursor % len(photo_bank)]
            p_cursor += 1
            p_item_2 = photo_bank[p_cursor % len(photo_bank)]
            if b_type == "SPLIT_COMPARE_BEAT":
                p_cursor += 1

            stage_1 = osm_stage if b_type == "MAP_LOCATOR_BEAT" else detect_faces_and_build_1080p_stage(p_item_1["image"], W, H)

            planned.append({
                "section_idx": sec_idx,
                "beat_in_section": b_i,
                "beat_type": b_type,
                "pan_dir": 1 if (p_cursor % 2 == 0) else -1,
                "duration": round(beat_dur, 3),
                "beat_excerpt": b_txt,
                "section_headline": sec_headline,
                "full_section_narration": narration,
                "word_timings": word_timings,
                "section_duration": sec_dur,
                "section_elapsed_before": round(b_i * beat_dur, 3),
                "stage_1": stage_1,
                "primary_im": p_item_1["image"],
                "primary_lbl": p_item_1["label"],
                "secondary_im": p_item_2["image"],
                "story": dossier
            })
    return planned

def render_1080p_beat_frame(beat, watermark, voice_sub_dir, local_t, W, H, is_short=True):
    beat_dur = beat["duration"]
    bp = min(max(local_t / max(beat_dur, 0.1), 0.0), 1.0)
    b_type = beat["beat_type"]
    story = beat["story"]
    c_prof = story["country_profile"]
    wb_years, wb_vals = story["wb_data"]
    section_t = beat["section_elapsed_before"] + local_t

    frame = extract_animated_frame_from_stage(beat["stage_1"], W, H, bp, pan_dir=beat["pan_dir"])
    draw = ImageDraw.Draw(frame, "RGBA")

    cy_card = 1145 if is_short else (H - 355)
    bx1, bx2 = (42, W - 42) if is_short else (64, 1290)

    if b_type == "PHOTO_BEAT":
        kicker = beat["primary_lbl"]
        hl = str(beat["section_headline"]).upper()
        f_k = get_font(24)
        f_h = get_font(33 if is_short else 36)
        kw = draw.textbbox((0, 0), kicker, font=f_k)[2] + 40

        draw.rounded_rectangle([(bx1, cy_card), (bx2, cy_card + 168)], radius=14, fill=(10, 16, 28, 232), outline=(255, 214, 10, 220), width=3)
        draw.rounded_rectangle([(bx1 + 20, cy_card + 18), (bx1 + 20 + kw, cy_card + 56)], radius=8, fill=(204, 18, 36, 255))
        draw.text((bx1 + 40, cy_card + 24), kicker, fill=(255, 255, 255, 255), font=f_k)
        for i_l, ln in enumerate(wrap_lines(draw, hl, f_h, (bx2 - bx1) - 52)[:2]):
            draw.text((bx1 + 24, cy_card + 68 + i_l * 42), ln, fill=(255, 255, 255, 255), font=f_h)

    elif b_type == "MAP_LOCATOR_BEAT":
        cx, cy = (W // 2, 650) if is_short else (W // 2 - 120, H // 2 - 45)
        for ri in range(3):
            rp = ((local_t * 0.8) + ri * 0.33) % 1.0
            rad = int(36 + rp * 210)
            draw.ellipse([(cx - rad, cy - rad), (cx + rad, cy + rad)], outline=(255, 45, 45, int(235 * (1.0 - rp))), width=4)
        draw.ellipse([(cx - 14, cy - 14), (cx + 14, cy + 14)], fill=(255, 214, 10, 255))

        pip_w, pip_h = (340, 220) if is_short else (430, 270)
        px, py = (W - pip_w - 42, 240) if is_short else (W - pip_w - 64, 160)
        pip_im = beat["secondary_im"].resize((pip_w, pip_h))
        draw.line([(cx, cy), (px + pip_w // 2, py + pip_h)], fill=(255, 214, 10, 220), width=3)
        frame.paste(pip_im, (px, py))
        draw.rounded_rectangle([(px - 3, py - 3), (px + pip_w + 3, py + pip_h + 3)], radius=8, outline=(255, 214, 10, 255), width=4)

        draw.rounded_rectangle([(bx1, cy_card), (bx2, cy_card + 168)], radius=14, fill=(10, 16, 28, 240), outline=(0, 210, 255, 225), width=3)
        draw.text((bx1 + 26, cy_card + 20), f"GEOGRAPHIC CORRIDOR  •  LAT {c_prof['lat']}° LON {c_prof['lon']}°", fill=(0, 210, 255, 255), font=get_font(24))
        draw.text((bx1 + 26, cy_card + 64), f"EPICENTER: {c_prof['capital'].upper()}, {c_prof['name']}", fill=(255, 214, 10, 255), font=get_font(33))
        draw.text((bx1 + 26, cy_card + 116), f"POPULATION: {c_prof['population']}  |  REGION: {c_prof['region'].upper()}", fill=(235, 240, 250, 255), font=get_font(24))

    elif b_type == "HEADLINE_EVIDENCE_BEAT":
        draw.rounded_rectangle([(bx1, cy_card - 10), (bx2, cy_card + 175)], radius=16, fill=(246, 244, 236, 248), outline=(204, 18, 36, 255), width=4)
        draw.rounded_rectangle([(bx1 + 24, cy_card + 8), (bx1 + 440, cy_card + 46)], radius=6, fill=(204, 18, 36, 255))
        draw.text((bx1 + 40, cy_card + 14), f"OFFICIAL RECORD • {c_prof['name']}", fill=(255, 255, 255, 255), font=get_font(22))

        hl_txt = beat["beat_excerpt"] if len(beat["beat_excerpt"]) > 28 else story["title"]
        f_q = get_font(30 if is_short else 32)
        lines = wrap_lines(draw, hl_txt, f_q, (bx2 - bx1) - 60)[:2]
        hl_w = int(((bx2 - bx1) - 64) * min(bp * 1.4, 1.0))
        draw.rounded_rectangle([(bx1 + 24, cy_card + 58), (bx1 + 24 + hl_w, cy_card + 100)], radius=6, fill=(255, 232, 65, 240))
        for idx_l, ln in enumerate(lines):
            draw.text((bx1 + 30, cy_card + 62 + idx_l * 44), ln, fill=(12, 16, 22, 255), font=f_q)

    elif b_type == "TIMELINE_GRAPH_BEAT":
        draw.rounded_rectangle([(bx1, cy_card - 20), (bx2, cy_card + 185)], radius=16, fill=(10, 16, 28, 242), outline=(255, 214, 10, 225), width=3)
        steps = [
            ("BUILDUP", f"Mounting pressure across {c_prof['region']}"),
            ("CATALYST", f"Key policy decision in {c_prof['capital']}"),
            ("NOW", story["title"][:44])
        ]
        sy = cy_card
        for idx_s, (slbl, stxt) in enumerate(steps):
            act = (bp >= idx_s * 0.28)
            bg_c = (204, 18, 36, 255) if act else (35, 45, 65, 210)
            draw.rounded_rectangle([(bx1 + 24, sy), (bx1 + 170, sy + 42)], radius=8, fill=bg_c)
            draw.text((bx1 + 34, sy + 8), slbl, fill=(255, 255, 255, 255), font=get_font(22))
            draw.text((bx1 + 190, sy + 6), stxt[:42], fill=(255, 255, 255, 255) if act else (160, 170, 185, 210), font=get_font(25))
            sy += 58

    elif b_type == "DATA_CHART_BEAT":
        draw.rounded_rectangle([(bx1, cy_card - 45), (bx2, cy_card + 195)], radius=16, fill=(10, 16, 28, 244), outline=(255, 214, 10, 230), width=3)
        draw.text((bx1 + 30, cy_card - 26), f"{c_prof['name']} GDP GROWTH (%)  •  WORLD BANK DATA", fill=(255, 214, 10, 255), font=get_font(25))
        anim_p = min(bp * 1.35, 1.0)
        n_bars = len(wb_years)
        slot_w = ((bx2 - bx1) - 90) // max(n_bars, 1)
        max_v = max(max(abs(v) for v in wb_vals), 1.0)
        for b_i, (yr, val) in enumerate(zip(wb_years, wb_vals)):
            bx = bx1 + 50 + b_i * slot_w
            bh = max(int(90 * (abs(val) / max_v) * anim_p), 12)
            b_top = cy_card + 125 - bh
            b_col = (255, 214, 10, 255) if val >= 0 else (204, 18, 36, 255)
            draw.rounded_rectangle([(bx, b_top), (bx + slot_w - 42, cy_card + 125)], radius=6, fill=b_col)
            draw.text((bx + 6, b_top - 30), f"{round(val * anim_p, 1)}%", fill=(255, 255, 255, 255), font=get_font(22))
            draw.text((bx + 8, cy_card + 136), yr, fill=(200, 215, 235, 255), font=get_font(22))

    else:
        mid_x = (bx1 + bx2) // 2
        draw.rounded_rectangle([(bx1, cy_card), (mid_x - 12, cy_card + 155)], radius=14, fill=(10, 18, 32, 240), outline=(0, 210, 255, 230), width=3)
        draw.text((bx1 + 24, cy_card + 20), "CALCULATION A", fill=(0, 210, 255, 255), font=get_font(24))
        draw.text((bx1 + 24, cy_card + 68), "STRATEGIC LEVERAGE", fill=(255, 255, 255, 255), font=get_font(27))

        draw.rounded_rectangle([(mid_x + 12, cy_card), (bx2, cy_card + 155)], radius=14, fill=(10, 18, 32, 240), outline=(255, 214, 10, 230), width=3)
        draw.text((mid_x + 36, cy_card + 20), "CALCULATION B", fill=(255, 214, 10, 255), font=get_font(24))
        draw.text((mid_x + 36, cy_card + 68), "ESCALATION RISK", fill=(255, 255, 255, 255), font=get_font(27))

    top_y = 115 if is_short else 38
    frame.paste(watermark, (42, top_y), watermark)
    if c_prof.get("flag_img"):
        fl = c_prof["flag_img"].resize((84, 54))
        frame.paste(fl, (198, top_y + 14), fl)

    sub_strip = voice_sub_dir.render_exact_synced_subtitles(beat["word_timings"], section_t, W, H, is_short=is_short)
    sub_y = 1435 if is_short else (H - 138)
    frame.paste(sub_strip, (0, sub_y), sub_strip)

    return np.array(frame.convert("RGB"))

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

class VoiceAndSubtitleEngine:
    async def synthesize_with_word_boundaries(self, text, out_path, voice_style="clear"):
        style_map = {
            "urgent": ("en-US-AndrewMultilingualNeural", "+7%", "+0Hz"),
            "clear": ("en-US-ChristopherNeural", "+4%", "-1Hz"),
            "analytical": ("en-US-AndrewMultilingualNeural", "+3%", "-2Hz"),
            "serious": ("en-US-ChristopherNeural", "+2%", "-2Hz")
        }
        v_name, rate, pitch = style_map.get(voice_style, ("en-US-AndrewMultilingualNeural", "+4%", "-1Hz"))
        word_timings = []

        for _ in range(2):
            try:
                comm = edge_tts.Communicate(text, v_name, rate=rate, pitch=pitch)
                word_timings = []
                with open(out_path, "wb") as audio_file:
                    async for chunk in comm.stream():
                        if chunk["type"] == "audio":
                            audio_file.write(chunk["data"])
                        elif chunk["type"] == "WordBoundary":
                            w_start = chunk["offset"] / 10_000_000.0
                            w_dur = chunk["duration"] / 10_000_000.0
                            word_timings.append({"word": chunk["text"], "start": round(w_start, 3), "end": round(w_start + max(w_dur, 0.08), 3)})
                if os.path.exists(out_path) and os.path.getsize(out_path) > 1000:
                    break
            except Exception:
                await asyncio.sleep(0.4)

        if not os.path.exists(out_path) or os.path.getsize(out_path) <= 1000:
            gTTS(text=text, lang="en").save(out_path)

        vc = AudioFileClip(out_path)
        total_dur = vc.duration
        if not word_timings:
            words = text.split()
            tot_chars = max(sum(len(w) for w in words), 1)
            cur = 0.0
            for w in words:
                wd = (len(w) / float(tot_chars)) * (total_dur - 0.1)
                word_timings.append({"word": w, "start": round(cur, 3), "end": round(cur + wd, 3)})
                cur += wd
        return vc, total_dur, word_timings

    def render_exact_synced_subtitles(self, word_timings, section_t, W, H, is_short=True):
        if not word_timings:
            return Image.new("RGBA", (W, 200), (0, 0, 0, 0))
        chunk_sz = 4 if is_short else 7
        chunks = [word_timings[i:i + chunk_sz] for i in range(0, len(word_timings), chunk_sz)]
        active_chunk = chunks[0]
        active_word_idx = 0
        for ch in chunks:
            if ch[0]["start"] <= section_t <= (ch[-1]["end"] + 0.15):
                active_chunk = ch
                for w_i, w_obj in enumerate(ch):
                    if section_t >= w_obj["start"]:
                        active_word_idx = w_i
                break
            elif section_t > (ch[-1]["end"] + 0.15):
                active_chunk = ch
                active_word_idx = len(ch) - 1

        strip_h = 210 if is_short else 130
        strip = Image.new("RGBA", (W, strip_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(strip, "RGBA")
        font = get_font(54 if is_short else 42)
        words_str_list = [w["word"] for w in active_chunk]

        if is_short:
            lines = [words_str_list[:2], words_str_list[2:]] if len(words_str_list) > 2 else [words_str_list]
            y_cur = 15
            w_cnt = 0
            for ln in lines:
                if not ln:
                    continue
                disp = [w.upper() for w in ln]
                lw = draw.textbbox((0, 0), " ".join(disp), font=font)[2]
                x_cur = (W - lw) // 2
                for dw in disp:
                    col = (255, 220, 0, 255) if w_cnt == active_word_idx else (255, 255, 255, 255)
                    draw.text((x_cur, y_cur), dw, font=font, fill=col, stroke_width=7, stroke_fill=(0, 0, 0, 255))
                    x_cur += draw.textbbox((0, 0), dw + " ", font=font)[2]
                    w_cnt += 1
                y_cur += 74
        else:
            phrase = " ".join(words_str_list)
            lw = draw.textbbox((0, 0), phrase, font=font)[2]
            bx1, bx2 = max((W - lw) // 2 - 32, 30), min((W + lw) // 2 + 32, W - 30)
            draw.rounded_rectangle([(bx1, 12), (bx2, 98)], radius=12, fill=(6, 9, 16, 232), outline=(255, 214, 10, 105), width=2)
            x_cur = (W - lw) // 2
            for idx_w, w in enumerate(words_str_list):
                col = (255, 214, 10, 255) if idx_w == active_word_idx else (255, 255, 255, 255)
                draw.text((x_cur, 28), w, font=font, fill=col, stroke_width=3, stroke_fill=(0, 0, 0, 240))
                x_cur += draw.textbbox((0, 0), w + " ", font=font)[2]
        return strip

def build_story_adaptive_soundtrack(filename, duration, beat_switch_times):
    sr = 22050
    n_samples = int(sr * duration)
    t = np.linspace(0, duration, n_samples, endpoint=False)
    prog = t / max(duration, 1.0)
    freq_env = np.where(prog < 0.30, 73.42, np.where(prog < 0.70, 58.27, 55.0))
    pad = 0.22 * np.sin(2 * np.pi * freq_env * t) + 0.11 * np.sin(2 * np.pi * (freq_env * 1.5) * t)
    breath = 0.70 + 0.30 * np.sin(2 * np.pi * 0.14 * t)
    audio = (pad * breath) * 0.075
    for bt in beat_switch_times:
        idx = int(bt * sr)
        if idx < n_samples:
            slen = min(int(0.16 * sr), n_samples - idx)
            st_t = np.linspace(0, slen / float(sr), slen, endpoint=False)
            audio[idx:idx + slen] += 0.10 * np.sin(2 * np.pi * (160 - 70 * st_t) * st_t) * np.exp(-st_t * 15.0)
    audio_int16 = np.int16(np.clip(audio, -1.0, 1.0) * 32767)
    with wave.open(filename, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(audio_int16.tobytes())
    return filename

def create_1080p_thumbnails(dossier, entities, photo_bank, watermark):
    W, H = 1920, 1080
    c_prof = dossier["country_profile"]
    p1 = photo_bank[0]["image"]
    ent_main = entities[0].upper() if entities else c_prof["name"]

    st1 = detect_faces_and_build_1080p_stage(p1, W, H)
    t1 = extract_animated_frame_from_stage(st1, W, H, 0.3)
    t1 = ImageEnhance.Contrast(t1).enhance(1.18)
    d1 = ImageDraw.Draw(t1, "RGBA")
    for x in range(0, 1200):
        d1.line([(x, 0), (x, H)], fill=(6, 9, 18, int(245 * (1.0 - (x / 1200.0) ** 1.3))))
    t1.paste(watermark, (64, 54), watermark)
    if c_prof.get("flag_img"):
        t1.paste(c_prof["flag_img"].resize((110, 70)), (220, 60), c_prof["flag_img"].resize((110, 70)))

    kick1 = f"{c_prof['name']} • {c_prof['capital'].upper()}"
    kw1 = d1.textbbox((0, 0), kick1, font=get_font(36))[2] + 54
    d1.rounded_rectangle([(64, 330), (64 + kw1, 405)], radius=12, fill=(204, 18, 36, 255))
    d1.text((90, 346), kick1, fill=(255, 255, 255, 255), font=get_font(36))

    h1_a = f"{ent_main[:16]}'S"
    h1_b = "NEXT BIG MOVE"
    fb = get_font(98)
    d1.text((64, 445), h1_a, fill=(255, 255, 255, 255), font=fb, stroke_width=6, stroke_fill=(0, 0, 0, 255))
    w2 = d1.textbbox((0, 0), h1_b, font=fb)[2] + 70
    d1.rounded_rectangle([(64, 590), (64 + w2, 735)], radius=18, fill=(255, 214, 10, 255))
    d1.text((98, 610), h1_b, fill=(10, 12, 18, 255), font=fb)
    path_c1 = "output/WTB_1080p_Thumb_1.jpg"
    t1.convert("RGB").save(path_c1, quality=96)

    selected_title = f"Why {dossier['title']} Changes {c_prof['name'].title()}'s Strategic Calculus"
    return {
        "selected_thumbnail": path_c1,
        "selected_title": selected_title,
        "hashtags": ["#WorldTalkBrief", f"#{c_prof['name'].replace(' ', '')}", "#Geopolitics", "#WorldNews"]
    }

def try_youtube_auto_upload(video_path, title, description, tags, is_short=False, thumbnail_path=None):
    token_b64 = os.environ.get("YOUTUBE_TOKEN_JSON_B64", "").strip()
    if not token_b64:
        print(f"ℹ️ [GitHub Cloud Test Mode] YOUTUBE_TOKEN_JSON_B64 not set yet; skipping live YouTube upload for {video_path}.", flush=True)
        return None
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        with open("token.json", "wb") as tf:
            tf.write(base64.b64decode(token_b64))
        creds = Credentials.from_authorized_user_file("token.json", ["https://www.googleapis.com/auth/youtube.upload"])
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        yt = build("youtube", "v3", credentials=creds)

        final_title = (title[:90] + " #Shorts") if is_short and "#shorts" not in title.lower() else title[:100]
        body = {
            "snippet": {"title": final_title, "description": description, "tags": tags, "categoryId": "25"},
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
        }
        media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/mp4")
        req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
        resp = None
        while resp is None:
            _, resp = req.next_chunk()
        vid_id = resp["id"]
        print(f"✅ [YOUTUBE LIVE UPLOAD SUCCESS] https://youtu.be/{vid_id}", flush=True)
        if thumbnail_path and os.path.exists(thumbnail_path) and not is_short:
            yt.thumbnails().set(videoId=vid_id, media_body=MediaFileUpload(thumbnail_path)).execute()
        return vid_id
    except Exception as e:
        print(f"⚠️ YouTube upload warning: {e}", flush=True)
        return None

async def main():
    watermark = build_wtb_watermark(width=140, height=82)
    voice_sub_dir = VoiceAndSubtitleEngine()

    dossiers = discover_and_build_dossiers()
    short_dossier = dossiers[0]
    long_dossiers = dossiers[1:3] if len(dossiers) >= 3 else dossiers[:2]

    print(f"\n📱 [2/6] Building True 1080p Full HD Short (1080x1920) on: {short_dossier['title']}", flush=True)
    short_sections, short_entities = build_short_script(short_dossier)
    s_photo_bank, s_osm = harvest_datacenter_safe_1080p_photos(short_dossier, short_entities, target_count=12, tag="short")

    for idx, sec in enumerate(short_sections):
        ap = f"temp/s_voice_{idx}.mp3"
        vc, dur, w_timings = await voice_sub_dir.synthesize_with_word_boundaries(sec["narration"], ap, voice_style=sec.get("voice_style", "clear"))
        sec["audio_clip"] = vc
        sec["duration"] = dur
        sec["word_timings"] = w_timings

    s_beats = build_storyboard_beats_1080p(short_sections, short_dossier, s_photo_bank, s_osm, 1080, 1920)

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
    bgm_s = AudioFileClip(build_story_adaptive_soundtrack("temp/bgm_s.wav", final_short.duration, beat_switch_times_s))
    final_short = final_short.with_audio(CompositeAudioClip([final_short.audio, bgm_s])) if MOVIEPY_V2 else final_short.set_audio(CompositeAudioClip([final_short.audio, bgm_s]))
    out_short = "output/WTB_1080p_Short_9x16.mp4"
    final_short.write_videofile(out_short, fps=24, codec="libx264", audio_codec="aac", bitrate="8000k", preset="ultrafast", threads=4, logger=None)

    print(f"\n📺 [4/6] Building True 1080p Full HD Long Documentary (1920x1080)...", flush=True)
    long_chapters = build_long_documentary_script(long_dossiers)
    lead_long_dossier = long_dossiers[0]
    lead_long_entities = extract_story_entities(lead_long_dossier)

    dossier_banks = {}
    for ch in long_chapters:
        d_ref = ch["dossier"]
        d_key = d_ref["title"]
        if d_key not in dossier_banks:
            d_ents = extract_story_entities(d_ref)
            p_bank, osm_im = harvest_datacenter_safe_1080p_photos(d_ref, d_ents, target_count=12, tag=f"long_{len(dossier_banks)}")
            dossier_banks[d_key] = (p_bank, osm_im)

    for idx, ch in enumerate(long_chapters):
        ap = f"temp/l_voice_{idx}.mp3"
        vc, dur, w_timings = await voice_sub_dir.synthesize_with_word_boundaries(ch["narration"], ap, voice_style=ch.get("voice_style", "clear"))
        ch["audio_clip"] = vc
        ch["duration"] = dur
        ch["word_timings"] = w_timings

    long_clips = []
    beat_switch_times_l = []
    cur_lt = 0.0

    for d_key, (p_bank, osm_im) in dossier_banks.items():
        d_chaps = [ch for ch in long_chapters if ch["dossier"]["title"] == d_key]
        l_beats = build_storyboard_beats_1080p(d_chaps, d_chaps[0]["dossier"], p_bank, osm_im, 1920, 1080)
        for local_sec_idx, ch in enumerate(d_chaps):
            sec_beats = [b for b in l_beats if b["section_idx"] == local_sec_idx]
            for b in sec_beats:
                beat_switch_times_l.append(round(cur_lt, 2))
                cur_lt += b["duration"]
            clip = make_section_clip_from_beats(sec_beats, watermark, voice_sub_dir, ch["duration"], 1920, 1080, is_short=False)
            clip = clip.with_audio(ch["audio_clip"]) if MOVIEPY_V2 else clip.set_audio(ch["audio_clip"])
            long_clips.append(clip)

    final_long = concatenate_videoclips(long_clips, method="compose")
    bgm_l = AudioFileClip(build_story_adaptive_soundtrack("temp/bgm_l.wav", final_long.duration, beat_switch_times_l))
    final_long = final_long.with_audio(CompositeAudioClip([final_long.audio, bgm_l])) if MOVIEPY_V2 else final_long.set_audio(CompositeAudioClip([final_long.audio, bgm_l]))
    out_long = "output/WTB_1080p_Long_16x9.mp4"
    final_long.write_videofile(out_long, fps=20, codec="libx264", audio_codec="aac", bitrate="8000k", preset="ultrafast", threads=4, logger=None)

    lead_p_bank, _ = dossier_banks[lead_long_dossier["title"]]
    pkg_report = create_1080p_thumbnails(lead_long_dossier, lead_long_entities, lead_p_bank, watermark)

    with open("output/wtb_1080p_report.json", "w") as f:
        json.dump({
            "short_topic": short_dossier["title"],
            "short_photos_collected": len(s_photo_bank),
            "long_topic": lead_long_dossier["title"],
            "long_photos_collected": len(lead_p_bank),
            "packaging": pkg_report
        }, f, indent=2)

    try_youtube_auto_upload(out_short, short_dossier["title"], short_dossier["title"], ["WorldTalkBrief", "Shorts", "WorldNews"], is_short=True)
    try_youtube_auto_upload(out_long, pkg_report["selected_title"], pkg_report["selected_title"], ["WorldTalkBrief", "Geopolitics", "Documentary"], is_short=False, thumbnail_path=pkg_report["selected_thumbnail"])

    print(f"✅ [6/6] GITHUB CLOUD 1080p FULL HD PRODUCTION COMPLETE!", flush=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print("❌ CRITICAL ERROR DETAILS:", flush=True)
        traceback.print_exc()
        sys.exit(1)
