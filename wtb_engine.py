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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9"
}
HEADERS_WIKI = {
    "User-Agent": "WorldTalkBriefBroadcastStudio/27.0 (https://github.com/bapuop17/wtb_engine; editorial@worldtalkbrief.org)"
}

HISTORY_FILE = "published_history.json"

# ==============================================================================
# 1. ALL 8 CONTENT PILLARS WITH GEN-2 NATURAL HUMAN CONVERSATIONAL VOICES
#    (Zero pitch-warping, zero robotic 1st-gen voices!)
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

# ONLY Gen-2 Ultra-Natural Conversational Voices (with natural human breathing & warm timbre)
CATEGORY_VOICE_CAST = {
    "WORLD": "en-US-AndrewMultilingualNeural",
    "TECHNOLOGY": "en-US-BrianMultilingualNeural",
    "MIND_BLOWING_FACTS": "en-US-AndrewMultilingualNeural",
    "SCIENCE": "en-US-BrianMultilingualNeural",
    "BUSINESS": "en-US-AndrewMultilingualNeural",
    "HEALTH": "en-US-AvaMultilingualNeural",
    "SPORTS": "en-US-BrianMultilingualNeural",
    "ENTERTAINMENT": "en-US-EmmaMultilingualNeural"
}

CATEGORY_FEEDS = {
    "WORLD": {
        "yt_category_id": "25",
        "playlist_title": "World Talk Brief • Global Geopolitics & World News",
        "badge_color": (204, 18, 36),
        "accent_color": (255, 214, 10),
        "hook_tag": "GEOPOLITICAL CASE STUDY",
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
        "badge_color": (0, 140, 255),
        "accent_color": (0, 235, 255),
        "hook_tag": "TECH & AI EXPLAINED",
        "search_query": "artificial intelligence humanoid robot gaming nvidia technology",
        "feeds": [
            ("TechCrunch AI & Tech", "https://techcrunch.com/feed/"),
            ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
            ("BBC Technology", "http://feeds.bbci.co.uk/news/technology/rss.xml"),
            ("The Guardian Tech", "https://www.theguardian.com/uk/technology/rss")
        ]
    },
    "MIND_BLOWING_FACTS": {
        "yt_category_id": "27",
        "playlist_title": "World Talk Brief • Mind-Blowing Facts & World Mysteries",
        "badge_color": (185, 20, 220),
        "accent_color": (255, 225, 0),
        "hook_tag": "MIND-BLOWING CASE STUDY",
        "search_query": "unbelievable facts scientific mystery mind blowing discovery",
        "feeds": [
            ("Smithsonian SmartNews", "https://www.smithsonianmag.com/rss/smart-news/"),
            ("SciTechDaily Discoveries", "https://scitechdaily.com/feed/"),
            ("Phys.org Breakthroughs", "https://phys.org/rss-feed/")
        ]
    },
    "SCIENCE": {
        "yt_category_id": "28",
        "playlist_title": "World Talk Brief • Space, NASA & Future Science",
        "badge_color": (110, 45, 225),
        "accent_color": (0, 230, 255),
        "hook_tag": "SPACE & SCIENCE",
        "search_query": "space nasa spacex astronomy quantum discovery",
        "feeds": [
            ("Space.com", "https://www.space.com/feeds/all"),
            ("BBC Science & Environment", "http://feeds.bbci.co.uk/news/science_and_environment/rss.xml"),
            ("The Guardian Science", "https://www.theguardian.com/science/rss")
        ]
    },
    "BUSINESS": {
        "yt_category_id": "25",
        "playlist_title": "World Talk Brief • Business, Markets & Global Economy",
        "badge_color": (16, 165, 110),
        "accent_color": (255, 214, 10),
        "hook_tag": "MARKETS & ECONOMY",
        "search_query": "global economy stock market business billionaire trade",
        "feeds": [
            ("CNBC Business", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147"),
            ("BBC Business", "http://feeds.bbci.co.uk/news/business/rss.xml"),
            ("The Guardian Business", "https://www.theguardian.com/uk/business/rss"),
            ("DW Business", "https://rss.dw.com/rdf/rss-en-bus")
        ]
    },
    "HEALTH": {
        "yt_category_id": "28",
        "playlist_title": "World Talk Brief • Health, Biotech & Medical Science",
        "badge_color": (14, 155, 145),
        "accent_color": (255, 220, 40),
        "hook_tag": "BIOTECH BREAKTHROUGH",
        "search_query": "medical breakthrough human brain health longevity",
        "feeds": [
            ("BBC Health", "http://feeds.bbci.co.uk/news/health/rss.xml"),
            ("The Guardian Health", "https://www.theguardian.com/society/health/rss"),
            ("SciTechDaily Health", "https://scitechdaily.com/news/health/feed/")
        ]
    },
    "SPORTS": {
        "yt_category_id": "17",
        "playlist_title": "World Talk Brief • Global Sports Arena",
        "badge_color": (230, 85, 15),
        "accent_color": (255, 214, 10),
        "hook_tag": "GLOBAL SPORTS ARENA",
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
        "accent_color": (255, 214, 10),
        "hook_tag": "CINEMA & CULTURE",
        "search_query": "movies box office gaming marvel gta entertainment",
        "feeds": [
            ("BBC Entertainment & Arts", "http://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml"),
            ("The Guardian Film", "https://www.theguardian.com/uk/film/rss"),
            ("Hollywood Reporter", "https://www.hollywoodreporter.com/feed/")
        ]
    }
}

# ==============================================================================
# 2. COMPLETE WORLD GEOPOLITICAL DATABASE
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
    "EGYPT": ("EG", "EGY", "Cairo", "112 million", "North Africa", 30.044, 31.235),
    "SOUTH AFRICA": ("ZA", "ZAF", "Pretoria", "60 million", "Southern Africa", -25.747, 28.229),
    "NIGERIA": ("NG", "NGA", "Abuja", "223 million", "West Africa", 9.076, 7.398),
    "KENYA": ("KE", "KEN", "Nairobi", "55 million", "East Africa", -1.292, 36.821),
    "DR CONGO": ("CD", "COD", "Kinshasa", "102 million", "Central Africa", -4.441, 15.266)
}

DEMONYM_TO_COUNTRY = {
    "barcelona": "SPAIN", "real madrid": "SPAIN", "la liga": "SPAIN", "madrid": "SPAIN", "spanish": "SPAIN",
    "england": "UNITED KINGDOM", "scotland": "UNITED KINGDOM", "wales": "UNITED KINGDOM", "nhs": "UNITED KINGDOM",
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
    "brazilian": "BRAZIL", "brasilia": "BRAZIL", "lula": "BRAZIL",
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
    "ytimg", "youtube", "cartoon", "clipart", "meme", "watermark", "agefotostock", "pond5"
]

PERSON_WIKI_MAP = {
    "antonelli": ("Andrea Kimi Antonelli", "MERCEDES F1 DRIVER KIMI ANTONELLI", "ITALY"),
    "verstappen": ("Max Verstappen", "RED BULL CHAMPION MAX VERSTAPPEN", "NETHERLANDS"),
    "hamilton": ("Lewis Hamilton", "FERRARI F1 STAR LEWIS HAMILTON", "UNITED KINGDOM"),
    "leclerc": ("Charles Leclerc", "FERRARI DRIVER CHARLES LECLERC", "ITALY"),
    "russell": ("George Russell (racing driver)", "MERCEDES DRIVER GEORGE RUSSELL", "UNITED KINGDOM"),
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
    "grok": ("XAI GROK MODEL", "Grok (chatbot)", "Grok xAI Elon Musk artificial intelligence"),
    "chatgpt": ("OPENAI CHATGPT", "ChatGPT", "ChatGPT OpenAI artificial intelligence"),
    "openai": ("OPENAI & GPT MODELS", "OpenAI", "OpenAI Sam Altman artificial intelligence"),
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
    "nvidia": ("NVIDIA AI CHIPS", "Nvidia", "Nvidia GPU semiconductor microchip"),
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

def build_wtb_watermark(width=140, height=82):
    logo = Image.new("RGBA", (260, 156), (255, 255, 255, 248))
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
# 3. FULL YOUTUBE DATA API v3 INTELLIGENCE + ALL 8 PLAYLISTS PRE-CREATION
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
                                "description": f"Official {target_pl_title} deep-dive explainers and shorts by World Talk Brief."
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
        return default_viral_kws, [], {}

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
                        if 3 <= len(tg) <= 28 and len(re.findall(r"[A-Za-z]", tg)) >= 3 and tg not in viral_yt_tags:
                            if not any(non_en in tg.lower() for non_en in ["telugu", "tamil", "hindi", "malayalam", "kannada"]):
                                viral_yt_tags.append(tg)
                    for w in re.findall(r"[a-z]{4,}", t_title.lower()):
                        if w not in stop_w and w not in winning_kws:
                            winning_kws.append(w)
            except Exception:
                pass

        for dkw in default_viral_kws:
            if dkw not in winning_kws:
                winning_kws.append(dkw)
        return winning_kws[:25], viral_yt_tags[:18], playlist_map
    except Exception:
        return default_viral_kws, [], {}

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
                            "textOriginal": f"📌 KEY TAKEAWAY: {summary_takeaway}\nWhat is your perspective on this development? Share your analysis below! 👇"
                        }
                    }
                }
            }
        ).execute()
        print(f"💬 [YouTube API Engagement Comment Posted] on Video {video_id}", flush=True)
    except Exception:
        pass

# ==============================================================================
# 4. NON-REPEATING HISTORY & STRICT URL / PRESS-RELEASE / AWKWARD TOPIC BLOCKER
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
                    "round_robin_idx": int(data.get("round_robin_idx", 0))
                }
        except Exception:
            pass
    return {"published_keys": set(), "event_fingerprints": [], "last_categories": [], "last_sources": [], "round_robin_idx": 0}

def save_published_history(hist_obj):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "updated_at": datetime.utcnow().isoformat(),
                "round_robin_idx": int(hist_obj.get("round_robin_idx", 0)),
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
        if overlap >= 0.50:
            return ("DUPLICATE", None)

    return ("NEW_STORY", None)

BANNED_ARTICLE_TITLES = [
    "uti", "utis", "urinary", "bladder", "bowel", "diarrhea", "constipation", "erectile", "sexually transmitted",
    "ovaries", "ovary", "menopause", "menstrual", "pregnancy", "fertility", "nathan fielder", "kill switch",
    "lance oppenheim", "indiewire", "birthday sale", "percent off", "% off", "sitewide", "promo code", "coupon",
    "best deals", "buying guide", "gift guide", "review:", "we tested", "horoscope", "wordle", "crossword",
    "sudoku", "live updates", "as it happened", "in pictures", "at a glance", "podcast", "quiz", "bandcamp",
    "synth-pop", "album review", "song review", "obsessed with scammers", "how to watch", "tv channel",
    "live stream", "prediction, team news", "power partnership"
]

BANNED_PHRASES = [
    "https://", "http://", "https/", "http/", "www.", ".gov", ".org/", ".com/",
    "for more information on", "visit https", "explore langley", "communications strategist",
    "turning what if into what will be", "popular on variety", "popular on ", "related:", "read more:",
    "also read:", "external ", "weeing lava", "need a wee", "founder summit", "buy one",
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
    "nbc news' ", "talks with ", "speaks with "
]

def clean_fact(text):
    """
    Transforms raw journalistic/press-release sentences into clean, conversational Nitish Rajput / Abhi & Niyu
    style spoken English! Strips URLs (`https/www.mnasa.gov`), PR titles (`Communications strategist`),
    and awkward newspaper attributions!
    """
    if not text:
        return ""
    repl = {"\u2011": "-", "\u2013": "-", "\u2014": " - ", "\u2018": "'", "\u2019": "'", "\u201c": "", "\u201d": "", '"': "", "\u00a0": " "}
    for k, v in repl.items():
        text = text.replace(k, v)

    if len(re.findall(r"\b(WHO|WHAT|WHERE|WHEN|HOW TO FOLLOW)\s*:", text)) >= 2:
        return ""

    # Strip URLs or domain fragments completely!
    if re.search(r"(https?:|www\.|\.gov\b|\.org\b|\.com\b)", text, flags=re.I):
        return ""

    text = re.sub(r"(?i)\bPopular on [A-Za-z]+\b", "", text)
    text = re.sub(r"(?i)\bexternal\b", "", text)
    text = re.sub(r"[A-Z][A-Z\s\.\-]{3,},\s*(HOST|BYLINE|CORRESPONDENT|ANCHOR|REPORTER)\s*:\s*", "", text)
    text = re.sub(r"(?i)^by\s+[A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+and\s+[A-Z][a-z]+\s+[A-Z][a-z]+)?\s*", "", text)
    text = re.sub(r"^[A-Z\s,\.]{3,28}\s*(\([A-Za-z\s]+\))?\s*(?:--|—|-)\s*", "", text)
    text = re.sub(r",\s*writes\s+[A-Z][a-z]+\s+[A-Z][a-z]+\.?$", ".", text)

    # Convert dry newspaper attributions (", an OpenAI spokesperson said." / ", said Alan Kilgore...") into natural spoken flow!
    text = re.sub(r",\s*(?:an?\s+)?[A-Za-z\s]{2,25}\s+(?:spokesperson|director|official|researcher|professor|investigator)\s+(?:said|stated|noted|added|told\s+[A-Za-z]+)\.?", ".", text, flags=re.I)
    text = re.sub(r",\s*according to\s+[A-Za-z\s]{2,25}\.?", ".", text, flags=re.I)

    text = re.sub(r"\s*\([^)]{1,45}\)", "", text)
    text = re.sub(r"(\d+)\s*km/h\b", r"\1 kilometers per hour", text, flags=re.I)
    text = re.sub(r"(\d+)\s*M\b", r"\1 million", text)

    text = re.sub(r"\bKhartoum\b", "Khar-toom", text)
    text = re.sub(r"\bTaiz\b", "Ta-iz", text)
    text = re.sub(r"\bSanaa\b", "Sa-naa", text)

    text = re.sub(r"(?i)\bthe bbc joins\b", "Correspondents join", text)
    text = re.sub(r"(?i)\btold the bbc\b", "stated", text)
    text = re.sub(r"(?i)\btells the bbc\b", "stated", text)
    text = re.sub(r"(?i)\btells bbc\b", "stated", text)
    text = re.sub(r"(?i)\b(BBC World Service|BBC World|BBC News|BBC|DW|Wired|Al Jazeera Sport|Al Jazeera|IndieWire|Variety)\b", "official reports", text)
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

def is_semantically_similar_claim(new_claim, existing_claims):
    new_words = {w.lower() for w in re.findall(r"[a-zA-Z]{4,}", new_claim)}
    if len(new_words) < 4:
        return True
    for old_c in existing_claims:
        old_words = {w.lower() for w in re.findall(r"[a-zA-Z]{4,}", old_c["text"])}
        if not old_words:
            continue
        overlap = len(new_words.intersection(old_words)) / float(min(len(new_words), len(old_words)))
        if overlap >= 0.45:
            return True
    return False

def craft_original_youtube_title(raw_title, pillar, c_prof):
    t = re.sub(r"\.\s*(DW|BBC|Reuters|AP|The Guardian|Wired).*$", "", raw_title, flags=re.I).strip()
    t = re.sub(r"^(Watch:|Listen:|Explained:|Opinion:|Analysis:)\s*", "", t, flags=re.I).strip()
    if len(t) <= 68:
        if pillar == "MIND_BLOWING_FACTS":
            return f"{t} | Case Study Explained"
        elif pillar in ["TECHNOLOGY", "SCIENCE"]:
            return f"{t} | {pillar.title()} Deep Dive"
        elif pillar == "SPORTS":
            return f"{t} | Sports Breakdown"
        elif not c_prof.get("is_global_topic"):
            return f"{t} | {c_prof['name'].title()} Case Study"
    return t[:95]

# ==============================================================================
# 5. STRICT CONCRETE NOUN & ENTITY EXTRACTOR
#    Fixes `nXqG3hXpRzg` where 'DISCOVER THAT' became an entity and pulled 'Brazil by Brasil'!
# ==============================================================================
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
    "chooses", "launch", "power", "partnership", "between", "through", "their", "there", "about"
}

def extract_primary_topic_anchor(dossier):
    low = f"{dossier['title']} {' '.join(dossier['raw_facts'][:2])}".lower()
    for word_key, (_, wiki_exact, _) in CONCRETE_WIKI_PROPS.items():
        if re.search(rf"\b{re.escape(word_key)}\b", low):
            return wiki_exact

    for k, (wiki_name, _, _) in PERSON_WIKI_MAP.items():
        if re.search(rf"\b{re.escape(k)}\b", low):
            return wiki_name

    content_nouns = [
        w for w in re.findall(r"[A-Za-z0-9]{4,}", dossier["title"])
        if w.lower() not in HEADLINE_STOP_VERBS_ADJS
    ]
    return " ".join(content_nouns[:2]) if content_nouns else dossier["title"][:28]

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
    for k, (wiki_name, _, _) in PERSON_WIKI_MAP.items():
        if re.search(rf"\b{re.escape(k)}\b", low):
            if wiki_name not in ents:
                ents.append(wiki_name)

    for word_key, (_, wiki_exact, _) in CONCRETE_WIKI_PROPS.items():
        if re.search(rf"\b{re.escape(word_key)}\b", low) and wiki_exact not in ents:
            ents.append(wiki_exact)

    content_nouns = [
        w for w in re.findall(r"[A-Za-z]{4,}", dossier["title"])
        if w.lower() not in HEADLINE_STOP_VERBS_ADJS
    ]
    if len(content_nouns) >= 2:
        noun_phrase = f"{content_nouns[0]} {content_nouns[1]}"
        if noun_phrase not in ents:
            ents.append(noun_phrase)

    if pillar == "WORLD" and not c_prof.get("is_global_topic"):
        for fb in [c_prof["capital"], c_prof["name"].title()]:
            if fb not in ents:
                ents.append(fb)
    elif not ents:
        ents.append(extract_primary_topic_anchor(dossier))
    return ents[:8]

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
                    "event_tokens": extract_event_fingerprint(viral_title),
                    "is_followup_update": False,
                    "previous_event_title": None,
                    "title": viral_title,
                    "original_yt_title": f"{viral_title} | Science Explained",
                    "wiki_hook_entity": wiki_page,
                    "visual_anchors": visual_anchors,
                    "category": "ai_tech_science",
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

    if best_match and pillar_name in ["WORLD", "BUSINESS", "SPORTS"]:
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
    if pillar_name in ["TECHNOLOGY", "SCIENCE", "MIND_BLOWING_FACTS"]:
        return "ai_tech_science"
    if pillar_name == "BUSINESS":
        return "economy_markets"
    if pillar_name == "HEALTH":
        return "environment_climate"
    comb = f"{title} {claims_text}".lower()
    if any(re.search(rf"\b{re.escape(w)}\b", comb) for w in ["missile", "strike", "offensive", "sabotage", "troops", "war", "attack", "killed", "military", "drone", "bomber", "violence", "fire", "clashes", "riots", "fighter", "jets"]):
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

            cur_fp_set = set(extract_event_fingerprint(title))
            if any(len(cur_fp_set.intersection(bfp)) / float(max(1, min(len(cur_fp_set), len(bfp)))) >= 0.45 for bfp in batch_fingerprints):
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

            for s in split_into_complete_sentences(summary):
                cs = clean_fact(s)
                if 40 <= len(cs) <= 200 and cs.lower() != title.lower() and not is_semantically_similar_claim(cs, verified_claims):
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

                    for p in soup.find_all("p"):
                        if p.find_parent("figcaption") or p.find_parent("figure") or p.find_parent("footer") or p.find_parent("aside") or p.find_parent("form"):
                            continue
                        for rs in split_into_complete_sentences(p.get_text(separator=" ")):
                            cs = clean_fact(rs)
                            if 45 <= len(cs) <= 210 and not is_semantically_similar_claim(cs, verified_claims):
                                if cs[-1] not in ".!?":
                                    cs += "."
                                verified_claims.append({
                                    "text": cs,
                                    "source_url": link,
                                    "source_name": src,
                                    "published_date": pub_date
                                })
                                if len(verified_claims) >= 20:
                                    break
                        if len(verified_claims) >= 20:
                            break
            except Exception:
                pass

            if len(verified_claims) < 16:
                try:
                    kw_q = " ".join([w for w in re.findall(r"[A-Za-z0-9]{4,}", title) if w.lower() not in HEADLINE_STOP_VERBS_ADJS][:4])
                    if kw_q:
                        b_rss = f"https://www.bing.com/news/search?q={urllib.parse.quote(kw_q)}&format=rss"
                        br = requests.get(b_rss, headers=HEADERS_WEB, timeout=6)
                        b_feed = feedparser.parse(br.content)
                        for b_ent in b_feed.entries[:12]:
                            b_desc = clean_fact(BeautifulSoup(getattr(b_ent, "summary", ""), "html.parser").get_text(separator=" "))
                            for bs in split_into_complete_sentences(b_desc):
                                cbs = clean_fact(bs)
                                if 45 <= len(cbs) <= 205 and not is_semantically_similar_claim(cbs, verified_claims):
                                    if cbs[-1] not in ".!?":
                                        cbs += "."
                                    verified_claims.append({
                                        "text": cbs,
                                        "source_url": link,
                                        "source_name": src,
                                        "published_date": pub_date
                                    })
                                    if len(verified_claims) >= 20:
                                        break
                except Exception:
                    pass

            if len(verified_claims) < 6:
                continue

            raw_facts = [c["text"] for c in verified_claims]
            c_prof = resolve_country_or_domain_profile(title, raw_facts, pillar_name=pillar)
            wb_data = fetch_verified_world_bank_gdp(c_prof["iso3"]) if not c_prof.get("is_global_topic") else None
            mood_cat = classify_story_mood_and_category(title, " ".join(raw_facts[:4]), pillar_name=pillar)

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
                "original_yt_title": craft_original_youtube_title(title, pillar, c_prof),
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
# 6. NITISH RAJPUT / ABHI & NIYU CONVERSATIONAL CASE-STUDY SCRIPT ENGINE
# ==============================================================================
def polish_journalistic_sentence(raw_fact, c_prof, role="BODY"):
    s = raw_fact.strip().rstrip(".")
    s = re.sub(r",\s*(police|officials|ministry|authorities|sources|reports|his office)\s+(say|said|reported|stated)$", "", s, flags=re.I)
    s = re.sub(r"^(police|officials|authorities|reports)\s+(say|said|state|stated)\s+(that\s+)?", "", s, flags=re.I)
    if not s:
        return ""
    s = s[0].upper() + s[1:]
    return f"{s}."

def make_clean_context_headline(text, max_words=8):
    first_clause = re.split(r"[.;:—–]", text)[0].strip()
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
    c3 = claims[3] if len(claims) > 3 else c2

    sections = [
        {
            "role": "HOOK",
            "headline": make_clean_context_headline(title, max_words=8),
            "narration": f"{title}. {polish_journalistic_sentence(c0['text'], c_prof)}",
            "claim_meta": c0
        },
        {
            "role": "WHAT_HAPPENED",
            "headline": make_clean_context_headline(c1["text"], max_words=8),
            "narration": polish_journalistic_sentence(c1["text"], c_prof),
            "claim_meta": c1
        },
        {
            "role": "CORE_EXPLANATION",
            "headline": make_clean_context_headline(c2["text"], max_words=8),
            "narration": polish_journalistic_sentence(c2["text"], c_prof),
            "claim_meta": c2
        },
        {
            "role": "SOLID_TAKEAWAY",
            "headline": make_clean_context_headline(c3["text"], max_words=8),
            "narration": polish_journalistic_sentence(c3["text"], c_prof),
            "claim_meta": c3
        }
    ]
    return sections, ents

def build_long_documentary_script(dossier):
    c_prof = dossier["country_profile"]
    claims = dossier["verified_claims"]

    unique_sents = []
    for c in claims:
        ps = polish_journalistic_sentence(c["text"], c_prof)
        if len(ps) > 35 and ps not in unique_sents:
            unique_sents.append(ps)

    chunk_size = 2 if len(unique_sents) < 12 else 3
    sent_groups = [unique_sents[i:i + chunk_size] for i in range(0, len(unique_sents), chunk_size)][:6]
    role_cycle = ["HOOK", "EVIDENCE", "CORE_MECHANISM", "TECHNICAL_DEEP_DIVE", "TIMELINE", "SOLID_TAKEAWAY"]

    chapters = []
    for idx, grp in enumerate(sent_groups):
        body_txt = " ".join(grp)
        if idx == 0:
            body_txt = f"{dossier['title']}. {body_txt}"
        if idx == len(sent_groups) - 1:
            body_txt = f"{body_txt} Subscribe to World Talk Brief for daily global case studies."
        c_meta = claims[min(idx, len(claims) - 1)]
        chapters.append({
            "chapter_num": idx + 1,
            "chapter_title": make_clean_context_headline(grp[0], max_words=8),
            "role": role_cycle[idx % len(role_cycle)],
            "dossier": dossier,
            "claim_meta": c_meta,
            "narration": body_txt
        })

    return chapters

# ==============================================================================
# 7. STRICT EXACT-TOPIC MOVING VIDEO B-ROLL ENGINE
# ==============================================================================
def is_valid_cinematic_video_frame(frame_rgb):
    arr = np.asarray(Image.fromarray(frame_rgb).resize((120, 120)), dtype=np.float32)
    white_px = np.sum((arr[:, :, 0] > 230) & (arr[:, :, 1] > 230) & (arr[:, :, 2] > 230)) / float(120 * 120)
    black_px = np.sum((arr[:, :, 0] < 25) & (arr[:, :, 1] < 25) & (arr[:, :, 2] < 25)) / float(120 * 120)
    if white_px > 0.30 or black_px > 0.55:
        return False
    return True

def fetch_and_transcode_real_video_broll(wiki_target, dossier, used_video_urls, tag_id="vclip"):
    topic_anchor = extract_primary_topic_anchor(dossier)
    clean_subj = re.sub(r"[^a-zA-Z0-9\s]", " ", f"{wiki_target} {topic_anchor}").strip()
    ambiguous_broll_words = {
        "voice", "block", "blocks", "model", "models", "sound", "sounds", "human", "rapid",
        "national", "care", "service", "popular", "discover", "discovered", "brasil", "brazil"
    }
    subj_words = [
        w.lower() for w in re.findall(r"[A-Za-z0-9]{4,}", clean_subj)
        if w.lower() not in HEADLINE_STOP_VERBS_ADJS and w.lower() not in ambiguous_broll_words
    ]
    if not subj_words:
        return None
    query_str = " ".join(subj_words[:2])

    banned_video_words = [
        "vlog", "webcam", "stream", "gaming", "twitch", "minecraft", "cartoon", "user", "test",
        "lecture", "interview", "golf", "tree", "park", "pronunciation", "spoken", "audio",
        "session", "recorded", "wikidata", "conference", "talk", "presentation", "isolated",
        "slate", "lawrence", "tutorial", "screen", "backpulver", "rakete", "voa", "voice of america",
        "migrant", "newscast", "anchor", "trooper", "police", "kamala", "harris", "senator", "governor",
        "brasil", "tourism", "commercial", "promo"
    ]

    try:
        api = "https://commons.wikimedia.org/w/api.php"
        params = {
            "action": "query", "generator": "search",
            "gsrsearch": f"filetype:video {query_str}",
            "gsrnamespace": "6", "gsrlimit": 8,
            "prop": "videoinfo|imageinfo", "viprop": "url|size|derivatives", "iiprop": "url|size", "format": "json"
        }
        r = requests.get(api, params=params, headers=HEADERS_WIKI, timeout=7).json()
        for pg in r.get("query", {}).get("pages", {}).values():
            v_title = pg.get("title", "").lower()
            if any(bw in v_title for bw in banned_video_words):
                continue
            if subj_words[0] not in v_title:
                continue

            vi = (pg.get("videoinfo") or pg.get("imageinfo") or [{}])[0]
            derivs = vi.get("derivatives", [])
            candidate_urls = []
            for d in derivs:
                du = d.get("src", "")
                if du.endswith((".webm", ".mp4", ".ogv")) and any(res in du for res in ["480p", "360p", "720p"]):
                    candidate_urls.append(du)
            orig_u = vi.get("url", "")
            if orig_u.lower().endswith((".webm", ".mp4", ".ogv")):
                candidate_urls.append(orig_u)

            for cand_u in candidate_urls[:2]:
                if cand_u in used_video_urls:
                    continue
                try:
                    ext = os.path.splitext(cand_u.split("?")[0])[1] or ".webm"
                    raw_local = f"temp/{tag_id}_raw{ext}"
                    clean_mp4 = f"temp/{tag_id}_{len(used_video_urls)}.mp4"

                    with requests.get(cand_u, headers=HEADERS_WIKI, stream=True, timeout=12) as vr:
                        if vr.status_code != 200:
                            continue
                        bytes_read = 0
                        with open(raw_local, "wb") as vf:
                            for chunk in vr.iter_content(chunk_size=262144):
                                if not chunk:
                                    break
                                vf.write(chunk)
                                bytes_read += len(chunk)
                                if bytes_read >= 5200000:
                                    break

                    if not os.path.exists(raw_local) or os.path.getsize(raw_local) < 40000:
                        continue

                    cmd = [
                        "ffmpeg", "-y",
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
                        if vc.duration >= 2.0:
                            mid_frame = vc.get_frame(min(1.0, vc.duration * 0.4))
                            if not is_valid_cinematic_video_frame(mid_frame):
                                continue
                            used_video_urls.add(cand_u)
                            print("   🎬 [EXACT-MATCH HD VIDEO LOCKED]:", query_str, f"({round(vc.duration, 1)}s)", flush=True)
                            return {
                                "vclip": vc,
                                "start_t": min(0.4, vc.duration * 0.1),
                                "label": f"LIVE FOOTAGE • {query_str.upper()[:20]}"
                            }
                except Exception:
                    pass
    except Exception:
        pass
    return None

# ==============================================================================
# 8. TOPIC-ANCHORED BING HD PHOTO HARVESTER
# ==============================================================================
def validate_and_enhance_1080p(im, existing_hashes, min_w=380, min_h=240):
    im = im.convert("RGB")
    w, h = im.size
    if w < min_w or h < min_h:
        return None
    if h > w * 1.15:
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

    rg_diff = np.mean(np.abs(arr[:, :, 0] - arr[:, :, 1]))
    gb_diff = np.mean(np.abs(arr[:, :, 1] - arr[:, :, 2]))
    if rg_diff < 6.0 and gb_diff < 6.0:
        return None

    quant = (arr // 32).astype(int)
    flat = quant[:, :, 0] * 64 + quant[:, :, 1] * 8 + quant[:, :, 2]
    _, counts = np.unique(flat, return_counts=True)
    if (counts.max() / float(80 * 80)) > 0.36:
        return None

    gray_cv = cv2.cvtColor(np.array(im.resize((320, 200))), cv2.COLOR_RGB2GRAY)
    blur_score = cv2.Laplacian(gray_cv, cv2.CV_64F).var()
    if blur_score < 28.0 or im.entropy() < 6.2:
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

def extract_speaker_or_prop_for_beat(beat_text, dossier, entities, beat_idx):
    low = beat_text.lower()
    pillar = dossier.get("pillar", "WORLD")
    topic_anchor = extract_primary_topic_anchor(dossier)

    for p_key, (wiki_page, badge_lbl, _) in PERSON_WIKI_MAP.items():
        if re.search(rf"\b{re.escape(p_key)}\b", low):
            if pillar in ["WORLD", "BUSINESS", "SPORTS", "TECHNOLOGY"] or p_key in dossier["title"].lower():
                return badge_lbl, wiki_page, f"{wiki_page} {topic_anchor}", True

    for word_key, (prop_badge, wiki_exact, news_q) in CONCRETE_WIKI_PROPS.items():
        if re.search(rf"\b{re.escape(word_key)}\b", low):
            return prop_badge, wiki_exact, f"{news_q} {topic_anchor}", False

    chosen_ent = entities[beat_idx % len(entities)]
    beat_keywords = [
        w for w in re.findall(r"[A-Za-z]{4,}", beat_text)
        if w.lower() not in HEADLINE_STOP_VERBS_ADJS and w.lower() not in {"look", "first", "what", "makes", "this", "even", "more", "interesting", "wider", "context", "here", "takeaway", "think", "welcome", "back", "world", "talk", "brief", "verified", "facts", "record", "story", "today", "their", "they", "them", "from", "into", "that", "with", "said", "says"}
    ]
    if len(beat_keywords) >= 2:
        clause_q = f"{topic_anchor} {beat_keywords[0]} {beat_keywords[1]}"
        return f"{pillar.replace('_', ' ')} • {topic_anchor.upper()[:18]}", chosen_ent, clause_q, False

    return f"{pillar.replace('_', ' ')} • {topic_anchor.upper()[:18]}", chosen_ent, f"{topic_anchor} {chosen_ent}", False

def fetch_verified_news_or_wiki_visual(wiki_exact_title, news_query, dossier, existing_hashes, failed_queries, tag_id="beat"):
    pillar = dossier.get("pillar", "WORLD")
    topic_anchor = extract_primary_topic_anchor(dossier)
    neg_filter = " -ukraine -trump -zelensky -war -capitol" if pillar in ["SCIENCE", "TECHNOLOGY", "HEALTH", "MIND_BLOWING_FACTS", "SPORTS", "ENTERTAINMENT"] and "ukraine" not in dossier["title"].lower() else ""

    for nq in [news_query + neg_filter, f"{topic_anchor} {wiki_exact_title}{neg_filter}", dossier["title"] + neg_filter]:
        try:
            rss_u = f"https://www.bing.com/news/search?q={urllib.parse.quote(nq)}&format=rss"
            r = requests.get(rss_u, headers=HEADERS_WEB, timeout=6)
            for u in re.findall(r"<News:Image>(https?://[^<]+)</News:Image>", r.text)[:15]:
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

    for b_img_q in [news_query, f"{topic_anchor} {wiki_exact_title}", dossier["title"]]:
        try:
            b_url = f"https://www.bing.com/images/async?q={urllib.parse.quote(b_img_q + neg_filter)}&first=0&count=18&qft=+filterui:imagesize-large+filterui:photo-photo+filterui:aspect-wide"
            r = requests.get(b_url, headers=HEADERS_WEB, timeout=6)
            murls = re.findall(r"murl&quot;:&quot;(https?://[^&]+?)&quot;", r.text)
            turls = re.findall(r"turl&quot;:&quot;(https?://[^&]+?)&quot;", r.text)
            for u in (turls + murls)[:16]:
                u_clean = u.replace("&amp;", "&")
                if any(b in u_clean.lower() for b in BANNED_IMAGE_SOURCES):
                    continue
                if "bing.com/th" in u_clean:
                    u_clean = u_clean.split("&")[0] + "&w=1920&h=1080&c=7&rs=1"
                ir = requests.get(u_clean, headers=HEADERS_WEB, timeout=5)
                if ir.status_code == 200 and len(ir.content) > 10000:
                    p = f"temp/{tag_id}_binghd.jpg"
                    with open(p, "wb") as f:
                        f.write(ir.content)
                    vim = validate_and_enhance_1080p(Image.open(p), existing_hashes)
                    if vim is not None:
                        return vim
        except Exception:
            pass

    for gal_u in dossier.get("wiki_gallery_urls", []):
        try:
            ir = requests.get(gal_u, headers=HEADERS_WIKI, timeout=5)
            if ir.status_code == 200 and len(ir.content) > 14000:
                p = f"temp/{tag_id}_wgal.jpg"
                with open(p, "wb") as f:
                    f.write(ir.content)
                vim = validate_and_enhance_1080p(Image.open(p), existing_hashes)
                if vim is not None:
                    return vim
        except Exception:
            pass

    failed_queries.append(news_query)
    return None

# ==============================================================================
# 9. GOD-LEVEL MULTI-ANGLE CAMERA & KEY-STAT CALLOUT COMPOSITOR
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
        if len(faces) >= 2 and target_w < target_h:
            faces_sorted = sorted(faces, key=lambda f: f[0])
            f_left, f_right = faces_sorted[0], faces_sorted[-1]
            span_x = (f_right[0] + f_right[2]) - f_left[0]
            if span_x > crop_w * 0.92:
                dual_stage = Image.new("RGB", (target_w, target_h), (10, 14, 24))
                half_h = target_h // 2
                left_half = im.crop((0, 0, iw // 2, ih)).resize((target_w, half_h), resample_mode)
                right_half = im.crop((iw // 2, 0, iw, ih)).resize((target_w, target_h - half_h), resample_mode)
                dual_stage.paste(left_half, (0, 0))
                dual_stage.paste(right_half, (0, half_h))
                d_line = ImageDraw.Draw(dual_stage)
                d_line.line([(0, half_h), (target_w, half_h)], fill=(255, 214, 10), width=6)
                return dual_stage

        if faces:
            main_f = max(faces, key=lambda f: f[2] * f[3])
            fx_center = main_f[0] + main_f[2] // 2
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

        hero_w, hero_h = int(W * 1.14), int(1340 * 1.14)
        fg = fit_full_height_face_aware_1080p(im, hero_w, hero_h)
        return ("SHORT_STAGE", canvas, fg)
    else:
        over_w, over_h = int(W * 1.14), int(H * 1.14)
        fg = fit_full_height_face_aware_1080p(im, over_w, over_h)
        return ("FULL_BLEED_STAGE", fg, None)

def extract_animated_frame_from_stage(stage_tuple, W, H, bp, pan_dir=1):
    resample_mode = getattr(Image, "Resampling", Image).BILINEAR
    mode_tag, base_a, base_b = stage_tuple
    smooth_p = 0.5 - 0.5 * math.cos(math.pi * bp)

    if mode_tag == "SHORT_STAGE":
        canvas = base_a.copy()
        fg = base_b
        fw, fh = fg.size
        win_w, win_h = W, 1340
        cur_w = int(win_w + (fw - win_w) * (1.0 - 0.75 * smooth_p))
        cur_h = int(win_h + (fh - win_h) * (1.0 - 0.75 * smooth_p))
        max_dx = max(fw - cur_w, 0)
        max_dy = max(fh - cur_h, 0)
        ox = int(max_dx * (smooth_p if pan_dir == 1 else (1.0 - smooth_p)))
        oy = int(max_dy * 0.45)
        slice_fg = fg.crop((ox, oy, ox + cur_w, oy + cur_h)).resize((win_w, win_h), resample_mode)
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
        cur_w = int(W + (fw - W) * (1.0 - 0.78 * smooth_p))
        cur_h = int(H + (fh - H) * (1.0 - 0.78 * smooth_p))
        max_dx = max(fw - cur_w, 0)
        max_dy = max(fh - cur_h, 0)
        ox = int(max_dx * (smooth_p if pan_dir == 1 else (1.0 - smooth_p)))
        oy = int(max_dy * (0.25 + 0.5 * smooth_p))
        frame = fg.crop((ox, oy, ox + cur_w, oy + cur_h)).resize((W, H), resample_mode).convert("RGBA")
        draw = ImageDraw.Draw(frame, "RGBA")
        for y in range(H - 260, H):
            draw.line([(0, y), (W, y)], fill=(4, 7, 14, int(215 * ((y - (H - 260)) / 260.0) ** 1.2)))
        return frame

def build_documentary_evidence_stage_1080p(base_photo, beat_text, prop_badge, dossier):
    resample_mode = getattr(Image, "Resampling", Image).LANCZOS
    W, H = 1920, 1080
    bg = base_photo.copy().resize((W, H), resample_mode).filter(ImageFilter.GaussianBlur(radius=28))
    bg = ImageEnhance.Brightness(bg).enhance(0.32).convert("RGBA")
    fg = fit_full_height_face_aware_1080p(base_photo, 1280, 720)
    bg.paste(fg, ((W - 1280) // 2, 70))
    draw = ImageDraw.Draw(bg, "RGBA")
    draw.rounded_rectangle([((W - 1280) // 2 - 4, 66), ((W + 1280) // 2 + 4, 794)], radius=12, outline=(255, 214, 10, 235), width=4)
    return bg.convert("RGB")

def extract_key_stat_callout(beat_text):
    m = re.search(r"\b(\d+(?:,\d+)*(?:\.\d+)?(?:\s*%|\s*percent|\s*million|\s*billion|\s*trillion|\s*miles|\s*kilometers|\s*km|\s*seconds|\s*years|\s*days|\s*hours|-point)?(?:\s+[A-Za-z]{3,12})?)\b", beat_text, flags=re.I)
    if m:
        val = m.group(1).strip().upper()
        if len(val) >= 3 and val not in {"2026", "2025", "1995", "1996"}:
            return f"⚡ KEY STAT: {val}"
    return None

# ==============================================================================
# 10. FAST-PACED 3.0s-3.4s BEAT STORYBOARD BUILDER
# ==============================================================================
def has_strict_economic_context(text):
    low = text.lower()
    if any(prison_w in low for prison_w in ["jailed", "prison", "sentenced", "murder", "killed", "court", "police"]):
        return False
    if re.search(r"\b(\d+(\.\d+)?%|\$\d+|\d+\s*(billion|trillion))\b", low):
        return True
    econ_terms = ["gdp", "inflation", "economy", "economic", "market", "trade", "tariff", "cost", "budget", "growth", "debt", "financial", "bank"]
    return any(re.search(rf"\b{re.escape(t)}\b", low) for t in econ_terms)

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
    map_beats = 0
    moving_video_beats = 0
    generated_infographic_beats = 0

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
    max_video_clips_for_block = 2 if W < H else 1

    for sec_idx, sec in enumerate(sections_list):
        narration = sec["narration"]
        sec_dur = sec["duration"]
        word_timings = sec["word_timings"]
        sec_headline = sec.get("headline") or sec.get("chapter_title") or make_clean_context_headline(dossier["title"])
        claim_meta = sec.get("claim_meta") or dossier["verified_claims"][0]

        target_beat_len = 3.1 if W < H else 3.5
        num_beats = max(2, int(round(sec_dur / target_beat_len)))
        beat_dur = sec_dur / float(num_beats)
        words = narration.split()
        w_per_b = max(1, int(math.ceil(len(words) / float(num_beats))))
        used_modes_in_sec = set()

        for b_i in range(num_beats):
            b_txt = " ".join(words[b_i * w_per_b:(b_i + 1) * w_per_b]) or narration
            prop_badge, wiki_target, search_q, _ = extract_speaker_or_prop_for_beat(b_txt, dossier, entities, global_beat_idx)
            low_b = b_txt.lower()
            stat_callout = extract_key_stat_callout(b_txt)

            vseg = None
            if b_i == 1 and moving_video_beats < max_video_clips_for_block:
                vseg = fetch_and_transcode_real_video_broll(
                    wiki_target, dossier, used_video_urls, tag_id=f"{tag_prefix}_vc_{global_beat_idx}"
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
                    if beat_im is not None:
                        unique_real_photos.append(beat_im)
                    elif unique_real_photos:
                        base_p = unique_real_photos[global_beat_idx % len(unique_real_photos)]
                        beat_im = build_documentary_evidence_stage_1080p(base_p, b_txt, prop_badge, dossier)
                        reused_photo_beats += 1
                    else:
                        beat_im = Image.new("RGB", (1920, 1080), (12, 18, 32))

                if has_strict_economic_context(b_txt) and dossier.get("wb_data") is not None and "DATA_CHART_BEAT" not in used_modes_in_sec:
                    b_type = "DATA_CHART_BEAT"
                elif re.search(r"\b(timeline|overnight|step by step|previously|september|october|days before|july)\b", low_b) and "TIMELINE_GRAPH_BEAT" not in used_modes_in_sec:
                    b_type = "TIMELINE_GRAPH_BEAT"
                elif re.search(r"\b(said|stated|confirmed|record|specifics|told|claim|claims|study|researchers)\b", low_b) and "HEADLINE_EVIDENCE_BEAT" not in used_modes_in_sec:
                    b_type = "HEADLINE_EVIDENCE_BEAT"
                elif re.search(r"\b(competing|colliding|whether|or if|versus|contrast|between|ahead of|beat)\b", low_b) and "SPLIT_COMPARE_BEAT" not in used_modes_in_sec and len(unique_real_photos) >= 2:
                    b_type = "SPLIT_COMPARE_BEAT"
                else:
                    b_type = "PHOTO_BEAT"

                stage_1 = build_clean_1080p_stage(beat_im, W, H)

            used_modes_in_sec.add(b_type)
            secondary_im = unique_real_photos[(len(unique_real_photos) - 2) % len(unique_real_photos)] if len(unique_real_photos) >= 2 else beat_im
            prev_stage = planned_beats[-1]["stage_1"] if planned_beats else None

            planned_beats.append({
                "section_idx": sec_idx,
                "beat_in_section": b_i,
                "beat_type": b_type,
                "pan_dir": 1 if (global_beat_idx % 2 == 0) else -1,
                "duration": round(beat_dur, 3),
                "beat_excerpt": b_txt,
                "stat_callout": stat_callout,
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
        "generated_infographic_beats": generated_infographic_beats,
        "reused_photo_beats": reused_photo_beats,
        "map_beats": map_beats,
        "failed_queries_count": len(failed_queries),
        "failed_queries": failed_queries[:10]
    }
    print("📊 [AUDIT]", tag_prefix.upper(), "| Beats:", stats["total_beats"], "| Total Unique Photos:", stats["unique_real_photos"], "| Moving Videos:", stats["moving_video_beats"], flush=True)
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
            t_vid = (vseg["start_t"] + local_t) % max(vc.duration - 0.15, 0.5)
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
        if local_t < 0.25 and beat.get("prev_stage") is not None:
            try:
                prev_f = extract_animated_frame_from_stage(beat["prev_stage"], W, H, 1.0, pan_dir=1)
                alpha_blend = local_t / 0.25
                frame = Image.blend(prev_f, frame, alpha_blend)
            except Exception:
                pass
        draw = ImageDraw.Draw(frame, "RGBA")

    if beat.get("stat_callout"):
        sc_txt = beat["stat_callout"]
        f_sc = get_font(26 if is_short else 30)
        sc_w = draw.textbbox((0, 0), sc_txt, font=f_sc)[2] + 44
        sc_x = (W - sc_w) // 2 if is_short else (W - sc_w - 48)
        sc_y = 148 if is_short else 108
        draw.rounded_rectangle([(sc_x, sc_y), (sc_x + sc_w, sc_y + 58)], radius=12, fill=(255, 214, 10, 248), outline=(10, 14, 24, 255), width=3)
        draw.text((sc_x + 22, sc_y + 12), sc_txt, fill=(10, 14, 24, 255), font=f_sc)

    cy_card = 1475 if is_short else (H - 305)
    bx1, bx2 = (42, W - 42) if is_short else (56, 1260)

    pillar_tag = story.get("pillar", "WORLD").replace("_", " ")
    citation_str = f"WORLD TALK BRIEF • {pillar_tag} CASE STUDY • {claim_meta['published_date']}"

    if b_type in ["PHOTO_BEAT", "VIDEO_BROLL_BEAT"]:
        kicker = beat["vseg"]["label"] if (b_type == "VIDEO_BROLL_BEAT" and beat.get("vseg")) else beat["primary_lbl"]
        hl = str(beat["section_headline"]).upper()
        f_k = get_font(21)
        f_h = get_font(28 if is_short else 30)
        kw = draw.textbbox((0, 0), kicker, font=f_k)[2] + 34

        draw.rounded_rectangle([(bx1, cy_card), (bx2, cy_card + 158)], radius=12, fill=(10, 16, 28, 226), outline=(255, 214, 10, 215), width=2)
        draw.rounded_rectangle([(bx1 + 18, cy_card + 14), (bx1 + 18 + kw, cy_card + 48)], radius=6, fill=(204, 18, 36, 255))
        draw.text((bx1 + 34, cy_card + 19), kicker, fill=(255, 255, 255, 255), font=f_k)
        for i_l, ln in enumerate(wrap_lines(draw, hl, f_h, (bx2 - bx1) - 48)[:2]):
            draw.text((bx1 + 22, cy_card + 56 + i_l * 34), ln, fill=(255, 255, 255, 255), font=f_h)
        draw.text((bx1 + 22, cy_card + 128), citation_str[:78], fill=(0, 210, 255, 235), font=get_font(17))

    elif b_type == "HEADLINE_EVIDENCE_BEAT":
        draw.rounded_rectangle([(bx1, cy_card), (bx2, cy_card + 162)], radius=14, fill=(246, 244, 236, 244), outline=(204, 18, 36, 255), width=3)
        draw.rounded_rectangle([(bx1 + 22, cy_card + 10), (bx1 + 520, cy_card + 42)], radius=6, fill=(204, 18, 36, 255))
        draw.text((bx1 + 36, cy_card + 14), f"VERIFIED EVIDENCE • {claim_meta['published_date']}", fill=(255, 255, 255, 255), font=get_font(20))

        hl_txt = beat["beat_excerpt"]
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
            ("CATALYST", story["title"][:44]),
            ("MECHANISM", beat["section_headline"][:44]),
            ("IMPACT", f"Reshaping {c_prof['region']}")
        ]
        sy = cy_card + 6
        for idx_s, (slbl, stxt) in enumerate(steps):
            act = (bp >= idx_s * 0.28)
            bg_c = (204, 18, 36, 255) if act else (35, 45, 65, 210)
            draw.rounded_rectangle([(bx1 + 22, sy), (bx1 + 175, sy + 38)], radius=6, fill=bg_c)
            draw.text((bx1 + 30, sy + 7), slbl, fill=(255, 255, 255, 255), font=get_font(19))
            draw.text((bx1 + 190, sy + 6), stxt[:42], fill=(255, 255, 255, 255) if act else (160, 170, 185, 210), font=get_font(23))
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
        draw.text((bx1 + 22, cy_card + 18), "CORE FACTOR A", fill=(0, 210, 255, 255), font=get_font(22))
        draw.text((bx1 + 22, cy_card + 62), "STRATEGIC ADVANTAGE", fill=(255, 255, 255, 255), font=get_font(24))

        draw.rounded_rectangle([(mid_x + 10, cy_card), (bx2, cy_card + 145)], radius=12, fill=(10, 18, 32, 235), outline=(255, 214, 10, 230), width=2)
        draw.text((mid_x + 32, cy_card + 18), "CORE FACTOR B", fill=(255, 214, 10, 255), font=get_font(22))
        draw.text((mid_x + 32, cy_card + 62), "OPERATIONAL SCALE", fill=(255, 255, 255, 255), font=get_font(24))

    top_y = 28 if is_short else 32
    frame.paste(watermark, (42, top_y), watermark)
    if c_prof.get("flag_img"):
        fl = c_prof["flag_img"].resize((84, 54))
        frame.paste(fl, (198, top_y + 14), fl)

    live_txt = f"● {pillar_tag} • {c_prof['name']}"
    f_lv = get_font(20)
    lw_box = draw.textbbox((0, 0), live_txt, font=f_lv)[2] + 36
    draw.rounded_rectangle([(W - lw_box - 42, top_y + 12), (W - 42, top_y + 56)], radius=8, fill=(14, 20, 34, 225), outline=(204, 18, 36, 255), width=2)
    draw.text((W - lw_box - 24, top_y + 22), live_txt, fill=(255, 214, 10, 255), font=f_lv)

    if not is_short:
        draw.rectangle([(0, H - 38), (W, H)], fill=(10, 15, 28, 248))
        ticker_str = f"   •   [{pillar_tag}] {story['original_yt_title'].upper()}   •   SUBSCRIBE FOR DEEP EXPLAINERS ON WORLD, TECH, AI, MYSTERIES, SCIENCE & BUSINESS   " * 2
        scroll_x = 255 - int((section_t * 105) % 1400)
        draw.text((scroll_x, H - 30), ticker_str, fill=(255, 214, 10, 255), font=get_font(18))
        draw.rectangle([(0, H - 38), (242, H)], fill=(204, 18, 36, 255))
        draw.line([(242, H - 38), (242, H)], fill=(255, 214, 10, 255), width=3)
        draw.text((18, H - 30), "WORLD TALK BRIEF", fill=(255, 255, 255, 255), font=get_font(19))

    if is_short and beat["section_idx"] == 0 and beat["beat_in_section"] == 0 and local_t < 0.35:
        draw.rounded_rectangle([(42, 740), (W - 42, 915)], radius=16, fill=(204, 18, 36, 242), outline=(255, 214, 10, 255), width=4)
        f_cov = get_font(44)
        for ci, cln in enumerate(wrap_lines(draw, story["title"].upper(), f_cov, W - 120)[:2]):
            draw.text((68, 765 + ci * 58), cln, fill=(255, 255, 255, 255), font=f_cov)

    sub_strip = voice_sub_dir.render_exact_synced_subtitles(beat["word_timings"], section_t, W, H, is_short=is_short)
    sub_y = 1655 if is_short else (H - 154)
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
# 11. 100% CLEAN HUMAN VOICE ENGINE (ZERO Kalpanik Sine-Wave Hum, ZERO Pitch Warping!)
# ==============================================================================
class VoiceAndSubtitleEngine:
    async def synthesize_with_word_boundaries(self, text, out_path, pillar="WORLD"):
        """
        Uses Microsoft's Gen-2 Ultra-Realistic Conversational Voices (`AndrewMultilingualNeural`,
        `BrianMultilingualNeural`, `AvaMultilingualNeural`, `EmmaMultilingualNeural`) at their
        100% natural human throat pitch (`pitch='+0Hz'`) with zero synthetic background hum!
        """
        v_name = CATEGORY_VOICE_CAST.get(pillar, "en-US-AndrewMultilingualNeural")
        raw_mp3 = out_path.replace(".mp3", "_raw.mp3")
        word_timings = []

        for _ in range(2):
            try:
                comm = edge_tts.Communicate(text, v_name, rate="+2%", pitch="+0Hz")
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

        # Pure, clean 48kHz broadcast vocal output with a natural 0.22s breath pause between sections (NO distortion filters!)
        try:
            cmd = [
                "ffmpeg", "-y", "-i", raw_mp3,
                "-af", "apad=pad_dur=0.22",
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
            tot_chars = max(sum(len(w) for w in words), 1)
            cur = 0.0
            for w in words:
                wd = (len(w) / float(tot_chars)) * (total_dur - 0.2)
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
            if ch[0]["start"] <= section_t <= (ch[-1]["end"] + 0.25):
                active_chunk = ch
                for w_i, w_obj in enumerate(ch):
                    if section_t >= w_obj["start"]:
                        active_word_idx = w_i
                break
            elif section_t > (ch[-1]["end"] + 0.25):
                active_chunk = ch
                active_word_idx = len(ch) - 1

        strip_h = 210 if is_short else 110
        strip = Image.new("RGBA", (W, strip_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(strip, "RGBA")
        font = get_font(52 if is_short else 38)
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
            draw.rounded_rectangle([(bx1, 8), (bx2, 86)], radius=12, fill=(6, 9, 16, 232), outline=(255, 214, 10, 105), width=2)
            x_cur = (W - lw) // 2
            for idx_w, w in enumerate(words_str_list):
                col = (255, 214, 10, 255) if idx_w == active_word_idx else (255, 255, 255, 255)
                draw.text((x_cur, 22), w, font=font, fill=col, stroke_width=3, stroke_fill=(0, 0, 0, 240))
                x_cur += draw.textbbox((0, 0), w + " ", font=font)[2]
        return strip

# ==============================================================================
# 12. FULL-BLEED 1080p THUMBNAIL ENGINE
# ==============================================================================
def extract_complete_viral_thumbnail_hook(dossier):
    words = [
        w.upper() for w in re.findall(r"[A-Za-z0-9']+", dossier["title"])
        if w.lower() not in HEADLINE_STOP_VERBS_ADJS and w.lower() not in {"the", "and", "for", "with", "from", "into", "over", "after", "that", "this", "their", "they"} and len(w) <= 12
    ]
    if len(words) >= 4:
        l1 = f"{words[0]} {words[1]}"
        l2 = f"{words[2]} {words[3]}"
    elif len(words) >= 2:
        l1 = words[0]
        l2 = words[1]
    else:
        l1 = dossier.get("pillar", "WORLD").replace("_", " ")
        l2 = "EXPLAINED"
    return l1, l2

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
    full_im = ImageEnhance.Color(ImageEnhance.Contrast(full_im).enhance(1.22)).enhance(1.18)
    canvas = full_im.convert("RGBA")
    draw = ImageDraw.Draw(canvas, "RGBA")

    for y in range(640, H):
        alpha = int(225 * (((y - 640) / 440.0) ** 1.35))
        draw.line([(0, y), (W, y)], fill=(6, 10, 20, alpha))

    draw.rectangle([(10, 10), (W - 10, H - 10)], outline=accent_col + (240,), width=8)
    draw.rectangle([(18, 18), (W - 18, H - 18)], outline=badge_col + (225,), width=4)

    canvas.paste(watermark, (54, 48), watermark)
    if c_prof.get("flag_img"):
        fl = c_prof["flag_img"].resize((112, 72))
        draw.rounded_rectangle([(208, 52), (328, 132)], radius=8, fill=accent_col + (255,))
        canvas.paste(fl, (212, 56), fl)

    brand_pill = f"WORLD TALK BRIEF  •  {pillar.replace('_', ' ')}"
    f_bp = get_font(28)
    bp_w = draw.textbbox((0, 0), brand_pill, font=f_bp)[2] + 48
    draw.rounded_rectangle([(54, 152), (54 + bp_w, 208)], radius=10, fill=badge_col + (245,), outline=(255, 255, 255, 240), width=2)
    draw.text((78, 165), brand_pill, fill=(255, 255, 255, 255), font=f_bp)

    hook_line_1, hook_line_2 = extract_complete_viral_thumbnail_hook(dossier)
    f_giant = get_font(92)
    f_sub = get_font(84)

    draw.text((62, 658), hook_line_1, fill=(0, 0, 0, 240), font=f_giant)
    draw.text((54, 650), hook_line_1, fill=(255, 255, 255, 255), font=f_giant, stroke_width=7, stroke_fill=(0, 0, 0, 255))

    w_l2 = draw.textbbox((0, 0), hook_line_2, font=f_sub)[2] + 76
    poly_pts = [(54, 775), (54 + w_l2, 775), (38 + w_l2, 898), (38, 898)]
    draw.polygon([(p[0] + 10, p[1] + 10) for p in poly_pts], fill=(0, 0, 0, 220))
    draw.polygon(poly_pts, fill=accent_col + (255,), outline=(255, 255, 255, 255))
    draw.text((82, 792), hook_line_2, fill=(10, 12, 18, 255), font=f_sub)

    sub_teaser = make_clean_context_headline(dossier["original_yt_title"], max_words=8)
    draw.text((58, 932), f"▶ {sub_teaser}", fill=(0, 230, 255, 255), font=get_font(34), stroke_width=3, stroke_fill=(0, 0, 0, 255))

    canvas.convert("RGB").save(out_path, quality=96)

    return {
        "selected_thumbnail": out_path,
        "thumbnail_category_style": pillar,
        "selected_title": dossier["original_yt_title"],
        "hashtags": ["#WorldTalkBrief", f"#{pillar.replace('_', '')}", f"#{c_prof['name'].replace(' ', '')}", "#Explained"]
    }

# ==============================================================================
# 13. YOUTUBE UPLOADER + AUTOMATIC PLAYLIST ASSIGNMENT + AUTO COMMENT
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
# 14. MODULAR RENDER FUNCTIONS (100% Pure Vocal Audio — Zero Kalpanik Sine-Wave Hum!)
# ==============================================================================
async def render_and_upload_short_unit(short_dossier, unit_num, watermark, voice_sub_dir, hist_obj, winning_keywords, viral_yt_tags, playlist_map):
    pillar = short_dossier.get("pillar", "WORLD")
    print(f"\n📱 [SHORT #{unit_num} - {pillar}] Building 1080p Short on: {short_dossier['original_yt_title']}", flush=True)
    short_sections, short_entities = build_short_script(short_dossier, variant_idx=len(hist_obj["published_keys"]) + unit_num)

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
    for sec_idx, sec in enumerate(short_sections):
        sec_beats = [b for b in s_beats if b["section_idx"] == sec_idx]
        clip = make_section_clip_from_beats(sec_beats, watermark, voice_sub_dir, sec["duration"], 1080, 1920, is_short=True)
        clip = clip.with_audio(sec["audio_clip"]) if MOVIEPY_V2 else clip.set_audio(sec["audio_clip"])
        short_clips.append(clip)

    final_short = concatenate_videoclips(short_clips, method="compose")
    out_short = "output/WTB_1080p_Short_9x16.mp4" if unit_num == 1 else f"output/WTB_1080p_Short_{unit_num}_9x16.mp4"
    final_short.write_videofile(out_short, fps=24, codec="libx264", audio_codec="aac", bitrate="8000k", preset="ultrafast", threads=4, logger=None)

    thumb_out = "output/WTB_1080p_Short_Thumb.jpg" if unit_num == 1 else f"output/WTB_1080p_Short_{unit_num}_Thumb.jpg"
    short_pkg = create_signature_wtb_brand_thumbnail(short_dossier, short_entities, s_unique_photos, watermark, out_path=thumb_out)

    short_hashtags_str = " ".join(short_pkg["hashtags"] + ["#Shorts", "#Explained"])
    short_seo_desc = (
        f"{short_dossier['original_yt_title']}\n\n"
        f"World Talk Brief [{pillar.replace('_', ' ')}] #Shorts case study.\n\n"
        f"🔑 KEY ENTITIES: {', '.join(short_entities[:5])}\n"
        f"📋 Editorial Reference ({short_dossier['published_date']}): {short_dossier['source_url']}\n\n"
        f"{short_hashtags_str}"
    )
    short_seo_tags = [
        "World Talk Brief", pillar.replace("_", " ").title(), "Explained", "YouTube Shorts",
        short_dossier["country_profile"]["name"].title()
    ] + short_entities[:5] + winning_keywords[:4] + viral_yt_tags[:5]

    try_youtube_auto_upload(
        out_short, short_dossier["original_yt_title"], short_seo_desc, short_seo_tags,
        category_id=short_dossier.get("yt_category_id", "25"), pillar=pillar, is_short=True,
        thumbnail_path=short_pkg["selected_thumbnail"], playlist_map=playlist_map,
        summary_takeaway=short_dossier["raw_facts"][0]
    )
    hist_obj["published_keys"].add(short_dossier["story_key"])
    hist_obj["event_fingerprints"].append({"title": short_dossier["title"], "tokens": short_dossier["event_tokens"]})
    hist_obj["last_categories"].append(pillar)
    hist_obj["last_sources"].append(short_dossier["source_name"])
    return s_stats

async def render_and_upload_long_unit(lead_long_dossier, unit_num, watermark, voice_sub_dir, hist_obj, winning_keywords, viral_yt_tags, playlist_map):
    pillar = lead_long_dossier.get("pillar", "WORLD")
    print(f"\n📺 [LONG #{unit_num} - {pillar}] Building Single-Topic Case Study on: {lead_long_dossier['original_yt_title']}", flush=True)
    long_chapters = build_long_documentary_script(lead_long_dossier)
    lead_long_entities = extract_story_entities(lead_long_dossier)

    for idx, ch in enumerate(long_chapters):
        ap = f"temp/l{unit_num}_voice_{idx}.mp3"
        vc, dur, w_timings = await voice_sub_dir.synthesize_with_word_boundaries(ch["narration"], ap, pillar=pillar)
        ch["audio_clip"] = vc
        ch["duration"] = dur
        ch["word_timings"] = w_timings

    long_clips = []
    shared_long_photos = []
    long_stats_list = []
    shared_long_hashes = []
    shared_long_video_urls = set()
    running_beat_offset = 0

    for ch_idx, ch in enumerate(long_chapters):
        d_ents = extract_story_entities(ch["dossier"])
        ch_beats, _, ch_st = build_prop_driven_storyboard_1080p(
            [ch], ch["dossier"], d_ents, 1920, 1080, tag_prefix=f"long_{unit_num}_ch{ch_idx+1}",
            shared_hashes=shared_long_hashes, shared_video_urls=shared_long_video_urls,
            start_beat_offset=running_beat_offset, shared_photo_pool=shared_long_photos
        )
        running_beat_offset += len(ch_beats)
        long_stats_list.append(ch_st)
        clip = make_section_clip_from_beats(ch_beats, watermark, voice_sub_dir, ch["duration"], 1920, 1080, is_short=False)
        clip = clip.with_audio(ch["audio_clip"]) if MOVIEPY_V2 else clip.set_audio(ch["audio_clip"])
        long_clips.append(clip)

    final_long = concatenate_videoclips(long_clips, method="compose")
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

    long_hashtags_str = " ".join(pkg_report["hashtags"] + ["#Documentary", "#DeepDive"])
    long_seo_desc = (
        f"{pkg_report['selected_title']}\n\n"
        f"World Talk Brief [{pillar.replace('_', ' ')}] presents a complete single-topic case study on: {lead_long_dossier['title']}.\n\n"
        f"⏱️ CHAPTER TIMESTAMPS:\n" + "\n".join(chap_lines) + "\n\n"
        f"🔑 KEY SUBJECTS & ENTITIES: {', '.join(lead_long_entities[:8])}\n"
        f"📋 Editorial Reference ({lead_long_dossier['published_date']}): {lead_long_dossier['source_url']}\n\n"
        f"{long_hashtags_str}"
    )
    long_seo_tags = [
        "World Talk Brief", pillar.replace("_", " ").title(), "Documentary Case Study",
        lead_long_dossier["country_profile"]["name"].title()
    ] + lead_long_entities[:6] + winning_keywords[:4] + viral_yt_tags[:5]

    try_youtube_auto_upload(
        out_long, pkg_report["selected_title"], long_seo_desc, long_seo_tags,
        category_id=lead_long_dossier.get("yt_category_id", "25"), pillar=pillar, is_short=False,
        thumbnail_path=pkg_report["selected_thumbnail"], playlist_map=playlist_map,
        summary_takeaway=lead_long_dossier["raw_facts"][0]
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
        watermark = build_wtb_watermark(width=140, height=82)
        voice_sub_dir = VoiceAndSubtitleEngine()
        hist_obj = load_published_history()
        winning_keywords, viral_yt_tags, playlist_map = run_youtube_api_full_intelligence()

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
        s1_stats = await render_and_upload_short_unit(s1_dossier, 1, watermark, voice_sub_dir, hist_obj, winning_keywords, viral_yt_tags, playlist_map)
        # 2. Long Documentary #1 (Pillar #2)
        pkg_1 = await render_and_upload_long_unit(l1_lead, 1, watermark, voice_sub_dir, hist_obj, winning_keywords, viral_yt_tags, playlist_map)
        # 3. Short Video #2 (Pillar #3)
        s2_stats = await render_and_upload_short_unit(s2_dossier, 2, watermark, voice_sub_dir, hist_obj, winning_keywords, viral_yt_tags, playlist_map)
        # 4. Long Documentary #2 (Pillar #4)
        pkg_2 = await render_and_upload_long_unit(l2_lead, 2, watermark, voice_sub_dir, hist_obj, winning_keywords, viral_yt_tags, playlist_map)

        save_published_history(hist_obj)

        with open("output/wtb_1080p_report.json", "w") as f:
            json.dump({
                "videos_produced_in_run": 4,
                "next_round_robin_index": hist_obj.get("round_robin_idx", 0),
                "playlists_synced": len(playlist_map),
                "analytics_winning_keywords": winning_keywords,
                "viral_youtube_tags_discovered": viral_yt_tags,
                "short_1": {"title": s1_dossier["original_yt_title"], "pillar": s1_dossier["pillar"], "audit": s1_stats},
                "long_1": {"title": l1_lead["original_yt_title"], "pillar": l1_lead["pillar"], "packaging": pkg_1},
                "short_2": {"title": s2_dossier["original_yt_title"], "pillar": s2_dossier["pillar"], "audit": s2_stats},
                "long_2": {"title": l2_lead["original_yt_title"], "pillar": l2_lead["pillar"], "packaging": pkg_2}
            }, f, indent=2)

        print("✅ [6/6] GITHUB CLOUD 100% CLEAN HUMAN VOICE + CASE-STUDY EXPLAINER BATCH COMPLETE!", flush=True)
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
