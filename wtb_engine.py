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
from datetime import datetime
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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9"
}
HEADERS_WIKI = {
    "User-Agent": "WorldTalkBriefCloudFactory/16.0 (https://github.com/bapuop17/wtb_engine; editorial@worldtalkbrief.org)"
}

HISTORY_FILE = "published_history.json"

# ==============================================================================
# 1. EXPANDED GLOBAL GEOPOLITICAL DATABASE + DEMONYM RESOLVER
# ==============================================================================
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
    "GAZA": ("PS", "PSE", "Gaza City", "2.1M", "Middle East", 31.501, 34.466),
    "PALESTINE": ("PS", "PSE", "Ramallah", "5.4M", "Middle East", 31.902, 35.206),
    "TAIWAN": ("TW", "TWN", "Taipei", "23.5M", "East Asia", 25.033, 121.565),
    "POLAND": ("PL", "POL", "Warsaw", "37.6M", "Europe", 52.229, 21.012),
    "ALBANIA": ("AL", "ALB", "Tirana", "2.8M", "Balkans / Europe", 41.327, 19.818),
    "SERBIA": ("RS", "SRB", "Belgrade", "6.6M", "Balkans / Europe", 44.786, 20.448),
    "GREECE": ("GR", "GRC", "Athens", "10.4M", "Europe", 37.983, 23.727),
    "SPAIN": ("ES", "ESP", "Madrid", "48.3M", "Europe", 40.416, -3.703),
    "NETHERLANDS": ("NL", "NLD", "Amsterdam", "17.9M", "Europe", 52.367, 4.904),
    "SWEDEN": ("SE", "SWE", "Stockholm", "10.5M", "Europe", 59.329, 18.068),
    "NORWAY": ("NO", "NOR", "Oslo", "5.5M", "Europe", 59.913, 10.752),
    "FINLAND": ("FI", "FIN", "Helsinki", "5.6M", "Europe", 60.169, 24.938),
    "SWITZERLAND": ("CH", "CHE", "Bern", "8.8M", "Europe", 46.948, 7.447),
    "AUSTRIA": ("AT", "AUT", "Vienna", "9.1M", "Europe", 48.208, 16.373),
    "BELGIUM": ("BE", "BEL", "Brussels", "11.7M", "Europe", 50.850, 4.351),
    "HUNGARY": ("HU", "HUN", "Budapest", "9.6M", "Europe", 47.497, 19.040),
    "ROMANIA": ("RO", "ROU", "Bucharest", "19M", "Europe", 44.426, 26.102),
    "GEORGIA": ("GE", "GEO", "Tbilisi", "3.7M", "Caucasus", 41.715, 44.827),
    "ARMENIA": ("AM", "ARM", "Yerevan", "3.0M", "Caucasus", 40.179, 44.499),
    "AZERBAIJAN": ("AZ", "AZE", "Baku", "10.1M", "Caucasus", 40.409, 49.867),
    "KAZAKHSTAN": ("KZ", "KAZ", "Astana", "20M", "Central Asia", 51.169, 71.449),
    "AFGHANISTAN": ("AF", "AFG", "Kabul", "41M", "South/Central Asia", 34.555, 69.207),
    "BANGLADESH": ("BD", "BGD", "Dhaka", "173M", "South Asia", 23.810, 90.412),
    "SRI LANKA": ("LK", "LKA", "Colombo", "22M", "South Asia", 6.927, 79.861),
    "MYANMAR": ("MM", "MMR", "Naypyidaw", "54M", "Southeast Asia", 19.763, 96.078),
    "THAILAND": ("TH", "THA", "Bangkok", "71.8M", "Southeast Asia", 13.756, 100.501),
    "VIETNAM": ("VN", "VNM", "Hanoi", "99M", "Southeast Asia", 21.028, 105.854),
    "PHILIPPINES": ("PH", "PHL", "Manila", "117M", "Southeast Asia", 14.599, 120.984),
    "INDONESIA": ("ID", "IDN", "Jakarta", "277M", "Southeast Asia", -6.208, 106.845),
    "MALAYSIA": ("MY", "MYS", "Kuala Lumpur", "34M", "Southeast Asia", 3.139, 101.686),
    "SINGAPORE": ("SG", "SGP", "Singapore", "5.9M", "Southeast Asia", 1.352, 103.819),
    "EGYPT": ("EG", "EGY", "Cairo", "112M", "North Africa", 30.044, 31.235),
    "SOUTH AFRICA": ("ZA", "ZAF", "Pretoria", "60M", "Southern Africa", -25.747, 28.229),
    "NIGERIA": ("NG", "NGA", "Abuja", "223M", "West Africa", 9.076, 7.398),
    "KENYA": ("KE", "KEN", "Nairobi", "55M", "East Africa", -1.292, 36.821),
    "ETHIOPIA": ("ET", "ETH", "Addis Ababa", "126M", "East Africa", 9.032, 38.746),
    "SOMALIA": ("SO", "SOM", "Mogadishu", "18M", "East Africa", 2.046, 45.318),
    "DR CONGO": ("CD", "COD", "Kinshasa", "102M", "Central Africa", -4.441, 15.266),
    "MOROCCO": ("MA", "MAR", "Rabat", "37.8M", "North Africa", 34.020, -6.841),
    "ALGERIA": ("DZ", "DZA", "Algiers", "45.6M", "North Africa", 36.753, 3.058),
    "TUNISIA": ("TN", "TUN", "Tunis", "12.4M", "North Africa", 36.806, 10.181),
    "LIBYA": ("LY", "LBY", "Tripoli", "6.8M", "North Africa", 32.887, 13.191),
    "IRAQ": ("IQ", "IRQ", "Baghdad", "45M", "Middle East", 33.315, 44.366),
    "JORDAN": ("JO", "JOR", "Amman", "11.3M", "Middle East", 31.945, 35.928),
    "QATAR": ("QA", "QAT", "Doha", "2.7M", "Middle East", 25.285, 51.531),
    "UAE": ("AE", "ARE", "Abu Dhabi", "9.5M", "Middle East", 24.453, 54.377),
    "KUWAIT": ("KW", "KWT", "Kuwait City", "4.3M", "Middle East", 29.375, 47.977),
    "ARGENTINA": ("AR", "ARG", "Buenos Aires", "46M", "South America", -34.603, -58.381),
    "COLOMBIA": ("CO", "COL", "Bogota", "52M", "South America", 4.711, -74.072),
    "VENEZUELA": ("VE", "VEN", "Caracas", "28.8M", "South America", 10.480, -66.903),
    "CHILE": ("CL", "CHL", "Santiago", "19.6M", "South America", -33.448, -70.669),
    "PERU": ("PE", "PER", "Lima", "34M", "South America", -12.046, -77.042),
    "CUBA": ("CU", "CUB", "Havana", "11.1M", "Caribbean", 23.113, -82.366),
    "HAITI": ("HT", "HTI", "Port-au-Prince", "11.7M", "Caribbean", 18.594, -72.307),
    "NEW ZEALAND": ("NZ", "NZL", "Wellington", "5.2M", "Oceania", -41.286, 174.776)
}

DEMONYM_TO_COUNTRY = {
    "american": "UNITED STATES", "u.s.": "UNITED STATES", "us ": "UNITED STATES", "washington": "UNITED STATES",
    "russian": "RUSSIA", "moscow": "RUSSIA", "kremlin": "RUSSIA",
    "chinese": "CHINA", "beijing": "CHINA",
    "israeli": "ISRAEL", "jerusalem": "ISRAEL", "tel aviv": "ISRAEL",
    "iranian": "IRAN", "tehran": "IRAN",
    "indian": "INDIA", "new delhi": "INDIA",
    "pakistani": "PAKISTAN", "islamabad": "PAKISTAN",
    "ukrainian": "UKRAINE", "ukrainians": "UKRAINE", "kyiv": "UKRAINE", "kiev": "UKRAINE",
    "french": "FRANCE", "paris": "FRANCE",
    "british": "UNITED KINGDOM", "uk ": "UNITED KINGDOM", "london": "UNITED KINGDOM",
    "german": "GERMANY", "berlin": "GERMANY",
    "italian": "ITALY", "rome": "ITALY",
    "canadian": "CANADA", "ottawa": "CANADA",
    "brazilian": "BRAZIL", "brasilia": "BRAZIL",
    "australian": "AUSTRALIA", "canberra": "AUSTRALIA",
    "mexican": "MEXICO", "mexico city": "MEXICO",
    "lebanese": "LEBANON", "beirut": "LEBANON",
    "syrian": "SYRIA", "damascus": "SYRIA",
    "albanian": "ALBANIA", "tirana": "ALBANIA",
    "serbian": "SERBIA", "belgrade": "SERBIA",
    "polish": "POLAND", "warsaw": "POLAND",
    "taiwanese": "TAIWAN", "taipei": "TAIWAN",
    "japanese": "JAPAN", "tokyo": "JAPAN",
    "palestinian": "PALESTINE", "gaza": "GAZA",
    "kenyan": "KENYA", "nairobi": "KENYA",
    "sudanese": "SUDAN", "khartoum": "SUDAN"
}

BANNED_IMAGE_SOURCES = [
    "alamy", "dreamstime", "freepik", "shutterstock", "gettyimages", "istockphoto",
    "123rf", "depositphotos", "vecteezy", "canstock", "bigstock", "sputnik",
    "ytimg", "youtube", "cartoon", "clipart", "meme", "watermark", "agefotostock",
    "pond5", "flipkart", "minecraft", "fortnite", "roblox", "pokemon", "anime"
]

PERSON_WIKI_MAP = {
    "trump": ("Donald Trump", "U.S. PRESIDENT DONALD TRUMP", "UNITED STATES"),
    "putin": ("Vladimir Putin", "RUSSIAN PRESIDENT VLADIMIR PUTIN", "RUSSIA"),
    "zelensky": ("Volodymyr Zelenskyy", "UKRAINIAN PRESIDENT ZELENSKYY", "UKRAINE"),
    "zelenskyy": ("Volodymyr Zelenskyy", "UKRAINIAN PRESIDENT ZELENSKYY", "UKRAINE"),
    "biden": ("Joe Biden", "U.S. PRESIDENT JOE BIDEN", "UNITED STATES"),
    "netanyahu": ("Benjamin Netanyahu", "ISRAELI PM BENJAMIN NETANYAHU", "ISRAEL"),
    "macron": ("Emmanuel Macron", "FRENCH PRESIDENT EMMANUEL MACRON", "FRANCE"),
    "lecornu": ("Sébastien Lecornu", "FRENCH MINISTER SEBASTIEN LECORNU", "FRANCE"),
    "starmer": ("Keir Starmer", "UK PM KEIR STARMER", "UNITED KINGDOM"),
    "modi": ("Narendra Modi", "INDIAN PM NARENDRA MODI", "INDIA"),
    "xi": ("Xi Jinping", "CHINESE PRESIDENT XI JINPING", "CHINA"),
    "lula": ("Luiz Inácio Lula da Silva", "BRAZILIAN PRESIDENT LULA", "BRAZIL"),
    "bolsonaro": ("Jair Bolsonaro", "FORMER PRESIDENT JAIR BOLSONARO", "BRAZIL"),
    "carney": ("Mark Carney", "CANADIAN PM MARK CARNEY", "CANADA"),
    "erdogan": ("Recep Tayyip Erdoğan", "TURKISH PRESIDENT ERDOGAN", "TURKEY"),
    "khamenei": ("Ali Khamenei", "IRANIAN SUPREME LEADER KHAMENEI", "IRAN")
}

CONCRETE_WIKI_PROPS = {
    "drone": ("MILITARY DRONE / UAV", "Bayraktar TB2", "military drone attack"),
    "drones": ("MILITARY DRONE FLEET", "Shahed 136", "military drone fleet"),
    "bomber": ("STRATEGIC BOMBER AIRCRAFT", "Tupolev Tu-95", "strategic bomber aircraft"),
    "bombers": ("STRATEGIC BOMBER FLEET", "Tupolev Tu-160", "strategic bomber airfield"),
    "munitions": ("MUNITIONS & ARTILLERY", "155 mm caliber", "artillery shells munitions"),
    "sabotage": ("COVERT SABOTAGE OPERATION", "Rail transport", "railway tracks security"),
    "intelligence": ("MILITARY INTELLIGENCE", "Military intelligence", "military radar command center"),
    "sanctions": ("ECONOMIC SANCTIONS ORDER", "United States Department of the Treasury", "economic sanctions port"),
    "curfew": ("NIGHT CURFEW ENFORCEMENT", "National Police (France)", "police patrol night street curfew"),
    "curfews": ("SECURITY CURFEW PATROL", "Riot police", "police security forces night street"),
    "riots": ("URBAN RIOT RESPONSE", "Riot control", "riot police shields street"),
    "looting": ("URBAN SECURITY CORDON", "Gendarmerie", "police security cordon city"),
    "clashes": ("PROTEST CLASHES", "Riot control", "protesters riot police clashes"),
    "protesters": ("MASS STREET PROTESTS", "Demonstration", "protesters rally police"),
    "migrants": ("IMMIGRATION & BORDER POLICY", "United States Department of Homeland Security", "US immigration border policy"),
    "deportation": ("IMMIGRATION ENFORCEMENT", "United States Citizenship and Immigration Services", "immigration policy court"),
    "negotiating": ("DIPLOMATIC NEGOTIATING TABLE", "Palais des Nations", "peace negotiations diplomatic table"),
    "negotiations": ("HIGH-STAKES PEACE TALKS", "United Nations Security Council", "peace talks summit"),
    "fire": ("EMERGENCY FIRE RESPONSE", "Firefighting", "firefighters battling blaze"),
    "flames": ("FIREFIGHTING OPERATION", "Fire engine", "firefighters emergency fire"),
    "base": ("MILITARY BASE INSTALLATION", "Military base", "military base soldiers"),
    "military": ("ARMED FORCES DEPLOYMENT", "Armed forces", "military troops deployment"),
    "violence": ("SECURITY CRACKDOWN", "Riot police", "police security forces patrol"),
    "missile": ("BALLISTIC MISSILE SYSTEM", "MIM-104 Patriot", "missile defense launcher"),
    "oil": ("GLOBAL OIL & ENERGY", "Oil refinery", "oil tanker energy"),
    "tariff": ("GLOBAL TRADE & TARIFFS", "Container ship", "container ship port trade"),
    "kremlin": ("MOSCOW KREMLIN", "Moscow Kremlin", "Moscow Kremlin Russia"),
    "white house": ("THE WHITE HOUSE", "White House", "White House Washington"),
    "pentagon": ("THE PENTAGON", "The Pentagon", "Pentagon defense department"),
    "nato": ("NATO HEADQUARTERS", "NATO headquarters", "NATO summit Brussels"),
    "amazon": ("AMAZON RAINFOREST", "Amazon rainforest", "Brazil Amazon rainforest")
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

# ==============================================================================
# 2. DAILY YOUTUBE CHANNEL ANALYTICS SELF-IMPROVEMENT ENGINE
# ==============================================================================
def fetch_channel_winning_keywords():
    token_envs = ["YOUTUBE_TOKEN_JSON_B64", "YOUTUBE_TOKEN_2_B64", "YOUTUBE_TOKEN_3_B64", "YOUTUBE_TOKEN_4_B64"]
    available_tokens = [os.environ.get(k, "").strip() for k in token_envs if os.environ.get(k, "").strip()]
    if not available_tokens:
        return []

    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        t_file = "temp/analytics_token.json"
        with open(t_file, "wb") as tf:
            tf.write(base64.b64decode(available_tokens[0]))
        creds = Credentials.from_authorized_user_file(t_file, ["https://www.googleapis.com/auth/youtube.readonly"])
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        yt = build("youtube", "v3", credentials=creds)

        ch_resp = yt.channels().list(part="contentDetails", mine=True).execute()
        items = ch_resp.get("items", [])
        if not items:
            return []
        uploads_pl = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
        pl_items = yt.playlistItems().list(part="contentDetails", playlistId=uploads_pl, maxResults=15).execute().get("items", [])
        vid_ids = [it["contentDetails"]["videoId"] for it in pl_items]
        if not vid_ids:
            return []

        v_stats = yt.videos().list(part="snippet,statistics", id=",".join(vid_ids)).execute().get("items", [])
        scored_vids = []
        for v in v_stats:
            views = int(v.get("statistics", {}).get("viewCount", 0))
            likes = int(v.get("statistics", {}).get("likeCount", 0))
            title = v.get("snippet", {}).get("title", "")
            scored_vids.append((views + likes * 5, title))

        scored_vids.sort(reverse=True)
        stop_w = {"why", "how", "the", "and", "for", "with", "from", "changes", "next", "move", "shorts", "says", "stated", "after"}
        winning_kws = []
        for _, t_str in scored_vids[:5]:
            for w in re.findall(r"[a-z]{4,}", t_str.lower()):
                if w not in stop_w and w not in winning_kws:
                    winning_kws.append(w)
        if winning_kws:
            print("📈 [Channel Analytics Optimizer] Top Audience-Winning Keywords Detected:", winning_kws[:8], flush=True)
        return winning_kws[:10]
    except Exception:
        return []

# ==============================================================================
# 3. SEMANTIC EVENT FINGERPRINTING, FOLLOW-UP DETECTION & 8-SOURCE ROTATION
# ==============================================================================
def load_published_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {
                    "published_keys": set(data.get("published_keys", [])),
                    "event_fingerprints": data.get("event_fingerprints", []),
                    "last_sources": data.get("last_sources", [])
                }
        except Exception:
            pass
    return {"published_keys": set(), "event_fingerprints": [], "last_sources": []}

def save_published_history(hist_obj):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "updated_at": datetime.utcnow().isoformat(),
                "published_keys": list(hist_obj["published_keys"])[-400:],
                "event_fingerprints": hist_obj["event_fingerprints"][-200:],
                "last_sources": hist_obj["last_sources"][-20:]
            }, f, indent=2)
    except Exception:
        pass

def make_story_key(title):
    words = re.findall(r"[a-z0-9]+", title.lower())
    return "_".join(words[:6])

def extract_event_fingerprint(title):
    stop_w = {"the", "and", "for", "with", "from", "over", "after", "into", "says", "said", "amid", "new", "how", "why", "what", "that", "this", "are", "was", "were"}
    tokens = sorted(list({w.lower() for w in re.findall(r"[a-zA-Z]{4,}", title) if w.lower() not in stop_w}))
    return tokens

def check_semantic_duplicate_or_update(title, first_fact, hist_obj):
    st_key = make_story_key(title)
    if st_key in hist_obj["published_keys"]:
        return ("DUPLICATE", None)

    cur_fp = set(extract_event_fingerprint(title))
    if not cur_fp:
        return ("NEW_STORY", None)

    for past in hist_obj["event_fingerprints"]:
        past_fp = set(past.get("tokens", []))
        if not past_fp:
            continue
        overlap = len(cur_fp.intersection(past_fp)) / float(min(len(cur_fp), len(past_fp)))
        if overlap >= 0.55:
            comb_low = f"{title} {first_fact}".lower()
            update_markers = ["update", "day ", "overnight", "calm", "responds", "retaliates", "new ", "latest", "second", "third", "seventh", "follows", "aftermath"]
            if any(um in comb_low for um in update_markers) and title.lower() != past.get("title", "").lower():
                return ("FOLLOW_UP_UPDATE", past.get("title"))
            return ("DUPLICATE", None)

    return ("NEW_STORY", None)

def resolve_country_profile_accurate(title, raw_facts_list):
    headline_low = title.lower()
    body_low = " ".join(raw_facts_list[:3]).lower()

    for c_name in COUNTRY_GEO_DB.keys():
        if re.search(rf"\b{re.escape(c_name.lower())}\b", headline_low):
            return build_country_dict_from_db(c_name)
    for dem, c_mapped in DEMONYM_TO_COUNTRY.items():
        if dem in headline_low:
            return build_country_dict_from_db(c_mapped)

    for c_name in COUNTRY_GEO_DB.keys():
        if re.search(rf"\b{re.escape(c_name.lower())}\b", body_low):
            return build_country_dict_from_db(c_name)
    for dem, c_mapped in DEMONYM_TO_COUNTRY.items():
        if dem in body_low:
            return build_country_dict_from_db(c_mapped)

    return build_country_dict_from_db("UNITED STATES")

def build_country_dict_from_db(c_name):
    iso2, iso3, cap, pop, reg, lat, lon = COUNTRY_GEO_DB.get(c_name, COUNTRY_GEO_DB["UNITED STATES"])
    c_prof = {"name": c_name, "iso2": iso2, "iso3": iso3, "capital": cap, "population": pop, "region": reg, "lat": lat, "lon": lon, "flag_img": None}
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

# Expanded BANNED_PHRASES to block Guardian/BBC reader callouts ("send us your questions", etc.)!
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
    "the bbc joins",
    "send us your questions",
    "share your story",
    "tell us what you think",
    "contact us",
    "have you been affected",
    "tap here to",
    "click here to",
    "listen to our podcast"
]

def clean_fact(text):
    if not text:
        return ""
    repl = {"\u2011": "-", "\u2013": "-", "\u2014": " - ", "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u00a0": " "}
    for k, v in repl.items():
        text = text.replace(k, v)
    text = re.sub(r"([a-z])([A-Z])", r"\1. \2", text)
    # Remove any third-party news channel self-mentions so narration sounds 100% original to World Talk Brief!
    text = re.sub(r"(?i)\bthe bbc joins\b", "Correspondents join", text)
    text = re.sub(r"(?i)\btold the bbc\b", "stated on the record", text)
    text = re.sub(r"(?i)\btells the bbc\b", "stated", text)
    text = re.sub(r"(?i)\btells bbc\b", "stated", text)
    text = re.sub(r"(?i)\btold al jazeera\b", "stated", text)
    text = re.sub(r"(?i)\btold the guardian\b", "stated", text)
    text = re.sub(r"(?i)\btold reuters\b", "confirmed", text)
    text = re.sub(r"(?i)\b(BBC World Service|BBC World|BBC News|BBC)\b", "international dispatches", text)
    text = re.sub(r"(?i)\(\s*(centre|center|left|right|pictured|file|ap|reuters|afp|getty)[^)]*\)", "", text)
    text = re.sub(r"\[([^\]]+)\]", r"\1", text)
    text = re.sub(r"[^\x20-\x7E]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    low = text.lower()
    for bp in BANNED_PHRASES:
        if bp in low:
            return ""
    return text

def normalize_pub_date(raw_date):
    if not raw_date:
        return datetime.utcnow().strftime("%Y-%m-%d")
    cleaned = re.sub(r"\s+", " ", str(raw_date)).strip()
    return cleaned[:25]

def classify_story_mood_and_category(title, claims_text):
    comb = f"{title} {claims_text}".lower()
    if any(re.search(rf"\b{re.escape(w)}\b", comb) for w in ["ai", "artificial intelligence", "microchip", "semiconductor", "quantum", "spacecraft", "nasa", "cyber", "robotics"]):
        return "ai_tech_science"
    if any(re.search(rf"\b{re.escape(w)}\b", comb) for w in ["gdp", "inflation", "stock market", "tariff", "tariffs", "central bank", "interest rate", "economy", "debt"]):
        return "economy_markets"
    if any(re.search(rf"\b{re.escape(w)}\b", comb) for w in ["climate", "amazon", "deforestation", "emissions", "wildfire", "flood", "earthquake", "hurricane"]):
        return "environment_climate"
    if any(re.search(rf"\b{re.escape(w)}\b", comb) for w in ["missile", "strike", "offensive", "sabotage", "troops", "war", "attack", "killed", "military", "drone", "bomber", "violence", "fire", "clashes", "riots"]):
        return "war_crisis"
    return "geopolitics_diplomacy"

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

def discover_and_build_dossiers(hist_obj, winning_keywords):
    print("📡 [1/6] Scanning 8 Global News Sources with Source-Rotation & Event Deduplication...", flush=True)
    feeds = [
        ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
        ("The Guardian", "https://www.theguardian.com/world/rss"),
        ("DW News", "https://rss.dw.com/rdf/rss-en-world"),
        ("France24", "https://www.france24.com/en/rss"),
        ("UN News", "https://news.un.org/feed/subscribe/en/news/all/rss.xml"),
        ("NPR World", "https://feeds.npr.org/1004/rss.xml"),
        ("TOI World", "https://timesofindia.indiatimes.com/rssfeeds/296589292.cms"),
        ("BBC World", "http://feeds.bbci.co.uk/news/world/rss.xml")
    ]
    recent_used_sources = set(hist_obj["last_sources"][-2:]) if hist_obj["last_sources"] else set()
    feeds.sort(key=lambda x: 1 if x[0] in recent_used_sources else 0)

    high_impact_terms = [
        "president", "prime minister", "china", "iran", "israel", "russia", "ukraine",
        "military", "summit", "un", "nato", "missile", "sanctions", "oil", "economy",
        "trade", "tariff", "parliament", "election", "court", "intelligence", "treaty"
    ]
    dossiers = []
    batch_fingerprints = []

    for src, url in feeds:
        try:
            r_feed = requests.get(url, headers=HEADERS_WEB, timeout=10)
            feed = feedparser.parse(r_feed.content)
        except Exception:
            continue

        src_count = 0
        for entry in feed.entries[:18]:
            if src_count >= 2:
                break
            raw_t = entry.title.rsplit(" - ", 1)[0]
            if any(skip in raw_t.lower() for skip in ["live", "latest updates", "as it happened", "at a glance", "in pictures", "quiz", "podcast"]):
                continue
            title = clean_fact(raw_t)
            if len(title) < 22:
                continue

            link = getattr(entry, "link", "").strip()
            pub_date = normalize_pub_date(getattr(entry, "published", "") or getattr(entry, "updated", ""))
            if not link or not pub_date:
                continue

            raw_sum = BeautifulSoup(getattr(entry, "summary", ""), "html.parser").get_text()
            summary = clean_fact(raw_sum)

            dup_status, prev_event_title = check_semantic_duplicate_or_update(title, summary, hist_obj)
            if dup_status == "DUPLICATE":
                continue

            cur_fp_set = set(extract_event_fingerprint(title))
            if any(len(cur_fp_set.intersection(bfp)) / float(max(1, min(len(cur_fp_set), len(bfp)))) >= 0.55 for bfp in batch_fingerprints):
                continue

            rss_img = None
            if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
                rss_img = entry.media_thumbnail[0].get("url")
                if rss_img and "bbci.co.uk" in rss_img:
                    rss_img = re.sub(r"/standard/\d+/", "/standard/1024/", rss_img)
            elif hasattr(entry, "media_content") and entry.media_content:
                rss_img = entry.media_content[0].get("url")

            og_img = None
            verified_claims = []
            extra_article_imgs = []
            seen_fk = set()

            for s in re.split(r"(?<=[.!?])\s+", summary):
                cs = clean_fact(s)
                if len(cs) >= 28 and cs.lower() != title.lower():
                    if cs[-1] not in ".!?":
                        cs += "."
                    seen_fk.add(re.sub(r"[^a-z0-9]", "", cs.lower())[:40])
                    verified_claims.append({
                        "text": cs,
                        "source_url": link,
                        "source_name": src,
                        "published_date": pub_date
                    })

            try:
                r = requests.get(link, headers=HEADERS_WEB, timeout=7)
                soup = BeautifulSoup(r.text, "html.parser")
                m_og = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "twitter:image"})
                if m_og and m_og.get("content"):
                    og_img = m_og["content"]
                for img_tag in soup.find_all("img"):
                    iu = img_tag.get("src") or img_tag.get("data-src") or ""
                    if iu.startswith("http") and any(ext in iu.lower() for ext in [".jpg", ".jpeg", ".png", "ichef.bbci.co.uk"]):
                        if "ichef.bbci.co.uk" in iu:
                            iu = re.sub(r"/standard/\d+/", "/standard/1024/", iu)
                        if not any(b in iu.lower() for b in ["logo", "icon", "avatar", "sprite", "1x1"]) and iu not in extra_article_imgs:
                            extra_article_imgs.append(iu)

                for p in soup.find_all("p"):
                    if p.find_parent("figcaption") or p.find_parent("figure") or p.find_parent("footer") or p.find_parent("aside"):
                        continue
                    for rs in re.split(r"(?<=[.!?])\s+", p.get_text()):
                        cs = clean_fact(rs)
                        if 42 <= len(cs) <= 210:
                            if cs[-1] not in ".!?":
                                cs += "."
                            fk = re.sub(r"[^a-z0-9]", "", cs.lower())[:40]
                            if fk not in seen_fk:
                                seen_fk.add(fk)
                                verified_claims.append({
                                    "text": cs,
                                    "source_url": link,
                                    "source_name": src,
                                    "published_date": pub_date
                                })
                                if len(verified_claims) >= 10:
                                    break
                    if len(verified_claims) >= 10:
                        break
            except Exception:
                pass

            if len(verified_claims) < 4:
                try:
                    kw_q = " ".join(re.findall(r"[A-Za-z]{4,}", title)[:4])
                    b_rss = f"https://www.bing.com/news/search?q={urllib.parse.quote(kw_q)}&format=rss"
                    br = requests.get(b_rss, headers=HEADERS_WEB, timeout=6)
                    b_feed = feedparser.parse(br.content)
                    for b_ent in b_feed.entries[:6]:
                        b_link = getattr(b_ent, "link", "").strip()
                        b_date = normalize_pub_date(getattr(b_ent, "published", pub_date))
                        b_desc = clean_fact(BeautifulSoup(getattr(b_ent, "summary", ""), "html.parser").get_text())
                        if b_link and len(b_desc) >= 40:
                            if b_desc[-1] not in ".!?":
                                b_desc += "."
                            fk = re.sub(r"[^a-z0-9]", "", b_desc.lower())[:40]
                            if fk not in seen_fk:
                                seen_fk.add(fk)
                                verified_claims.append({
                                    "text": b_desc,
                                    "source_url": b_link,
                                    "source_name": "Global Wire",
                                    "published_date": b_date
                                })
                except Exception:
                    pass

            if len(verified_claims) < 3:
                continue

            raw_facts = [c["text"] for c in verified_claims]
            c_prof = resolve_country_profile_accurate(title, raw_facts)
            wb_data = fetch_verified_world_bank_gdp(c_prof["iso3"])
            category = classify_story_mood_and_category(title, " ".join(raw_facts[:4]))

            comb = f"{title} {' '.join(raw_facts[:3])}".lower()
            trend_score = sum(4 for kw in high_impact_terms if re.search(rf"\b{re.escape(kw)}\b", comb)) + len(verified_claims) * 3
            analytics_boost = sum(6 for w_kw in winning_keywords if w_kw in comb)
            # Slight bonus for sources not used in the last run so all 8 news agencies get equal representation!
            diversity_bonus = 0 if src in recent_used_sources else 5
            trend_score += analytics_boost + diversity_bonus

            batch_fingerprints.append(cur_fp_set)
            src_count += 1
            dossiers.append({
                "score": trend_score,
                "story_key": make_story_key(title),
                "event_tokens": list(cur_fp_set),
                "is_followup_update": (dup_status == "FOLLOW_UP_UPDATE"),
                "previous_event_title": prev_event_title,
                "title": title,
                "category": category,
                "source_url": link,
                "published_date": pub_date,
                "source_name": src,
                "verified_claims": verified_claims,
                "raw_facts": raw_facts,
                "lead_img": og_img or rss_img,
                "extra_article_imgs": extra_article_imgs[:10],
                "country_profile": c_prof,
                "wb_data": wb_data
            })
            if len(dossiers) >= 12:
                break
        if len(dossiers) >= 12:
            break

    dossiers.sort(key=lambda x: x["score"], reverse=True)
    return dossiers

# ==============================================================================
# 4. COUNTRY-LOCKED ENTITY & SCRIPT DIRECTOR (100% Original WTB Narration)
# ==============================================================================
def extract_story_entities(dossier):
    text = f"{dossier['title']} {' '.join(dossier['raw_facts'][:4])}"
    c_prof = dossier["country_profile"]
    ents = []
    low = text.lower()
    for k, (wiki_name, _, leader_country) in PERSON_WIKI_MAP.items():
        if re.search(rf"\b{re.escape(k)}\b", low):
            if wiki_name not in ents:
                ents.append(wiki_name)

    for fb in [c_prof["capital"], c_prof["name"].title(), f"{c_prof['name'].title()} government"]:
        if fb not in ents:
            ents.append(fb)
    return ents[:8]

def polish_journalistic_sentence(raw_fact, c_prof, role="BODY"):
    s = raw_fact.strip().rstrip(".")
    s = re.sub(r",\s*(police|officials|ministry|authorities|sources|reports|his office)\s+(say|said|reported|stated)$", "", s, flags=re.I)
    s = re.sub(r"^(police|officials|authorities|reports)\s+(say|said|state|stated)\s+(that\s+)?", "", s, flags=re.I)
    if not s:
        return ""
    s = s[0].upper() + s[1:]
    return f"{s}."

def make_clean_context_headline(text, max_words=8):
    cleaned = re.sub(r"^(Behind the scenes,|Crucially,|Meanwhile,|Look at the specifics confirmed on the record\.)\s*", "", text, flags=re.I)
    first_clause = re.split(r"[.;:—–]", cleaned)[0].strip()
    words = first_clause.split()
    dangling = {"THE", "A", "AN", "TO", "IN", "ON", "OF", "FOR", "WITH", "AND", "OR", "BY", "AS", "AT", "FROM", "THAT", "WHICH", "WHILE", "HIS", "HER", "ITS", "FOUR", "TWO"}
    selected = words[:max_words]
    while len(selected) > 3 and selected[-1].upper().strip(",.:;'\"") in dangling:
        selected.pop()
    return " ".join(selected).upper()

def build_short_script(dossier, variant_idx=0):
    c_prof = dossier["country_profile"]
    ents = extract_story_entities(dossier)
    claims = dossier["verified_claims"]
    title = dossier["title"]

    c0 = claims[0]
    c1 = claims[1] if len(claims) > 1 else c0
    c2 = claims[2] if len(claims) > 2 else c1

    hook_templates = [
        f"{title}. Major developments from {c_prof['capital']} are shifting the strategic balance right now.",
        f"Breaking dispatch from {c_prof['name'].title()}: {title}. Here is what the verified record reveals.",
        f"In a decisive development out of {c_prof['capital']}, {title}."
    ]
    if dossier.get("is_followup_update"):
        hook_narration = f"Major new update from {c_prof['capital']}: {title}. Here is what has just changed on the ground."
    else:
        hook_narration = hook_templates[variant_idx % len(hook_templates)]

    outro_templates = [
        f"What is your assessment of {c_prof['name'].title()}'s next move?",
        f"Will this contain the crisis in {c_prof['region']} or trigger a wider shift?",
        f"Share your analysis on how this reshapes {c_prof['region']}."
    ]

    sections = [
        {
            "role": "HOOK",
            "voice_style": "urgent",
            "headline": make_clean_context_headline(title, max_words=8),
            "narration": hook_narration,
            "claim_meta": c0
        },
        {
            "role": "WHAT_HAPPENED",
            "voice_style": "clear",
            "headline": make_clean_context_headline(c0["text"], max_words=8),
            "narration": polish_journalistic_sentence(c0["text"], c_prof, role="BODY"),
            "claim_meta": c0
        },
        {
            "role": "CONTEXT",
            "voice_style": "analytical",
            "headline": make_clean_context_headline(c1["text"], max_words=8),
            "narration": polish_journalistic_sentence(c1["text"], c_prof, role="CONTEXT"),
            "claim_meta": c1
        },
        {
            "role": "PAYOFF",
            "voice_style": "serious",
            "headline": make_clean_context_headline(c2["text"], max_words=8),
            "narration": f"{polish_journalistic_sentence(c2['text'], c_prof, role='PAYOFF')} {outro_templates[variant_idx % len(outro_templates)]}",
            "claim_meta": c2
        }
    ]
    return sections, ents

def build_long_documentary_script(dossiers):
    """
    Never speaks third-party channel names ('BBC World', etc.) in the narration!
    Keeps chapters in strict chronological order so the Subscribe Outro is ALWAYS last!
    """
    lead = dossiers[0]
    c_prof = lead["country_profile"]
    ents = extract_story_entities(lead)
    claims = lead["verified_claims"]

    c0 = claims[0]
    c1 = claims[1] if len(claims) > 1 else c0
    c2 = claims[2] if len(claims) > 2 else c1
    c3 = claims[3] if len(claims) > 3 else c2

    chapters = [
        {
            "chapter_num": 1,
            "chapter_title": make_clean_context_headline(lead["title"], max_words=8),
            "role": "HOOK",
            "voice_style": "urgent",
            "dossier": lead,
            "claim_meta": c0,
            "narration": f"{lead['title']}. As dispatches emerge from {c_prof['capital']}, verified reporting reveals a critical turning point for {c_prof['name'].title()}. {polish_journalistic_sentence(c0['text'], c_prof, 'BODY')}"
        },
        {
            "chapter_num": 2,
            "chapter_title": make_clean_context_headline(c1["text"], max_words=8),
            "role": "EVIDENCE",
            "voice_style": "clear",
            "dossier": lead,
            "claim_meta": c1,
            "narration": f"Examine the specifics confirmed by official dispatches. {polish_journalistic_sentence(c1['text'], c_prof, 'BODY')}"
        },
        {
            "chapter_num": 3,
            "chapter_title": f"STRATEGIC CORRIDOR: {c_prof['capital'].upper()}, {c_prof['name']}",
            "role": "GEOGRAPHY",
            "voice_style": "analytical",
            "dossier": lead,
            "claim_meta": c1,
            "narration": f"Geography explains why international observers are focused on {c_prof['capital']}. With a population of {c_prof['population']}, {c_prof['name'].title()} sits at a pivotal crossroads in {c_prof['region']}."
        },
        {
            "chapter_num": 4,
            "chapter_title": make_clean_context_headline(c2["text"], max_words=8),
            "role": "TIMELINE",
            "voice_style": "analytical",
            "dossier": lead,
            "claim_meta": c2,
            "narration": f"The buildup to this moment has been months in the making. {polish_journalistic_sentence(c2['text'], c_prof, 'CONTEXT')}"
        },
        {
            "chapter_num": 5,
            "chapter_title": make_clean_context_headline(c3["text"], max_words=8),
            "role": "COMPARISON",
            "voice_style": "serious",
            "dossier": lead,
            "claim_meta": c3,
            "narration": f"Now competing strategic priorities are being tested. {polish_journalistic_sentence(c3['text'], c_prof, 'BODY')}"
        }
    ]

    if len(dossiers) > 1 and dossiers[1] is not None:
        sec_d = dossiers[1]
        sc_prof = sec_d["country_profile"]
        sc0 = sec_d["verified_claims"][0]
        sc1 = sec_d["verified_claims"][1] if len(sec_d["verified_claims"]) > 1 else sc0
        chapters.append({
            "chapter_num": 6,
            "chapter_title": make_clean_context_headline(sec_d["title"], max_words=8),
            "role": "WIDER_CONTEXT",
            "voice_style": "clear",
            "dossier": sec_d,
            "claim_meta": sc0,
            "narration": f"In our second international dispatch, attention turns to {sc_prof['capital']}, {sc_prof['name'].title()}: {sec_d['title']}. {polish_journalistic_sentence(sc0['text'], sc_prof, 'BODY')} {polish_journalistic_sentence(sc1['text'], sc_prof, 'BODY')}"
        })

    chapters.append({
        "chapter_num": len(chapters) + 1,
        "chapter_title": f"THE OUTLOOK FOR {c_prof['name']}",
        "role": "PAYOFF",
        "voice_style": "serious",
        "dossier": lead,
        "claim_meta": c3,
        "narration": f"The coming days will prove decisive for {c_prof['capital']} and wider stability across {c_prof['region']}. Share your perspective in the comments and subscribe to World Talk Brief for verified global coverage."
    })

    return chapters

# ==============================================================================
# 5. STRICT COUNTRY-LOCKED VISUAL HARVESTER + ASPECT-RATIO-AWARE INFOGRAPHICS
# ==============================================================================
def validate_and_enhance_1080p(im, existing_hashes, min_w=420, min_h=260):
    im = im.convert("RGB")
    w, h = im.size
    if w < min_w or h < min_h:
        return None

    im = im.crop((int(w * 0.04), int(h * 0.04), int(w * 0.96), int(h * 0.92)))

    arr = np.asarray(im.resize((80, 80)), dtype=np.float32)
    c_box = arr[28:52, 28:52]
    red_px = np.sum((c_box[:, :, 0] > 195) & (c_box[:, :, 1] < 45) & (c_box[:, :, 2] < 45))
    if (red_px / float(24 * 24)) > 0.15:
        return None

    white_px = np.sum((arr[:, :, 0] > 235) & (arr[:, :, 1] > 235) & (arr[:, :, 2] > 235))
    if (white_px / float(80 * 80)) > 0.25:
        return None

    quant = (arr // 32).astype(int)
    flat = quant[:, :, 0] * 64 + quant[:, :, 1] * 8 + quant[:, :, 2]
    _, counts = np.unique(flat, return_counts=True)
    if (counts.max() / float(80 * 80)) > 0.35:
        return None

    gray_cv = cv2.cvtColor(np.array(im.resize((320, 200))), cv2.COLOR_RGB2GRAY)
    blur_score = cv2.Laplacian(gray_cv, cv2.CV_64F).var()
    if blur_score < 32.0 or im.entropy() < 6.4:
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

    im = im.filter(ImageFilter.UnsharpMask(radius=1.5, percent=125, threshold=3))
    im = ImageEnhance.Contrast(im).enhance(1.06)
    return im

def extract_speaker_or_prop_for_beat(beat_text, dossier, entities, beat_idx):
    low = beat_text.lower()
    c_prof = dossier["country_profile"]

    for p_key, (wiki_page, badge_lbl, _) in PERSON_WIKI_MAP.items():
        if re.search(rf"\b{re.escape(p_key)}\b", low):
            return badge_lbl, wiki_page, f"{wiki_page} {c_prof['name']} news", True

    for word_key, (prop_badge, wiki_exact, news_q) in CONCRETE_WIKI_PROPS.items():
        if re.search(rf"\b{re.escape(word_key)}\b", low):
            return prop_badge, wiki_exact, f"{news_q} {c_prof['name']}", False

    chosen_ent = entities[beat_idx % len(entities)]
    return f"DISPATCH • {c_prof['name']}", chosen_ent, f"{dossier['title']} {c_prof['name']}", False

def fetch_verified_news_or_wiki_visual(wiki_exact_title, news_query, dossier, existing_hashes, failed_queries, tag_id="beat"):
    c_prof = dossier["country_profile"]

    for nq in [news_query, dossier["title"], f"{wiki_exact_title} {c_prof['name']}"]:
        try:
            rss_u = f"https://www.bing.com/news/search?q={urllib.parse.quote(nq)}&format=rss"
            r = requests.get(rss_u, headers=HEADERS_WEB, timeout=6)
            for u in re.findall(r"<News:Image>(https?://[^<]+)</News:Image>", r.text)[:10]:
                u_clean = u.replace("&amp;", "&")
                if "bing.com/th" in u_clean:
                    u_clean = u_clean.split("&")[0] + "&w=1920&h=1080&c=7&rs=1"
                ir = requests.get(u_clean, headers=HEADERS_WEB, timeout=6)
                if ir.status_code == 200 and len(ir.content) > 10000:
                    p = f"temp/{tag_id}_bnews.jpg"
                    with open(p, "wb") as f:
                        f.write(ir.content)
                    vim = validate_and_enhance_1080p(Image.open(p), existing_hashes)
                    if vim is not None:
                        return vim
        except Exception:
            pass

    for extra_u in dossier.get("extra_article_imgs", []):
        try:
            ir = requests.get(extra_u, headers=HEADERS_WEB, timeout=5)
            if ir.status_code == 200 and len(ir.content) > 12000:
                p = f"temp/{tag_id}_art.jpg"
                with open(p, "wb") as f:
                    f.write(ir.content)
                vim = validate_and_enhance_1080p(Image.open(p), existing_hashes)
                if vim is not None:
                    return vim
        except Exception:
            pass

    try:
        w_rest = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(wiki_exact_title)}"
        wr = requests.get(w_rest, headers=HEADERS_WIKI, timeout=5).json()
        img_u = wr.get("originalimage", {}).get("source") or wr.get("thumbnail", {}).get("source")
        if img_u and img_u.lower().endswith((".jpg", ".jpeg", ".png")) and not any(b in img_u.lower() for b in ["map", "diagram", "chart", "logo", "flag"]):
            ir = requests.get(img_u, headers=HEADERS_WIKI, timeout=6)
            if ir.status_code == 200 and len(ir.content) > 14000:
                p = f"temp/{tag_id}_wrest.jpg"
                with open(p, "wb") as f:
                    f.write(ir.content)
                vim = validate_and_enhance_1080p(Image.open(p), existing_hashes)
                if vim is not None:
                    return vim
    except Exception:
        pass

    failed_queries.append(news_query)
    return None

def fetch_and_transcode_real_video_broll(wiki_target, country_name, capital_name, tag_id="vclip"):
    queries = [capital_name, country_name, "parliament", "military", "diplomacy", "city traffic", "police"]
    for vq in queries:
        try:
            api = "https://commons.wikimedia.org/w/api.php"
            params = {
                "action": "query", "generator": "search",
                "gsrsearch": f"filetype:video {vq}",
                "gsrnamespace": "6", "gsrlimit": 8,
                "prop": "imageinfo", "iiprop": "url|size", "format": "json"
            }
            r = requests.get(api, params=params, headers=HEADERS_WIKI, timeout=7).json()
            for pg in r.get("query", {}).get("pages", {}).values():
                ii = pg.get("imageinfo", [{}])[0]
                vu = ii.get("url", "")
                vsz = ii.get("size", 99999999)
                if vu.lower().endswith((".webm", ".mp4", ".ogv")) and 40000 < vsz < 15000000:
                    vr = requests.get(vu, headers=HEADERS_WIKI, timeout=14)
                    if vr.status_code == 200 and len(vr.content) > 40000:
                        ext = os.path.splitext(vu.lower())[1]
                        raw_v = f"temp/{tag_id}_raw{ext}"
                        clean_mp4 = f"temp/{tag_id}_clean.mp4"
                        with open(raw_v, "wb") as f:
                            f.write(vr.content)
                        cmd = [
                            "ffmpeg", "-y", "-i", raw_v, "-t", "6",
                            "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1",
                            "-r", "24", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast", clean_mp4
                        ]
                        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=22, check=False)
                        if os.path.exists(clean_mp4) and os.path.getsize(clean_mp4) > 25000:
                            vc = VideoFileClip(clean_mp4)
                            GLOBAL_OPEN_VCLIPS.append(vc)
                            if vc.duration >= 2.2:
                                print("   🎬 [VIDEO B-ROLL LOCKED] 1080p MP4 Clip:", vq, flush=True)
                                return {
                                    "vclip": vc,
                                    "start_t": 0.0,
                                    "label": f"ARCHIVE FOOTAGE • {country_name}"
                                }
        except Exception:
            pass
    return None

def generate_bespoke_speech_infographic_1080p(beat_text, prop_badge, claim_meta, dossier, W=1920, H=1080):
    """
    Fixes the Short video cropped-card bug!
    Builds a native 1080x1920 Vertical Infographic when `W < H` (Short) and 1920x1080 when `W >= H` (Long)
    so text is NEVER cut off at the left/right edges!
    """
    c_prof = dossier["country_profile"]
    canvas = Image.new("RGB", (W, H), (10, 16, 28))
    draw = ImageDraw.Draw(canvas, "RGBA")

    for x in range(0, W, 80):
        draw.line([(x, 0), (x, H)], fill=(0, 210, 255, 22), width=1)
    for y in range(0, H, 80):
        draw.line([(0, y), (W, y)], fill=(0, 210, 255, 22), width=1)

    key_nums = re.findall(r"(\$?\d+(?:,\d+)*(?:\.\d+)?\s*(?:%|million|billion|trillion|years|days|hours|km|troops|dead|injured)?)", beat_text, re.I)
    stat_str = key_nums[0].strip().upper() if (key_nums and len(key_nums[0].strip()) >= 2) else c_prof["name"]

    if W < H:
        # 9:16 Vertical Layout (fits inside x=60..1020 so zero horizontal clipping!)
        draw.rounded_rectangle([(60, 260), (W - 60, 1180)], radius=20, fill=(14, 24, 42, 242), outline=(255, 214, 10, 220), width=4)
        draw.rounded_rectangle([(95, 305), (W - 95, 365)], radius=8, fill=(204, 18, 36, 255))
        draw.text((115, 318), prop_badge[:30], fill=(255, 255, 255, 255), font=get_font(26))
        draw.text((95, 405), f"KEY DATA: {stat_str[:18]}", fill=(255, 214, 10, 255), font=get_font(42))
        f_body = get_font(34)
        for l_i, ln in enumerate(wrap_lines(draw, f'"{beat_text}"', f_body, W - 200)[:6]):
            draw.text((95, 495 + l_i * 52), ln, fill=(245, 248, 255, 255), font=f_body)
        draw.text((95, 1105), f"VERIFIED DISPATCH • {claim_meta['published_date']}", fill=(0, 210, 255, 255), font=get_font(22))
    else:
        draw.rounded_rectangle([(160, 150), (1760, 680)], radius=20, fill=(14, 24, 42, 240), outline=(255, 214, 10, 220), width=4)
        draw.rounded_rectangle([(200, 185), (680, 240)], radius=8, fill=(204, 18, 36, 255))
        draw.text((224, 198), prop_badge[:32], fill=(255, 255, 255, 255), font=get_font(26))
        draw.text((200, 270), f"KEY FOCUS: {stat_str}", fill=(255, 214, 10, 255), font=get_font(48))
        f_body = get_font(38)
        for l_i, ln in enumerate(wrap_lines(draw, f'"{beat_text}"', f_body, 1480)[:3]):
            draw.text((200, 355 + l_i * 54), ln, fill=(245, 248, 255, 255), font=f_body)
        draw.text((200, 615), f"VERIFIED INTERNATIONAL DISPATCH  •  PUBLISHED: {claim_meta['published_date']}", fill=(0, 210, 255, 255), font=get_font(22))
    return canvas

# ==============================================================================
# 6. TRUE FULL-HEIGHT 1080p FRAMING
# ==============================================================================
def has_well_framed_face(im):
    if FACE_CASCADE is None:
        return False
    try:
        iw, ih = im.size
        sw = 480
        sh = max(int(ih * (480.0 / iw)), 270)
        gray_s = cv2.cvtColor(np.array(im.resize((sw, sh))), cv2.COLOR_RGB2GRAY)
        faces = FACE_CASCADE.detectMultiScale(gray_s, scaleFactor=1.12, minNeighbors=5, minSize=(40, 40))
        for (fx, fy, fw, fh) in faces:
            if fx > sw * 0.05 and (fx + fw) < sw * 0.95 and fy > sh * 0.05 and (fy + fh) < sh * 0.92 and fh < sh * 0.60:
                return True
    except Exception:
        pass
    return False

def fit_full_height_face_aware_1080p(im, target_w, target_h):
    resample_mode = getattr(Image, "Resampling", Image).LANCZOS
    iw, ih = im.size
    target_ratio = target_w / float(target_h)
    img_ratio = iw / float(ih)

    faces = []
    if FACE_CASCADE is not None:
        try:
            sw = 500
            sh = max(int(ih * (500.0 / iw)), 280)
            gray_s = cv2.cvtColor(np.array(im.resize((sw, sh))), cv2.COLOR_RGB2GRAY)
            raw_faces = FACE_CASCADE.detectMultiScale(gray_s, scaleFactor=1.12, minNeighbors=5, minSize=(36, 36))
            scale_x, scale_y = iw / float(sw), ih / float(sh)
            for (fx, fy, fw, fh) in raw_faces:
                faces.append((int(fx * scale_x), int(fy * scale_y), int(fw * scale_x), int(fh * scale_y)))
        except Exception:
            faces = []

    if img_ratio >= target_ratio:
        crop_h = ih
        crop_w = int(ih * target_ratio)
        if faces:
            fx_center = sum(f[0] + f[2] // 2 for f in faces) // len(faces)
            left = max(0, min(iw - crop_w, fx_center - crop_w // 2))
        else:
            left = (iw - crop_w) // 2
        cropped = im.crop((left, 0, left + crop_w, crop_h))
        return cropped.resize((target_w, target_h), resample_mode)

    crop_w = iw
    crop_h = int(iw / target_ratio)
    if faces:
        min_y = min(f[1] for f in faces)
        max_y = max(f[1] + f[3] for f in faces)
        face_span_h = max_y - min_y
        if face_span_h * 1.85 <= crop_h:
            desired_top = min_y - int(face_span_h * 0.45)
            top = max(0, min(ih - crop_h, desired_top))
            cropped = im.crop((0, top, crop_w, top + crop_h))
            return cropped.resize((target_w, target_h), resample_mode)
    else:
        top = int((ih - crop_h) * 0.22)
        cropped = im.crop((0, top, crop_w, top + crop_h))
        return cropped.resize((target_w, target_h), resample_mode)

    bg = im.copy().resize((target_w, target_h), resample_mode).filter(ImageFilter.GaussianBlur(radius=32))
    bg = ImageEnhance.Brightness(bg).enhance(0.35)
    fit_h = target_h
    fit_w = max(1, int(iw * (target_h / float(ih))))
    fg = im.resize((fit_w, fit_h), resample_mode)
    bg.paste(fg, ((target_w - fit_w) // 2, 0))
    return bg

def build_clean_1080p_stage(im, W, H):
    resample_mode = getattr(Image, "Resampling", Image).LANCZOS
    if W < H:
        bg = im.copy().resize((W, H), resample_mode).filter(ImageFilter.GaussianBlur(radius=30))
        bg = ImageEnhance.Brightness(bg).enhance(0.32)
        canvas = bg.convert("RGBA")

        hero_w, hero_h = int(W * 1.05), 1360
        fg = fit_full_height_face_aware_1080p(im, hero_w, hero_h)
        return ("SHORT_STAGE", canvas, fg)
    else:
        over_w, over_h = int(W * 1.05), int(H * 1.05)
        fg = fit_full_height_face_aware_1080p(im, over_w, over_h)
        return ("FULL_BLEED_STAGE", fg, None)

def extract_animated_frame_from_stage(stage_tuple, W, H, bp, pan_dir=1):
    mode_tag, base_a, base_b = stage_tuple
    if mode_tag == "SHORT_STAGE":
        canvas = base_a.copy()
        fg = base_b
        fw, fh = fg.size
        win_w, win_h = W, 1340
        max_dx = max(fw - win_w, 0)
        max_dy = max(fh - win_h, 0)
        ox = int(max_dx * (bp if pan_dir == 1 else (1.0 - bp)))
        oy = int(max_dy * 0.5)
        slice_fg = fg.crop((ox, oy, ox + win_w, oy + win_h))
        canvas.paste(slice_fg, (0, 120))

        draw = ImageDraw.Draw(canvas, "RGBA")
        for y in range(1460, H):
            draw.line([(0, y), (W, y)], fill=(6, 9, 18, int(235 * min(1.0, (y - 1460) / 180.0))))
        draw.line([(0, 120), (W, 120)], fill=(255, 214, 10, 220), width=3)
        draw.line([(0, 1460), (W, 1460)], fill=(255, 214, 10, 220), width=3)
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
        for y in range(H - 260, H):
            draw.line([(0, y), (W, y)], fill=(4, 7, 14, int(215 * ((y - (H - 260)) / 260.0) ** 1.2)))
        return frame

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
        map_img = ImageEnhance.Brightness(map_img).enhance(0.68)
    return map_img

# ==============================================================================
# 7. NATURAL SENTENCE-PACED STORYBOARD (4.8s - 5.5s Beats)
# ==============================================================================
def has_strict_economic_context(text):
    low = text.lower()
    if any(prison_w in low for prison_w in ["jailed", "prison", "sentenced", "murder", "killed", "court", "police"]):
        return False
    if re.search(r"\b(\d+(\.\d+)?%|\$\d+|\d+\s*(billion|trillion))\b", low):
        return True
    econ_terms = ["gdp", "inflation", "economy", "economic", "market", "trade", "tariff", "cost", "budget", "growth", "debt", "financial", "bank"]
    return any(re.search(rf"\b{re.escape(t)}\b", low) for t in econ_terms)

def build_prop_driven_storyboard_1080p(sections_list, dossier, entities, W, H, tag_prefix="short"):
    planned_beats = []
    existing_hashes = []
    unique_real_photos = []
    failed_queries = []
    reused_photo_beats = 0
    map_beats = 0
    moving_video_beats = 0
    generated_infographic_beats = 0

    c_prof = dossier["country_profile"]
    osm_map = build_real_openstreetmap_1080p(c_prof, zoom=5, W=1920, H=1080)
    osm_stage = build_clean_1080p_stage(osm_map, W, H)

    story_vclip_1 = fetch_and_transcode_real_video_broll(entities[0], c_prof["name"], c_prof["capital"], tag_id=f"{tag_prefix}_vc1")

    if dossier.get("lead_img") and not any(b in dossier["lead_img"].lower() for b in BANNED_IMAGE_SOURCES):
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

    map_used_in_video = False
    global_beat_idx = 0

    for sec_idx, sec in enumerate(sections_list):
        narration = sec["narration"]
        sec_dur = sec["duration"]
        word_timings = sec["word_timings"]
        sec_role = sec.get("role", "BODY")
        sec_headline = sec.get("headline") or sec.get("chapter_title") or make_clean_context_headline(dossier["title"])
        claim_meta = sec.get("claim_meta") or dossier["verified_claims"][0]

        target_beat_len = 4.8 if W < H else 5.4
        num_beats = max(2, int(round(sec_dur / target_beat_len)))
        beat_dur = sec_dur / float(num_beats)
        words = narration.split()
        w_per_b = max(1, int(math.ceil(len(words) / float(num_beats))))
        used_modes_in_sec = set()

        for b_i in range(num_beats):
            b_txt = " ".join(words[b_i * w_per_b:(b_i + 1) * w_per_b]) or narration
            prop_badge, wiki_target, search_q, is_person = extract_speaker_or_prop_for_beat(b_txt, dossier, entities, global_beat_idx)
            low_b = b_txt.lower()

            if not map_used_in_video and (sec_role == "GEOGRAPHY" or re.search(r"\b(geography|corridor|neighboring borders|centered around)\b", low_b)):
                b_type = "MAP_LOCATOR_BEAT"
                map_used_in_video = True
                map_beats += 1
                beat_im = osm_map
                vseg = None
                stage_1 = osm_stage
            else:
                vseg = None
                if not is_person and story_vclip_1 is not None and moving_video_beats == 0 and global_beat_idx >= 1:
                    vseg = story_vclip_1

                if vseg is not None:
                    b_type = "VIDEO_BROLL_BEAT"
                    moving_video_beats += 1
                    beat_im = unique_real_photos[-1] if unique_real_photos else osm_map
                    stage_1 = build_clean_1080p_stage(beat_im, W, H)
                else:
                    if global_beat_idx == 0 and unique_real_photos:
                        beat_im = unique_real_photos[0]
                    else:
                        beat_im = fetch_verified_news_or_wiki_visual(
                            wiki_target, search_q, dossier, existing_hashes, failed_queries, tag_id=f"{tag_prefix}_b{global_beat_idx}"
                        )
                        if beat_im is not None:
                            unique_real_photos.append(beat_im)
                        else:
                            beat_im = generate_bespoke_speech_infographic_1080p(b_txt, prop_badge, claim_meta, dossier, W=W, H=H)
                            generated_infographic_beats += 1

                    if has_strict_economic_context(b_txt) and dossier.get("wb_data") is not None and "DATA_CHART_BEAT" not in used_modes_in_sec:
                        b_type = "DATA_CHART_BEAT"
                    elif re.search(r"\b(timeline|overnight|step by step|previously|september|october|days before)\b", low_b) and "TIMELINE_GRAPH_BEAT" not in used_modes_in_sec:
                        b_type = "TIMELINE_GRAPH_BEAT"
                    elif re.search(r"\b(said|stated|confirmed|record|specifics|told|claim|claims)\b", low_b) and "HEADLINE_EVIDENCE_BEAT" not in used_modes_in_sec:
                        b_type = "HEADLINE_EVIDENCE_BEAT"
                    elif re.search(r"\b(competing|colliding|whether|or if|versus|row with)\b", low_b) and "SPLIT_COMPARE_BEAT" not in used_modes_in_sec and len(unique_real_photos) >= 2:
                        b_type = "SPLIT_COMPARE_BEAT"
                    else:
                        b_type = "PHOTO_BEAT"

                    stage_1 = build_clean_1080p_stage(beat_im, W, H)

            used_modes_in_sec.add(b_type)
            secondary_im = unique_real_photos[(len(unique_real_photos) - 2) % len(unique_real_photos)] if len(unique_real_photos) >= 2 else beat_im

            planned_beats.append({
                "section_idx": sec_idx,
                "beat_in_section": b_i,
                "beat_type": b_type,
                "pan_dir": 1 if (global_beat_idx % 2 == 0) else -1,
                "duration": round(beat_dur, 3),
                "beat_excerpt": b_txt,
                "section_headline": sec_headline,
                "full_section_narration": narration,
                "word_timings": word_timings,
                "section_duration": sec_dur,
                "section_elapsed_before": round(b_i * beat_dur, 3),
                "stage_1": stage_1,
                "primary_im": beat_im,
                "primary_lbl": prop_badge,
                "secondary_im": secondary_im,
                "vseg": vseg,
                "claim_meta": claim_meta,
                "story": dossier
            })
            global_beat_idx += 1

    min_expected_photos = min(6, max(3, int(len(planned_beats) * 0.45)))
    run_status = "PASS"
    if len(unique_real_photos) < min_expected_photos or reused_photo_beats > 2:
        run_status = "WARNING: QUALITY_REVIEW_REQUIRED (LOW_UNIQUE_PHOTOS)"

    stats = {
        "run_status": run_status,
        "total_beats": len(planned_beats),
        "unique_real_photos": len(unique_real_photos),
        "moving_video_beats": moving_video_beats,
        "generated_infographic_beats": generated_infographic_beats,
        "reused_photo_beats": reused_photo_beats,
        "map_beats": map_beats,
        "failed_queries_count": len(failed_queries),
        "failed_queries": failed_queries[:15]
    }
    print("📊 [AUDIT]", tag_prefix.upper(), "| Status:", run_status, "| Beats:", stats["total_beats"], "| Unique Photos:", stats["unique_real_photos"], "| Moving Video:", stats["moving_video_beats"], flush=True)
    return planned_beats, unique_real_photos, stats

def render_1080p_beat_frame(beat, watermark, voice_sub_dir, local_t, W, H, is_short=True):
    beat_dur = beat["duration"]
    bp = min(max(local_t / max(beat_dur, 0.1), 0.0), 1.0)
    b_type = beat["beat_type"]
    story = beat["story"]
    c_prof = story["country_profile"]
    claim_meta = beat["claim_meta"]
    section_t = beat["section_elapsed_before"] + local_t

    if b_type == "VIDEO_BROLL_BEAT" and beat.get("vseg") is not None:
        vseg = beat["vseg"]
        vc = vseg["vclip"]
        try:
            t_vid = (vseg["start_t"] + local_t) % max(vc.duration - 0.1, 1.0)
            raw_vf = Image.fromarray(vc.get_frame(t_vid)).convert("RGB")
            st_v = build_clean_1080p_stage(raw_vf, W, H)
            frame = extract_animated_frame_from_stage(st_v, W, H, bp, pan_dir=1)
        except Exception:
            frame = extract_animated_frame_from_stage(beat["stage_1"], W, H, bp, pan_dir=beat["pan_dir"])
        draw = ImageDraw.Draw(frame, "RGBA")
    elif b_type == "SPLIT_COMPARE_BEAT":
        frame = Image.new("RGBA", (W, H), (8, 12, 22, 255))
        if is_short:
            top_im = fit_full_height_face_aware_1080p(beat["primary_im"], W, 665)
            bot_im = fit_full_height_face_aware_1080p(beat["secondary_im"], W, 665)
            frame.paste(top_im, (0, 120))
            frame.paste(bot_im, (0, 790))
            draw = ImageDraw.Draw(frame, "RGBA")
            draw.line([(0, 787), (W, 787)], fill=(255, 214, 10, 255), width=6)
        else:
            left_im = fit_full_height_face_aware_1080p(beat["primary_im"], W // 2, H)
            right_im = fit_full_height_face_aware_1080p(beat["secondary_im"], W // 2, H)
            frame.paste(left_im, (0, 0))
            frame.paste(right_im, (W // 2, 0))
            draw = ImageDraw.Draw(frame, "RGBA")
            draw.line([(W // 2, 0), (W // 2, H)], fill=(255, 214, 10, 255), width=6)
            for y in range(H - 260, H):
                draw.line([(0, y), (W, y)], fill=(4, 7, 14, int(215 * ((y - (H - 260)) / 260.0) ** 1.2)))
    else:
        frame = extract_animated_frame_from_stage(beat["stage_1"], W, H, bp, pan_dir=beat["pan_dir"])
        draw = ImageDraw.Draw(frame, "RGBA")

    cy_card = 1475 if is_short else (H - 305)
    bx1, bx2 = (42, W - 42) if is_short else (56, 1260)

    # Brand-Safe Verification Footer on Video Card (No third-party URLs on screen; full URL stays in YouTube Description!)
    citation_str = f"WORLD TALK BRIEF VERIFIED DISPATCH • {c_prof['capital'].upper()} • {claim_meta['published_date']}"

    if b_type in ["PHOTO_BEAT", "VIDEO_BROLL_BEAT"]:
        kicker = beat["vseg"]["label"] if (b_type == "VIDEO_BROLL_BEAT" and beat.get("vseg")) else beat["primary_lbl"]
        hl = str(beat["section_headline"]).upper()
        f_k = get_font(21)
        f_h = get_font(28 if is_short else 30)
        kw = draw.textbbox((0, 0), kicker, font=f_k)[2] + 34

        draw.rounded_rectangle([(bx1, cy_card), (bx2, cy_card + 158)], radius=12, fill=(10, 16, 28, 222), outline=(255, 214, 10, 215), width=2)
        draw.rounded_rectangle([(bx1 + 18, cy_card + 14), (bx1 + 18 + kw, cy_card + 48)], radius=6, fill=(204, 18, 36, 255))
        draw.text((bx1 + 34, cy_card + 19), kicker, fill=(255, 255, 255, 255), font=f_k)
        for i_l, ln in enumerate(wrap_lines(draw, hl, f_h, (bx2 - bx1) - 48)[:2]):
            draw.text((bx1 + 22, cy_card + 56 + i_l * 34), ln, fill=(255, 255, 255, 255), font=f_h)
        draw.text((bx1 + 22, cy_card + 128), citation_str[:78], fill=(0, 210, 255, 235), font=get_font(17))

    elif b_type == "MAP_LOCATOR_BEAT":
        cx, cy = (W // 2, 720) if is_short else (W // 2 - 120, H // 2 - 45)
        for ri in range(3):
            rp = ((local_t * 0.8) + ri * 0.33) % 1.0
            rad = int(36 + rp * 210)
            draw.ellipse([(cx - rad, cy - rad), (cx + rad, cy + rad)], outline=(255, 45, 45, int(235 * (1.0 - rp))), width=4)
        draw.ellipse([(cx - 14, cy - 14), (cx + 14, cy + 14)], fill=(255, 214, 10, 255))

        pip_w, pip_h = (340, 220) if is_short else (430, 270)
        px, py = (W - pip_w - 42, 160) if is_short else (W - pip_w - 64, 120)
        pip_im = fit_full_height_face_aware_1080p(beat["secondary_im"], pip_w, pip_h)
        draw.line([(cx, cy), (px + pip_w // 2, py + pip_h)], fill=(255, 214, 10, 220), width=3)
        frame.paste(pip_im, (px, py))
        draw.rounded_rectangle([(px - 3, py - 3), (px + pip_w + 3, py + pip_h + 3)], radius=8, outline=(255, 214, 10, 255), width=4)

        draw.rounded_rectangle([(bx1, cy_card), (bx2, cy_card + 158)], radius=12, fill=(10, 16, 28, 232), outline=(0, 210, 255, 225), width=2)
        draw.text((bx1 + 24, cy_card + 16), f"GEOGRAPHIC CORRIDOR  •  LAT {c_prof['lat']}° LON {c_prof['lon']}°", fill=(0, 210, 255, 255), font=get_font(22))
        draw.text((bx1 + 24, cy_card + 54), f"EPICENTER: {c_prof['capital'].upper()}, {c_prof['name']} (POP: {c_prof['population']})", fill=(255, 214, 10, 255), font=get_font(29))
        draw.text((bx1 + 24, cy_card + 124), citation_str[:78], fill=(215, 230, 250, 235), font=get_font(17))

    elif b_type == "HEADLINE_EVIDENCE_BEAT":
        draw.rounded_rectangle([(bx1, cy_card), (bx2, cy_card + 162)], radius=14, fill=(246, 244, 236, 244), outline=(204, 18, 36, 255), width=3)
        draw.rounded_rectangle([(bx1 + 22, cy_card + 10), (bx1 + 520, cy_card + 42)], radius=6, fill=(204, 18, 36, 255))
        draw.text((bx1 + 36, cy_card + 14), f"OFFICIAL RECORD • {claim_meta['published_date']}", fill=(255, 255, 255, 255), font=get_font(20))

        hl_txt = claim_meta["text"]
        f_q = get_font(26 if is_short else 28)
        lines = wrap_lines(draw, hl_txt, f_q, (bx2 - bx1) - 56)[:2]
        hl_w = int(((bx2 - bx1) - 60) * min(bp * 1.4, 1.0))
        draw.rounded_rectangle([(bx1 + 22, cy_card + 50), (bx1 + 22 + hl_w, cy_card + 86)], radius=6, fill=(255, 232, 65, 240))
        for idx_l, ln in enumerate(lines):
            draw.text((bx1 + 28, cy_card + 52 + idx_l * 36), ln, fill=(12, 16, 22, 255), font=f_q)
        draw.text((bx1 + 28, cy_card + 130), citation_str[:74], fill=(80, 90, 110, 255), font=get_font(17))

    elif b_type == "TIMELINE_GRAPH_BEAT":
        draw.rounded_rectangle([(bx1, cy_card - 8), (bx2, cy_card + 164)], radius=14, fill=(10, 16, 28, 236), outline=(255, 214, 10, 225), width=2)
        steps = [
            ("BUILDUP", f"Mounting pressure across {c_prof['region']}"),
            ("CATALYST", f"Key policy decision in {c_prof['capital']}"),
            ("NOW", story["title"][:44])
        ]
        sy = cy_card + 6
        for idx_s, (slbl, stxt) in enumerate(steps):
            act = (bp >= idx_s * 0.28)
            bg_c = (204, 18, 36, 255) if act else (35, 45, 65, 210)
            draw.rounded_rectangle([(bx1 + 22, sy), (bx1 + 165, sy + 38)], radius=6, fill=bg_c)
            draw.text((bx1 + 32, sy + 7), slbl, fill=(255, 255, 255, 255), font=get_font(20))
            draw.text((bx1 + 182, sy + 6), stxt[:42], fill=(255, 255, 255, 255) if act else (160, 170, 185, 210), font=get_font(23))
            sy += 50

    elif b_type == "DATA_CHART_BEAT" and story.get("wb_data") is not None:
        wb_years, wb_vals = story["wb_data"]
        draw.rounded_rectangle([(bx1, cy_card - 25), (bx2, cy_card + 165)], radius=14, fill=(10, 16, 28, 240), outline=(255, 214, 10, 230), width=2)
        draw.text((bx1 + 26, cy_card - 10), f"{c_prof['name']} VERIFIED GDP GROWTH (%)  •  WORLD BANK OPEN DATA", fill=(255, 214, 10, 255), font=get_font(22))
        anim_p = min(bp * 1.35, 1.0)
        n_bars = len(wb_years)
        slot_w = ((bx2 - bx1) - 90) // max(n_bars, 1)
        max_v = max(max(abs(v) for v in wb_vals), 1.0)
        for b_i, (yr, val) in enumerate(zip(wb_years, wb_vals)):
            bx = bx1 + 48 + b_i * slot_w
            bh = max(int(75 * (abs(val) / max_v) * anim_p), 10)
            b_top = cy_card + 115 - bh
            b_col = (255, 214, 10, 255) if val >= 0 else (204, 18, 36, 255)
            draw.rounded_rectangle([(bx, b_top), (bx + slot_w - 42, cy_card + 115)], radius=5, fill=b_col)
            draw.text((bx + 6, b_top - 26), f"{round(val * anim_p, 1)}%", fill=(255, 255, 255, 255), font=get_font(20))
            draw.text((bx + 8, cy_card + 124), yr, fill=(200, 215, 235, 255), font=get_font(20))

    else:
        mid_x = (bx1 + bx2) // 2
        draw.rounded_rectangle([(bx1, cy_card), (mid_x - 10, cy_card + 145)], radius=12, fill=(10, 18, 32, 235), outline=(0, 210, 255, 230), width=2)
        draw.text((bx1 + 22, cy_card + 18), "CALCULATION A", fill=(0, 210, 255, 255), font=get_font(22))
        draw.text((bx1 + 22, cy_card + 62), "STRATEGIC LEVERAGE", fill=(255, 255, 255, 255), font=get_font(25))

        draw.rounded_rectangle([(mid_x + 10, cy_card), (bx2, cy_card + 145)], radius=12, fill=(10, 18, 32, 235), outline=(255, 214, 10, 230), width=2)
        draw.text((mid_x + 32, cy_card + 18), "CALCULATION B", fill=(255, 214, 10, 255), font=get_font(22))
        draw.text((mid_x + 32, cy_card + 62), "ESCALATION RISK", fill=(255, 255, 255, 255), font=get_font(25))

    top_y = 28 if is_short else 32
    frame.paste(watermark, (42, top_y), watermark)
    if c_prof.get("flag_img"):
        fl = c_prof["flag_img"].resize((84, 54))
        frame.paste(fl, (198, top_y + 14), fl)

    if is_short and beat["section_idx"] == 0 and beat["beat_in_section"] == 0 and local_t < 0.35:
        draw.rounded_rectangle([(42, 740), (W - 42, 915)], radius=16, fill=(204, 18, 36, 242), outline=(255, 214, 10, 255), width=4)
        f_cov = get_font(44)
        for ci, cln in enumerate(wrap_lines(draw, story["title"].upper(), f_cov, W - 120)[:2]):
            draw.text((68, 765 + ci * 58), cln, fill=(255, 255, 255, 255), font=f_cov)

    sub_strip = voice_sub_dir.render_exact_synced_subtitles(beat["word_timings"], section_t, W, H, is_short=is_short)
    sub_y = 1655 if is_short else (H - 128)
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

# ==============================================================================
# 8. VOICE, SUBTITLES & SOFT 4.2% DOCUMENTARY BACKGROUND SCORE
# ==============================================================================
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

        strip_h = 210 if is_short else 120
        strip = Image.new("RGBA", (W, strip_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(strip, "RGBA")
        font = get_font(52 if is_short else 40)
        words_str_list = [w["word"] for w in active_chunk]

        if is_short:
            lines = [words_str_list[:2], words_str_list[2:]] if len(words_str_list) > 2 else [words_str_list]
            y_cur = 12
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
                y_cur += 70
        else:
            phrase = " ".join(words_str_list)
            lw = draw.textbbox((0, 0), phrase, font=font)[2]
            bx1, bx2 = max((W - lw) // 2 - 30, 30), min((W + lw) // 2 + 30, W - 30)
            draw.rounded_rectangle([(bx1, 10), (bx2, 92)], radius=12, fill=(6, 9, 16, 232), outline=(255, 214, 10, 105), width=2)
            x_cur = (W - lw) // 2
            for idx_w, w in enumerate(words_str_list):
                col = (255, 214, 10, 255) if idx_w == active_word_idx else (255, 255, 255, 255)
                draw.text((x_cur, 25), w, font=font, fill=col, stroke_width=3, stroke_fill=(0, 0, 0, 240))
                x_cur += draw.textbbox((0, 0), w + " ", font=font)[2]
        return strip

def build_situation_adaptive_soft_soundtrack(filename, duration, beat_switch_times, category="geopolitics_diplomacy"):
    sr = 22050
    n_samples = int(sr * duration)
    t = np.linspace(0, duration, n_samples, endpoint=False)

    if category == "war_crisis":
        f1, f2, f3, tempo = 110.0, 164.81, 220.0, 0.75
    elif category == "ai_tech_science":
        f1, f2, f3, tempo = 146.83, 220.0, 293.66, 0.65
    elif category == "economy_markets":
        f1, f2, f3, tempo = 123.47, 185.0, 246.94, 0.70
    elif category == "environment_climate":
        f1, f2, f3, tempo = 130.81, 196.0, 261.63, 0.85
    else:
        f1, f2, f3, tempo = 98.0, 146.83, 196.0, 0.80

    chords = (
        0.45 * np.sin(2 * np.pi * f1 * t)
        + 0.30 * np.sin(2 * np.pi * f2 * t)
        + 0.18 * np.sin(2 * np.pi * f3 * t)
    )
    lfo = 0.75 + 0.25 * np.sin(2 * np.pi * 0.16 * t)
    beat_phase = t % tempo
    pulse = 0.20 * np.sin(2 * np.pi * f2 * beat_phase) * np.exp(-beat_phase * 8.0)

    raw_music = (chords * lfo) + pulse
    max_amp = max(float(np.max(np.abs(raw_music))), 1e-4)
    audio = (raw_music / max_amp) * 0.042

    for bt in beat_switch_times:
        idx = int(bt * sr)
        if idx < n_samples:
            slen = min(int(0.20 * sr), n_samples - idx)
            st_t = np.linspace(0, slen / float(sr), slen, endpoint=False)
            sfx = 0.038 * np.sin(2 * np.pi * (240 - 110 * st_t) * st_t) * np.exp(-st_t * 14.0)
            audio[idx:idx + slen] += sfx

    audio_int16 = np.int16(np.clip(audio, -1.0, 1.0) * 32767)
    with wave.open(filename, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(audio_int16.tobytes())
    return filename

def create_category_adaptive_1080p_thumbnail(dossier, entities, unique_photos, watermark, out_path="output/WTB_1080p_Thumb_1.jpg"):
    W, H = 1920, 1080
    c_prof = dossier["country_profile"]
    cat = dossier.get("category", "geopolitics_diplomacy")
    ent_main = entities[0].upper() if entities else c_prof["name"]

    chosen_thumb_im = None
    for cand_im in unique_photos:
        if has_well_framed_face(cand_im):
            chosen_thumb_im = cand_im
            break
    if chosen_thumb_im is None:
        chosen_thumb_im = unique_photos[0] if unique_photos else build_real_openstreetmap_1080p(c_prof, zoom=5, W=1920, H=1080)

    theme_palettes = {
        "ai_tech_science": ((8, 18, 38), (0, 210, 255), (255, 214, 10), "TECH & AI SHIFT"),
        "economy_markets": ((8, 26, 22), (16, 185, 129), (255, 214, 10), "MARKET SHOCKWAVE"),
        "environment_climate": ((10, 28, 32), (34, 197, 94), (255, 220, 40), "PLANETARY ALERT"),
        "war_crisis": ((16, 10, 18), (220, 38, 38), (255, 214, 10), "CRISIS BRIEFING"),
        "geopolitics_diplomacy": ((10, 14, 28), (37, 99, 235), (255, 214, 10), "STRATEGIC PIVOT")
    }
    bg_col, badge_col, box_col, sub_hook = theme_palettes.get(cat, theme_palettes["geopolitics_diplomacy"])

    canvas = Image.new("RGBA", (W, H), bg_col + (255,))
    right_stage = fit_full_height_face_aware_1080p(chosen_thumb_im, 1160, H)
    right_stage = ImageEnhance.Contrast(right_stage).enhance(1.14)
    canvas.paste(right_stage, (760, 0))

    draw = ImageDraw.Draw(canvas, "RGBA")
    for x in range(0, 920):
        if x < 740:
            alpha = 255
        else:
            alpha = int(255 * (1.0 - (x - 740) / 180.0))
        draw.line([(x, 0), (x, H)], fill=(bg_col[0], bg_col[1], bg_col[2], alpha))

    canvas.paste(watermark, (64, 54), watermark)
    if c_prof.get("flag_img"):
        fl = c_prof["flag_img"].resize((110, 70))
        canvas.paste(fl, (220, 60), fl)

    kick1 = f"{c_prof['name']} • {cat.replace('_', ' ').upper()}"
    f_k = get_font(30)
    kw1 = draw.textbbox((0, 0), kick1, font=f_k)[2] + 48
    draw.rounded_rectangle([(64, 310), (64 + kw1, 380)], radius=12, fill=badge_col + (255,))
    draw.text((88, 326), kick1, fill=(255, 255, 255, 255), font=f_k)

    h1_a = f"{ent_main[:15]}"
    h1_b = sub_hook
    fb = get_font(78)
    draw.text((64, 420), h1_a, fill=(255, 255, 255, 255), font=fb, stroke_width=5, stroke_fill=(0, 0, 0, 255))
    w2 = draw.textbbox((0, 0), h1_b, font=fb)[2] + 64
    draw.rounded_rectangle([(64, 545), (64 + w2, 675)], radius=16, fill=box_col + (255,))
    draw.text((96, 565), h1_b, fill=(10, 12, 18, 255), font=fb)

    canvas.convert("RGB").save(out_path, quality=96)

    raw_t = dossier["title"]
    if len(raw_t) <= 78:
        selected_title = f"{raw_t} | {c_prof['name'].title()} Briefing"
    else:
        selected_title = raw_t[:95]

    return {
        "selected_thumbnail": out_path,
        "thumbnail_category_style": cat,
        "selected_title": selected_title,
        "hashtags": ["#WorldTalkBrief", f"#{c_prof['name'].replace(' ', '')}", "#Geopolitics", "#WorldNews"]
    }

create_1080p_thumbnails = create_category_adaptive_1080p_thumbnail

# ==============================================================================
# 9. MULTI-TOKEN YOUTUBE API UPLOADER (Supports up to 4 Tokens = 24 Videos/Day!)
# ==============================================================================
def try_youtube_auto_upload(video_path, title, description, tags, is_short=False, thumbnail_path=None):
    token_envs = ["YOUTUBE_TOKEN_JSON_B64", "YOUTUBE_TOKEN_2_B64", "YOUTUBE_TOKEN_3_B64", "YOUTUBE_TOKEN_4_B64"]
    available_tokens = [os.environ.get(k, "").strip() for k in token_envs if os.environ.get(k, "").strip()]

    if not available_tokens:
        print("ℹ️ [GitHub Cloud Test Mode] No YouTube API token set yet; saved to GitHub Artifacts:", video_path, flush=True)
        return None

    for t_idx, token_b64 in enumerate(available_tokens):
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload

            t_file = f"temp/token_{t_idx}.json"
            with open(t_file, "wb") as tf:
                tf.write(base64.b64decode(token_b64))
            creds = Credentials.from_authorized_user_file(t_file, ["https://www.googleapis.com/auth/youtube.upload"])
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            yt = build("youtube", "v3", credentials=creds)

            final_title = (title[:90] + " #Shorts") if is_short and "#shorts" not in title.lower() else title[:100]
            body = {
                "snippet": {"title": final_title, "description": description, "tags": tags[:25], "categoryId": "25"},
                "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
            }
            media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/mp4")
            req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
            resp = None
            while resp is None:
                _, resp = req.next_chunk()
            vid_id = resp["id"]
            print(f"✅ [YOUTUBE LIVE UPLOAD SUCCESS - Token #{t_idx+1}] https://youtu.be/{vid_id}", flush=True)
            if thumbnail_path and os.path.exists(thumbnail_path):
                try:
                    yt.thumbnails().set(videoId=vid_id, media_body=MediaFileUpload(thumbnail_path)).execute()
                except Exception as te:
                    print("⚠️ Thumbnail set warning:", te, flush=True)
            return vid_id
        except Exception as e:
            err_str = str(e)
            print(f"⚠️ Token #{t_idx+1} upload attempt failed:", err_str[:120], flush=True)
            if "quotaExceeded" in err_str and t_idx + 1 < len(available_tokens):
                print(f"🔄 Switching to backup YouTube API Token #{t_idx+2}...", flush=True)
                continue
            break
    return None

# ==============================================================================
# MASTER EXECUTION (Strict Chronological Chapters + Multi-Source Diversity)
# ==============================================================================
async def main():
    try:
        watermark = build_wtb_watermark(width=140, height=82)
        voice_sub_dir = VoiceAndSubtitleEngine()
        hist_obj = load_published_history()
        winning_keywords = fetch_channel_winning_keywords()

        dossiers = discover_and_build_dossiers(hist_obj, winning_keywords)
        if len(dossiers) < 2:
            hist_obj["published_keys"].clear()
            hist_obj["event_fingerprints"].clear()
            dossiers = discover_and_build_dossiers(hist_obj, winning_keywords)

        lead_long_dossier = dossiers[0]
        short_dossier = next((d for d in dossiers[1:] if d["source_name"] != lead_long_dossier["source_name"]), dossiers[1])
        sec_long_dossier = next((d for d in dossiers[1:] if d["title"] != short_dossier["title"]), None)
        long_dossiers = [lead_long_dossier, sec_long_dossier] if sec_long_dossier else [lead_long_dossier]

        # 1. BUILD 1080p SHORT
        print("\n📱 [2/6] Building 1080p Short (1080x1920) on:", short_dossier["title"], "| Country:", short_dossier["country_profile"]["name"], "| Source:", short_dossier["source_name"], flush=True)
        short_sections, short_entities = build_short_script(short_dossier, variant_idx=len(hist_obj["published_keys"]))

        for idx, sec in enumerate(short_sections):
            ap = f"temp/s_voice_{idx}.mp3"
            vc, dur, w_timings = await voice_sub_dir.synthesize_with_word_boundaries(sec["narration"], ap, voice_style=sec.get("voice_style", "clear"))
            sec["audio_clip"] = vc
            sec["duration"] = dur
            sec["word_timings"] = w_timings

        s_beats, s_unique_photos, s_stats = build_prop_driven_storyboard_1080p(
            short_sections, short_dossier, short_entities, 1080, 1920, tag_prefix="short"
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
        bgm_s = AudioFileClip(build_situation_adaptive_soft_soundtrack("temp/bgm_s.wav", final_short.duration, beat_switch_times_s, category=short_dossier["category"]))
        final_short = final_short.with_audio(CompositeAudioClip([final_short.audio, bgm_s])) if MOVIEPY_V2 else final_short.set_audio(CompositeAudioClip([final_short.audio, bgm_s]))
        out_short = "output/WTB_1080p_Short_9x16.mp4"
        final_short.write_videofile(out_short, fps=24, codec="libx264", audio_codec="aac", bitrate="8000k", preset="ultrafast", threads=4, logger=None)

        short_pkg = create_category_adaptive_1080p_thumbnail(short_dossier, short_entities, s_unique_photos, watermark, out_path="output/WTB_1080p_Short_Thumb.jpg")

        # 2. BUILD 1080p LONG DOCUMENTARY (In STRICT Chapter 1..7 Order!)
        print("\n📺 [4/6] Building 1080p Long Documentary (1920x1080) on #1 Trending:", lead_long_dossier["title"], "| Country:", lead_long_dossier["country_profile"]["name"], "| Source:", lead_long_dossier["source_name"], flush=True)
        long_chapters = build_long_documentary_script(long_dossiers)
        lead_long_entities = extract_story_entities(lead_long_dossier)

        for idx, ch in enumerate(long_chapters):
            ap = f"temp/l_voice_{idx}.mp3"
            vc, dur, w_timings = await voice_sub_dir.synthesize_with_word_boundaries(ch["narration"], ap, voice_style=ch.get("voice_style", "clear"))
            ch["audio_clip"] = vc
            ch["duration"] = dur
            ch["word_timings"] = w_timings

        long_clips = []
        beat_switch_times_l = []
        total_long_unique_photos = []
        long_stats_list = []
        cur_lt = 0.0

        # Build each chapter in strict chronological sequence (Chapter 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7)
        # so the Subscribe Outro (Chapter 7) is ALWAYS at the very end of the video!
        for ch_idx, ch in enumerate(long_chapters):
            d_ents = extract_story_entities(ch["dossier"])
            ch_beats, ch_photos, ch_st = build_prop_driven_storyboard_1080p(
                [ch], ch["dossier"], d_ents, 1920, 1080, tag_prefix=f"long_ch{ch_idx+1}"
            )
            total_long_unique_photos.extend(ch_photos)
            long_stats_list.append(ch_st)
            for b in ch_beats:
                beat_switch_times_l.append(round(cur_lt, 2))
                cur_lt += b["duration"]
            clip = make_section_clip_from_beats(ch_beats, watermark, voice_sub_dir, ch["duration"], 1920, 1080, is_short=False)
            clip = clip.with_audio(ch["audio_clip"]) if MOVIEPY_V2 else clip.set_audio(ch["audio_clip"])
            long_clips.append(clip)

        final_long = concatenate_videoclips(long_clips, method="compose")
        bgm_l = AudioFileClip(build_situation_adaptive_soft_soundtrack("temp/bgm_l.wav", final_long.duration, beat_switch_times_l, category=lead_long_dossier["category"]))
        final_long = final_long.with_audio(CompositeAudioClip([final_long.audio, bgm_l])) if MOVIEPY_V2 else final_long.set_audio(CompositeAudioClip([final_long.audio, bgm_l]))
        out_long = "output/WTB_1080p_Long_16x9.mp4"
        final_long.write_videofile(out_long, fps=20, codec="libx264", audio_codec="aac", bitrate="8000k", preset="ultrafast", threads=4, logger=None)

        pkg_report = create_category_adaptive_1080p_thumbnail(lead_long_dossier, lead_long_entities, total_long_unique_photos, watermark, out_path="output/WTB_1080p_Thumb_1.jpg")

        for d_used in [short_dossier, lead_long_dossier]:
            hist_obj["published_keys"].add(d_used["story_key"])
            hist_obj["event_fingerprints"].append({"title": d_used["title"], "tokens": d_used["event_tokens"]})
            hist_obj["last_sources"].append(d_used["source_name"])
        save_published_history(hist_obj)

        agg_long_stats = {
            "run_status": "PASS",
            "total_beats": sum(s["total_beats"] for s in long_stats_list),
            "unique_real_photos": sum(s["unique_real_photos"] for s in long_stats_list),
            "moving_video_beats": sum(s["moving_video_beats"] for s in long_stats_list),
            "generated_infographic_beats": sum(s["generated_infographic_beats"] for s in long_stats_list),
            "reused_photo_beats": sum(s["reused_photo_beats"] for s in long_stats_list),
            "map_beats": sum(s["map_beats"] for s in long_stats_list),
            "failed_queries_count": sum(s["failed_queries_count"] for s in long_stats_list),
            "failed_queries": [q for s in long_stats_list for q in s["failed_queries"]][:20]
        }

        with open("output/wtb_1080p_report.json", "w") as f:
            json.dump({
                "analytics_winning_keywords": winning_keywords,
                "short_topic": short_dossier["title"],
                "short_source_name": short_dossier["source_name"],
                "short_country": short_dossier["country_profile"]["name"],
                "short_audit": s_stats,
                "long_topic": lead_long_dossier["title"],
                "long_source_name": lead_long_dossier["source_name"],
                "long_country": lead_long_dossier["country_profile"]["name"],
                "long_audit": agg_long_stats,
                "packaging": pkg_report
            }, f, indent=2)

        short_hashtags_str = " ".join(short_pkg["hashtags"] + ["#Shorts", "#BreakingNews"])
        short_seo_desc = (
            f"{short_dossier['title']}\n\n"
            f"World Talk Brief #Shorts dispatch from {short_dossier['country_profile']['capital']}, "
            f"{short_dossier['country_profile']['name'].title()}.\n\n"
            f"🔑 KEY ENTITIES: {', '.join(short_entities[:5])}\n"
            f"📋 Editorial Reference ({short_dossier['published_date']}): {short_dossier['source_url']}\n\n"
            f"{short_hashtags_str}"
        )
        short_seo_tags = [
            "World Talk Brief", "World News", "Geopolitics", "Breaking News", "YouTube Shorts",
            short_dossier["country_profile"]["name"].title(), short_dossier["country_profile"]["capital"]
        ] + short_entities[:5] + winning_keywords[:4]

        chap_lines = []
        t_acc = 0
        for ch in long_chapters:
            mm = int(t_acc) // 60
            ss = int(t_acc) % 60
            chap_lines.append(f"{mm:02d}:{ss:02d} - {ch['chapter_title']}")
            t_acc += ch.get("duration", 16)

        long_hashtags_str = " ".join(pkg_report["hashtags"] + ["#Documentary", "#GlobalNews"])
        long_seo_desc = (
            f"{pkg_report['selected_title']}\n\n"
            f"World Talk Brief presents an original documentary analysis on: {lead_long_dossier['title']}.\n\n"
            f"⏱️ CHAPTER TIMESTAMPS:\n" + "\n".join(chap_lines) + "\n\n"
            f"🔑 KEY SUBJECTS & ENTITIES: {', '.join(lead_long_entities[:8])}\n"
            f"📋 Editorial Reference ({lead_long_dossier['published_date']}): {lead_long_dossier['source_url']}\n\n"
            f"{long_hashtags_str}"
        )
        long_seo_tags = [
            "World Talk Brief", "Geopolitics", "World News Documentary", "International Relations",
            lead_long_dossier["country_profile"]["name"].title(),
            lead_long_dossier["country_profile"]["capital"],
            lead_long_dossier["country_profile"]["region"]
        ] + lead_long_entities[:6] + winning_keywords[:4]

        try_youtube_auto_upload(out_short, short_dossier["title"], short_seo_desc, short_seo_tags, is_short=True, thumbnail_path=short_pkg["selected_thumbnail"])
        try_youtube_auto_upload(out_long, pkg_report["selected_title"], long_seo_desc, long_seo_tags, is_short=False, thumbnail_path=pkg_report["selected_thumbnail"])

        print("✅ [6/6] GITHUB CLOUD 1080p FULL HD PRODUCTION & UPLOAD COMPLETE!", flush=True)
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
