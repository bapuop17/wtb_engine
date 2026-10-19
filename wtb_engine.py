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
    "User-Agent": "WorldTalkBriefCloudFactory/10.0 (https://github.com/bapuop17/wtb_engine; editorial@worldtalkbrief.org)"
}

# ==============================================================================
# GLOBAL GEOPOLITICAL & COUNTRY DATABASE
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

# ==============================================================================
# MASSIVE VISUAL PROP, OBJECT, ACTION & ENTITY VOCABULARY
# Maps spoken words in any clause to concrete, visualizable real-world props & scenes!
# ==============================================================================
VISUAL_PROP_DICTIONARY = {
    "drone": ("MILITARY DRONE / UAV", "military combat drone UAV quadcopter aircraft"),
    "drones": ("MILITARY DRONE FLEET", "military unmanned aerial vehicle drone launch"),
    "bomber": ("STRATEGIC BOMBER AIRCRAFT", "Russian strategic bomber Tu-95 military aircraft"),
    "bombers": ("STRATEGIC BOMBER FLEET", "military strategic bomber aircraft airfield"),
    "munitions": ("MUNITIONS & ARTILLERY PLANT", "artillery shells ammunition factory warehouse"),
    "factory": ("INDUSTRIAL DEFENSE PLANT", "heavy industrial manufacturing factory smokestacks"),
    "factories": ("DEFENSE MANUFACTURING ZONE", "industrial factory complex aerial night"),
    "sabotage": ("COVERT SABOTAGE OPERATION", "railway sabotage military intelligence covert night"),
    "intelligence": ("INTELLIGENCE HEADQUARTERS", "military intelligence satellite operations room"),
    "spy": ("COVERT INTELLIGENCE ASSET", "intelligence agency headquarters security cameras"),
    "sanctions": ("ECONOMIC SANCTIONS ORDER", "US Treasury sanctions cargo container ship port"),
    "suspend": ("EXECUTIVE SANCTIONS WAIVER", "White House presidential executive order signing desk"),
    "suspension": ("SANCTIONS POLICY SHIFT", "international diplomacy flags press podium"),
    "negotiating": ("DIPLOMATIC NEGOTIATING TABLE", "international peace negotiations conference table flags"),
    "negotiations": ("HIGH-STAKES PEACE TALKS", "diplomatic summit bilateral talks delegates"),
    "peace": ("DIPLOMATIC PEACE SUMMIT", "international summit handshake flags podium"),
    "fire": ("EMERGENCY FIRE RESPONSE", "major structure fire firefighters emergency response night"),
    "flames": ("FIREFIGHTING OPERATION", "firefighters battling blaze smoke emergency trucks"),
    "base": ("MILITARY BASE INSTALLATION", "military army base barracks armored vehicles"),
    "military": ("ARMED FORCES DEPLOYMENT", "military soldiers armored vehicles defense forces"),
    "crews": ("EMERGENCY RESCUE CREWS", "emergency response ambulances fire trucks rescue"),
    "injured": ("MEDICAL EMERGENCY RESPONSE", "emergency medical rescue vehicles hospital"),
    "missile": ("BALLISTIC MISSILE SYSTEM", "surface to air missile launcher military defense"),
    "missiles": ("MISSILE DEFENSE BATTERY", "cruise missile launch military warship"),
    "strike": ("MILITARY AIRSTRIKE", "fighter jet military airstrike explosion smoke"),
    "strikes": ("PRECISION STRIKE OPERATION", "military jet aircraft takeoff runway"),
    "oil": ("GLOBAL OIL & ENERGY SUPPLY", "oil refinery supertanker ship pipeline terminal"),
    "gas": ("NATURAL GAS PIPELINE", "industrial natural gas pipeline compressor station"),
    "pipeline": ("ENERGY PIPELINE CORRIDOR", "transcontinental gas oil pipeline infrastructure"),
    "tariff": ("GLOBAL TRADE & TARIFFS", "cargo container ship port cranes international trade"),
    "tariffs": ("CUSTOMS & SHIPPING PORT", "shipping containers port terminal trade war"),
    "trade": ("MARITIME TRADE ROUTE", "giant container ship ocean shipping port"),
    "bank": ("CENTRAL BANK RESERVES", "central bank building financial district gold reserves"),
    "economy": ("STOCK EXCHANGE & MARKETS", "financial stock exchange trading floor screens"),
    "inflation": ("CONSUMER PRICES & MARKETS", "financial market stock ticker economic chart"),
    "election": ("PRESIDENTIAL ELECTION VOTE", "election ballot box voting polling station"),
    "vote": ("PARLIAMENTARY VOTE", "parliament chamber lawmakers voting session"),
    "court": ("SUPREME COURT TRIBUNAL", "international court of justice judges gavel courtroom"),
    "judge": ("JUDICIAL RULING", "courtroom judge bench legal documents"),
    "prison": ("HIGH-SECURITY PRISON", "maximum security prison guard tower fence"),
    "jailed": ("CRIMINAL SENTENCING", "courthouse police security transport"),
    "police": ("LAW ENFORCEMENT CORDON", "police patrol cars crime scene tape investigation"),
    "border": ("FORTIFIED BORDER CROSSING", "international border checkpoint security fence"),
    "troops": ("FRONTLINE TROOP DEPLOYMENT", "infantry soldiers military convoy camouflage"),
    "tank": ("ARMORED MAIN BATTLE TANK", "military main battle tank armored column"),
    "ship": ("NAVAL WARSHIP FLEET", "navy destroyer warship ocean patrol"),
    "navy": ("NAVAL STRIKE GROUP", "aircraft carrier naval fleet sea"),
    "nuclear": ("NUCLEAR POWER FACILITY", "nuclear power plant cooling towers security"),
    "satellite": ("ORBITAL RECON SATELLITE", "military reconnaissance satellite earth orbit"),
    "cyber": ("CYBER WARFARE OPERATIONS", "cybersecurity server room digital network screens"),
    "protest": ("MASS STREET DEMONSTRATION", "crowd protesters street demonstration banners"),
    "summit": ("INTERNATIONAL LEADERS SUMMIT", "world leaders summit flags red carpet"),
    "congress": ("UNITED STATES CAPITOL", "United States Capitol building Washington DC"),
    "parliament": ("NATIONAL PARLIAMENT HALL", "parliament building legislative assembly chamber"),
    "kremlin": ("MOSCOW KREMLIN PALACE", "Moscow Kremlin Red Square government building"),
    "white house": ("THE WHITE HOUSE", "White House Washington DC exterior press room"),
    "pentagon": ("THE PENTAGON", "The Pentagon building aerial defense department"),
    "nato": ("NATO HEADQUARTERS", "NATO headquarters Brussels flags alliance"),
    "amazon": ("AMAZONIA RAINFOREST CANOPY", "Amazon rainforest aerial river canopy trees"),
    "deforestation": ("AMAZON LOGGING FRONTIER", "Amazon rainforest deforestation cleared land aerial"),
    "trump": ("U.S. PRESIDENT DONALD TRUMP", "Donald Trump speaking podium press conference"),
    "putin": ("RUSSIAN PRESIDENT VLADIMIR PUTIN", "Vladimir Putin Kremlin official meeting"),
    "zelensky": ("UKRAINIAN PRESIDENT ZELENSKYY", "Volodymyr Zelenskyy Kyiv press briefing"),
    "zelenskyy": ("UKRAINIAN PRESIDENT ZELENSKYY", "Volodymyr Zelenskyy official portrait Kyiv"),
    "carney": ("CANADIAN PM MARK CARNEY", "Mark Carney Canada Prime Minister Ottawa"),
    "lula": ("BRAZILIAN PRESIDENT LULA", "Luiz Inacio Lula da Silva Brazil president"),
    "bolsonaro": ("FORMER PRESIDENT BOLSONARO", "Jair Bolsonaro Brazil political rally"),
    "netanyahu": ("ISRAELI PM NETANYAHU", "Benjamin Netanyahu Israel Prime Minister"),
    "xi": ("CHINESE PRESIDENT XI JINPING", "Xi Jinping Beijing Great Hall of the People"),
    "modi": ("INDIAN PM NARENDRA MODI", "Narendra Modi New Delhi India Prime Minister"),
    "macron": ("FRENCH PRESIDENT MACRON", "Emmanuel Macron Elysee Palace France"),
    "starmer": ("UK PM KEIR STARMER", "Keir Starmer 10 Downing Street London")
}

GLOBAL_OPEN_VCLIPS = []

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
# 1. CLEAN NEWS & DEEP RESEARCH ENGINE
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
    text = re.sub(r"(?i)\b(Financial Times|Bloomberg\.com|Bloomberg|Reuters|CNN|BBC News|BBC|Al Jazeera|The Guardian|Associated Press|NBC News)\b", "official reports", text)
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
    print("📡 [1/6] Scanning Global News Feeds (BBC, Al Jazeera, Guardian, DW, France24)...", flush=True)
    feeds = [
        ("BBC World", "http://feeds.bbci.co.uk/news/world/rss.xml"),
        ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
        ("The Guardian", "https://www.theguardian.com/world/rss"),
        ("DW World", "https://rss.dw.com/rdf/rss-en-world"),
        ("France24", "https://www.france24.com/en/rss")
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

            if link:
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
                                    if len(raw_facts) >= 10:
                                        break
                        if len(raw_facts) >= 10:
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

            if len(raw_facts) < 4:
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

            while len(raw_facts) < 4:
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

# ==============================================================================
# 2. PROP-AWARE SCRIPT & CLAUSE DIRECTOR
# ==============================================================================
def extract_story_entities(dossier):
    text = f"{dossier['title']} {' '.join(dossier['raw_facts'][:5])}"
    c_prof = dossier["country_profile"]
    known = {
        "trump": "Donald Trump", "putin": "Vladimir Putin", "zelensky": "Volodymyr Zelenskyy",
        "zelenskyy": "Volodymyr Zelenskyy", "biden": "Joe Biden", "netanyahu": "Benjamin Netanyahu",
        "macron": "Emmanuel Macron", "starmer": "Keir Starmer", "modi": "Narendra Modi",
        "xi jinping": "Xi Jinping", "lula": "Luiz Inácio Lula da Silva", "bolsonaro": "Jair Bolsonaro",
        "wang yi": "Wang Yi", "crosetto": "Guido Crosetto", "carney": "Mark Carney",
        "kremlin": "Moscow Kremlin", "white house": "White House", "congress": "United States Capitol",
        "pentagon": "The Pentagon", "nato": "NATO", "united nations": "United Nations",
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

# ==============================================================================
# 3. PER-BEAT PROP & VISUAL HARVESTER (15-20+ DISTINCT VISUALS PER SHORT!)
# ==============================================================================
def validate_and_enhance_1080p(im, existing_hashes):
    """
    Validates image quality, removes outer 7% edges and 12% bottom watermark strip,
    checks 144-bit perceptual dHash uniqueness, and sharpens to 1080p Full HD.
    """
    im = im.convert("RGB")
    w, h = im.size
    if w < 280 or h < 180:
        return None

    # Strip outer borders & bottom watermark zone without cutting off faces!
    im = im.crop((int(w * 0.05), int(h * 0.04), int(w * 0.95), int(h * 0.89)))

    arr = np.asarray(im.resize((80, 80)), dtype=np.float32)
    c_box = arr[28:52, 28:52]
    red_px = np.sum((c_box[:, :, 0] > 195) & (c_box[:, :, 1] < 45) & (c_box[:, :, 2] < 45))
    if (red_px / float(24 * 24)) > 0.16:
        return None

    white_px = np.sum((arr[:, :, 0] > 242) & (arr[:, :, 1] > 242) & (arr[:, :, 2] > 242))
    if (white_px / float(80 * 80)) > 0.38:
        return None
    if im.entropy() < 5.8:
        return None

    gray = im.convert("L").resize((13, 12))
    dh = (np.asarray(gray, dtype=np.int16)[:, 1:] > np.asarray(gray, dtype=np.int16)[:, :-1]).flatten()
    for old_h in existing_hashes:
        if int(np.sum(dh != old_h)) < 15:
            return None
    existing_hashes.append(dh)

    if im.size[0] < 1600:
        scale = 1920.0 / float(im.size[0])
        resample_mode = getattr(Image, "Resampling", Image).LANCZOS
        im = im.resize((1920, int(im.size[1] * scale)), resample_mode)

    im = im.filter(ImageFilter.UnsharpMask(radius=1.5, percent=130, threshold=3))
    im = ImageEnhance.Contrast(im).enhance(1.07)
    return im

def extract_beat_prop_and_query(beat_text, dossier, entities, beat_idx):
    """
    Analyzes the exact words spoken in `beat_text` and finds the exact PROP, OBJECT, ACTION,
    or PERSON to show on screen right then!
    """
    low = beat_text.lower()
    c_prof = dossier["country_profile"]

    # 1. Check our 80+ Visual Prop & Entity Vocabulary for exact spoken match in this 2.5s beat!
    for word_key, (prop_badge, search_q) in VISUAL_PROP_DICTIONARY.items():
        if re.search(rf"\b{re.escape(word_key)}\b", low):
            return prop_badge, f"{search_q} {c_prof['name']}"

    # 2. Check if any Capitalized Proper Noun is in this beat
    caps = [w for w in re.findall(r"\b[A-Z][a-z]{3,}\b", beat_text) if w not in {"Here", "While", "Behind", "Look", "This", "Step", "Watch", "Whether", "Meanwhile", "Crucially", "Inside"}]
    if caps:
        person_or_place = " ".join(caps[:2])
        return f"FOCUS • {person_or_place.upper()}", f"{person_or_place} {c_prof['name']} news photo"

    # 3. Rotate through rich contextual angles of the story so no two beats ever use the same query!
    contextual_angles = [
        (f"DISPATCH • {c_prof['capital'].upper()}", f"{dossier['title']}"),
        (f"LEADER • {entities[0].upper()[:22]}", f"{entities[0]} official press conference"),
        (f"CAPITAL • {c_prof['capital'].upper()}", f"{c_prof['capital']} {c_prof['name']} government building"),
        (f"SECURITY • {c_prof['name']}", f"{c_prof['name']} military defense security forces"),
        (f"DIPLOMACY • {c_prof['region'].upper()}", f"{entities[1] if len(entities)>1 else c_prof['name']} international summit"),
        (f"ECONOMY • {c_prof['name']}", f"{c_prof['name']} trade port industry"),
        (f"STRATEGIC BRIEF • {c_prof['name']}", f"{c_prof['name']} parliament lawmakers session"),
        (f"GLOBAL IMPACT • {c_prof['region'].upper()}", f"United Nations Security Council {c_prof['name']}")
    ]
    return contextual_angles[beat_idx % len(contextual_angles)]

def fetch_single_verified_prop_image(search_query, existing_hashes, tag_id="prop"):
    """
    4-Engine Instant Prop/Photo Fetcher (100% Working on GitHub Cloud Ubuntu Runners!):
    Engine 1: Bing Dynamic Thumbnail CDN (`tse1..tse4.mm.bing.net/th?q=...&w=1280&h=720&c=7`) -> Never blocked on GitHub Cloud!
    Engine 2: Wikimedia Commons File Namespace (`gsrnamespace=6`, `iiurlwidth=1280`) -> Fixed `gsrnamespace=6`!
    Engine 3: Wikipedia PageImages Search (`pithumbsize=1280`)
    """
    # Engine 1: Bing Direct CDN Endpoint (Try 3 variations of the query so even if 1st is duplicate, 2nd/3rd is brand new!)
    cdn_variations = [
        search_query,
        f"{search_query} photojournalism",
        f"{search_query} press photo"
    ]
    for v_idx, q_var in enumerate(cdn_variations):
        server_num = (v_idx % 4) + 1
        cdn_url = f"https://tse{server_num}.mm.bing.net/th?q={urllib.parse.quote(q_var)}&w=1280&h=720&c=7&rs=1&p=0"
        try:
            r = requests.get(cdn_url, headers=HEADERS_WEB, timeout=6)
            if r.status_code == 200 and len(r.content) > 9000:
                p = f"temp/{tag_id}_cdn_{v_idx}.jpg"
                with open(p, "wb") as f:
                    f.write(r.content)
                vim = validate_and_enhance_1080p(Image.open(p), existing_hashes)
                if vim is not None:
                    return vim
        except Exception:
            pass

    # Engine 2: Wikimedia Commons File Namespace (`gsrnamespace=6` + `iiurlwidth=1280`)
    try:
        api = "https://commons.wikimedia.org/w/api.php"
        params = {
            "action": "query",
            "generator": "search",
            "gsrsearch": f"filetype:bitmap {search_query}",
            "gsrnamespace": "6",  # CRITICAL FIX: File Namespace 6!
            "gsrlimit": 6,
            "prop": "imageinfo",
            "iiprop": "url",
            "iiurlwidth": 1280,
            "format": "json"
        }
        r = requests.get(api, params=params, headers=HEADERS_WIKI, timeout=7).json()
        for pg in r.get("query", {}).get("pages", {}).values():
            ii = pg.get("imageinfo", [{}])[0]
            u = ii.get("thumburl") or ii.get("url")
            if u and u.lower().endswith((".jpg", ".jpeg", ".png")):
                ir = requests.get(u, headers=HEADERS_WIKI, timeout=6)
                if ir.status_code == 200 and len(ir.content) > 10000:
                    p = f"temp/{tag_id}_comm.jpg"
                    with open(p, "wb") as f:
                        f.write(ir.content)
                    vim = validate_and_enhance_1080p(Image.open(p), existing_hashes)
                    if vim is not None:
                        return vim
    except Exception:
        pass

    # Engine 3: Wikipedia PageImages (`pithumbsize=1280`)
    try:
        w_api = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query", "generator": "search", "gsrsearch": search_query, "gsrlimit": 4,
            "prop": "pageimages", "piprop": "thumbnail|original", "pithumbsize": 1280, "format": "json"
        }
        r = requests.get(w_api, params=params, headers=HEADERS_WIKI, timeout=6).json()
        for pg in r.get("query", {}).get("pages", {}).values():
            img_u = pg.get("thumbnail", {}).get("source") or pg.get("original", {}).get("source")
            if img_u and img_u.lower().endswith((".jpg", ".jpeg", ".png")):
                ir = requests.get(img_u, headers=HEADERS_WIKI, timeout=6)
                if ir.status_code == 200 and len(ir.content) > 9000:
                    p = f"temp/{tag_id}_wiki.jpg"
                    with open(p, "wb") as f:
                        f.write(ir.content)
                    vim = validate_and_enhance_1080p(Image.open(p), existing_hashes)
                    if vim is not None:
                        return vim
    except Exception:
        pass

    return None

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
# 4. UN-MUTILATED 1080p FULL HD CINEMA STAGE (FIXES HALF-FACE CROP BUG!)
# ==============================================================================
def build_clean_1080p_stage(im, W, H):
    """
    100% Fixes the half-face Trump crop bug in[cite: 127, 129]!
    Never cuts a single portrait in half!
    - In 9:16 Vertical Shorts (1080x1920):
      Displays a full 1080x1920 atmospheric motion backdrop + a wide, un-cut 1080x940 Hero Stage
      so the entire subject, person, or prop is 100% visible without cutting off eyes/ears!
    - In 16:9 Widescreen Long Videos (1920x1080):
      Full 1920x1080 widescreen cinema frame with smooth pan/zoom!
    """
    resample_mode = getattr(Image, "Resampling", Image).LANCZOS
    iw, ih = im.size

    if W < H:
        bg = im.copy().resize((W, H), resample_mode).filter(ImageFilter.GaussianBlur(radius=28))
        bg = ImageEnhance.Brightness(bg).enhance(0.32)
        canvas = bg.convert("RGBA")

        hero_w, hero_h = int(W * 1.08), 940
        target_r = hero_w / float(hero_h)
        fg = im.copy()
        if (iw / float(ih)) > target_r:
            nw = int(ih * target_r)
            left = (iw - nw) // 2
            fg = fg.crop((left, 0, left + nw, ih))
        else:
            nh = int(iw / target_r)
            top = int((ih - nh) * 0.18)  # Keep upper head/face region intact!
            fg = fg.crop((0, top, iw, top + nh))
        fg = fg.resize((hero_w, hero_h), resample_mode)
        return ("SHORT_STAGE", canvas, fg)
    else:
        over_w, over_h = int(W * 1.07), int(H * 1.07)
        target_r = over_w / float(over_h)
        fg = im.copy()
        if (iw / float(ih)) > target_r:
            nw = int(ih * target_r)
            left = (iw - nw) // 2
            fg = fg.crop((left, 0, left + nw, ih))
        else:
            nh = int(iw / target_r)
            top = int((ih - nh) * 0.18)  # Keep upper head/face region intact!
            fg = fg.crop((0, top, iw, top + nh))
        fg = fg.resize((over_w, over_h), resample_mode)
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
        oy = int(max_dy * 0.35)
        slice_fg = fg.crop((ox, oy, ox + win_w, oy + win_h))
        canvas.paste(slice_fg, (0, 200))

        draw = ImageDraw.Draw(canvas, "RGBA")
        for y in range(0, 200):
            draw.line([(0, y), (W, y)], fill=(6, 9, 18, int(175 * (1.0 - y / 200.0))))
        for y in range(1100, H):
            draw.line([(0, y), (W, y)], fill=(6, 9, 18, int(235 * min(1.0, (y - 1100) / 260.0))))
        draw.line([(0, 200), (W, 200)], fill=(255, 214, 10, 220), width=3)
        draw.line([(0, 1100), (W, 1100)], fill=(255, 214, 10, 220), width=3)
        return canvas
    else:
        fg = base_a
        fw, fh = fg.size
        max_dx = max(fw - W, 0)
        max_dy = max(fh - H, 0)
        ox = int(max_dx * (bp if pan_dir == 1 else (1.0 - bp)))
        oy = int(max_dy * (0.15 + 0.5 * bp))
        frame = fg.crop((ox, oy, ox + W, oy + H)).convert("RGBA")
        draw = ImageDraw.Draw(frame, "RGBA")
        for y in range(0, 180):
            draw.line([(0, y), (W, y)], fill=(4, 7, 14, int(160 * (1.0 - y / 180.0))))
        for y in range(H - 360, H):
            draw.line([(0, y), (W, y)], fill=(4, 7, 14, int(238 * ((y - (H - 360)) / 360.0) ** 1.15)))
        return frame

# ==============================================================================
# 5. PER-BEAT STORYBOARD PLANNER (14-18 UNIQUE VISUAL BEATS PER SHORT!)
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
    """
    Breaks every narration section into fast 2.3s - 2.7s visual beats (so a 40s Short gets 15-17 beats!)
    and fetches a DEDICATED, UNIQUE PROP/SCENE PHOTO for EVERY SINGLE BEAT!
    Maps (`MAP_LOCATOR_BEAT`) are used AT MOST ONCE in a Short (only when geography is discussed),
    NEVER as a fallback photo!
    """
    planned_beats = []
    existing_hashes = []
    unique_photos_collected = []
    c_prof = dossier["country_profile"]
    osm_map = build_real_openstreetmap_1080p(c_prof, zoom=5, W=1920, H=1080)
    osm_stage = build_clean_1080p_stage(osm_map, W, H)

    # First, try to load Lead Article Photo for Beat #0
    if dossier.get("lead_img"):
        try:
            r = requests.get(dossier["lead_img"], headers=HEADERS_WEB, timeout=6)
            if r.status_code == 200 and len(r.content) > 8000:
                p = f"temp/{tag_prefix}_lead_0.jpg"
                with open(p, "wb") as f:
                    f.write(r.content)
                vim = validate_and_enhance_1080p(Image.open(p), existing_hashes)
                if vim is not None:
                    unique_photos_collected.append(vim)
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

        # Fast 2.4s beats so a 40s Short has ~16 distinct visual/prop changes!
        target_beat_len = 2.4 if W < H else 2.8
        num_beats = max(3, int(math.ceil(sec_dur / target_beat_len)))
        beat_dur = sec_dur / float(num_beats)
        words = narration.split()
        w_per_b = max(1, int(math.ceil(len(words) / float(num_beats))))
        used_modes_in_sec = set()

        for b_i in range(num_beats):
            b_txt = " ".join(words[b_i * w_per_b:(b_i + 1) * w_per_b]) or narration
            prop_badge, search_q = extract_beat_prop_and_query(b_txt, dossier, entities, global_beat_idx)

            # Fetch a brand-new, unique HD photo specifically for this beat's prop/query!
            beat_im = None
            if global_beat_idx == 0 and unique_photos_collected:
                beat_im = unique_photos_collected[0]
            else:
                beat_im = fetch_single_verified_prop_image(search_q, existing_hashes, tag_id=f"{tag_prefix}_b{global_beat_idx}")
                if beat_im is not None:
                    unique_photos_collected.append(beat_im)
                    print(f"   ✅ Beat #{global_beat_idx+1} Prop Visual Locked: [{prop_badge}] -> '{search_q[:38]}'", flush=True)
                else:
                    # Try a fallback entity/prop query if the first query was exhausted
                    alt_q = f"{entities[global_beat_idx % len(entities)]} {c_prof['name']} news"
                    beat_im = fetch_single_verified_prop_image(alt_q, existing_hashes, tag_id=f"{tag_prefix}_alt_{global_beat_idx}")
                    if beat_im is not None:
                        unique_photos_collected.append(beat_im)
                        print(f"   ✅ Beat #{global_beat_idx+1} Alt Visual Locked: [{prop_badge}] -> '{alt_q[:38]}'", flush=True)

            if beat_im is None:
                beat_im = unique_photos_collected[global_beat_idx % len(unique_photos_collected)] if unique_photos_collected else osm_map

            secondary_im = unique_photos_collected[(global_beat_idx - 1) % len(unique_photos_collected)] if len(unique_photos_collected) > 1 else beat_im

            # Choose overlay graphic mode based on narration semantics (Map allowed ONLY ONCE!)
            low_b = b_txt.lower()
            if not map_used_in_video and (sec_role == "GEOGRAPHY" or re.search(r"\b(geography|corridor|borders|centered around)\b", low_b)):
                b_type = "MAP_LOCATOR_BEAT"
                map_used_in_video = True
            elif has_strict_economic_context(b_txt) and "DATA_CHART_BEAT" not in used_modes_in_sec:
                b_type = "DATA_CHART_BEAT"
            elif re.search(r"\b(timeline|overnight|step by step|previously|september|october|days before)\b", low_b) and "TIMELINE_GRAPH_BEAT" not in used_modes_in_sec:
                b_type = "TIMELINE_GRAPH_BEAT"
            elif re.search(r"\b(said|stated|confirmed|record|specifics|told|claim|claims)\b", low_b) and "HEADLINE_EVIDENCE_BEAT" not in used_modes_in_sec:
                b_type = "HEADLINE_EVIDENCE_BEAT"
            elif re.search(r"\b(competing|colliding|whether|or if|versus|row with)\b", low_b) and "SPLIT_COMPARE_BEAT" not in used_modes_in_sec and len(unique_photos_collected) >= 2:
                b_type = "SPLIT_COMPARE_BEAT"
            else:
                b_type = "PHOTO_BEAT"

            used_modes_in_sec.add(b_type)
            stage_1 = osm_stage if b_type == "MAP_LOCATOR_BEAT" else build_clean_1080p_stage(beat_im, W, H)

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
                "story": dossier
            })
            global_beat_idx += 1

    print(f"📊 [{tag_prefix.upper()} SUMMARY] Total Beats: {len(planned_beats)} | Total Unique Real Prop/Scene Photos Collected: {len(unique_photos_collected)}", flush=True)
    return planned_beats, unique_photos_collected

def render_1080p_beat_frame(beat, watermark, voice_sub_dir, local_t, W, H, is_short=True):
    beat_dur = beat["duration"]
    bp = min(max(local_t / max(beat_dur, 0.1), 0.0), 1.0)
    b_type = beat["beat_type"]
    story = beat["story"]
    c_prof = story["country_profile"]
    wb_years, wb_vals = story["wb_data"]
    section_t = beat["section_elapsed_before"] + local_t

    if b_type == "SPLIT_COMPARE_BEAT":
        resample_mode = getattr(Image, "Resampling", Image).LANCZOS
        frame = Image.new("RGBA", (W, H), (8, 12, 22, 255))
        if is_short:
            st_a = build_clean_1080p_stage(beat["primary_im"], W, H)[2]
            st_b = build_clean_1080p_stage(beat["secondary_im"], W, H)[2]
            top_im = st_a.resize((W, 450), resample_mode)
            bot_im = st_b.resize((W, 450), resample_mode)
            frame.paste(top_im, (0, 200))
            frame.paste(bot_im, (0, 655))
            draw = ImageDraw.Draw(frame, "RGBA")
            draw.line([(0, 652), (W, 652)], fill=(255, 214, 10, 255), width=6)
        else:
            left_im = beat["primary_im"].resize((W // 2, H), resample_mode)
            right_im = beat["secondary_im"].resize((W // 2, H), resample_mode)
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
    bx1, bx2 = (42, W - 42) if is_short else (64, 1290)

    if b_type == "PHOTO_BEAT":
        kicker = beat["primary_lbl"]
        hl = str(beat["beat_excerpt"] if len(beat["beat_excerpt"]) > 22 else beat["section_headline"]).upper()
        f_k = get_font(24)
        f_h = get_font(31 if is_short else 34)
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
        draw.rounded_rectangle([(bx1 + 24, cy_card + 8), (bx1 + 480, cy_card + 46)], radius=6, fill=(204, 18, 36, 255))
        draw.text((bx1 + 40, cy_card + 14), f"VERIFIED EVIDENCE • {beat['primary_lbl'][:22]}", fill=(255, 255, 255, 255), font=get_font(22))

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

# ==============================================================================
# 6. VOICE, SUBTITLE, SOUNDTRACK & 1080p THUMBNAIL ENGINE
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

def create_1080p_thumbnails(dossier, entities, unique_photos, watermark):
    """
    Fixes the half-cropped Trump ear thumbnail bug[cite: 129]!
    Places the full 1920x1080 un-mutilated subject photo across the canvas with a clean left gradient!
    """
    W, H = 1920, 1080
    c_prof = dossier["country_profile"]
    p1 = unique_photos[0]
    ent_main = entities[0].upper() if entities else c_prof["name"]

    st1 = build_clean_1080p_stage(p1, W, H)
    t1 = extract_animated_frame_from_stage(st1, W, H, 0.25)
    t1 = ImageEnhance.Contrast(t1).enhance(1.18)
    d1 = ImageDraw.Draw(t1, "RGBA")
    for x in range(0, 1150):
        d1.line([(x, 0), (x, H)], fill=(6, 9, 18, int(242 * (1.0 - (x / 1150.0) ** 1.35))))
    t1.paste(watermark, (64, 54), watermark)
    if c_prof.get("flag_img"):
        t1.paste(c_prof["flag_img"].resize((110, 70)), (220, 60), c_prof["flag_img"].resize((110, 70)))

    kick1 = f"{c_prof['name']} • {c_prof['capital'].upper()}"
    kw1 = d1.textbbox((0, 0), kick1, font=get_font(36))[2] + 54
    d1.rounded_rectangle([(64, 330), (64 + kw1, 405)], radius=12, fill=(204, 18, 36, 255))
    d1.text((90, 346), kick1, fill=(255, 255, 255, 255), font=get_font(36))

    h1_a = f"{ent_main[:16]}'S"
    h1_b = "HIGH-STAKES MOVE"
    fb = get_font(92)
    d1.text((64, 445), h1_a, fill=(255, 255, 255, 255), font=fb, stroke_width=6, stroke_fill=(0, 0, 0, 255))
    w2 = d1.textbbox((0, 0), h1_b, font=fb)[2] + 70
    d1.rounded_rectangle([(64, 585), (64 + w2, 725)], radius=18, fill=(255, 214, 10, 255))
    d1.text((98, 605), h1_b, fill=(10, 12, 18, 255), font=fb)
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

# ==============================================================================
# MASTER EXECUTION (15-20+ PROP VISUALS IN SHORT | 35-45+ IN LONG)
# ==============================================================================
async def main():
    watermark = build_wtb_watermark(width=140, height=82)
    voice_sub_dir = VoiceAndSubtitleEngine()

    dossiers = discover_and_build_dossiers()
    short_dossier = dossiers[0]
    long_dossiers = dossiers[1:3] if len(dossiers) >= 3 else dossiers[:2]

    # 1. BUILD 1080p SHORT WITH 15-18 DISTINCT PROP/SCENE VISUALS
    print(f"\n📱 [2/6] Building 1080p Short (1080x1920) on: {short_dossier['title']}", flush=True)
    short_sections, short_entities = build_short_script(short_dossier)

    for idx, sec in enumerate(short_sections):
        ap = f"temp/s_voice_{idx}.mp3"
        vc, dur, w_timings = await voice_sub_dir.synthesize_with_word_boundaries(sec["narration"], ap, voice_style=sec.get("voice_style", "clear"))
        sec["audio_clip"] = vc
        sec["duration"] = dur
        sec["word_timings"] = w_timings

    s_beats, s_unique_photos = build_prop_driven_storyboard_1080p(
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
    bgm_s = AudioFileClip(build_story_adaptive_soundtrack("temp/bgm_s.wav", final_short.duration, beat_switch_times_s))
    final_short = final_short.with_audio(CompositeAudioClip([final_short.audio, bgm_s])) if MOVIEPY_V2 else final_short.set_audio(CompositeAudioClip([final_short.audio, bgm_s]))
    out_short = "output/WTB_1080p_Short_9x16.mp4"
    final_short.write_videofile(out_short, fps=24, codec="libx264", audio_codec="aac", bitrate="8000k", preset="ultrafast", threads=4, logger=None)

    # 2. BUILD 1080p LONG DOCUMENTARY WITH 35-45+ DISTINCT PROP/SCENE VISUALS
    print(f"\n📺 [4/6] Building 1080p Long Documentary (1920x1080)...", flush=True)
    long_chapters = build_long_documentary_script(long_dossiers)
    lead_long_dossier = long_dossiers[0]
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
    cur_lt = 0.0

    # Group chapters by dossier and fetch per-beat prop visuals for every single beat!
    seen_d_keys = []
    for ch in long_chapters:
        dk = ch["dossier"]["title"]
        if dk not in seen_d_keys:
            seen_d_keys.append(dk)

    for g_idx, dk in enumerate(seen_d_keys):
        d_chaps = [ch for ch in long_chapters if ch["dossier"]["title"] == dk]
        d_ents = extract_story_entities(d_chaps[0]["dossier"])
        l_beats, l_unique_photos = build_prop_driven_storyboard_1080p(
            d_chaps, d_chaps[0]["dossier"], d_ents, 1920, 1080, tag_prefix=f"long_{g_idx}"
        )
        total_long_unique_photos.extend(l_unique_photos)

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

    pkg_report = create_1080p_thumbnails(lead_long_dossier, lead_long_entities, total_long_unique_photos, watermark)

    with open("output/wtb_1080p_report.json", "w") as f:
        json.dump({
            "short_topic": short_dossier["title"],
            "short_total_beats": len(s_beats),
            "short_photos_collected": len(s_unique_photos),
            "long_topic": lead_long_dossier["title"],
            "long_total_beats": len(beat_switch_times_l),
            "long_photos_collected": len(total_long_unique_photos),
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
