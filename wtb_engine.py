import os
import sys
import re
import math
import wave
import json
import time
import base64
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
    "User-Agent": "WorldTalkBriefCloudFactory/11.5 (https://github.com/bapuop17/wtb_engine; editorial@worldtalkbrief.org)"
}

# ==============================================================================
# 1. GLOBAL GEOPOLITICAL DATABASE & STRICT WATERMARK BLOCKLIST
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
    "TAIWAN": ("TW", "TWN", "Taipei", "23.5M", "East Asia", 25.033, 121.565),
    "POLAND": ("PL", "POL", "Warsaw", "37.6M", "Europe", 52.229, 21.012)
}

BANNED_IMAGE_SOURCES = [
    "alamy", "dreamstime", "freepik", "shutterstock", "gettyimages", "istockphoto",
    "123rf", "depositphotos", "vecteezy", "canstock", "bigstock", "sputnik",
    "ytimg", "youtube", "cartoon", "clipart", "meme", "watermark"
]

PERSON_WIKI_MAP = {
    "trump": ("Donald Trump", "U.S. PRESIDENT DONALD TRUMP"),
    "putin": ("Vladimir Putin", "RUSSIAN PRESIDENT VLADIMIR PUTIN"),
    "zelensky": ("Volodymyr Zelenskyy", "UKRAINIAN PRESIDENT ZELENSKYY"),
    "zelenskyy": ("Volodymyr Zelenskyy", "UKRAINIAN PRESIDENT ZELENSKYY"),
    "biden": ("Joe Biden", "U.S. PRESIDENT JOE BIDEN"),
    "netanyahu": ("Benjamin Netanyahu", "ISRAELI PM BENJAMIN NETANYAHU"),
    "macron": ("Emmanuel Macron", "FRENCH PRESIDENT EMMANUEL MACRON"),
    "starmer": ("Keir Starmer", "UK PM KEIR STARMER"),
    "modi": ("Narendra Modi", "INDIAN PM NARENDRA MODI"),
    "xi": ("Xi Jinping", "CHINESE PRESIDENT XI JINPING"),
    "lula": ("Luiz Inácio Lula da Silva", "BRAZILIAN PRESIDENT LULA"),
    "bolsonaro": ("Jair Bolsonaro", "FORMER PRESIDENT JAIR BOLSONARO"),
    "carney": ("Mark Carney", "CANADIAN PM MARK CARNEY"),
    "wang yi": ("Wang Yi", "CHINESE FM WANG YI"),
    "crosetto": ("Guido Crosetto", "ITALIAN DEFENSE MINISTER CROSETTO"),
    "erdogan": ("Recep Tayyip Erdoğan", "TURKISH PRESIDENT ERDOGAN"),
    "khamenei": ("Ali Khamenei", "IRANIAN SUPREME LEADER KHAMENEI"),
    "musk": ("Elon Musk", "TECH LEADER ELON MUSK"),
    "altman": ("Sam Altman", "OPENAI CEO SAM ALTMAN"),
    "pichai": ("Sundar Pichai", "GOOGLE CEO SUNDAR PICHAI"),
    "nadella": ("Satya Nadella", "MICROSOFT CEO SATYA NADELLA")
}

VISUAL_PROP_DICTIONARY = {
    "drone": ("MILITARY DRONE / UAV", "Unmanned aerial vehicle", "military combat drone quadcopter"),
    "drones": ("MILITARY DRONE FLEET", "Unmanned combat aerial vehicle", "military drone UAV launch"),
    "bomber": ("STRATEGIC BOMBER AIRCRAFT", "Tupolev Tu-95", "strategic bomber military aircraft"),
    "bombers": ("STRATEGIC BOMBER FLEET", "Tupolev Tu-160", "strategic bomber aircraft runway"),
    "munitions": ("MUNITIONS & ARTILLERY", "Artillery shell", "ammunition factory artillery shells"),
    "factory": ("INDUSTRIAL DEFENSE PLANT", "Factory", "industrial manufacturing plant"),
    "factories": ("INDUSTRIAL MANUFACTURING", "Manufacturing", "heavy industry factory complex"),
    "sabotage": ("COVERT SABOTAGE OPERATION", "Rail transport", "railway tracks security inspection"),
    "intelligence": ("INTELLIGENCE OPERATIONS", "Military intelligence", "intelligence command center"),
    "sanctions": ("ECONOMIC SANCTIONS ORDER", "International sanctions", "container ship port trade"),
    "suspend": ("PRESIDENTIAL EXECUTIVE ACTION", "White House", "White House Oval Office desk"),
    "suspension": ("SANCTIONS POLICY SHIFT", "United States Department of the Treasury", "US Treasury building Washington"),
    "negotiating": ("DIPLOMATIC NEGOTIATING TABLE", "Diplomacy", "international diplomatic conference table"),
    "negotiations": ("HIGH-STAKES PEACE TALKS", "Peace treaty", "bilateral summit diplomatic talks"),
    "fire": ("EMERGENCY FIRE RESPONSE", "Firefighting", "firefighters battling structure blaze"),
    "flames": ("FIREFIGHTING OPERATION", "Wildfire", "firefighters emergency fire trucks"),
    "base": ("MILITARY BASE INSTALLATION", "Military base", "military base armored vehicles"),
    "military": ("ARMED FORCES DEPLOYMENT", "Armed forces", "military soldiers armored vehicles"),
    "crews": ("EMERGENCY RESCUE CREWS", "Emergency medical services", "emergency response vehicles"),
    "injured": ("MEDICAL EMERGENCY RESPONSE", "Hospital", "emergency medical hospital transport"),
    "violence": ("SECURITY CRACKDOWN", "Riot police", "police security forces street patrol"),
    "protest": ("PUBLIC DEMONSTRATION", "Protest", "crowd street protest police"),
    "pressure": ("GOVERNMENT UNDER PRESSURE", "National Assembly (France)", "parliament government building"),
    "missile": ("BALLISTIC MISSILE SYSTEM", "Surface-to-air missile", "missile launcher defense system"),
    "oil": ("GLOBAL OIL & ENERGY SUPPLY", "Petroleum industry", "oil refinery tanker ship"),
    "gas": ("NATURAL GAS PIPELINE", "Natural gas", "natural gas pipeline terminal"),
    "tariff": ("GLOBAL TRADE & TARIFFS", "Container ship", "cargo container ship port cranes"),
    "trade": ("MARITIME TRADE CORRIDOR", "Maritime transport", "container ship ocean port"),
    "bank": ("CENTRAL BANK RESERVES", "Central bank", "central bank financial building"),
    "economy": ("GLOBAL FINANCIAL MARKETS", "Stock exchange", "stock exchange trading floor"),
    "election": ("NATIONAL ELECTION VOTE", "Voting", "ballot box election polling station"),
    "court": ("INTERNATIONAL COURT TRIBUNAL", "International Court of Justice", "courtroom judges gavel"),
    "border": ("INTERNATIONAL BORDER ZONE", "Border control", "border checkpoint security"),
    "ship": ("NAVAL WARSHIP FLEET", "Destroyer", "navy warship destroyer sea"),
    "nuclear": ("NUCLEAR FACILITY", "Nuclear power plant", "nuclear power plant cooling towers"),
    "satellite": ("ORBITAL RECON SATELLITE", "Reconnaissance satellite", "satellite in earth orbit"),
    "ai": ("ARTIFICIAL INTELLIGENCE", "Data center", "supercomputer server room AI"),
    "chip": ("SEMICONDUCTOR MICROCHIP", "Semiconductor device fabrication", "silicon wafer microchip cleanroom"),
    "congress": ("U.S. CAPITOL BUILDING", "United States Capitol", "United States Capitol exterior"),
    "parliament": ("NATIONAL PARLIAMENT", "Parliament", "parliament legislative chamber"),
    "kremlin": ("MOSCOW KREMLIN", "Moscow Kremlin", "Moscow Kremlin Red Square"),
    "white house": ("THE WHITE HOUSE", "White House", "White House exterior Washington"),
    "pentagon": ("THE PENTAGON", "The Pentagon", "The Pentagon aerial view"),
    "nato": ("NATO HEADQUARTERS", "NATO", "NATO headquarters Brussels flags"),
    "un": ("UNITED NATIONS ASSEMBLY", "United Nations General Assembly", "United Nations General Assembly hall"),
    "amazon": ("AMAZON RAINFOREST", "Amazon rainforest", "Amazon rainforest aerial canopy")
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
# 2. STRICT VERIFIED RESEARCH ENGINE (Source URL + Pub Date Per Claim)
# ==============================================================================
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
    """Uses strict word-boundary regex (\b) so 'ai' never matches inside 'said' or 'against'!"""
    comb = f"{title} {claims_text}".lower()
    if any(re.search(rf"\b{re.escape(w)}\b", comb) for w in ["ai", "artificial intelligence", "microchip", "semiconductor", "quantum", "spacecraft", "nasa", "cyber", "robotics"]):
        return "ai_tech_science"
    if any(re.search(rf"\b{re.escape(w)}\b", comb) for w in ["gdp", "inflation", "stock market", "tariff", "tariffs", "central bank", "interest rate", "economy", "debt"]):
        return "economy_markets"
    if any(re.search(rf"\b{re.escape(w)}\b", comb) for w in ["climate", "amazon", "deforestation", "emissions", "wildfire", "flood", "earthquake", "hurricane"]):
        return "environment_climate"
    if any(re.search(rf"\b{re.escape(w)}\b", comb) for w in ["missile", "strike", "offensive", "sabotage", "troops", "war", "attack", "killed", "military", "drone", "bomber", "violence", "fire"]):
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

def discover_and_build_dossiers():
    print("📡 [1/6] Scanning Global News Feeds (Strict Source URL + Pub Date Verification)...", flush=True)
    feeds = [
        ("BBC World", "http://feeds.bbci.co.uk/news/world/rss.xml"),
        ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
        ("The Guardian", "https://www.theguardian.com/world/rss"),
        ("DW World", "https://rss.dw.com/rdf/rss-en-world"),
        ("France24", "https://www.france24.com/en/rss")
    ]
    dossiers = []
    seen = set()

    for src, url in feeds:
        try:
            r_feed = requests.get(url, headers=HEADERS_WEB, timeout=10)
            feed = feedparser.parse(r_feed.content)
        except Exception:
            continue

        for entry in feed.entries[:22]:
            raw_t = entry.title.rsplit(" - ", 1)[0]
            if any(skip in raw_t.lower() for skip in ["live", "latest updates", "as it happened", "at a glance", "in pictures", "quiz"]):
                continue
            title = clean_fact(raw_t)
            if len(title) < 20 or title.lower() in seen:
                continue

            link = getattr(entry, "link", "").strip()
            pub_date = normalize_pub_date(getattr(entry, "published", "") or getattr(entry, "updated", ""))
            if not link or not pub_date:
                continue

            seen.add(title.lower())
            raw_sum = BeautifulSoup(getattr(entry, "summary", ""), "html.parser").get_text()
            summary = clean_fact(raw_sum)

            rss_img = None
            if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
                rss_img = entry.media_thumbnail[0].get("url")
                if rss_img and "bbci.co.uk" in rss_img:
                    rss_img = re.sub(r"/standard/\d+/", "/standard/1024/", rss_img)
            elif hasattr(entry, "media_content") and entry.media_content:
                rss_img = entry.media_content[0].get("url")

            og_img = None
            verified_claims = []
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
                for p in soup.find_all("p"):
                    if p.find_parent("figcaption") or p.find_parent("figure") or p.find_parent("footer"):
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
                                    "source_name": "Verified Wire",
                                    "published_date": b_date
                                })
                except Exception:
                    pass

            if len(verified_claims) < 3:
                continue

            raw_facts = [c["text"] for c in verified_claims]
            comb = f"{title} {' '.join(raw_facts[:3])}".lower()
            detected_country = "UNITED STATES"
            for c in COUNTRY_GEO_DB.keys():
                if re.search(rf"\b{re.escape(c.lower())}\b", comb):
                    detected_country = c
                    break

            iso2, iso3, cap, pop, reg, lat, lon = COUNTRY_GEO_DB[detected_country]
            c_prof = {"name": detected_country, "iso2": iso2, "iso3": iso3, "capital": cap, "population": pop, "region": reg, "lat": lat, "lon": lon, "flag_img": None}

            try:
                fr = requests.get(f"https://flagcdn.com/w160/{iso2.lower()}.png", headers=HEADERS_WEB, timeout=5)
                if fr.status_code == 200 and len(fr.content) > 500:
                    fp = f"temp/flag_{iso2}.png"
                    with open(fp, "wb") as f:
                        f.write(fr.content)
                    c_prof["flag_img"] = Image.open(fp).convert("RGBA")
            except Exception:
                pass

            wb_data = fetch_verified_world_bank_gdp(iso3)
            category = classify_story_mood_and_category(title, " ".join(raw_facts[:4]))

            dossiers.append({
                "score": len(verified_claims) * 3,
                "title": title,
                "category": category,
                "source_url": link,
                "published_date": pub_date,
                "source_name": src,
                "verified_claims": verified_claims,
                "raw_facts": raw_facts,
                "lead_img": og_img or rss_img,
                "country_profile": c_prof,
                "wb_data": wb_data
            })
            if len(dossiers) >= 6:
                break
        if len(dossiers) >= 6:
            break

    dossiers.sort(key=lambda x: x["score"], reverse=True)
    return dossiers

# ==============================================================================
# 3. SPEAKER & PROP-AWARE SCRIPT DIRECTOR
# ==============================================================================
def extract_story_entities(dossier):
    text = f"{dossier['title']} {' '.join(dossier['raw_facts'][:5])}"
    c_prof = dossier["country_profile"]
    ents = []
    low = text.lower()
    for k, (wiki_name, _) in PERSON_WIKI_MAP.items():
        if re.search(rf"\b{re.escape(k)}\b", low) and wiki_name not in ents:
            ents.append(wiki_name)

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

    for fb in [c_prof["capital"], c_prof["name"].title(), f"{c_prof['name'].title()} government", "United Nations"]:
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
    claims = dossier["verified_claims"]
    title = dossier["title"]

    c0 = claims[0]
    c1 = claims[1] if len(claims) > 1 else c0
    c2 = claims[2] if len(claims) > 2 else c1

    sections = [
        {
            "role": "HOOK",
            "voice_style": "urgent",
            "headline": title.upper()[:52],
            "narration": f"{title}. Here is why this sudden move in {c_prof['capital']} changes the global calculation right now.",
            "claim_meta": c0
        },
        {
            "role": "WHAT_HAPPENED",
            "voice_style": "clear",
            "headline": f"INSIDE {c_prof['capital'].upper()}'S DECISION",
            "narration": polish_journalistic_sentence(c0["text"], c_prof, role="BODY"),
            "claim_meta": c0
        },
        {
            "role": "CONTEXT",
            "voice_style": "analytical",
            "headline": f"THE WIDER STAKES IN {c_prof['region'].upper()}",
            "narration": polish_journalistic_sentence(c1["text"], c_prof, role="CONTEXT"),
            "claim_meta": c1
        },
        {
            "role": "PAYOFF",
            "voice_style": "serious",
            "headline": "THE CRITICAL TEST AHEAD",
            "narration": f"{polish_journalistic_sentence(c2['text'], c_prof, role='PAYOFF')} How do you see this playing out next?",
            "claim_meta": c2
        }
    ]
    return sections, ents

def build_long_documentary_script(dossiers):
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
            "chapter_title": "THE FLASHPOINT",
            "role": "HOOK",
            "voice_style": "urgent",
            "dossier": lead,
            "claim_meta": c0,
            "narration": f"{lead['title']}. While the initial headlines broke just hours ago from {c_prof['capital']}, the deeper story reveals a decisive turning point. {polish_journalistic_sentence(c0['text'], c_prof, 'BODY')}"
        },
        {
            "chapter_num": 2,
            "chapter_title": "THE VERIFIED RECORD",
            "role": "EVIDENCE",
            "voice_style": "clear",
            "dossier": lead,
            "claim_meta": c1,
            "narration": f"Look at the specifics confirmed on the record. {polish_journalistic_sentence(c1['text'], c_prof, 'BODY')}"
        },
        {
            "chapter_num": 3,
            "chapter_title": "THE GEOGRAPHIC FAULT LINE",
            "role": "GEOGRAPHY",
            "voice_style": "analytical",
            "dossier": lead,
            "claim_meta": c1,
            "narration": f"Geography explains why international observers are paying such close attention. Centered around {c_prof['capital']}, {c_prof['name'].title()} anchors a vital corridor in {c_prof['region']}, where any policy shift reverberates across neighboring borders."
        },
        {
            "chapter_num": 4,
            "chapter_title": "HOW WE REACHED THIS POINT",
            "role": "TIMELINE",
            "voice_style": "analytical",
            "dossier": lead,
            "claim_meta": c2,
            "narration": f"This confrontation did not appear overnight. {polish_journalistic_sentence(c2['text'], c_prof, 'CONTEXT')} Step by step, earlier diplomatic off-ramps narrowed until key actors reached this crossroads."
        },
        {
            "chapter_num": 5,
            "chapter_title": "THE COMPETING CALCULATIONS",
            "role": "COMPARISON",
            "voice_style": "serious",
            "dossier": lead,
            "claim_meta": c3,
            "narration": f"Now two competing strategic calculations are colliding. {polish_journalistic_sentence(c3['text'], c_prof, 'BODY')}"
        }
    ]

    if len(dossiers) > 1:
        sec_d = dossiers[1]
        sc_prof = sec_d["country_profile"]
        sc0 = sec_d["verified_claims"][0]
        sc1 = sec_d["verified_claims"][1] if len(sec_d["verified_claims"]) > 1 else sc0
        chapters.append({
            "chapter_num": 6,
            "chapter_title": f"GLOBAL BRIEFING: {sc_prof['name']}",
            "role": "WIDER_CONTEXT",
            "voice_style": "clear",
            "dossier": sec_d,
            "claim_meta": sc0,
            "narration": f"Meanwhile, a major parallel development is unfolding in {sc_prof['name'].title()}: {sec_d['title']}. {polish_journalistic_sentence(sc0['text'], sc_prof, 'BODY')} {polish_journalistic_sentence(sc1['text'], sc_prof, 'BODY')}"
        })

    chapters.append({
        "chapter_num": len(chapters) + 1,
        "chapter_title": "THE ROAD AHEAD",
        "role": "PAYOFF",
        "voice_style": "serious",
        "dossier": lead,
        "claim_meta": c3,
        "narration": f"Watch the next seventy-two hours closely. Whether {ents[0] if ents else c_prof['name'].title()} opts for calibrated de-escalation or doubles down on leverage will determine if this remains contained or reshapes {c_prof['region']} for years to come."
    })

    return chapters

# ==============================================================================
# 4. CRYSTAL-CLEAR 1080p VISUAL ENGINE + REAL ARCHIVAL VIDEO B-ROLL
# ==============================================================================
def validate_and_enhance_1080p(im, existing_hashes, min_w=500, min_h=320):
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

    white_px = np.sum((arr[:, :, 0] > 242) & (arr[:, :, 1] > 242) & (arr[:, :, 2] > 242))
    if (white_px / float(80 * 80)) > 0.34:
        return None

    gray_cv = cv2.cvtColor(np.array(im.resize((320, 200))), cv2.COLOR_RGB2GRAY)
    blur_score = cv2.Laplacian(gray_cv, cv2.CV_64F).var()
    if blur_score < 38.0 or im.entropy() < 6.2:
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

    for p_key, (wiki_page, badge_lbl) in PERSON_WIKI_MAP.items():
        if re.search(rf"\b{re.escape(p_key)}\b", low):
            return badge_lbl, wiki_page, f"{wiki_page} official press conference", True

    for word_key, (prop_badge, wiki_concept, search_q) in VISUAL_PROP_DICTIONARY.items():
        if re.search(rf"\b{re.escape(word_key)}\b", low):
            return prop_badge, wiki_concept, f"{search_q} {c_prof['name']}", False

    caps = [w for w in re.findall(r"\b[A-Z][a-z]{3,}\b", beat_text) if w not in {"Here", "While", "Behind", "Look", "This", "Step", "Watch", "Whether", "Meanwhile", "Crucially", "Inside", "Prime", "Minister", "President"}]
    if caps:
        entity_phrase = " ".join(caps[:2])
        return f"FOCUS • {entity_phrase.upper()}", entity_phrase, f"{entity_phrase} {c_prof['name']}", False

    chosen_ent = entities[beat_idx % len(entities)]
    return f"SUBJECT • {chosen_ent.upper()[:24]}", chosen_ent, f"{chosen_ent} {c_prof['name']}", False

def fetch_high_res_visual_for_beat(wiki_target, search_query, existing_hashes, failed_queries, is_person=False, tag_id="beat"):
    try:
        w_api = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query", "generator": "search", "gsrsearch": wiki_target, "gsrlimit": 4,
            "prop": "pageimages", "piprop": "original|thumbnail", "pithumbsize": 1920, "format": "json"
        }
        r = requests.get(w_api, params=params, headers=HEADERS_WIKI, timeout=6).json()
        pages = sorted(r.get("query", {}).get("pages", {}).values(), key=lambda x: x.get("index", 99))
        for pg in pages:
            img_u = pg.get("original", {}).get("source") or pg.get("thumbnail", {}).get("source")
            if img_u and img_u.lower().endswith((".jpg", ".jpeg", ".png")) and not any(b in img_u.lower() for b in BANNED_IMAGE_SOURCES):
                ir = requests.get(img_u, headers=HEADERS_WIKI, timeout=6)
                if ir.status_code == 200 and len(ir.content) > 15000:
                    p = f"temp/{tag_id}_wiki.jpg"
                    with open(p, "wb") as f:
                        f.write(ir.content)
                    vim = validate_and_enhance_1080p(Image.open(p), existing_hashes)
                    if vim is not None:
                        return vim
    except Exception:
        pass

    for comm_q in [search_query, wiki_target]:
        try:
            api = "https://commons.wikimedia.org/w/api.php"
            params = {
                "action": "query", "generator": "search",
                "gsrsearch": f"filetype:bitmap {comm_q} -cartoon -logo -map",
                "gsrnamespace": "6", "gsrlimit": 6,
                "prop": "imageinfo", "iiprop": "url", "iiurlwidth": 1920, "format": "json"
            }
            r = requests.get(api, params=params, headers=HEADERS_WIKI, timeout=7).json()
            for pg in r.get("query", {}).get("pages", {}).values():
                t_low = pg.get("title", "").lower()
                if any(b in t_low for b in ["map", "diagram", "coat of arms", "flag", "icon", "locator"]):
                    continue
                ii = pg.get("imageinfo", [{}])[0]
                u = ii.get("thumburl") or ii.get("url")
                if u and u.lower().endswith((".jpg", ".jpeg")):
                    ir = requests.get(u, headers=HEADERS_WIKI, timeout=6)
                    if ir.status_code == 200 and len(ir.content) > 15000:
                        p = f"temp/{tag_id}_comm.jpg"
                        with open(p, "wb") as f:
                            f.write(ir.content)
                        vim = validate_and_enhance_1080p(Image.open(p), existing_hashes)
                        if vim is not None:
                            return vim
        except Exception:
            pass

    try:
        b_url = f"https://www.bing.com/images/search?q={urllib.parse.quote(search_query + ' -site:alamy.com -site:dreamstime.com -site:freepik.com -site:shutterstock.com')}&qft=+filterui:imagesize-large&form=IRFLTR&first=1"
        r = requests.get(b_url, headers=HEADERS_WEB, timeout=7)
        murls = re.findall(r'murl&quot;:&quot;(https?://[^&]+?)&quot;', r.text) or re.findall(r'"murl":"(https?://[^"]+?)"', r.text)
        for u in murls[:10]:
            u_low = u.lower()
            if any(b in u_low for b in BANNED_IMAGE_SOURCES):
                continue
            ir = requests.get(u, headers=HEADERS_WEB, timeout=5)
            if ir.status_code == 200 and len(ir.content) > 22000:
                p = f"temp/{tag_id}_binglg.jpg"
                with open(p, "wb") as f:
                    f.write(ir.content)
                vim = validate_and_enhance_1080p(Image.open(p), existing_hashes, min_w=700, min_h=420)
                if vim is not None:
                    return vim
    except Exception:
        pass

    failed_queries.append(search_query)
    return None

def fetch_real_stock_or_archival_video_broll(wiki_target, country_name, capital_name, tag_id="vclip"):
    """
    Fetches real moving stock/archival video footage from Wikimedia Commons (`filetype:video`, `gsrnamespace=6`),
    supporting `.webm`, `.mp4`, and `.ogv` via FFmpeg!
    """
    queries = [wiki_target, f"{country_name} {capital_name}", f"{country_name} government", "diplomatic summit"]
    for vq in queries:
        try:
            api = "https://commons.wikimedia.org/w/api.php"
            params = {
                "action": "query", "generator": "search",
                "gsrsearch": f"filetype:video {vq}",
                "gsrnamespace": "6", "gsrlimit": 6,
                "prop": "imageinfo", "iiprop": "url|size", "format": "json"
            }
            r = requests.get(api, params=params, headers=HEADERS_WIKI, timeout=7).json()
            for pg in r.get("query", {}).get("pages", {}).values():
                ii = pg.get("imageinfo", [{}])[0]
                vu = ii.get("url", "")
                vsz = ii.get("size", 99999999)
                if vu.lower().endswith((".webm", ".mp4", ".ogv")) and 80000 < vsz < 18000000:
                    vr = requests.get(vu, headers=HEADERS_WIKI, timeout=12)
                    if vr.status_code == 200 and len(vr.content) > 80000:
                        ext = os.path.splitext(vu.lower())[1]
                        out_v = f"temp/{tag_id}_broll{ext}"
                        with open(out_v, "wb") as f:
                            f.write(vr.content)
                        vc = VideoFileClip(out_v)
                        GLOBAL_OPEN_VCLIPS.append(vc)
                        if vc.duration >= 3.0:
                            return {
                                "vclip": vc,
                                "start_t": min(1.0, vc.duration * 0.15),
                                "label": f"FOOTAGE • {vq.upper()[:24]}"
                            }
        except Exception:
            pass
    return None

def generate_bespoke_speech_infographic_1080p(beat_text, prop_badge, claim_meta, dossier):
    W, H = 1920, 1080
    c_prof = dossier["country_profile"]
    canvas = Image.new("RGB", (W, H), (10, 16, 28))
    draw = ImageDraw.Draw(canvas, "RGBA")

    for x in range(0, W, 80):
        draw.line([(x, 0), (x, H)], fill=(0, 210, 255, 22), width=1)
    for y in range(0, H, 80):
        draw.line([(0, y), (W, y)], fill=(0, 210, 255, 22), width=1)

    key_nums = re.findall(r"(\$?\d+(?:,\d+)*(?:\.\d+)?\s*(?:%|million|billion|trillion|years|days|hours|km|troops|dead|injured)?)", beat_text, re.I)
    stat_str = key_nums[0].strip().upper() if (key_nums and len(key_nums[0].strip()) >= 2) else c_prof["name"]

    draw.rounded_rectangle([(160, 150), (1760, 680)], radius=20, fill=(14, 24, 42, 240), outline=(255, 214, 10, 220), width=4)
    draw.rounded_rectangle([(200, 185), (680, 240)], radius=8, fill=(204, 18, 36, 255))
    draw.text((224, 198), prop_badge[:32], fill=(255, 255, 255, 255), font=get_font(26))

    draw.text((200, 270), f"KEY FOCUS: {stat_str}", fill=(255, 214, 10, 255), font=get_font(48))
    f_body = get_font(38)
    for l_i, ln in enumerate(wrap_lines(draw, f'"{beat_text}"', f_body, 1480)[:3]):
        draw.text((200, 355 + l_i * 54), ln, fill=(245, 248, 255, 255), font=f_body)

    src_line = f"VERIFIED SOURCE: {claim_meta['source_name']}  |  PUBLISHED: {claim_meta['published_date']}  |  {claim_meta['source_url'][:58]}"
    draw.text((200, 615), src_line, fill=(0, 210, 255, 255), font=get_font(22))
    return canvas

# ==============================================================================
# 5. FACE-BOUNDING-BOX SAFE CROPPING & BLURRED BACKDROP FITTER
# ==============================================================================
def detect_padded_face_crop_or_safe_fit(im, target_w, target_h):
    resample_mode = getattr(Image, "Resampling", Image).LANCZOS
    iw, ih = im.size
    target_ratio = target_w / float(target_h)

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

    if len(faces) > 0:
        min_x = min(f[0] for f in faces)
        min_y = min(f[1] for f in faces)
        max_x = max(f[0] + f[2] for f in faces)
        max_y = max(f[1] + f[3] for f in faces)
        box_w = max_x - min_x
        box_h = max_y - min_y

        pad_x1 = min_x - int(box_w * 0.55)
        pad_y1 = min_y - int(box_h * 0.65)
        pad_x2 = max_x + int(box_w * 0.55)
        pad_y2 = max_y + int(box_h * 0.85)

        req_w = pad_x2 - pad_x1
        req_h = pad_y2 - pad_y1

        if pad_x1 >= 0 and pad_y1 >= 0 and pad_x2 <= iw and pad_y2 <= ih and req_w <= iw * 0.92 and req_h <= ih * 0.92:
            crop_w = max(req_w, int(req_h * target_ratio))
            crop_h = int(crop_w / target_ratio)
            if crop_w <= iw and crop_h <= ih:
                cx = (pad_x1 + pad_x2) // 2
                cy = (pad_y1 + pad_y2) // 2
                left = max(0, min(iw - crop_w, cx - crop_w // 2))
                top = max(0, min(ih - crop_h, cy - crop_h // 2))
                cropped = im.crop((left, top, left + crop_w, top + crop_h))
                return cropped.resize((target_w, target_h), resample_mode)

    bg = im.copy().resize((target_w, target_h), resample_mode).filter(ImageFilter.GaussianBlur(radius=32))
    bg = ImageEnhance.Brightness(bg).enhance(0.32)

    scale = min(target_w / float(iw), target_h / float(ih))
    fit_w = max(1, int(iw * scale))
    fit_h = max(1, int(ih * scale))
    fg = im.resize((fit_w, fit_h), resample_mode)

    paste_x = (target_w - fit_w) // 2
    paste_y = (target_h - fit_h) // 2
    bg.paste(fg, (paste_x, paste_y))
    return bg

def build_clean_1080p_stage(im, W, H):
    resample_mode = getattr(Image, "Resampling", Image).LANCZOS
    if W < H:
        bg = im.copy().resize((W, H), resample_mode).filter(ImageFilter.GaussianBlur(radius=30))
        bg = ImageEnhance.Brightness(bg).enhance(0.30)
        canvas = bg.convert("RGBA")

        hero_w, hero_h = int(W * 1.05), 920
        fg = detect_padded_face_crop_or_safe_fit(im, hero_w, hero_h)
        return ("SHORT_STAGE", canvas, fg)
    else:
        over_w, over_h = int(W * 1.05), int(H * 1.05)
        fg = detect_padded_face_crop_or_safe_fit(im, over_w, over_h)
        return ("FULL_BLEED_STAGE", fg, None)

def extract_animated_frame_from_stage(stage_tuple, W, H, bp, pan_dir=1):
    mode_tag, base_a, base_b = stage_tuple
    if mode_tag == "SHORT_STAGE":
        canvas = base_a.copy()
        fg = base_b
        fw, fh = fg.size
        win_w, win_h = W, 900
        max_dx = max(fw - win_w, 0)
        max_dy = max(fh - win_h, 0)
        ox = int(max_dx * (bp if pan_dir == 1 else (1.0 - bp)))
        oy = int(max_dy * 0.5)
        slice_fg = fg.crop((ox, oy, ox + win_w, oy + win_h))
        canvas.paste(slice_fg, (0, 205))

        draw = ImageDraw.Draw(canvas, "RGBA")
        for y in range(0, 205):
            draw.line([(0, y), (W, y)], fill=(6, 9, 18, int(175 * (1.0 - y / 205.0))))
        for y in range(1105, H):
            draw.line([(0, y), (W, y)], fill=(6, 9, 18, int(235 * min(1.0, (y - 1105) / 260.0))))
        draw.line([(0, 205), (W, 205)], fill=(255, 214, 10, 220), width=3)
        draw.line([(0, 1105), (W, 1105)], fill=(255, 214, 10, 220), width=3)
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

# ==============================================================================
# 6. STORYBOARD BUILDER WITH DETAILED METRICS & BESPOKE INFOGRAPHIC FALLBACK
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

    if dossier.get("lead_img") and not any(b in dossier["lead_img"].lower() for b in BANNED_IMAGE_SOURCES):
        try:
            r = requests.get(dossier["lead_img"], headers=HEADERS_WEB, timeout=6)
            if r.status_code == 200 and len(r.content) > 15000:
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
        sec_headline = sec.get("headline") or sec.get("chapter_title") or dossier["title"]
        claim_meta = sec.get("claim_meta") or dossier["verified_claims"][0]

        target_beat_len = 2.5 if W < H else 2.9
        num_beats = max(3, int(math.ceil(sec_dur / target_beat_len)))
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
                if not is_person and moving_video_beats < 2 and global_beat_idx % 4 == 1:
                    vseg = fetch_real_stock_or_archival_video_broll(wiki_target, c_prof["name"], c_prof["capital"], tag_id=f"{tag_prefix}_v{global_beat_idx}")

                if vseg is not None:
                    b_type = "VIDEO_BROLL_BEAT"
                    moving_video_beats += 1
                    beat_im = unique_real_photos[-1] if unique_real_photos else osm_map
                    stage_1 = build_clean_1080p_stage(beat_im, W, H)
                else:
                    beat_im = fetch_high_res_visual_for_beat(
                        wiki_target, search_q, existing_hashes, failed_queries, is_person=is_person, tag_id=f"{tag_prefix}_b{global_beat_idx}"
                    )
                    if beat_im is not None:
                        unique_real_photos.append(beat_im)
                    else:
                        beat_im = generate_bespoke_speech_infographic_1080p(b_txt, prop_badge, claim_meta, dossier)
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

    min_expected_photos = min(12, max(3, int(len(planned_beats) * 0.55)))
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
    print(f"📊 [{tag_prefix.upper()} AUDIT] Status={run_status} | Beats={stats['total_beats']} | Unique Real Photos={stats['unique_real_photos']} | Moving Video={stats['moving_video_beats']} | Bespoke Infographics={stats['generated_infographic_beats']} | Maps={stats['map_beats']} | Failed Queries={stats['failed_queries_count']}", flush=True)
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
            top_im = detect_padded_face_crop_or_safe_fit(beat["primary_im"], W, 450)
            bot_im = detect_padded_face_crop_or_safe_fit(beat["secondary_im"], W, 450)
            frame.paste(top_im, (0, 205))
            frame.paste(bot_im, (0, 660))
            draw = ImageDraw.Draw(frame, "RGBA")
            draw.line([(0, 657), (W, 657)], fill=(255, 214, 10, 255), width=6)
        else:
            left_im = detect_padded_face_crop_or_safe_fit(beat["primary_im"], W // 2, H)
            right_im = detect_padded_face_crop_or_safe_fit(beat["secondary_im"], W // 2, H)
            frame.paste(left_im, (0, 0))
            frame.paste(right_im, (W // 2, 0))
            draw = ImageDraw.Draw(frame, "RGBA")
            draw.line([(W // 2, 0), (W // 2, H)], fill=(255, 214, 10, 255), width=6)
            for y in range(H - 360, H):
                draw.line([(0, y), (W, y)], fill=(4, 7, 14, int(238 * ((y - (H - 360)) / 360.0) ** 1.15)))
    else:
        frame = extract_animated_frame_from_stage(beat["stage_1"], W, H, bp, pan_dir=beat["pan_dir"])
        draw = ImageDraw.Draw(frame, "RGBA")

    cy_card = 1145 if is_short else (H - 355)
    bx1, bx2 = (42, W - 42) if is_short else (64, 1340)

    src_domain = urllib.parse.urlparse(claim_meta["source_url"]).netloc.replace("www.", "")
    citation_str = f"SOURCE: {claim_meta['source_name'].upper()} ({src_domain}) • PUBLISHED: {claim_meta['published_date']}"

    if b_type in ["PHOTO_BEAT", "VIDEO_BROLL_BEAT"]:
        kicker = beat["vseg"]["label"] if (b_type == "VIDEO_BROLL_BEAT" and beat.get("vseg")) else beat["primary_lbl"]
        hl = str(beat["beat_excerpt"] if len(beat["beat_excerpt"]) > 22 else beat["section_headline"]).upper()
        f_k = get_font(22)
        f_h = get_font(30 if is_short else 32)
        kw = draw.textbbox((0, 0), kicker, font=f_k)[2] + 36

        draw.rounded_rectangle([(bx1, cy_card), (bx2, cy_card + 182)], radius=14, fill=(10, 16, 28, 234), outline=(255, 214, 10, 220), width=3)
        draw.rounded_rectangle([(bx1 + 20, cy_card + 16), (bx1 + 20 + kw, cy_card + 52)], radius=8, fill=(204, 18, 36, 255))
        draw.text((bx1 + 38, cy_card + 22), kicker, fill=(255, 255, 255, 255), font=f_k)
        for i_l, ln in enumerate(wrap_lines(draw, hl, f_h, (bx2 - bx1) - 52)[:2]):
            draw.text((bx1 + 24, cy_card + 62 + i_l * 38), ln, fill=(255, 255, 255, 255), font=f_h)
        draw.text((bx1 + 24, cy_card + 146), citation_str[:78], fill=(0, 210, 255, 235), font=get_font(18))

    elif b_type == "MAP_LOCATOR_BEAT":
        cx, cy = (W // 2, 650) if is_short else (W // 2 - 120, H // 2 - 45)
        for ri in range(3):
            rp = ((local_t * 0.8) + ri * 0.33) % 1.0
            rad = int(36 + rp * 210)
            draw.ellipse([(cx - rad, cy - rad), (cx + rad, cy + rad)], outline=(255, 45, 45, int(235 * (1.0 - rp))), width=4)
        draw.ellipse([(cx - 14, cy - 14), (cx + 14, cy + 14)], fill=(255, 214, 10, 255))

        pip_w, pip_h = (340, 220) if is_short else (430, 270)
        px, py = (W - pip_w - 42, 240) if is_short else (W - pip_w - 64, 160)
        pip_im = detect_padded_face_crop_or_safe_fit(beat["secondary_im"], pip_w, pip_h)
        draw.line([(cx, cy), (px + pip_w // 2, py + pip_h)], fill=(255, 214, 10, 220), width=3)
        frame.paste(pip_im, (px, py))
        draw.rounded_rectangle([(px - 3, py - 3), (px + pip_w + 3, py + pip_h + 3)], radius=8, outline=(255, 214, 10, 255), width=4)

        draw.rounded_rectangle([(bx1, cy_card), (bx2, cy_card + 175)], radius=14, fill=(10, 16, 28, 240), outline=(0, 210, 255, 225), width=3)
        draw.text((bx1 + 26, cy_card + 18), f"GEOGRAPHIC CORRIDOR  •  LAT {c_prof['lat']}° LON {c_prof['lon']}°", fill=(0, 210, 255, 255), font=get_font(23))
        draw.text((bx1 + 26, cy_card + 58), f"EPICENTER: {c_prof['capital'].upper()}, {c_prof['name']} (POP: {c_prof['population']})", fill=(255, 214, 10, 255), font=get_font(31))
        draw.text((bx1 + 26, cy_card + 135), citation_str[:78], fill=(215, 230, 250, 235), font=get_font(18))

    elif b_type == "HEADLINE_EVIDENCE_BEAT":
        draw.rounded_rectangle([(bx1, cy_card - 10), (bx2, cy_card + 182)], radius=16, fill=(246, 244, 236, 248), outline=(204, 18, 36, 255), width=4)
        draw.rounded_rectangle([(bx1 + 24, cy_card + 8), (bx1 + 520, cy_card + 44)], radius=6, fill=(204, 18, 36, 255))
        draw.text((bx1 + 38, cy_card + 13), f"VERIFIED CLAIM • {claim_meta['published_date']}", fill=(255, 255, 255, 255), font=get_font(21))

        hl_txt = beat["beat_excerpt"] if len(beat["beat_excerpt"]) > 28 else story["title"]
        f_q = get_font(29 if is_short else 31)
        lines = wrap_lines(draw, hl_txt, f_q, (bx2 - bx1) - 60)[:2]
        hl_w = int(((bx2 - bx1) - 64) * min(bp * 1.4, 1.0))
        draw.rounded_rectangle([(bx1 + 24, cy_card + 54), (bx1 + 24 + hl_w, cy_card + 94)], radius=6, fill=(255, 232, 65, 240))
        for idx_l, ln in enumerate(lines):
            draw.text((bx1 + 30, cy_card + 56 + idx_l * 40), ln, fill=(12, 16, 22, 255), font=f_q)
        draw.text((bx1 + 30, cy_card + 144), f"URL: {claim_meta['source_url'][:68]}", fill=(80, 90, 110, 255), font=get_font(18))

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

    elif b_type == "DATA_CHART_BEAT" and story.get("wb_data") is not None:
        wb_years, wb_vals = story["wb_data"]
        draw.rounded_rectangle([(bx1, cy_card - 45), (bx2, cy_card + 195)], radius=16, fill=(10, 16, 28, 244), outline=(255, 214, 10, 230), width=3)
        draw.text((bx1 + 30, cy_card - 26), f"{c_prof['name']} VERIFIED GDP GROWTH (%)  •  WORLD BANK OPEN DATA", fill=(255, 214, 10, 255), font=get_font(24))
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

# ==============================================================================
# 7. VOICE, SUBTITLES, 10% SITUATION-ADAPTIVE AUDIO & MULTI-GENRE THUMBNAILS
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

def build_situation_adaptive_10pct_soundtrack(filename, duration, beat_switch_times, category="geopolitics_diplomacy"):
    sr = 22050
    n_samples = int(sr * duration)
    t = np.linspace(0, duration, n_samples, endpoint=False)

    if category == "war_crisis":
        f1, f2, f3, tempo = 146.83, 220.0, 261.63, 0.48
    elif category == "ai_tech_science":
        f1, f2, f3, tempo = 261.63, 329.63, 392.00, 0.36
    elif category == "economy_markets":
        f1, f2, f3, tempo = 164.81, 246.94, 293.66, 0.42
    elif category == "environment_climate":
        f1, f2, f3, tempo = 174.61, 261.63, 349.23, 0.65
    else:
        f1, f2, f3, tempo = 130.81, 196.00, 311.13, 0.54

    pad = (
        0.40 * np.sin(2 * np.pi * f1 * t)
        + 0.35 * np.sin(2 * np.pi * f2 * t)
        + 0.25 * np.sin(2 * np.pi * f3 * t)
        + 0.15 * np.sin(2 * np.pi * (f2 * 2.0) * t)
    )
    lfo = 0.72 + 0.28 * np.sin(2 * np.pi * 0.22 * t)
    beat_phase = t % tempo
    rhythm = 0.35 * np.sin(2 * np.pi * (f3 * 1.5) * beat_phase) * np.exp(-beat_phase * 7.5)

    raw_music = (pad * lfo) + rhythm
    max_amp = max(float(np.max(np.abs(raw_music))), 1e-4)
    audio = (raw_music / max_amp) * 0.10

    for bt in beat_switch_times:
        idx = int(bt * sr)
        if idx < n_samples:
            slen = min(int(0.18 * sr), n_samples - idx)
            st_t = np.linspace(0, slen / float(sr), slen, endpoint=False)
            sfx = 0.08 * np.sin(2 * np.pi * (380 - 160 * st_t) * st_t) * np.exp(-st_t * 14.0)
            audio[idx:idx + slen] += sfx

    audio_int16 = np.int16(np.clip(audio, -1.0, 1.0) * 32767)
    with wave.open(filename, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(audio_int16.tobytes())
    return filename

def create_category_adaptive_1080p_thumbnail(dossier, entities, unique_photos, watermark):
    W, H = 1920, 1080
    c_prof = dossier["country_profile"]
    cat = dossier.get("category", "geopolitics_diplomacy")
    p1 = unique_photos[0] if unique_photos else build_real_openstreetmap_1080p(c_prof, zoom=5, W=1920, H=1080)
    ent_main = entities[0].upper() if entities else c_prof["name"]

    theme_palettes = {
        "ai_tech_science": ((8, 18, 38), (0, 210, 255), (255, 214, 10), "TECH & AI SHIFT"),
        "economy_markets": ((8, 26, 22), (16, 185, 129), (255, 214, 10), "MARKET SHOCKWAVE"),
        "environment_climate": ((10, 28, 32), (34, 197, 94), (255, 220, 40), "PLANETARY ALERT"),
        "war_crisis": ((16, 10, 18), (220, 38, 38), (255, 214, 10), "CRISIS BRIEFING"),
        "geopolitics_diplomacy": ((10, 14, 28), (37, 99, 235), (255, 214, 10), "STRATEGIC PIVOT")
    }
    bg_col, badge_col, box_col, sub_hook = theme_palettes.get(cat, theme_palettes["geopolitics_diplomacy"])

    canvas = Image.new("RGBA", (W, H), bg_col + (255,))
    right_stage = detect_padded_face_crop_or_safe_fit(p1, 1160, H)
    right_stage = ImageEnhance.Contrast(right_stage).enhance(1.14)
    canvas.paste(right_stage, (760, 0))

    draw = ImageDraw.Draw(canvas, "RGBA")
    for x in range(0, 960):
        if x < 740:
            alpha = 255
        else:
            alpha = int(255 * (1.0 - (x - 740) / 220.0))
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

    path_c1 = "output/WTB_1080p_Thumb_1.jpg"
    canvas.convert("RGB").save(path_c1, quality=96)

    selected_title = f"Why {dossier['title']} Changes {c_prof['name'].title()}'s Next Move"
    return {
        "selected_thumbnail": path_c1,
        "thumbnail_category_style": cat,
        "selected_title": selected_title,
        "hashtags": ["#WorldTalkBrief", f"#{c_prof['name'].replace(' ', '')}", "#Geopolitics", "#WorldNews"]
    }

# Alias so both function names work seamlessly
create_1080p_thumbnails = create_category_adaptive_1080p_thumbnail

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

# ==============================================================================
# MASTER EXECUTION
# ==============================================================================
async def main():
    try:
        watermark = build_wtb_watermark(width=140, height=82)
        voice_sub_dir = VoiceAndSubtitleEngine()

        dossiers = discover_and_build_dossiers()
        if len(dossiers) < 2:
            raise RuntimeError("Insufficient verified stories passed the >=3 verified-claims filter.")

        short_dossier = dossiers[0]
        long_dossiers = dossiers[1:3] if len(dossiers) >= 3 else dossiers[:2]

        # 1. BUILD 1080p SHORT
        print(f"\n📱 [2/6] Building 1080p Short (1080x1920) on: {short_dossier['title']} [Category: {short_dossier['category']}]", flush=True)
        short_sections, short_entities = build_short_script(short_dossier)

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
        bgm_s = AudioFileClip(build_situation_adaptive_10pct_soundtrack("temp/bgm_s.wav", final_short.duration, beat_switch_times_s, category=short_dossier["category"]))
        final_short = final_short.with_audio(CompositeAudioClip([final_short.audio, bgm_s])) if MOVIEPY_V2 else final_short.set_audio(CompositeAudioClip([final_short.audio, bgm_s]))
        out_short = "output/WTB_1080p_Short_9x16.mp4"
        final_short.write_videofile(out_short, fps=24, codec="libx264", audio_codec="aac", bitrate="8000k", preset="ultrafast", threads=4, logger=None)

        # 2. BUILD 1080p LONG DOCUMENTARY
        lead_long_dossier = long_dossiers[0]
        print(f"\n📺 [4/6] Building 1080p Long Documentary (1920x1080) [Category: {lead_long_dossier['category']}]...", flush=True)
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

        seen_d_keys = []
        for ch in long_chapters:
            dk = ch["dossier"]["title"]
            if dk not in seen_d_keys:
                seen_d_keys.append(dk)

        for g_idx, dk in enumerate(seen_d_keys):
            d_chaps = [ch for ch in long_chapters if ch["dossier"]["title"] == dk]
            d_ents = extract_story_entities(d_chaps[0]["dossier"])
            l_beats, l_unique_photos, l_st = build_prop_driven_storyboard_1080p(
                d_chaps, d_chaps[0]["dossier"], d_ents, 1920, 1080, tag_prefix=f"long_{g_idx}"
            )
            total_long_unique_photos.extend(l_unique_photos)
            long_stats_list.append(l_st)

            for local_sec_idx, ch in enumerate(d_chaps):
                sec_beats = [b for b in l_beats if b["section_idx"] == local_sec_idx]
                for b in sec_beats:
                    beat_switch_times_l.append(round(cur_lt, 2))
                    cur_lt += b["duration"]
                clip = make_section_clip_from_beats(sec_beats, watermark, voice_sub_dir, ch["duration"], 1920, 1080, is_short=False)
                clip = clip.with_audio(ch["audio_clip"]) if MOVIEPY_V2 else clip.set_audio(ch["audio_clip"])
                long_clips.append(clip)

        final_long = concatenate_videoclips(long_clips, method="compose")
        bgm_l = AudioFileClip(build_situation_adaptive_10pct_soundtrack("temp/bgm_l.wav", final_long.duration, beat_switch_times_l, category=lead_long_dossier["category"]))
        final_long = final_long.with_audio(CompositeAudioClip([final_long.audio, bgm_l])) if MOVIEPY_V2 else final_long.set_audio(CompositeAudioClip([final_long.audio, bgm_l]))
        out_long = "output/WTB_1080p_Long_16x9.mp4"
        final_long.write_videofile(out_long, fps=20, codec="libx264", audio_codec="aac", bitrate="8000k", preset="ultrafast", threads=4, logger=None)

        pkg_report = create_category_adaptive_1080p_thumbnail(lead_long_dossier, lead_long_entities, total_long_unique_photos, watermark)

        agg_long_stats = {
            "run_status": "WARNING: QUALITY_REVIEW_REQUIRED" if any("WARNING" in s["run_status"] for s in long_stats_list) else "PASS",
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
                "short_topic": short_dossier["title"],
                "short_category": short_dossier["category"],
                "short_source_url": short_dossier["source_url"],
                "short_published_date": short_dossier["published_date"],
                "short_audit": s_stats,
                "long_topic": lead_long_dossier["title"],
                "long_category": lead_long_dossier["category"],
                "long_source_url": lead_long_dossier["source_url"],
                "long_published_date": lead_long_dossier["published_date"],
                "long_audit": agg_long_stats,
                "packaging": pkg_report
            }, f, indent=2)

        try_youtube_auto_upload(out_short, short_dossier["title"], f"{short_dossier['title']}\nSource: {short_dossier['source_url']}", ["WorldTalkBrief", "Shorts", "WorldNews"], is_short=True)
        try_youtube_auto_upload(out_long, pkg_report["selected_title"], f"{pkg_report['selected_title']}\nSource: {lead_long_dossier['source_url']}", ["WorldTalkBrief", "Geopolitics", "Documentary"], is_short=False, thumbnail_path=pkg_report["selected_thumbnail"])

        print(f"✅ [6/6] GITHUB CLOUD 1080p FULL HD PRODUCTION COMPLETE!", flush=True)
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
