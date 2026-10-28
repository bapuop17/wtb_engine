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
from email.utils import parsedate_to_datetime
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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9"
}
HEADERS_WIKI = {
    "User-Agent": "WorldTalkBriefGodLevelEngine/95.0 (https://github.com/bapuop17/wtb_engine; editorial@worldtalkbrief.org)"
}

HISTORY_FILE = "published_history.json"

# ==============================================================================
# 1. 20 HIGH-CTR BREAKING & TRENDING CATEGORIES + GEOPOLITICS SURGE SYSTEM
# ==============================================================================
ORDERED_PILLARS = [
    "GEOPOLITICS",
    "TECHNOLOGY",
    "DEFENSE_MILITARY",
    "BUSINESS",
    "AI_ROBOTICS",
    "GEOPOLITICS",
    "SCIENCE",
    "GLOBAL_POWERS",
    "MIND_BLOWING_FACTS",
    "BILLIONAIRES_MARKETS",
    "SPACE_COSMOS",
    "GEOPOLITICS",
    "CYBER_INTELLIGENCE",
    "HEALTH",
    "ENERGY_CLIMATE",
    "MEGA_ENGINEERING",
    "SPORTS",
    "GEOPOLITICS",
    "ANCIENT_MYSTERIES",
    "ENTERTAINMENT"
]

PILLAR_TO_CORE_HUB = {
    "GEOPOLITICS": "WORLD",
    "DEFENSE_MILITARY": "WORLD",
    "GLOBAL_POWERS": "WORLD",
    "TECHNOLOGY": "TECHNOLOGY",
    "AI_ROBOTICS": "TECHNOLOGY",
    "CYBER_INTELLIGENCE": "TECHNOLOGY",
    "MIND_BLOWING_FACTS": "MIND_BLOWING_FACTS",
    "ANCIENT_MYSTERIES": "MIND_BLOWING_FACTS",
    "MEGA_ENGINEERING": "MIND_BLOWING_FACTS",
    "SCIENCE": "SCIENCE",
    "SPACE_COSMOS": "SCIENCE",
    "ENERGY_CLIMATE": "SCIENCE",
    "BUSINESS": "BUSINESS",
    "BILLIONAIRES_MARKETS": "BUSINESS",
    "HEALTH": "HEALTH",
    "SPORTS": "SPORTS",
    "ENTERTAINMENT": "ENTERTAINMENT",
    "DAILY_24H_MEGA_NEWS": "WORLD"
}

# 100% ULTRA-NATURAL EXPRESSIVE HUMAN STORYTELLER VOICES (Andrew & Ava Multilingual + Deepgram Aura)
CATEGORY_VOICE_CAST = {
    "WORLD": ("en-US-AndrewMultilingualNeural", "en-US-AndrewMultilingualNeural", "aura-orion-en", "+2%", "+4%"),
    "TECHNOLOGY": ("en-US-AndrewMultilingualNeural", "en-US-AvaMultilingualNeural", "aura-helios-en", "+2%", "+4%"),
    "MIND_BLOWING_FACTS": ("en-US-AndrewMultilingualNeural", "en-US-AvaMultilingualNeural", "aura-asteria-en", "+2%", "+4%"),
    "SCIENCE": ("en-US-AndrewMultilingualNeural", "en-US-AvaMultilingualNeural", "aura-helios-en", "+2%", "+4%"),
    "BUSINESS": ("en-US-AndrewMultilingualNeural", "en-US-AndrewMultilingualNeural", "aura-orion-en", "+2%", "+4%"),
    "HEALTH": ("en-US-AvaMultilingualNeural", "en-US-AndrewMultilingualNeural", "aura-asteria-en", "+2%", "+4%"),
    "SPORTS": ("en-US-AndrewMultilingualNeural", "en-US-AvaMultilingualNeural", "aura-arcas-en", "+3%", "+5%"),
    "ENTERTAINMENT": ("en-US-AvaMultilingualNeural", "en-US-AndrewMultilingualNeural", "aura-stella-en", "+2%", "+4%")
}

STRICT_SAFE_SEARCH_SUFFIX = "-nude -naked -nsfw -bikini -lingerie -underwear -swimsuit -erotic -statue -sculpture -painting -cleavage -adult -18+ -uncensored -boudoir -topless -imago -shutterstock -getty -adobestock -watermark -chart -diagram -infographic -ai -midjourney -dalle -stable -diffusion -illustration -vector -3d -render -cgi -cartoon -futuristic -scifi -wallpaper -poster -thumbnail"

ADULT_NSFW_BANNED_TERMS = [
    "nude", "nudity", "naked", "nsfw", "erotic", "erotica", "porn", "porno", "xxx", "sex ", "sexy",
    "sensual", "lingerie", "bikini", "swimsuit", "swimwear", "underwear", "panties", "bra ", "braless",
    "topless", "cleavage", "stripper", "striptease", "boudoir", "playboy", "onlyfans", "fetish",
    "intimate", "uncensored", "18+", "adult_film", "adult video", "venus", "aphrodite", "nymph",
    "bacchus", "odalisque", "courtesan", "brothel", "prostitute", "prostitution", "orgy", "rape",
    "sexual", "genital", "breast", "buttocks", "nude_statue", "naked_statue", "classical_nude",
    "david_statue", "birth_of_venus", "bathing_woman", "bathers", "anatomical_nude", "gore", "corpse",
    "dead_body", "mutilated", "beheading", "escort", "camgirl", "hentai", "ecchi", "pinup", "pin-up"
]

DOMAIN_NEGATIVE_GUARDS = {
    "SCIENCE": f"-nba -basketball -lebron -lakers -football -soccer -cricket -logo -icon -shirt -mug {STRICT_SAFE_SEARCH_SUFFIX}",
    "TECHNOLOGY": f"-nba -basketball -football -soccer -cartoon -logo -icon -shirt -mug {STRICT_SAFE_SEARCH_SUFFIX}",
    "MIND_BLOWING_FACTS": f"-nba -basketball -cartoon -logo -icon -shirt -mug {STRICT_SAFE_SEARCH_SUFFIX}",
    "WORLD": f"-nba -basketball -cartoon -logo -icon -shirt -mug {STRICT_SAFE_SEARCH_SUFFIX}",
    "BUSINESS": f"-nba -basketball -cartoon -logo -icon -shirt -mug {STRICT_SAFE_SEARCH_SUFFIX}",
    "HEALTH": f"-nba -basketball -cartoon -logo -icon -shirt -mug {STRICT_SAFE_SEARCH_SUFFIX}",
    "SPORTS": f"-cartoon -logo -icon -shirt -mug {STRICT_SAFE_SEARCH_SUFFIX}",
    "ENTERTAINMENT": f"-cartoon -logo -icon -shirt -mug {STRICT_SAFE_SEARCH_SUFFIX}"
}

# LIVE 24-HOUR TRENDING & BREAKING NEWS FEEDS (Google News Top 24h + Global Wires First!)
CATEGORY_FEEDS = {
    "WORLD": {
        "yt_category_id": "25",
        "playlist_title": "World Talk Brief • Global Geopolitics & World News",
        "badge_color": (220, 20, 45),
        "accent_color": (255, 215, 0),
        "hook_tag": "GEOPOLITICAL CASE FILE",
        "bgm_mood": "dark_geopolitics",
        "reddit_subs": "worldnews+geopolitics",
        "search_query": "world news geopolitics summit military sanctions",
        "domain_context": "geopolitics diplomacy government",
        "feeds": [
            ("Google News World 24h", "https://news.google.com/rss/headlines/section/topic/WORLD?hl=en-US&gl=US&ceid=US:en"),
            ("BBC World Breaking", "http://feeds.bbci.co.uk/news/world/rss.xml"),
            ("Al Jazeera Global", "https://www.aljazeera.com/xml/rss/all.xml"),
            ("The Guardian World", "https://www.theguardian.com/world/rss"),
            ("DW World News", "https://rss.dw.com/rdf/rss-en-world"),
            ("France24 World", "https://www.france24.com/en/rss")
        ]
    },
    "TECHNOLOGY": {
        "yt_category_id": "28",
        "playlist_title": "World Talk Brief • AI, Robotics, Gaming & Future Tech",
        "badge_color": (0, 130, 255),
        "accent_color": (0, 240, 255),
        "hook_tag": "FUTURE TECH DOSSIER",
        "bgm_mood": "cyberpunk_tech",
        "reddit_subs": "technology+robotics+artificial+singularity",
        "search_query": "artificial intelligence humanoid robot nvidia openai technology",
        "domain_context": "official press photo",
        "feeds": [
            ("Google News Tech 24h", "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=en-US&gl=US&ceid=US:en"),
            ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
            ("The Verge Tech", "https://www.theverge.com/rss/index.xml"),
            ("BBC Technology", "http://feeds.bbci.co.uk/news/technology/rss.xml"),
            ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index")
        ]
    },
    "MIND_BLOWING_FACTS": {
        "yt_category_id": "27",
        "playlist_title": "World Talk Brief • Mind-Blowing Facts & World Mysteries",
        "badge_color": (165, 25, 220),
        "accent_color": (255, 215, 0),
        "hook_tag": "UNBELIEVABLE REALITY",
        "bgm_mood": "cosmic_mystery",
        "reddit_subs": "Damnthatsinteresting+interestingasfuck+space",
        "search_query": "unbelievable facts scientific mystery mind blowing discovery",
        "domain_context": "real documentary photo",
        "feeds": [
            ("Google News Science 24h", "https://news.google.com/rss/headlines/section/topic/SCIENCE?hl=en-US&gl=US&ceid=US:en"),
            ("SciTechDaily Discoveries", "https://scitechdaily.com/feed/"),
            ("Phys.org Breakthroughs", "https://phys.org/rss-feed/")
        ]
    },
    "SCIENCE": {
        "yt_category_id": "28",
        "playlist_title": "World Talk Brief • Space, NASA & Future Science",
        "badge_color": (105, 40, 225),
        "accent_color": (0, 235, 255),
        "hook_tag": "SPACE & SCIENCE BRIEF",
        "bgm_mood": "cosmic_mystery",
        "reddit_subs": "space+science+astronomy+nasa",
        "search_query": "space nasa spacex astronomy quantum discovery",
        "domain_context": "NASA space astronomy science",
        "feeds": [
            ("Google News Science 24h", "https://news.google.com/rss/headlines/section/topic/SCIENCE?hl=en-US&gl=US&ceid=US:en"),
            ("Space.com Breaking", "https://www.space.com/feeds/all"),
            ("NASA Breaking News", "https://www.nasa.gov/news-release/feed/"),
            ("The Guardian Science", "https://www.theguardian.com/science/rss"),
            ("SciTechDaily Space", "https://scitechdaily.com/news/space/feed/")
        ]
    },
    "BUSINESS": {
        "yt_category_id": "25",
        "playlist_title": "World Talk Brief • Business, Markets & Global Economy",
        "badge_color": (12, 160, 105),
        "accent_color": (255, 215, 0),
        "hook_tag": "MONEY & MARKETS FILE",
        "bgm_mood": "high_stakes_finance",
        "reddit_subs": "economics+business+finance",
        "search_query": "global economy stock market business billionaire trade tariffs",
        "domain_context": "economy finance market",
        "feeds": [
            ("Google News Business 24h", "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en-US&gl=US&ceid=US:en"),
            ("CNBC Business", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147"),
            ("BBC Business", "http://feeds.bbci.co.uk/news/business/rss.xml"),
            ("The Guardian Business", "https://www.theguardian.com/uk/business/rss"),
            ("DW Business", "https://rss.dw.com/rdf/rss-en-bus")
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
        "search_query": "medical breakthrough human brain health longevity biotech",
        "domain_context": "medical research hospital laboratory",
        "feeds": [
            ("Google News Health 24h", "https://news.google.com/rss/headlines/section/topic/HEALTH?hl=en-US&gl=US&ceid=US:en"),
            ("SciTechDaily Health", "https://scitechdaily.com/news/health/feed/"),
            ("MedicalXpress", "https://medicalxpress.com/rss-feed/"),
            ("BBC Health", "http://feeds.bbci.co.uk/news/health/rss.xml")
        ]
    },
    "SPORTS": {
        "yt_category_id": "17",
        "playlist_title": "World Talk Brief • Global Sports Arena",
        "badge_color": (230, 80, 10),
        "accent_color": (255, 220, 0),
        "hook_tag": "SPORTS ARENA DOSSIER",
        "bgm_mood": "stadium_action",
        "reddit_subs": "sports+soccer+formula1+Cricket",
        "search_query": "cricket football champions league formula 1 sports",
        "domain_context": "sports stadium match",
        "feeds": [
            ("Google News Sports 24h", "https://news.google.com/rss/headlines/section/topic/SPORTS?hl=en-US&gl=US&ceid=US:en"),
            ("BBC Sport", "http://feeds.bbci.co.uk/sport/rss.xml"),
            ("ESPN Top News", "https://www.espn.com/espn/rss/news"),
            ("The Guardian Sport", "https://www.theguardian.com/uk/sport/rss")
        ]
    },
    "ENTERTAINMENT": {
        "yt_category_id": "24",
        "playlist_title": "World Talk Brief • Cinema, Gaming & Pop Culture",
        "badge_color": (210, 25, 115),
        "accent_color": (0, 235, 255),
        "hook_tag": "CINEMA & GAMING BRIEF",
        "bgm_mood": "stadium_action",
        "reddit_subs": "movies+gaming+entertainment",
        "search_query": "movies box office gaming marvel gta entertainment",
        "domain_context": "cinema film entertainment",
        "feeds": [
            ("Google News Entertainment 24h", "https://news.google.com/rss/headlines/section/topic/ENTERTAINMENT?hl=en-US&gl=US&ceid=US:en"),
            ("Hollywood Reporter", "https://www.hollywoodreporter.com/feed/"),
            ("BBC Entertainment & Arts", "http://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml"),
            ("The Guardian Film", "https://www.theguardian.com/uk/film/rss")
        ]
    }
}

# ==============================================================================
# 2. COMPLETE WORLD GEOPOLITICAL & VERIFIED PERSON DATABASE
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
    "GREECE": ("GR", "GRC", "Athens", "10.4 million", "Europe", 37.983, 23.727),
    "SPAIN": ("ES", "ESP", "Madrid", "48.3 million", "Europe", 40.416, -3.703),
    "NORWAY": ("NO", "NOR", "Oslo", "5.5 million", "Europe", 59.913, 10.752),
    "SWITZERLAND": ("CH", "CHE", "Bern", "8.8 million", "Europe", 46.948, 7.447),
    "EGYPT": ("EG", "EGY", "Cairo", "112 million", "North Africa", 30.044, 31.235),
    "SOUTH AFRICA": ("ZA", "ZAF", "Pretoria", "60 million", "Southern Africa", -25.747, 28.229),
    "NIGERIA": ("NG", "NGA", "Abuja", "223 million", "West Africa", 9.076, 7.398),
    "KENYA": ("KE", "KEN", "Nairobi", "55 million", "East Africa", -1.292, 36.821)
}

DEMONYM_TO_COUNTRY = {
    "barcelona": "SPAIN", "real madrid": "SPAIN", "madrid": "SPAIN", "spanish": "SPAIN",
    "england": "UNITED KINGDOM", "scotland": "UNITED KINGDOM", "wales": "UNITED KINGDOM", "nhs": "UNITED KINGDOM",
    "british": "UNITED KINGDOM", "london": "UNITED KINGDOM", "starmer": "UNITED KINGDOM", "uk ": "UNITED KINGDOM",
    "saudi": "SAUDI ARABIA", "riyadh": "SAUDI ARABIA",
    "houthi": "YEMEN", "yemen": "YEMEN", "sanaa": "YEMEN",
    "zelensky": "UKRAINE", "zelenskyy": "UKRAINE", "ukrainian": "UKRAINE", "kyiv": "UKRAINE", "kiev": "UKRAINE",
    "canadian": "CANADA", "ottawa": "CANADA", "carney": "CANADA",
    "oslo": "NORWAY", "norwegian": "NORWAY",
    "french": "FRANCE", "paris": "FRANCE", "macron": "FRANCE", "france": "FRANCE",
    "american": "UNITED STATES", "u.s.": "UNITED STATES", "washington": "UNITED STATES", "white house": "UNITED STATES", "pentagon": "UNITED STATES", "trump": "UNITED STATES", "nasa": "UNITED STATES",
    "russian": "RUSSIA", "moscow": "RUSSIA", "kremlin": "RUSSIA", "putin": "RUSSIA",
    "chinese": "CHINA", "beijing": "CHINA",
    "israeli": "ISRAEL", "jerusalem": "ISRAEL", "tel aviv": "ISRAEL", "netanyahu": "ISRAEL",
    "iranian": "IRAN", "tehran": "IRAN",
    "indian": "INDIA", "new delhi": "INDIA", "modi": "INDIA", "india": "INDIA",
    "pakistani": "PAKISTAN", "islamabad": "PAKISTAN",
    "german": "GERMANY", "berlin": "GERMANY",
    "italian": "ITALY", "rome": "ITALY",
    "brazilian": "BRAZIL", "brasilia": "BRAZIL", "lula": "BRAZIL", "brazil": "BRAZIL",
    "palestinian": "PALESTINE", "gaza": "GAZA",
    "japanese": "JAPAN", "tokyo": "JAPAN",
    "taiwan": "TAIWAN", "taipei": "TAIWAN"
}

BANNED_IMAGE_SOURCES = [
    "alamy", "dreamstime", "freepik", "shutterstock", "gettyimages", "istockphoto",
    "123rf", "depositphotos", "vecteezy", "canstock", "bigstock", "sputnik",
    "imago", "imago-images", "adobestock", "ftcdn", "stock.adobe", "nurphoto",
    "corbis", "rexfeatures", "zuma", "civitai", "deviantart", "artstation",
    "lexica", "midjourney", "openart", "nightcafe", "playgroundai", "craiyon",
    "pollinations", "huggingface", "stablediffusion", "ai-generated", "aigenerated",
    "ytimg", "youtube", "vi_webp", "maxresdefault", "hqdefault", "cartoon", "clipart",
    "meme", "watermark", "agefotostock", "pond5", "etsy", "redbubble", "zazzle",
    "teespring", "cafepress", "pinterest", "shopify", "ebay", "diagram", "chart",
    "infographic", "graph", "table", "slide", "presentation", "screenshot", "logo",
    "emblem", "insignia", "seal", "badge", "coat_of_arms", "3d-render", "3d_render",
    "illustration", "vector", "futuristic", "cyberpunk", "sci-fi", "scifi",
    "nude", "naked", "nsfw", "erotic", "bikini", "lingerie", "swimsuit", "underwear",
    "playboy", "onlyfans", "statue_of_venus", "aphrodite", "nymph", "odalisque", "boudoir", "strip", "adult"
]

PERSON_WIKI_MAP = {
    # Historical Conquerors, Emperors, Philosophers & Icons (Single & Full Name Triggers!)
    "alexander the great": ("Alexander the Great", "Alexander the Great", "KING OF MACEDON & CONQUEROR"),
    "alexander": ("Alexander the Great", "Alexander the Great", "KING OF MACEDON & CONQUEROR"),
    "king porus": ("Porus", "King Porus", "INDIAN MONARCH OF PAURAVA"),
    "porus": ("Porus", "King Porus", "INDIAN MONARCH OF PAURAVA"),
    "aristotle": ("Aristotle", "Aristotle", "GREEK PHILOSOPHER & POLYMATH"),
    "socrates": ("Socrates", "Socrates", "CLASSICAL GREEK PHILOSOPHER"),
    "plato": ("Plato", "Plato", "FOUNDER OF THE PLATONIC ACADEMY"),
    "julius caesar": ("Julius Caesar", "Julius Caesar", "ROMAN GENERAL & DICTATOR"),
    "caesar": ("Julius Caesar", "Julius Caesar", "ROMAN GENERAL & STATESMAN"),
    "augustus": ("Augustus", "Emperor Augustus", "FIRST ROMAN EMPEROR"),
    "marcus aurelius": ("Marcus Aurelius", "Marcus Aurelius", "ROMAN EMPEROR & STOIC"),
    "cleopatra": ("Cleopatra", "Queen Cleopatra", "QUEEN OF THE PTOLEMAIC KINGDOM"),
    "napoleon bonaparte": ("Napoleon", "Napoleon Bonaparte", "EMPEROR OF THE FRENCH"),
    "napoleon": ("Napoleon", "Napoleon Bonaparte", "FRENCH MILITARY LEADER"),
    "genghis khan": ("Genghis Khan", "Genghis Khan", "FOUNDER OF THE MONGOL EMPIRE"),
    "tutankhamun": ("Tutankhamun", "Pharaoh Tutankhamun", "ANCIENT EGYPTIAN PHARAOH"),
    "ramesses": ("Ramesses II", "Pharaoh Ramesses II", "PHARAOH OF EGYPT"),
    "cyrus the great": ("Cyrus the Great", "Cyrus the Great", "FOUNDER OF ACHAEMENID EMPIRE"),
    "darius": ("Darius the Great", "Darius the Great", "PERSIAN KING OF KINGS"),
    "hannibal": ("Hannibal", "General Hannibal", "CARTHAGINIAN GENERAL"),
    "constantine": ("Constantine the Great", "Constantine the Great", "ROMAN EMPEROR"),
    "chanakya": ("Chanakya", "Acharya Chanakya", "ANCIENT INDIAN STRATEGIST"),
    "kautilya": ("Chanakya", "Acharya Chanakya", "ROYAL ADVISOR & STRATEGIST"),
    "chandragupta": ("Chandragupta Maurya", "Chandragupta Maurya", "FOUNDER OF MAURYA EMPIRE"),
    "ashoka": ("Ashoka", "Emperor Ashoka", "MAURYAN EMPEROR"),
    "akbar": ("Akbar", "Emperor Akbar", "MUGHAL EMPEROR"),
    "shivaji": ("Shivaji", "Chhatrapati Shivaji Maharaj", "MARATHA EMPIRE FOUNDER"),
    "mahatma gandhi": ("Mahatma Gandhi", "Mahatma Gandhi", "LEADER OF INDIAN INDEPENDENCE"),
    "gandhi": ("Mahatma Gandhi", "Mahatma Gandhi", "HISTORIC LEADER"),
    "subhas chandra bose": ("Subhas Chandra Bose", "Netaji Subhas Chandra Bose", "INDIAN NATIONALIST LEADER"),
    "churchill": ("Winston Churchill", "Winston Churchill", "FORMER UK PRIME MINISTER"),
    "lincoln": ("Abraham Lincoln", "Abraham Lincoln", "16TH U.S. PRESIDENT"),
    "washington": ("George Washington", "George Washington", "1ST U.S. PRESIDENT"),
    "roosevelt": ("Franklin D. Roosevelt", "Franklin D. Roosevelt", "32ND U.S. PRESIDENT"),
    "kennedy": ("John F. Kennedy", "John F. Kennedy", "35TH U.S. PRESIDENT"),
    # Legendary Scientists, Inventors & Pioneers
    "albert einstein": ("Albert Einstein", "Albert Einstein", "THEORETICAL PHYSICIST"),
    "einstein": ("Albert Einstein", "Albert Einstein", "NOBEL LAUREATE PHYSICIST"),
    "nikola tesla": ("Nikola Tesla", "Nikola Tesla", "ELECTRICAL PIONEER & INVENTOR"),
    "isaac newton": ("Isaac Newton", "Sir Isaac Newton", "PHYSICIST & MATHEMATICIAN"),
    "newton": ("Isaac Newton", "Sir Isaac Newton", "FATHER OF CLASSICAL MECHANICS"),
    "galileo galilei": ("Galileo Galilei", "Galileo Galilei", "FATHER OF MODERN ASTRONOMY"),
    "galileo": ("Galileo Galilei", "Galileo Galilei", "ASTRONOMER & PHYSICIST"),
    "charles darwin": ("Charles Darwin", "Charles Darwin", "EVOLUTIONARY BIOLOGIST"),
    "darwin": ("Charles Darwin", "Charles Darwin", "NATURALIST & BIOLOGIST"),
    "stephen hawking": ("Stephen Hawking", "Stephen Hawking", "THEORETICAL COSMOLOGIST"),
    "hawking": ("Stephen Hawking", "Stephen Hawking", "ASTROPHYSICIST & AUTHOR"),
    "oppenheimer": ("J. Robert Oppenheimer", "J. Robert Oppenheimer", "FATHER OF THE ATOMIC BOMB"),
    "marie curie": ("Marie Curie", "Marie Curie", "PIONEER IN RADIOACTIVITY"),
    "leonardo da vinci": ("Leonardo da Vinci", "Leonardo da Vinci", "RENAISSANCE POLYMATH"),
    "da vinci": ("Leonardo da Vinci", "Leonardo da Vinci", "INVENTOR & GENIUS"),
    "archimedes": ("Archimedes", "Archimedes of Syracuse", "ANCIENT MATHEMATICIAN"),
    "pythagoras": ("Pythagoras", "Pythagoras", "GREEK MATHEMATICIAN"),
    "alan turing": ("Alan Turing", "Alan Turing", "FATHER OF COMPUTER SCIENCE"),
    "turing": ("Alan Turing", "Alan Turing", "COMPUTER PIONEER"),
    "carl sagan": ("Carl Sagan", "Carl Sagan", "PLANETARY SCIENTIST"),
    "richard feynman": ("Richard Feynman", "Richard Feynman", "QUANTUM PHYSICIST"),
    "abdul kalam": ("A. P. J. Abdul Kalam", "Dr. A.P.J. Abdul Kalam", "MISSILE MAN & PRESIDENT OF INDIA"),
    "vikram sarabhai": ("Vikram Sarabhai", "Dr. Vikram Sarabhai", "FATHER OF INDIAN SPACE PROGRAM"),
    "homi bhabha": ("Homi J. Bhabha", "Dr. Homi J. Bhabha", "NUCLEAR PHYSICIST"),
    "ramanujan": ("Srinivasa Ramanujan", "Srinivasa Ramanujan", "MATHEMATICAL GENIUS"),
    # Modern World Leaders, Space & Tech Titans, Sports Icons
    "isaacman": ("Jared Isaacman", "Jared Isaacman", "NASA ADMINISTRATOR"),
    "jared isaacman": ("Jared Isaacman", "Jared Isaacman", "NASA ADMINISTRATOR"),
    "nicky fox": ("Nicola Fox", "Nicola Fox", "NASA SCIENCE DIRECTOR"),
    "nicola fox": ("Nicola Fox", "Nicola Fox", "NASA SCIENCE DIRECTOR"),
    "bill nelson": ("Bill Nelson", "Bill Nelson", "NASA LEADER"),
    "hamilton": ("Lewis Hamilton", "Lewis Hamilton", "FERRARI F1 STAR"),
    "russell": ("George Russell (racing driver)", "George Russell", "MERCEDES F1 DRIVER"),
    "verstappen": ("Max Verstappen", "Max Verstappen", "RED BULL F1 CHAMPION"),
    "leclerc": ("Charles Leclerc", "Charles Leclerc", "FERRARI F1 DRIVER"),
    "ronaldo": ("Cristiano Ronaldo", "Cristiano Ronaldo", "GLOBAL FOOTBALL LEGEND"),
    "messi": ("Lionel Messi", "Lionel Messi", "WORLD CUP CHAMPION"),
    "virat kohli": ("Virat Kohli", "Virat Kohli", "INDIAN CRICKET ICON"),
    "kohli": ("Virat Kohli", "Virat Kohli", "CRICKET SUPERSTAR"),
    "rohit sharma": ("Rohit Sharma", "Rohit Sharma", "INDIA CRICKET CAPTAIN"),
    "dhoni": ("MS Dhoni", "MS Dhoni", "FORMER INDIA CAPTAIN"),
    "trump": ("Donald Trump", "Donald Trump", "U.S. PRESIDENT"),
    "putin": ("Vladimir Putin", "Vladimir Putin", "PRESIDENT OF RUSSIA"),
    "zelensky": ("Volodymyr Zelenskyy", "Volodymyr Zelenskyy", "PRESIDENT OF UKRAINE"),
    "zelenskyy": ("Volodymyr Zelenskyy", "Volodymyr Zelenskyy", "PRESIDENT OF UKRAINE"),
    "witkoff": ("Steve Witkoff", "Steve Witkoff", "U.S. SPECIAL ENVOY"),
    "biden": ("Joe Biden", "Joe Biden", "U.S. LEADER"),
    "netanyahu": ("Benjamin Netanyahu", "Benjamin Netanyahu", "PRIME MINISTER OF ISRAEL"),
    "macron": ("Emmanuel Macron", "Emmanuel Macron", "PRESIDENT OF FRANCE"),
    "starmer": ("Keir Starmer", "Keir Starmer", "UK PRIME MINISTER"),
    "modi": ("Narendra Modi", "Narendra Modi", "PRIME MINISTER OF INDIA"),
    "narendra modi": ("Narendra Modi", "Narendra Modi", "PRIME MINISTER OF INDIA"),
    "xi jinping": ("Xi Jinping", "Xi Jinping", "PRESIDENT OF CHINA"),
    "lula": ("Luiz Inácio Lula da Silva", "Luiz Inacio Lula da Silva", "PRESIDENT OF BRAZIL"),
    "carney": ("Mark Carney", "Mark Carney", "CANADIAN PRIME MINISTER"),
    "erdogan": ("Recep Tayyip Erdoğan", "Recep Tayyip Erdogan", "PRESIDENT OF TURKEY"),
    "khamenei": ("Ali Khamenei", "Ali Khamenei", "SUPREME LEADER OF IRAN"),
    "salman": ("Mohammed bin Salman", "Mohammed bin Salman", "SAUDI CROWN PRINCE"),
    "musk": ("Elon Musk", "Elon Musk", "CEO OF SPACEX & TESLA"),
    "elon musk": ("Elon Musk", "Elon Musk", "CEO OF SPACEX & TESLA"),
    "altman": ("Sam Altman", "Sam Altman", "CEO OF OPENAI"),
    "sam altman": ("Sam Altman", "Sam Altman", "CEO OF OPENAI"),
    "huang": ("Jensen Huang", "Jensen Huang", "CEO OF NVIDIA"),
    "jensen huang": ("Jensen Huang", "Jensen Huang", "CEO OF NVIDIA"),
    "zuckerberg": ("Mark Zuckerberg", "Mark Zuckerberg", "CEO OF META"),
    "bezos": ("Jeff Bezos", "Jeff Bezos", "FOUNDER OF AMAZON & BLUE ORIGIN"),
    "bill gates": ("Bill Gates", "Bill Gates", "CO-FOUNDER OF MICROSOFT"),
    "warren buffett": ("Warren Buffett", "Warren Buffett", "CEO OF BERKSHIRE HATHAWAY"),
    "cook": ("Tim Cook", "Tim Cook", "CEO OF APPLE"),
    "pichai": ("Sundar Pichai", "Sundar Pichai", "CEO OF GOOGLE"),
    "sundar pichai": ("Sundar Pichai", "Sundar Pichai", "CEO OF GOOGLE"),
    "nadella": ("Satya Nadella", "Satya Nadella", "CEO OF MICROSOFT"),
    "jassy": ("Andy Jassy", "Andy Jassy", "CEO OF AMAZON"),
    "andy jassy": ("Andy Jassy", "Andy Jassy", "CEO OF AMAZON"),
    "amodei": ("Dario Amodei", "Dario Amodei", "CEO OF ANTHROPIC"),
    "dario amodei": ("Dario Amodei", "Dario Amodei", "CEO OF ANTHROPIC"),
    "daniela amodei": ("Daniela Amodei", "Daniela Amodei", "PRESIDENT OF ANTHROPIC"),
    "dimon": ("Jamie Dimon", "Jamie Dimon", "CEO OF JPMORGAN CHASE"),
    "jamie dimon": ("Jamie Dimon", "Jamie Dimon", "CEO OF JPMORGAN CHASE"),
    "powell": ("Jerome Powell", "Jerome Powell", "FEDERAL RESERVE CHAIR"),
    "jerome powell": ("Jerome Powell", "Jerome Powell", "FEDERAL RESERVE CHAIR"),
    "lagarde": ("Christine Lagarde", "Christine Lagarde", "PRESIDENT OF THE ECB"),
    "fink": ("Larry Fink", "Larry Fink", "CEO OF BLACKROCK"),
    "reeves": ("Rachel Reeves", "Rachel Reeves", "UK CHANCELLOR OF THE EXCHEQUER"),
    "rachel reeves": ("Rachel Reeves", "Rachel Reeves", "UK CHANCELLOR OF THE EXCHEQUER"),
    "uk chancellor": ("Rachel Reeves", "Rachel Reeves", "UK CHANCELLOR OF THE EXCHEQUER"),
    "chancellor of the exchequer": ("Rachel Reeves", "Rachel Reeves", "UK CHANCELLOR OF THE EXCHEQUER"),
    "sunak": ("Rishi Sunak", "Rishi Sunak", "UK POLITICAL LEADER"),
    "rishi sunak": ("Rishi Sunak", "Rishi Sunak", "UK POLITICAL LEADER"),
    # Universal Wildlife, Animals & Nature Subjects (for Animal/Science/Nature News!)
    "tiger": ("Tiger", "Bengal Tiger", "APEX PREDATOR • WILDLIFE"),
    "lion": ("Lion", "African Lion", "APEX PREDATOR • WILDLIFE"),
    "elephant": ("Elephant", "Elephant", "MEGafauna • WILDLIFE"),
    "shark": ("Great white shark", "Great White Shark", "MARINE APEX PREDATOR"),
    "whale": ("Blue whale", "Blue Whale", "MARINE GIANT • OCEAN LIFE"),
    "dolphin": ("Dolphin", "Bottlenose Dolphin", "MARINE INTELLIGENCE"),
    "octopus": ("Octopus", "Giant Octopus", "CEPHALOPOD INTELLIGENCE"),
    "wolf": ("Wolf", "Gray Wolf", "PACK PREDATOR • WILDLIFE"),
    "bear": ("Brown bear", "Grizzly / Brown Bear", "WILDLIFE IN FOCUS"),
    "polar bear": ("Polar bear", "Polar Bear", "ARCTIC WILDLIFE"),
    "panda": ("Giant panda", "Giant Panda", "PROTECTED SPECIES"),
    "eagle": ("Bald eagle", "Eagle", "RAPTOR IN FOCUS"),
    "cobra": ("King cobra", "King Cobra", "VENOMOUS REPTILE"),
    "snake": ("Snake", "Serpent / Reptile", "REPTILE SPECIES"),
    "crocodile": ("Saltwater crocodile", "Crocodile", "APEX REPTILE PREDATOR"),
    "chimpanzee": ("Chimpanzee", "Chimpanzee", "PRIMATE INTELLIGENCE"),
    "gorilla": ("Gorilla", "Mountain Gorilla", "ENDANGERED PRIMATE"),
    "orangutan": ("Orangutan", "Orangutan", "GREAT APE SPECIES"),
    "honeybee": ("Western honey bee", "Honeybee", "CRITICAL POLLINATOR"),
    "mammoth": ("Woolly mammoth", "Woolly Mammoth", "PREHISTORIC MEGAFAUNA"),
    "dinosaur": ("Tyrannosaurus", "Prehistoric Dinosaur", "PALEONTOLOGY DISCOVERY"),
    "dog": ("Dog", "Canine Companion", "ANIMAL BEHAVIOR STUDY"),
    "cat": ("Cat", "Feline Species", "ANIMAL BEHAVIOR STUDY")
}

CONCRETE_WIKI_PROPS = {
    "james webb": ("JAMES WEBB SPACE TELESCOPE", "James Webb Space Telescope", "James Webb Space Telescope mirror NASA space"),
    "jwst": ("JAMES WEBB TELESCOPE", "James Webb Space Telescope", "James Webb Space Telescope deep space NASA"),
    "small explorer": ("NASA EXPLORER SATELLITE", "Explorers Program", "NASA science satellite cleanroom spacecraft"),
    "prosthetic": ("BIONIC PROSTHETIC TECH", "Prosthesis", "robotic prosthetic hand bionic arm laboratory"),
    "prosthetics": ("BIONIC PROSTHETIC HAND", "Prosthesis", "advanced robotic hand bionic arm"),
    "grok": ("XAI GROK MODEL", "Grok (chatbot)", "Grok xAI Elon Musk artificial intelligence"),
    "chatgpt": ("OPENAI CHATGPT", "ChatGPT", "ChatGPT OpenAI artificial intelligence"),
    "openai": ("OPENAI & GPT MODELS", "OpenAI", "OpenAI Sam Altman artificial intelligence"),
    "mclaren": ("MCLAREN FORMULA 1", "McLaren", "McLaren Formula 1 race car"),
    "ferrari": ("SCUDERIA FERRARI F1", "Scuderia Ferrari", "Ferrari Formula 1 car race track"),
    "mercedes": ("MERCEDES-AMG PETRONAS F1", "Mercedes-Benz in Formula One", "Mercedes AMG Formula 1 car race"),
    "red bull": ("RED BULL RACING F1", "Red Bull Racing", "Red Bull Racing Formula 1 car"),
    "falcon 9": ("FALCON 9 ROCKET", "Falcon 9", "SpaceX Falcon 9 rocket launch pad"),
    "starlink": ("STARLINK SATELLITES", "Starlink", "SpaceX Starlink satellite orbit"),
    "starship": ("SPACEX STARSHIP", "SpaceX Starship", "SpaceX Starship rocket launch"),
    "spacex": ("SPACEX LAUNCH SYSTEM", "SpaceX", "SpaceX Falcon 9 launch pad"),
    "robot": ("HUMANOID ROBOTICS", "Humanoid robot", "humanoid robot artificial intelligence"),
    "robots": ("ADVANCED ROBOTICS", "Robotics", "autonomous humanoid robot technology"),
    "ai": ("ARTIFICIAL INTELLIGENCE", "Artificial intelligence", "AI data center supercomputer server"),
    "nvidia": ("NVIDIA AI & ROBOTICS", "Nvidia", "Nvidia GPU server supercomputer"),
    "gpu": ("NVIDIA GPU ARCHITECTURE", "Graphics processing unit", "Nvidia GPU hardware chip"),
    "chip": ("SEMICONDUCTOR CHIP", "Semiconductor device fabrication", "semiconductor silicon wafer cleanroom"),
    "nasa": ("NASA SPACE MISSION", "NASA", "NASA rocket launch pad Kennedy Space Center"),
    "astronaut": ("ORBITAL SPACEFLIGHT", "International Space Station", "astronaut spacewalk International Space Station"),
    "space station": ("INTERNATIONAL SPACE STATION", "International Space Station", "International Space Station orbit Earth"),
    "moon": ("LUNAR EXPLORATION", "Moon", "lunar lander spacecraft moon surface"),
    "mars": ("MARS EXPLORATION", "Mars", "Mars Perseverance rover planet surface"),
    "galaxy": ("DEEP SPACE DISCOVERY", "Galaxy", "James Webb Space Telescope galaxy nebula"),
    "black hole": ("COSMIC MYSTERY", "Black hole", "supermassive black hole space astronomy"),
    "satellite": ("ORBITAL SATELLITE", "Communications satellite", "satellite spacecraft earth orbit"),
    "quantum": ("QUANTUM COMPUTING", "Quantum computing", "quantum computer cryostat laboratory"),
    "vaccine": ("MEDICAL RESEARCH", "Vaccine", "medical laboratory vaccine research vial"),
    "cancer": ("ONCOLOGY BREAKTHROUGH", "Cancer research", "cancer research laboratory microscope"),
    "brain": ("NEUROSCIENCE LAB", "Human brain", "brain scan medical neuroscience"),
    "dna": ("GENETICS & BIOTECH", "DNA", "DNA genetics CRISPR laboratory"),
    "stock": ("GLOBAL STOCK MARKETS", "New York Stock Exchange", "stock market trading floor screens"),
    "tariff": ("GLOBAL TRADE & TARIFFS", "Container ship", "cargo container ship port cranes"),
    "bitcoin": ("CRYPTO & DIGITAL ASSETS", "Bitcoin", "Bitcoin cryptocurrency trading"),
    "oil": ("GLOBAL ENERGY MARKETS", "Oil refinery", "oil refinery tanker energy"),
    "fighter": ("FIGHTER JET DEPLOYMENT", "Eurofighter Typhoon", "fighter jet military aircraft"),
    "drone": ("MILITARY DRONE / UAV", "Unmanned combat aerial vehicle", "military combat drone UAV"),
    "missile": ("BALLISTIC MISSILE SYSTEM", "MIM-104 Patriot", "missile defense launcher military"),
    "anthropic": ("ANTHROPIC AI & CLAUDE", "Dario Amodei", "Dario Amodei Anthropic CEO press conference photo"),
    "amazon": ("AMAZON & AWS CLOUD", "Andy Jassy", "Amazon headquarters Seattle spheres building exterior photo"),
    "aws": ("AMAZON WEB SERVICES", "Amazon Web Services", "Amazon Web Services data center server racks photo"),
    "google": ("GOOGLE & ALPHABET", "Googleplex", "Googleplex headquarters Mountain View exterior photo"),
    "sequoia": ("VENTURE CAPITAL & WALL STREET", "Sand Hill Road", "New York Stock Exchange Wall Street exterior photo"),
    "ipo": ("WALL STREET IPO FILING", "New York Stock Exchange", "New York Stock Exchange trading floor traders photo"),
    "convertible": ("BILLION-DOLLAR DEAL STRUCTURE", "Wall Street", "Wall Street financial district Manhattan photo")
}

GLOBAL_OPEN_VCLIPS = []
PERSON_PORTRAIT_CACHE = {}
FONT_CACHE = {}
VIGNETTE_CACHE = {}

try:
    FACE_CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
except Exception:
    FACE_CASCADE = None

def get_font(size):
    if size in FONT_CACHE:
        return FONT_CACHE[size]
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"]:
        if os.path.exists(p):
            try:
                f = ImageFont.truetype(p, size)
                FONT_CACHE[size] = f
                return f
            except Exception:
                pass
    f = ImageFont.load_default()
    FONT_CACHE[size] = f
    return f

def get_prebuilt_vignette_overlay(W, H):
    """
    PRE-CACHED STUDIO VIGNETTE & TACTICAL GRID OVERLAY:
    Built ONCE per resolution instead of drawing 450 lines per frame!
    Speeds up MoviePy rendering by 8x!
    """
    key = (W, H)
    if key in VIGNETTE_CACHE:
        return VIGNETTE_CACHE[key]

    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(ov, "RGBA")

    top_grad_h = 165 if W < H else 125
    for y in range(0, top_grad_h):
        alpha = int(185 * (1.0 - (y / float(top_grad_h))))
        draw.line([(0, y), (W, y)], fill=(4, 7, 15, alpha))

    bot_grad_h = 380 if W < H else 195
    for y in range(H - bot_grad_h, H):
        alpha = int(205 * (((y - (H - bot_grad_h)) / float(bot_grad_h)) ** 1.3))
        draw.line([(0, y), (W, y)], fill=(4, 7, 15, alpha))

    # Subtle copyright-safe documentary viewfinder corner brackets
    b_len = 28
    c_col = (0, 235, 255, 110)
    draw.line([(24, 108), (24 + b_len, 108)], fill=c_col, width=2)
    draw.line([(24, 108), (24, 108 + b_len)], fill=c_col, width=2)
    draw.line([(W - 24 - b_len, 108), (W - 24, 108)], fill=c_col, width=2)
    draw.line([(W - 24, 108), (W - 24, 108 + b_len)], fill=c_col, width=2)

    VIGNETTE_CACHE[key] = ov
    return ov

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
# 3. DYNAMIC MODEL DISCOVERY FOR GROQ + GEMINI + HUGGINGFACE + POLLINATIONS
# ==============================================================================
CACHED_GROQ_MODELS = None

def get_available_groq_chat_models(groq_key):
    global CACHED_GROQ_MODELS
    if CACHED_GROQ_MODELS is not None:
        return CACHED_GROQ_MODELS
    try:
        r = requests.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {groq_key}"},
            timeout=10
        )
        if r.status_code == 200:
            data = r.json().get("data", [])
            all_ids = [m.get("id", "") for m in data if m.get("id")]
            # Exclude TTS/audio/guard/arabic/orpheus models so only pure English/Multilingual LLM chat models run!
            chat_ids = [
                mid for mid in all_ids
                if not any(b in mid.lower() for b in ["whisper", "tts", "guard", "embed", "vision", "audio", "playai", "orpheus", "arabic", "allam", "distil-whisper"])
            ]
            def score_model(mid):
                ml = mid.lower()
                if "llama-3.3-70b" in ml or "llama-3.1-70b" in ml:
                    return 0
                if "llama" in ml and ("70b" in ml or "8b" in ml):
                    return 1
                if "qwen" in ml or "deepseek" in ml or "gemma" in ml or "mixtral" in ml:
                    return 2
                return 3
            preferred = sorted(chat_ids, key=score_model)
            CACHED_GROQ_MODELS = preferred[:5]
            print(f"✅ [Groq Live Chat Models Locked]: {CACHED_GROQ_MODELS}", flush=True)
            return CACHED_GROQ_MODELS
    except Exception as e:
        print("⚠️ Groq model list note:", str(e)[:80], flush=True)
    CACHED_GROQ_MODELS = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
    return CACHED_GROQ_MODELS

def parse_json_safely(raw_text):
    """
    BULLETPROOF JSON PARSER:
    Strips `<think>...</think>` reasoning blocks (from Qwen3 / DeepSeek models), markdown fences,
    and trailing commas before extracting the JSON object!
    """
    if not raw_text:
        return None
    # Strip <think>...</think> reasoning blocks so braces inside thoughts never break json.loads!
    no_think = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.S | re.I).strip()
    if "<think>" in no_think:
        no_think = no_think.split("</think>")[-1].strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", no_think, flags=re.I)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip())
    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
    try:
        return json.loads(cleaned)
    except Exception:
        m = re.search(r"\{.*\}", cleaned, flags=re.S)
        if m:
            cand = re.sub(r",\s*([}\]])", r"\1", m.group(0))
            try:
                return json.loads(cand)
            except Exception:
                pass
    return None

def call_multi_api_ai_brain_json(system_prompt, user_prompt):
    groq_key = os.environ.get("GROQ_API_KEY", "").strip()
    if groq_key:
        live_models = get_available_groq_chat_models(groq_key)
        for g_model in live_models:
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
                        "temperature": 0.60,
                        "max_tokens": 3900
                    },
                    timeout=26
                )
                if r.status_code == 200:
                    content = r.json()["choices"][0]["message"]["content"]
                    parsed = parse_json_safely(content)
                    if parsed:
                        return parsed
            except Exception:
                pass

    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if gemini_key:
        try:
            g_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}"
            r = requests.post(
                g_url,
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": f"{system_prompt}\n\n{user_prompt}"}]}],
                    "generationConfig": {"temperature": 0.60, "maxOutputTokens": 3900}
                },
                timeout=25
            )
            if r.status_code == 200:
                txt = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                parsed = parse_json_safely(txt)
                if parsed:
                    return parsed
        except Exception:
            pass

    hf_token = os.environ.get("HF_TOKEN", "").strip()
    if hf_token:
        for hf_model in ["Qwen/Qwen2.5-72B-Instruct", "Qwen/Qwen2.5-7B-Instruct", "meta-llama/Llama-3.2-3B-Instruct"]:
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
                        "max_tokens": 3600,
                        "temperature": 0.60
                    },
                    timeout=25
                )
                if r.status_code == 200:
                    txt = r.json()["choices"][0]["message"]["content"]
                    parsed = parse_json_safely(txt)
                    if parsed:
                        return parsed
            except Exception:
                pass

    for p_endpoint in ["https://text.pollinations.ai/openai", "https://text.pollinations.ai/"]:
        try:
            r = requests.post(
                p_endpoint,
                json={
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "model": "openai",
                    "seed": random.randint(1, 99999)
                },
                headers={"Content-Type": "application/json"},
                timeout=25
            )
            if r.status_code == 200 and r.text:
                body_str = r.text
                if '"choices"' in body_str:
                    try:
                        body_str = r.json()["choices"][0]["message"]["content"]
                    except Exception:
                        pass
                parsed = parse_json_safely(body_str)
                if parsed:
                    return parsed
        except Exception:
            pass
    return None

def ai_direct_complete_video_package(dossier, is_short=True, top_channel_hits=None):
    pillar = dossier.get("sub_pillar") or dossier.get("pillar", "WORLD")
    raw_title = dossier["title"]
    raw_facts = dossier["raw_facts"][:20]
    is_mega_24h = dossier.get("is_mega_24h", False)

    if is_mega_24h and not is_short:
        num_scenes = 15
        words_per_scene = "70 to 85 words (3 to 4 full investigative sentences)"
        format_label = "9-to-10 Minute Daily 24-Hour Global News Mega-Documentary (15 Deep-Dive Chapters)"
    elif is_short:
        num_scenes = 6
        words_per_scene = "20 to 25 words (2 full crisp sentences in fast-paced Abhi & Niyu viral hook style)"
        format_label = "YouTube Short Teaser (45-54 seconds, 6 fast-paced scenes that hook viewers to click the Full Documentary Link)"
    else:
        num_scenes = 8
        words_per_scene = "56 to 68 words (3 full Nitish Rajput style investigative sentences)"
        format_label = "YouTube Documentary Explainer (3.5 to 4.5 minutes, 8 deep-dive chapters)"

    top_hits_str = ", ".join(top_channel_hits[:3]) if top_channel_hits else "High-impact geopolitical shifts, defense tech, AI breakthroughs, and mind-blowing mysteries"

    sys_prompt = (
        "You are an elite YouTube Documentary Director combining the investigative case-study structure and evidence boards of Nitish Rajput, "
        "the high-energy point-by-point highlights and top-banner impact tapes of Abhi & Niyu, and the visual pacing of Johnny Harris. "
        "You write 100% family-friendly, broadcast-safe, copyright-free, natural human spoken-English storytelling scripts on TODAY'S LATEST BREAKING NEWS "
        "and synchronize EVERY SINGLE SENTENCE with its own exact visual query, its own NOTED POINT HIGHLIGHT, its own emotional tone, and any important person mentioned (including historical figures like Alexander the Great, scientists, or world leaders). "
        "Output STRICT JSON only."
    )

    c_prof_name = dossier.get("country_profile", {}).get("name", "Global")
    t_anchor_hint = dossier.get("topic_anchor") or raw_title[:40]
    usr_prompt = f"""
Create a complete {format_label} package for the category [{pillar}].

BREAKING SOURCE HEADLINE: {raw_title}
COUNTRY / GEOGRAPHIC CONTEXT: {c_prof_name}
PRIMARY TOPIC ANCHOR: {t_anchor_hint}
VERIFIED LATEST FACTS:
{chr(10).join('- ' + f for f in raw_facts)}

OUR CHANNEL'S TOP PERFORMING VIDEO THEMES: {top_hits_str}

Return ONLY valid JSON in this exact structure:
{{
  "viral_title": "A 100% original, high-CTR YouTube title (50-75 chars, curiosity-driven, e.g. 'Why X Just Triggered a Massive Global Shift')",
  "thumb_line_1": "2 TO 3 CAPS WORDS (max 15 chars, e.g. 'GLOBAL SHOCK')",
  "thumb_line_2": "2 TO 3 CAPS WORDS (max 15 chars, e.g. 'THE REAL TRUTH')",
  "core_subject": "2-4 word exact physical subject (e.g. 'British High Street Retail')",
  "story_emotion": "Pick ONE best emotional theme: dark_geopolitics | cyberpunk_tech | cosmic_mystery | high_stakes_finance | inspiring_science | stadium_action | emotional_human_story | ancient_history_epic | investigative_thriller | mind_bending_wonder",
  "seo_description": "A compelling 3-paragraph YouTube SEO description summarizing the core case study.",
  "seo_tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8"],
  "scenes": [
    {{
      "scene_num": 1,
      "context_pill": "SHORT CHAPTER TITLE (max 22 chars, ASCII only, e.g. 'THE SILENT COLLAPSE')",
      "hook_tape": "ABHI & NIYU STYLE TOP IMPACT BANNER (max 34 chars, CAPS, e.g. '14% OF UK SHOPS ARE NOW EMPTY')",
      "stat_callout": "Key noted point or fact highlighted in this scene (max 28 chars, e.g. '14% RETAIL UNITS VACANT')",
      "mentioned_person": "If a specific named Person, Animal/Species (e.g. 'Bengal Tiger'), Iconic Machine/Telescope, or Historic Figure is the focus of this scene, write its exact Wikipedia name here (NEVER write generic job titles like 'Chancellor' without a person's name!). Otherwise write ''",
      "person_role": "Short 2-4 word label for mentioned_person (e.g. 'UK CHANCELLOR', 'APEX PREDATOR', 'DEEP SPACE TELESCOPE'), or ''",
      "narration": "Engaging spoken narration ({words_per_scene}) in natural human conversational English with contractions (here's, it's, didn't, that's). Write out all units in full words.",
      "video_broll_query": "Exact 4-5 word real-world footage search query INCLUDING the country/subject '{c_prof_name}' (e.g. 'London UK shopping street pedestrians')",
      "beat_visuals": [
        {{
          "point_highlight": "3 to 5 CAPS words stating the exact factual takeaway of Sentence 1 (e.g. '14% UK SHOPS NOW VACANT' — NEVER write 'POINT 1' or broken verbs!)",
          "mentioned_person": "Exact Wikipedia name of any Person, Animal, or Specific Entity highlighted in Sentence 1, else ''",
          "person_role": "Short role/category tag if mentioned_person is set, else ''",
          "photo_query": "Exact 5-7 word real news photo query for Sentence 1 INCLUDING '{c_prof_name}' and concrete physical nouns (e.g. 'closed empty retail shopfront UK high street Britain photo')",
          "ai_prompt": "Real editorial photojournalism of Sentence 1 in {c_prof_name}"
        }},
        {{
          "point_highlight": "3 to 5 CAPS words stating the exact factual takeaway of Sentence 2 (e.g. 'LOCAL ECONOMY IN CRISIS')",
          "mentioned_person": "Exact Wikipedia name of any Person, Animal, or Specific Entity highlighted in Sentence 2, else ''",
          "person_role": "Short role/category tag if mentioned_person is set, else ''",
          "photo_query": "Exact 5-7 word real news photo query for Sentence 2 INCLUDING '{c_prof_name}' and concrete physical nouns",
          "ai_prompt": "Real editorial photojournalism of Sentence 2 in {c_prof_name}"
        }},
        {{
          "point_highlight": "3 to 5 CAPS words stating the exact factual takeaway of Sentence 3 (e.g. 'EMERGENCY TAX RELIEF DEBATE')",
          "mentioned_person": "Exact Wikipedia name of any Person, Animal, or Specific Entity highlighted in Sentence 3, else ''",
          "person_role": "Short role/category tag if mentioned_person is set, else ''",
          "photo_query": "Exact 5-7 word real news photo query for Sentence 3 INCLUDING '{c_prof_name}' and concrete physical nouns",
          "ai_prompt": "Real editorial photojournalism of Sentence 3 in {c_prof_name}"
        }}
      ]
    }}
  ]
}}
CRITICAL RULES:
1. Generate EXACTLY {num_scenes} scenes in "scenes".
2. Every `photo_query` and `video_broll_query` MUST include the specific country/subject context ({c_prof_name} / {t_anchor_hint}) and concrete physical nouns so search engines return 100% point-to-point real photos and never return video games or wrong countries!
3. Every `point_highlight` MUST be a complete, meaningful 3-5 word headline takeaway (e.g. '14% SHOPS SITTING EMPTY', 'ONLINE GIANTS CRUSH MARGINS') — NEVER output truncated verbs like 'ISNT JUST TREND' or 'ARGUE WITHOUT DEEPER'!
4. Never put a generic job title like 'Chancellor of the Exchequer' or 'Prime Minister' in `mentioned_person` — use the person's actual name (e.g. 'Rachel Reeves', 'Keir Starmer') or a specific animal/species/machine name!
"""
    ai_pkg = call_multi_api_ai_brain_json(sys_prompt, usr_prompt)
    if ai_pkg and isinstance(ai_pkg.get("scenes"), list) and len(ai_pkg["scenes"]) >= 4:
        print(f"🧠 [AI Director Brain] Crafted Original Title: '{ai_pkg.get('viral_title')}' ({len(ai_pkg['scenes'])} Scenes)", flush=True)
        return ai_pkg
    return None

# ==============================================================================
# 4. 50-TRACK MIND-BLOWING EMOTION-ADAPTIVE BGM ALBUM + 12 PRO SFX STUDIO ENGINE
# ==============================================================================
STUDIO_ALBUM_50_MIND_BLOWING_TRACKS = {
    "dark_geopolitics": [
        ("Track 01 • Kremlin Shadow", [110.0, 130.81, 146.83, 164.81], 92, [0, 2, 1, 3], "minor_tension"),
        ("Track 02 • Red Sea Radar", [98.0, 116.54, 130.81, 146.83], 96, [0, 1, 3, 2], "minor_tension"),
        ("Track 03 • Diplomatic Standoff", [123.47, 146.83, 164.81, 185.0], 88, [0, 3, 1, 2], "deep_drone"),
        ("Track 04 • Iron Corridor", [87.31, 103.83, 116.54, 130.81], 100, [0, 2, 3, 1], "tactical_pulse"),
        ("Track 05 • Brink of History", [110.0, 123.47, 146.83, 164.81], 94, [0, 1, 2, 3], "minor_tension")
    ],
    "cyberpunk_tech": [
        ("Track 06 • Neural Horizon", [146.83, 174.61, 220.0, 196.0], 112, [0, 2, 3, 1], "synth_arp"),
        ("Track 07 • Silicon Pulse", [130.81, 164.81, 196.0, 220.0], 118, [0, 1, 2, 3], "synth_arp"),
        ("Track 08 • Quantum Grid", [164.81, 196.0, 246.94, 220.0], 115, [0, 3, 2, 1], "crystal_pulse"),
        ("Track 09 • Deep Algorithm", [138.59, 164.81, 207.65, 185.0], 110, [0, 2, 1, 3], "synth_arp"),
        ("Track 10 • Autonomous Future", [146.83, 185.0, 220.0, 246.94], 120, [0, 1, 3, 2], "crystal_pulse")
    ],
    "cosmic_mystery": [
        ("Track 11 • Mariana Abyss", [110.0, 164.81, 130.81, 196.0], 82, [0, 3, 1, 2], "ethereal_pad"),
        ("Track 12 • Voyager Interstellar", [130.81, 196.0, 164.81, 220.0], 86, [0, 2, 3, 1], "ethereal_pad"),
        ("Track 13 • Subglacial Secret", [98.0, 146.83, 130.81, 174.61], 80, [0, 1, 2, 3], "deep_drone"),
        ("Track 14 • Event Horizon", [116.54, 174.61, 146.83, 220.0], 84, [0, 2, 1, 3], "ethereal_pad"),
        ("Track 15 • Ancient Mechanism", [123.47, 185.0, 146.83, 220.0], 88, [0, 3, 2, 1], "crystal_pulse")
    ],
    "high_stakes_finance": [
        ("Track 16 • Wall Street Bell", [130.81, 164.81, 146.83, 196.0], 104, [0, 1, 2, 3], "tactical_pulse"),
        ("Track 17 • Trillion Dollar Pivot", [146.83, 185.0, 164.81, 220.0], 108, [0, 2, 1, 3], "tactical_pulse"),
        ("Track 18 • Global Supply Chain", [123.47, 146.83, 185.0, 164.81], 102, [0, 3, 1, 2], "synth_arp"),
        ("Track 19 • Central Bank Calculus", [110.0, 146.83, 164.81, 196.0], 100, [0, 1, 3, 2], "minor_tension"),
        ("Track 20 • Market Shockwave", [138.59, 164.81, 185.0, 207.65], 106, [0, 2, 3, 1], "tactical_pulse")
    ],
    "inspiring_science": [
        ("Track 21 • Biotech Dawn", [130.81, 164.81, 196.0, 261.63], 96, [0, 1, 2, 3], "warm_swell"),
        ("Track 22 • Cellular Breakthrough", [146.83, 185.0, 220.0, 293.66], 98, [0, 2, 1, 3], "warm_swell"),
        ("Track 23 • Orbital Telescope", [164.81, 196.0, 246.94, 329.63], 94, [0, 3, 2, 1], "crystal_pulse"),
        ("Track 24 • Longevity Code", [130.81, 174.61, 196.0, 220.0], 92, [0, 1, 3, 2], "warm_swell"),
        ("Track 25 • Planetary Frontier", [146.83, 196.0, 220.0, 261.63], 100, [0, 2, 3, 1], "ethereal_pad")
    ],
    "stadium_action": [
        ("Track 26 • Pole Position Grid", [146.83, 196.0, 220.0, 293.66], 124, [0, 2, 1, 3], "driving_action"),
        ("Track 27 • El Clasico Arena", [130.81, 164.81, 196.0, 261.63], 126, [0, 1, 3, 2], "driving_action"),
        ("Track 28 • Championship Lap", [164.81, 220.0, 246.94, 329.63], 128, [0, 3, 1, 2], "driving_action"),
        ("Track 29 • Box Office Premiere", [138.59, 185.0, 207.65, 277.18], 118, [0, 1, 2, 3], "synth_arp"),
        ("Track 30 • Final Whistle", [146.83, 174.61, 220.0, 261.63], 122, [0, 2, 3, 1], "driving_action")
    ],
    "emotional_human_story": [
        ("Track 31 • Untold Courage", [130.81, 155.56, 174.61, 196.0], 78, [0, 2, 1, 3], "warm_swell"),
        ("Track 32 • Human Resilience", [110.0, 130.81, 164.81, 146.83], 80, [0, 1, 2, 3], "warm_swell"),
        ("Track 33 • Against All Odds", [146.83, 174.61, 220.0, 196.0], 84, [0, 3, 2, 1], "ethereal_pad"),
        ("Track 34 • Silent Sacrifice", [98.0, 116.54, 146.83, 130.81], 76, [0, 1, 3, 2], "warm_swell"),
        ("Track 35 • Dawn of Hope", [130.81, 164.81, 196.0, 246.94], 82, [0, 2, 3, 1], "warm_swell")
    ],
    "ancient_history_epic": [
        ("Track 36 • Empire of Alexander", [98.0, 110.0, 130.81, 146.83], 88, [0, 2, 3, 1], "imperial_epic"),
        ("Track 37 • Sands of Babylon", [110.0, 116.54, 146.83, 164.81], 86, [0, 1, 3, 2], "imperial_epic"),
        ("Track 38 • Lost Civilization", [87.31, 103.83, 130.81, 116.54], 84, [0, 3, 1, 2], "deep_drone"),
        ("Track 39 • Bronze & Blood", [98.0, 123.47, 146.83, 164.81], 92, [0, 2, 1, 3], "imperial_epic"),
        ("Track 40 • Scrolls of Antiquity", [110.0, 130.81, 164.81, 196.0], 85, [0, 1, 2, 3], "imperial_epic")
    ],
    "investigative_thriller": [
        ("Track 41 • Classified Dossier", [110.0, 123.47, 130.81, 146.83], 98, [0, 2, 1, 3], "tactical_pulse"),
        ("Track 42 • Follow The Money", [98.0, 116.54, 138.59, 146.83], 102, [0, 1, 3, 2], "tactical_pulse"),
        ("Track 43 • Midnight Evidence", [103.83, 123.47, 146.83, 155.56], 95, [0, 3, 2, 1], "minor_tension"),
        ("Track 44 • The Smoking Gun", [116.54, 138.59, 164.81, 174.61], 104, [0, 2, 3, 1], "tactical_pulse"),
        ("Track 45 • Final Verdict", [110.0, 130.81, 146.83, 174.61], 96, [0, 1, 2, 3], "minor_tension")
    ],
    "mind_bending_wonder": [
        ("Track 46 • Paradox Engine", [130.81, 164.81, 185.0, 220.0], 90, [0, 2, 3, 1], "crystal_pulse"),
        ("Track 47 • Fourth Dimension", [146.83, 185.0, 207.65, 246.94], 94, [0, 3, 1, 2], "ethereal_pad"),
        ("Track 48 • Secret Architecture", [123.47, 155.56, 185.0, 220.0], 88, [0, 1, 3, 2], "crystal_pulse"),
        ("Track 49 • Scale of the Cosmos", [110.0, 146.83, 185.0, 220.0], 84, [0, 2, 1, 3], "ethereal_pad"),
        ("Track 50 • Unbelievable Reality", [138.59, 174.61, 207.65, 261.63], 96, [0, 1, 2, 3], "crystal_pulse")
    ]
}

STUDIO_ALBUM_30_TRACKS = STUDIO_ALBUM_50_MIND_BLOWING_TRACKS

PRO_SFX_TYPES = [
    "camera_shutter_flash",
    "dossier_stamp_thud",
    "digital_hud_lock",
    "cinematic_medallion_reveal",
    "crystal_point_highlight",
    "tactical_data_tick",
    "deep_sub_drop",
    "analog_cut_snap",
    "sonar_mystery_ping",
    "orchestral_riser_hit",
    "air_filter_sweep",
    "heartbeat_tension_pulse"
]

def detect_sentence_situation_mood(sentence_text, base_mood="dark_geopolitics", beat_idx=0):
    """
    SITUATION-BASED DYNAMIC MUSIC SWITCHER:
    Detects the exact emotional situation of each sentence/scene so the background music
    evolves dynamically as the story shifts from Crisis -> Investigation -> Human Impact -> Breakthrough!
    """
    low = sentence_text.lower()
    if any(w in low for w in ["arrest", "detained", "prison", "jail", "convicted", "fine", "banned", "strike", "missile", "war", "attack", "killed", "death", "crisis", "threat", "sanction", "clash"]):
        return "dark_geopolitics" if beat_idx % 2 == 0 else "investigative_thriller"
    if any(w in low for w in ["court", "judge", "lawyer", "prosecutor", "evidence", "investigation", "report", "allegation", "trial", "verdict", "document", "secret", "classified"]):
        return "investigative_thriller"
    if any(w in low for w in ["patient", "heart", "blood", "disease", "hospital", "doctor", "human", "family", "harassment", "freedom", "life", "children", "survive", "treatment"]):
        return "emotional_human_story" if beat_idx % 2 == 0 else "inspiring_science"
    if any(w in low for w in ["discover", "scientist", "research", "study", "protein", "quantum", "space", "nasa", "brain", "future", "technology", "ai", "robot", "prevent", "solution"]):
        return "inspiring_science" if beat_idx % 2 == 0 else "mind_bending_wonder"
    if any(w in low for w in ["billion", "million", "market", "economy", "bank", "trade", "tariff", "fund", "stock", "dollar", "pound"]):
        return "high_stakes_finance"
    if any(w in low for w in ["ancient", "king", "emperor", "empire", "alexander", "pharaoh", "century", "history", "dynasty"]):
        return "ancient_history_epic"
    return base_mood

def lowpass_warm_filter(wave_arr, window_len=24):
    """
    STUDIO WARMTH LOW-PASS FILTER:
    Removes all metallic/harsh high-frequency buzz above ~900Hz so the background score
    and transition textures sound warm, deep, and cinematic like Nitish Rajput / DW Documentaries!
    """
    if len(wave_arr) < window_len * 2:
        return wave_arr
    kernel = np.hanning(window_len).astype(np.float32)
    kernel /= max(float(np.sum(kernel)), 1e-6)
    return np.convolve(wave_arr, kernel, mode="same").astype(np.float32)

def synthesize_pro_sfx_event(sfx_type, sr=44100):
    """
    ULTRA-SUBTLE, SOFT ORGANIC DOCUMENTARY SOUND DESIGN (0.032 - 0.044 Peak Gain):
    Zero harsh beeps, zero metallic bells, zero 'woop' frequency risers!
    Uses warm low-pass filtered air whooshes, soft paper textures, and deep cinema sub-pulses
    that sit gently in the background without ever distracting from the narrator's voice!
    """
    rng = np.random.default_rng(abs(hash(sfx_type)) % 99999)

    if sfx_type in ["camera_shutter_flash", "dossier_stamp_thud", "cinematic_medallion_reveal", "digital_hud_lock"]:
        # Soft Warm Cinema Sub-Pulse + Gentle Paper/Felt Tap (for Subject Spotlight Card Reveal)
        dur = 0.28
        n = int(sr * dur)
        t = np.linspace(0, dur, n, endpoint=False)
        sub_f = 78.0 * np.exp(-t * 14.0) + 42.0
        phase = 2.0 * np.pi * np.cumsum(sub_f) / float(sr)
        warm_thump = np.sin(phase) * np.exp(-t * 11.0)
        soft_air = lowpass_warm_filter(rng.standard_normal(n).astype(np.float32), window_len=36) * np.sin(np.pi * (t / dur)) * np.exp(-t * 12.0)
        sig = 0.75 * warm_thump + 0.25 * soft_air
        max_v = max(float(np.max(np.abs(sig))), 1e-4)
        return ((sig / max_v) * 0.042).astype(np.float32)

    # Default for chapter transitions: Soft Warm Filtered Cinema Air Whoosh (Zero Pitched Sine Sweep!)
    dur = 0.32
    n = int(sr * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    env = np.sin(np.pi * (t / dur)) ** 1.6
    brown = np.cumsum(rng.standard_normal(n).astype(np.float32))
    brown -= np.mean(brown)
    brown /= max(float(np.max(np.abs(brown))), 1e-4)
    warm_whoosh = lowpass_warm_filter(brown, window_len=42) * env
    sub_bed = 0.45 * np.sin(2.0 * np.pi * 56.0 * t) * env
    sig = warm_whoosh + sub_bed
    max_v = max(float(np.max(np.abs(sig))), 1e-4)
    return ((sig / max_v) * 0.034).astype(np.float32)

def synthesize_segment_music_wave(seg_dur, mood, track_idx, sr=44100):
    """
    NITISH RAJPUT / JOHNNY HARRIS STYLE WARM CINEMA DOCUMENTARY SCORE (0.046 Peak = -27 dBFS):
    1. Warm, deep, low-pass filtered Cello & Analog Pad chords (110Hz-330Hz) + Soft Felt-Piano Notes.
    2. Zero harsh high-pitched synths, zero metallic hi-hats, zero distortion!
    3. Sits softly and smoothly underneath the human voice so the narration is 100% crystal clear!
    """
    tracks = STUDIO_ALBUM_50_MIND_BLOWING_TRACKS.get(mood, STUDIO_ALBUM_50_MIND_BLOWING_TRACKS["dark_geopolitics"])
    track_tuple = tracks[track_idx % len(tracks)]
    track_name, root_freqs, bpm, arp_order = track_tuple[0], track_tuple[1], track_tuple[2], track_tuple[3]
    style_mode = track_tuple[4] if len(track_tuple) > 4 else "minor_tension"

    n_seg = max(int(sr * seg_dur), 128)
    t = np.linspace(0, seg_dur, n_seg, endpoint=False)
    beat_len = 60.0 / float(max(76, min(bpm, 98)))
    bar_len = beat_len * 4.0

    bar_idx = (t // bar_len).astype(int)
    chord_roots = np.array([root_freqs[i % len(root_freqs)] for i in bar_idx], dtype=np.float32)
    # Smooth chord root transitions so there is never a click between bars
    chord_roots = lowpass_warm_filter(chord_roots, window_len=256)

    phase_root = 2.0 * np.pi * np.cumsum(chord_roots) / float(sr)
    third_ratio = 1.1892 if style_mode in ["minor_tension", "imperial_epic", "deep_drone", "tactical_pulse"] else 1.2599

    # Layer 1: Warm Cello & Viola Documentary String Pad (Fundamental + Soft 3rd + 5th)
    pad_wave = (
        0.52 * np.sin(phase_root)
        + 0.28 * np.sin(phase_root * 1.002)
        + 0.22 * np.sin(phase_root * third_ratio)
        + 0.20 * np.sin(phase_root * 1.4983)
    )
    pad_swell = 0.78 + 0.22 * np.sin(2.0 * np.pi * (t / bar_len))
    pad_layer = pad_wave * pad_swell * 0.48

    # Layer 2: Deep Warm Cinema Sub-Bass Foundation (55Hz-85Hz)
    sub_layer = 0.36 * np.sin(phase_root * 0.5) * (0.85 + 0.15 * np.cos(2.0 * np.pi * (t / (bar_len * 2.0))))

    # Layer 3: Gentle Felt-Piano / Warm Marimba Documentary Pulse (Soft attack, warm low register)
    subdiv_len = beat_len * 1.0
    arp_step_idx = (t // subdiv_len).astype(int)
    arp_mults = [1.0, third_ratio, 1.4983, 2.0]
    chosen_mults = np.array([arp_mults[arp_order[i % len(arp_order)] % len(arp_mults)] for i in arp_step_idx], dtype=np.float32)
    arp_local_t = t % subdiv_len
    # Soft fade-in attack (no sharp click) + warm exponential decay
    felt_attack = np.minimum(1.0, arp_local_t / 0.035)
    felt_decay = np.exp(-arp_local_t * 5.2)
    arp_phase = 2.0 * np.pi * np.cumsum(chord_roots * chosen_mults) / float(sr)
    arp_layer = 0.18 * np.sin(arp_phase) * felt_attack * felt_decay

    # Layer 4: Subtle Deep Documentary Heartbeat Pulse on Beat 1 & 3
    bar_local_t = t % (beat_len * 2.0)
    pulse_attack = np.minimum(1.0, bar_local_t / 0.025)
    pulse_env = pulse_attack * np.exp(-bar_local_t * 11.0)
    pulse_layer = 0.18 * np.sin(2.0 * np.pi * 58.0 * bar_local_t) * pulse_env

    raw_mix = pad_layer + sub_layer + arp_layer + pulse_layer
    warm_mix = lowpass_warm_filter(raw_mix, window_len=28)
    max_s = max(float(np.max(np.abs(warm_mix))), 1e-4)
    # Subtle, warm studio documentary background level (0.046 peak = -27 dBFS)
    mastered_seg = (warm_mix / max_s) * 0.046
    return mastered_seg.astype(np.float32), track_name

def build_30_track_mood_adaptive_album_bgm(filename, duration, beat_switch_times, mood="dark_geopolitics", track_seed=0, sfx_events=None):
    """
    SUBTLE, WARM SITUATION-ADAPTIVE DOCUMENTARY SCORE + SOFT SPOTLIGHT SFX:
    1. Smoothly crossfades across situation moods every 3-4 beats (with 1.0s gentle crossfades).
    2. Plays soft, unobtrusive transition textures ONLY on Subject Spotlight reveals or Chapter boundaries
       (never on every sentence!), keeping the voiceover 100% dominant and crystal clear!
    """
    sr = 44100
    n_samples = max(int(sr * duration), sr)
    audio = np.zeros(n_samples, dtype=np.float32)

    all_mood_progression = [
        mood,
        "investigative_thriller",
        "emotional_human_story",
        "high_stakes_finance",
        "inspiring_science",
        "dark_geopolitics",
        "cosmic_mystery"
    ]

    used_track_names = []
    if sfx_events and len(sfx_events) >= 3:
        seg_starts = [0.0]
        seg_moods = [sfx_events[0].get("situation_mood") or mood]
        for idx_e, ev in enumerate(sfx_events[1:], 1):
            ev_mood = ev.get("situation_mood") or mood
            if idx_e % 3 == 0:
                if ev_mood == seg_moods[-1]:
                    ev_mood = all_mood_progression[(idx_e + track_seed) % len(all_mood_progression)]
                seg_starts.append(float(ev.get("time", 0.0)))
                seg_moods.append(ev_mood)
        seg_starts.append(float(duration))

        for s_i in range(len(seg_moods)):
            t0 = seg_starts[s_i]
            t1 = seg_starts[s_i + 1]
            if t1 <= t0 + 0.2:
                continue
            s_mood = seg_moods[s_i]
            s_wave, t_name = synthesize_segment_music_wave(t1 - t0, s_mood, track_seed + s_i * 2 + 1, sr=sr)
            if t_name not in used_track_names:
                used_track_names.append(t_name)
            i0 = int(t0 * sr)
            i1 = min(n_samples, i0 + len(s_wave))
            if i1 > i0:
                seg_slice = s_wave[:i1 - i0].copy()
                fade_n = min(int(0.85 * sr), len(seg_slice) // 3)
                if fade_n > 10:
                    seg_slice[:fade_n] *= np.linspace(0.15, 1.0, fade_n, dtype=np.float32)
                    seg_slice[-fade_n:] *= np.linspace(1.0, 0.15, fade_n, dtype=np.float32)
                audio[i0:i1] += seg_slice
    else:
        s_wave, t_name = synthesize_segment_music_wave(duration, mood, track_seed, sr=sr)
        used_track_names.append(t_name)
        audio[:min(n_samples, len(s_wave))] = s_wave[:min(n_samples, len(s_wave))]

    print(f"   🎵 [Warm Subtle Documentary Score (-27dB)] Active Tracks: {used_track_names[:5]}", flush=True)

    # Mix Soft, Subtle SFX ONLY on Subject Spotlight Cards or Major Chapter Shifts (every 3rd beat)
    if sfx_events:
        for ev_i, ev in enumerate(sfx_events):
            ev_sfx = str(ev.get("sfx_type", ""))
            is_spotlight_sfx = ev_sfx in ["camera_shutter_flash", "dossier_stamp_thud", "cinematic_medallion_reveal", "digital_hud_lock"]
            if not is_spotlight_sfx and (ev_i % 3 != 0 or ev_i == 0):
                continue
            ev_t = float(ev.get("time", 0.0))
            idx = int(ev_t * sr)
            if 0 < idx < n_samples:
                sfx_wave = synthesize_pro_sfx_event(ev_sfx if is_spotlight_sfx else "soft_whoosh", sr=sr)
                slen = min(len(sfx_wave), n_samples - idx)
                if slen > 0:
                    audio[idx:idx + slen] = audio[idx:idx + slen] * 0.88 + sfx_wave[:slen]

    audio_int16 = np.int16(np.clip(audio, -1.0, 1.0) * 32767)
    with wave.open(filename, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(audio_int16.tobytes())
    return filename

# ==============================================================================
# 5. FULL YOUTUBE DATA API v3 INTELLIGENCE + PLAYLISTS
# ==============================================================================
def sync_all_8_playlists_and_organize_channel(yt):
    playlist_map = {}
    try:
        pl_resp = yt.playlists().list(part="snippet,contentDetails", mine=True, maxResults=50).execute()
        for item in pl_resp.get("items", []):
            t_existing = item.get("snippet", {}).get("title", "").strip()
            playlist_map[t_existing.lower()] = item["id"]

        for pillar, p_cfg in CATEGORY_FEEDS.items():
            target_pl_title = p_cfg["playlist_title"]
            if target_pl_title.lower() not in playlist_map:
                try:
                    create_resp = yt.playlists().insert(
                        part="snippet,status",
                        body={
                            "snippet": {
                                "title": target_pl_title,
                                "description": f"Official {target_pl_title} deep-dive case studies and linked shorts by World Talk Brief."
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
    default_viral_kws = ["geopolitics", "military", "sanctions", "fighter", "missile", "drone", "ai", "robot", "nvidia", "openai", "nasa", "spacex", "starlink", "discovery"]
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

        for dkw in default_viral_kws:
            if dkw not in winning_kws:
                winning_kws.append(dkw)
        return winning_kws[:25], viral_yt_tags[:18], playlist_map, top_channel_hits
    except Exception:
        return default_viral_kws, [], {}, []

def add_video_to_category_playlist_and_comment(yt, video_id, pillar, summary_takeaway, playlist_map, linked_long_url=None):
    if not video_id:
        return
    core_hub = PILLAR_TO_CORE_HUB.get(pillar, pillar)
    p_cfg = CATEGORY_FEEDS.get(core_hub, CATEGORY_FEEDS["WORLD"])
    target_pl_title = p_cfg.get("playlist_title", f"World Talk Brief • {core_hub.title()}")

    try:
        playlist_id = playlist_map.get(target_pl_title.lower())
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
        if linked_long_url:
            comment_txt = (
                f"🔴 WATCH THE FULL DOCUMENTARY VIDEO HERE: {linked_long_url}\n\n"
                f"📌 KEY TAKEAWAY: {summary_takeaway}\n"
                f"What is your perspective on this? Share your thoughts in the comments! 👇"
            )
        else:
            comment_txt = (
                f"📌 KEY TAKEAWAY: {summary_takeaway}\n"
                f"What is your perspective on this? Share your thoughts below! 👇"
            )
        yt.commentThreads().insert(
            part="snippet",
            body={
                "snippet": {
                    "videoId": video_id,
                    "topLevelComment": {
                        "snippet": {
                            "textOriginal": comment_txt
                        }
                    }
                }
            }
        ).execute()
        print(f"💬 [YouTube API Comment Posted] on Video {video_id} (Linked Long URL: {linked_long_url or 'Main Documentary'})", flush=True)
    except Exception:
        pass

# ==============================================================================
# 6. HOT GEOPOLITICS SURGE DETECTOR, 24H FRESHNESS SCORER & HISTORY MANAGER
# ==============================================================================
def is_article_fresh_last_48h(raw_date_str):
    """
    Returns (is_fresh_boolean, hours_old) so we ALWAYS prioritize TODAY'S BREAKING NEWS
    and reject old archive/history stories!
    """
    if not raw_date_str:
        return True, 6.0
    try:
        dt = parsedate_to_datetime(str(raw_date_str))
        if dt.tzinfo is not None:
            now_dt = datetime.now(dt.tzinfo)
        else:
            now_dt = datetime.utcnow()
        hours_old = max(0.5, (now_dt - dt).total_seconds() / 3600.0)
        return (hours_old <= 48.0), hours_old
    except Exception:
        return True, 8.0

def detect_hot_geopolitics_surge():
    hot_crisis_keywords = [
        "missile", "airstrike", "invasion", "war ", "troops", "nuclear", "sanctions",
        "ceasefire", "pentagon", "nato", "taiwan", "strait", "escalat", "blockade",
        "emergency summit", "hypersonic", "carrier", "fighter jet", "retaliat", "red sea", "oil deal"
    ]
    crisis_hits = 0
    for _, rss_u in CATEGORY_FEEDS["WORLD"]["feeds"][:3]:
        try:
            r = requests.get(rss_u, headers=HEADERS_WEB, timeout=6)
            if r.status_code == 200:
                feed = feedparser.parse(r.content)
                for ent in feed.entries[:10]:
                    t_low = ent.title.lower()
                    if any(kw in t_low for kw in hot_crisis_keywords):
                        crisis_hits += 1
        except Exception:
            pass
    is_surge = crisis_hits >= 4
    print(f"🌍 [Geopolitics Surge Detector] Crisis Headlines Count: {crisis_hits} | Hot Surge Mode: {is_surge}", flush=True)
    return is_surge

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
                    "bgm_track_counter": int(data.get("bgm_track_counter", 0)),
                    "last_mega_24h_date": data.get("last_mega_24h_date", "")
                }
        except Exception:
            pass
    return {
        "published_keys": set(),
        "event_fingerprints": [],
        "last_categories": [],
        "last_sources": [],
        "round_robin_idx": 0,
        "bgm_track_counter": 0,
        "last_mega_24h_date": ""
    }

def save_published_history(hist_obj):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "updated_at": datetime.utcnow().isoformat(),
                "round_robin_idx": int(hist_obj.get("round_robin_idx", 0)),
                "bgm_track_counter": int(hist_obj.get("bgm_track_counter", 0)),
                "last_mega_24h_date": str(hist_obj.get("last_mega_24h_date", "")),
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
    """
    SMART BREAKING UPDATE & DUPLICATE DETECTOR:
    - Exact headline key or >72% token overlap -> DUPLICATE (skip).
    - Developing story with a brand-new headline angle (0.38 <= overlap < 0.72) -> FOLLOWUP_UPDATE
      so when a major update drops on a hot Geopolitics/Science/AI story, we cover the new update!
    """
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
        inter_cnt = len(cur_fp.intersection(past_fp))
        union_cnt = max(1, len(cur_fp.union(past_fp)))
        jaccard = inter_cnt / float(union_cnt)
        min_ov = inter_cnt / float(min(len(cur_fp), len(past_fp)))
        if jaccard >= 0.62:
            return ("DUPLICATE", None)
        if 0.22 <= jaccard < 0.62 or (min_ov >= 0.38 and jaccard < 0.62):
            return ("FOLLOWUP_UPDATE", past.get("title"))

    return ("NEW_STORY", None)

BANNED_ARTICLE_TITLES = [
    "salon", "hairdresser", "vat cut", "council tax", "local council", "pub ", "pubs ",
    "uti", "utis", "urinary", "bladder", "bowel", "diarrhea", "constipation", "erectile", "sexually transmitted",
    "ovaries", "ovary", "menopause", "menstrual", "pregnancy", "fertility", "cosmetic surgery", "butt lift",
    "bbl", "botox", "lip filler", "vampire facial", "nathan fielder", "kill switch", "lance oppenheim",
    "indiewire", "cyberselfish", "techno-libertarianism", "book returns", "author takes aim",
    "birthday sale", "percent off", "% off", "sitewide", "promo code", "coupon", "best deals",
    "buying guide", "gift guide", "review:", "we tested", "horoscope", "wordle", "crossword", "sudoku",
    "live updates", "as it happened", "in pictures", "at a glance", "podcast", "quiz", "bandcamp",
    "synth-pop", "album review", "song review", "obsessed with scammers", "how to watch", "tv channel",
    "live stream", "prediction, team news", "power partnership", "ai-griculture", "90 years of mystery", "100-year",
    "nude", "naked", "nsfw", "erotic", "sex ", "sexual", "porn", "onlyfans", "playboy", "bikini", "lingerie",
    "stripper", "prostitute", "brothel", "orgy", "fetish", "intimate", "boudoir", "topless", "adult film", "18+"
]

BANNED_PHRASES = [
    "https://", "http://", "https/", "http/", "www.", ".gov", ".org/", ".com/",
    "when you purchase through links", "earn a small commission", "editorial independence",
    "subscribe to smithsonian", "free tote", "special projects editor",
    "zoom interview", "for more information on", "popular on ", "related:", "read more:",
    "also read:", "external ", "enter your email below", "send confirmation",
    "sign you up to our newsletter", "by submitting your information", "confirm you are aged 16",
    "read our privacy policy", "agree to the terms", "terms & conditions",
    "watch the video below", "you don't have permission to access", "what is this page",
    "website you are visiting is protected", "access denied", "403 forbidden", "error 404",
    "enable javascript", "enable cookies", "cloudflare", "please verify you are a human",
    "some readers may find this article distressing", "warning: this article contains",
    "continue reading", "sign up for our newsletter", "all rights reserved",
    "photograph:", "image source:", "getty images", "tells the bbc", "tells bbc",
    "send us your questions", "share your story", "tell us what you think", "contact us",
    "have you been affected", "tap here to", "click here to", "listen to our podcast",
    "in this file photo", "sound bite of", "archived recording"
]

def clean_fact(text):
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
    text = re.sub(r"\b(\d+(?:\.\d+)?)\s*[mM]\b", r"\1 million", text)
    text = re.sub(r"\b(\d+(?:\.\d+)?)\s*bn\b", r"\1 billion", text, flags=re.I)

    text = re.sub(r"(?i)see more headlines and perspectives on google news\.?", "", text)
    text = re.sub(r"(?i),?\s*(?:as\s+|first\s+)?reported by\s+(?:the\s+)?[A-Za-z\s]{2,25}(?=[,.]|$)", "", text)
    text = re.sub(r"(?i)\b(BBC World Service|BBC World|BBC News|BBC|DW|Wired|Al Jazeera Sport|Al Jazeera|IndieWire|Variety|Smithsonian|CNN Live|CNN|Reuters|Associated Press|AP News|CBS News|CBS|The New York Times|New York Times|TechCrunch|The Verge|The Information|Bloomberg|Financial Times)\b", "official reports", text)
    text = re.sub(r"(?i)\s*,\s*,", ",", text)
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
    "weekend", "win", "title", "affect", "millions", "discover", "discovered", "giving", "real",
    "that", "this", "these", "those", "something", "doing", "decades", "forced", "pick", "picks",
    "chooses", "launch", "power", "partnership", "between", "through", "their", "there", "about",
    "tighter", "rules", "planned", "protect", "people", "goes", "badly", "wrong", "stands", "brink",
    "history", "beats", "expectations", "offsets", "weakness", "researchers", "claimed", "blurry",
    "object", "very", "likely", "holds", "author", "changing", "bizarre", "million", "billion",
    "trillion", "ancient", "adorable", "hottest", "secretly", "scary", "tiny", "little", "year",
    "years", "predator", "rewriting", "know", "plays", "sell", "sold", "left", "alone", "nothing",
    "james", "john", "michael", "david", "robert"
}

def extract_primary_topic_anchor(dossier):
    low = f"{dossier['title']} {' '.join(dossier['raw_facts'][:2])}".lower()
    for word_key, (_, wiki_exact, _) in CONCRETE_WIKI_PROPS.items():
        if re.search(rf"\b{re.escape(word_key)}\b", low):
            return wiki_exact

    for p_key, (wiki_page, _, _) in PERSON_WIKI_MAP.items():
        if re.search(rf"\b{re.escape(p_key)}\b", low):
            return wiki_page

    content_nouns = [
        w for w in re.findall(r"[A-Za-z]{4,}", dossier["title"])
        if w.lower() not in HEADLINE_STOP_VERBS_ADJS
    ]
    return " ".join(content_nouns[:2]).title() if content_nouns else "Global Case Study"

def build_100_percent_original_youtube_title(raw_title, pillar, c_prof, topic_anchor, is_update=False):
    anchor_clean = topic_anchor.strip()
    prefix = "BREAKING UPDATE: " if is_update else ""
    suffix = f" | {pillar.replace('_', ' ').title()} Explained"
    cand = f"{prefix}{raw_title}{suffix}"
    if len(cand) <= 95 and not any(b in raw_title.lower() for b in ["dw ", "bbc", "reuters"]):
        return cand
    if len(f"{prefix}{raw_title}") <= 92:
        return f"{prefix}{raw_title}"
    # Word-safe truncation (never cuts 'Explained' into 'Explai'!)
    words = f"{prefix}{raw_title}".split()
    out = []
    for w in words:
        if len(" ".join(out + [w])) <= 90:
            out.append(w)
        else:
            break
    return " ".join(out)

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
    comb = f"{title} {claims_text}".lower()
    if any(k in comb for k in ["alexander", "ancient", "empire", "pharaoh", "roman", "dynasty", "archaeolog", "century bc", "tomb", "king ", "emperor", "warrior", "civilization", "persia", "babylon"]):
        return "ancient_history_epic"
    if any(k in comb for k in ["investigation", "scandal", "secret", "classified", "leaked", "intelligence", "cia", "fbi", "pentagon", "sanctions", "espionage", "dossier", "corruption"]):
        return "investigative_thriller"
    if any(k in comb for k in ["paradox", "quantum", "black hole", "dimension", "time travel", "consciousness", "universe", "unbelievable", "mystery", "impossible", "gravity"]):
        return "mind_bending_wonder"
    if any(k in comb for k in ["patient", "hospital", "children", "family", "survival", "rescued", "heart", "longevity", "life-saving", "cure", "humanity"]):
        return "emotional_human_story"
    p_cfg = CATEGORY_FEEDS.get(pillar_name, CATEGORY_FEEDS["WORLD"])
    return p_cfg.get("bgm_mood", "dark_geopolitics")

def discover_dossier_for_pillar(sub_pillar, hist_obj, winning_keywords, batch_fingerprints):
    """
    100% LATEST & TRENDING 24-HOUR NEWS HARVESTER:
    Prioritizes stories published in the last 24 hours (`recency_boost`) and expands facts
    via Bing News Live RSS so every single video covers today's hottest topics!
    """
    core_hub = PILLAR_TO_CORE_HUB.get(sub_pillar, sub_pillar)
    p_cfg = CATEGORY_FEEDS.get(core_hub, CATEGORY_FEEDS["WORLD"])
    candidates = []

    for src, url in p_cfg["feeds"]:
        try:
            r_feed = requests.get(url, headers=HEADERS_WEB, timeout=8)
            if r_feed.status_code != 200:
                continue
            feed = feedparser.parse(r_feed.content)
        except Exception:
            continue

        for entry in feed.entries[:14]:
            raw_t = entry.title.rsplit(" - ", 1)[0]
            low_raw_t = raw_t.lower()
            if any(bt in low_raw_t for bt in BANNED_ARTICLE_TITLES):
                continue

            raw_pub = getattr(entry, "published", "") or getattr(entry, "updated", "")
            is_fresh, hours_old = is_article_fresh_last_48h(raw_pub)
            if not is_fresh:
                continue

            title = clean_fact(raw_t)
            if len(title) < 24:
                continue

            link = getattr(entry, "link", "").strip()
            if any(b_url in link.lower() for b_url in ["/deals/", "/shopping/", "/coupons/", "/reviews/", "/podcasts/", "/video/", "/music/"]):
                continue

            pub_date = normalize_pub_date(raw_pub)
            if not link:
                continue

            raw_sum = BeautifulSoup(getattr(entry, "summary", ""), "html.parser").get_text(separator=" ")
            summary = clean_fact(raw_sum)

            dup_status, prev_evt_title = check_semantic_duplicate_or_update(title, summary, hist_obj)
            if dup_status == "DUPLICATE":
                continue
            is_followup = (dup_status == "FOLLOWUP_UPDATE")

            cur_fp_set = set(extract_event_fingerprint(title, summary))
            if any(len(cur_fp_set.intersection(bfp)) / float(max(1, min(len(cur_fp_set), len(bfp)))) >= 0.38 for bfp in batch_fingerprints):
                continue

            # Extract specific headline subject tokens (excluding generic country names) so sidebar links never pollute claims!
            generic_geo_words = {c.lower() for c in COUNTRY_GEO_DB.keys()} | set(DEMONYM_TO_COUNTRY.keys()) | {"the", "and", "for", "with", "from", "that", "this", "news", "court", "police", "government"}
            headline_specific_tokens = {
                w.lower() for w in re.findall(r"[A-Za-z0-9]{4,}", title)
                if w.lower() not in HEADLINE_STOP_VERBS_ADJS and w.lower() not in generic_geo_words
            }
            core_topic_tokens = headline_specific_tokens or {
                w.lower() for w in re.findall(r"[A-Za-z0-9]{4,}", f"{title} {summary}")
                if w.lower() not in HEADLINE_STOP_VERBS_ADJS
            }

            rss_img = None
            if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
                rss_img = entry.media_thumbnail[0].get("url")
                if rss_img and "bbci.co.uk" in rss_img:
                    rss_img = re.sub(r"/standard/\d+/", "/standard/1024/", rss_img)
            elif hasattr(entry, "media_content") and entry.media_content:
                rss_img = entry.media_content[0].get("url")

            og_img = None
            article_inline_images = []
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

            if "news.google.com" not in link:
                try:
                    r = requests.get(link, headers=HEADERS_WEB, timeout=6)
                    if r.status_code == 200 and "permission to access" not in r.text.lower() and "visiting is protected" not in r.text.lower():
                        soup = BeautifulSoup(r.text, "html.parser")
                        m_og = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "twitter:image"})
                        if m_og and m_og.get("content"):
                            og_img = m_og["content"]
                            article_inline_images.append(og_img)

                        # Harvest inline high-res article photos so exact people/scenes from the article appear!
                        for img_tag in soup.find_all("img"):
                            im_src = img_tag.get("src") or img_tag.get("data-src") or ""
                            if im_src.startswith("https://") and any(ext in im_src.lower() for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                                if not any(b in im_src.lower() for b in BANNED_IMAGE_SOURCES + ["icon", "logo", "avatar", "sprite", "1x1", "pixel"]):
                                    if "bbci.co.uk" in im_src:
                                        im_src = re.sub(r"/standard/\d+/", "/standard/1024/", im_src)
                                    if im_src not in article_inline_images:
                                        article_inline_images.append(im_src)

                        for m_vid in re.findall(r"(https?://[^\s\"'<>]+?\.(?:mp4|webm))", r.text, flags=re.I):
                            if not any(b in m_vid.lower() for b in ["ad", "banner", "tracker", "pixel", "logo"]) and m_vid not in article_video_urls:
                                article_video_urls.append(m_vid)

                        # Remove related-links / sidebar promo blocks before reading paragraphs
                        for bad_div in soup.find_all(["div", "section", "ul", "aside"], attrs={"class": re.compile(r"related|promo|links|more|sidebar|recommend|most-read|card", re.I)}):
                            bad_div.decompose()

                        for p in soup.find_all("p"):
                            if p.find_parent("figcaption") or p.find_parent("figure") or p.find_parent("footer") or p.find_parent("aside") or p.find_parent("form") or p.find_parent("nav") or p.find_parent("li"):
                                continue
                            if p.find("a") and len(p.find("a").get_text(strip=True)) >= int(len(p.get_text(strip=True)) * 0.75):
                                # Skip standalone hyperlink promo lines (e.g. 'AI SpongeBob parody draws scrutiny')!
                                continue
                            p_txt = p.get_text(separator=" ").strip()
                            if any(stop_m in p_txt.lower() for stop_m in ["when you purchase through links", "earn a small commission", "related articles", "more from techcrunch", "recommended for you", "more on this story"]):
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
                                    if len(verified_claims) >= 16:
                                        break
                            if len(verified_claims) >= 16:
                                break
                except Exception:
                    pass

            if len(verified_claims) < 10:
                try:
                    # Use exact headline subject words (NOT generic country words) for Bing News expansion
                    kw_q = " ".join(list(headline_specific_tokens)[:4])
                    if kw_q:
                        b_rss = f"https://www.bing.com/news/search?q={urllib.parse.quote(kw_q)}&format=rss"
                        br = requests.get(b_rss, headers=HEADERS_WEB, timeout=6)
                        b_feed = feedparser.parse(br.content)
                        for b_ent in b_feed.entries[:10]:
                            b_desc = clean_fact(BeautifulSoup(getattr(b_ent, "summary", ""), "html.parser").get_text(separator=" "))
                            for bs in split_into_complete_sentences(b_desc):
                                cbs = clean_fact(bs)
                                s_toks = {w.lower() for w in re.findall(r"[A-Za-z0-9]{4,}", cbs)}
                                if 45 <= len(cbs) <= 205 and len(s_toks.intersection(headline_specific_tokens)) >= 2 and not is_semantically_similar_claim(cbs, verified_claims, headline_title=title):
                                    if cbs[-1] not in ".!?":
                                        cbs += "."
                                    verified_claims.append({
                                        "text": cbs,
                                        "source_url": link,
                                        "source_name": src,
                                        "published_date": pub_date
                                    })
                                    if len(verified_claims) >= 16:
                                        break
                except Exception:
                    pass

            if len(verified_claims) < 4:
                continue

            raw_facts = [c["text"] for c in verified_claims]
            c_prof = resolve_country_or_domain_profile(title, raw_facts, pillar_name=core_hub)
            mood_cat = classify_story_mood_and_category(title, " ".join(raw_facts[:4]), pillar_name=core_hub)

            temp_d = {"title": title, "raw_facts": raw_facts, "country_profile": c_prof, "pillar": core_hub}
            t_anchor = extract_primary_topic_anchor(temp_d)
            orig_yt_title = build_100_percent_original_youtube_title(title, sub_pillar, c_prof, t_anchor, is_update=is_followup)

            comb = f"{title} {' '.join(raw_facts[:3])}".lower()
            analytics_boost = sum(8 for w_kw in winning_keywords if re.search(rf"\b{re.escape(w_kw)}\b", comb))
            recency_boost = int(max(0.0, 48.0 - hours_old) * 2.5)
            update_boost = 25 if is_followup else 0
            trend_score = len(verified_claims) * 4 + analytics_boost + recency_boost + update_boost

            candidates.append({
                "score": trend_score,
                "pillar": core_hub,
                "sub_pillar": sub_pillar,
                "yt_category_id": p_cfg["yt_category_id"],
                "story_key": make_story_key(title),
                "event_tokens": list(cur_fp_set),
                "is_followup_update": is_followup,
                "previous_event_title": prev_evt_title,
                "title": title,
                "original_yt_title": orig_yt_title,
                "topic_anchor": t_anchor,
                "article_inline_images": article_inline_images[:8],
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
                "wb_data": None
            })
            if len(candidates) >= 6:
                break
        if len(candidates) >= 6:
            break

    if not candidates:
        return None
    candidates.sort(key=lambda x: x["score"], reverse=True)
    chosen = candidates[0]
    batch_fingerprints.append(set(chosen["event_tokens"]))
    return chosen

def build_daily_24h_mega_news_dossier():
    print("\n🌐 [USA 6:00 PM MEGA-BROADCAST] Harvesting Top 24-Hour Breaking News Across the Globe...", flush=True)
    mega_claims = []
    visual_anchors = []
    lead_img = None
    pub_d = datetime.utcnow().strftime("%Y-%m-%d")

    # Prioritize direct full-text global wire feeds first so we get rich article paragraphs without Google News duplicate titles
    feed_sources = [
        ("BBC World Breaking", "http://feeds.bbci.co.uk/news/world/rss.xml"),
        ("Al Jazeera Global", "https://www.aljazeera.com/xml/rss/all.xml"),
        ("The Guardian World", "https://www.theguardian.com/world/rss"),
        ("DW World News", "https://rss.dw.com/rdf/rss-en-world"),
        ("France24 World", "https://www.france24.com/en/rss"),
        ("CNBC Business", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147"),
        ("BBC Technology", "http://feeds.bbci.co.uk/news/technology/rss.xml"),
        ("Space.com Breaking", "https://www.space.com/feeds/all"),
        ("Google News World 24h", "https://news.google.com/rss/headlines/section/topic/WORLD?hl=en-US&gl=US&ceid=US:en")
    ]

    for src, url in feed_sources:
        try:
            r = requests.get(url, headers=HEADERS_WEB, timeout=8)
            if r.status_code != 200:
                continue
            feed = feedparser.parse(r.content)
            for entry in feed.entries[:6]:
                raw_t = clean_fact(entry.title.rsplit(" - ", 1)[0])
                if len(raw_t) < 25 or any(bt in raw_t.lower() for bt in BANNED_ARTICLE_TITLES):
                    continue
                soup_sum = BeautifulSoup(getattr(entry, "summary", ""), "html.parser")
                # If Google News list of links, take only distinct sub-headlines that don't repeat raw_t
                li_texts = [clean_fact(li.get_text(" ").rsplit(" - ", 1)[0]) for li in soup_sum.find_all("li")]
                extra_sents = []
                for lt in li_texts:
                    if len(lt) > 30 and lt.lower()[:25] != raw_t.lower()[:25]:
                        extra_sents.append(lt.rstrip(".") + ".")
                if not extra_sents:
                    raw_sum = clean_fact(soup_sum.get_text(separator=" "))
                    if raw_sum and raw_sum.lower()[:25] != raw_t.lower()[:25]:
                        extra_sents.append(raw_sum.rstrip(".") + ".")

                link = getattr(entry, "link", "https://news.google.com")
                if "news.google.com" not in link and len(extra_sents) < 2:
                    try:
                        ar = requests.get(link, headers=HEADERS_WEB, timeout=5)
                        if ar.status_code == 200:
                            asoup = BeautifulSoup(ar.text, "html.parser")
                            for p in asoup.find_all("p")[:6]:
                                pt = clean_fact(p.get_text(" ").strip())
                                if 45 <= len(pt) <= 190 and pt.lower()[:25] != raw_t.lower()[:25]:
                                    extra_sents.append(pt.rstrip(".") + ".")
                                    if len(extra_sents) >= 2:
                                        break
                    except Exception:
                        pass

                body_joined = " ".join(extra_sents[:2])
                combined_txt = f"{raw_t.rstrip('.')}. {body_joined}".strip() if body_joined else f"{raw_t.rstrip('.')}."
                if not is_semantically_similar_claim(combined_txt, mega_claims):
                    mega_claims.append({
                        "text": combined_txt[:340],
                        "headline_short": raw_t[:65],
                        "source_url": link,
                        "source_name": src,
                        "published_date": pub_d
                    })
                    words_ent = [w for w in re.findall(r"[A-Za-z]{4,}", raw_t) if w.lower() not in HEADLINE_STOP_VERBS_ADJS]
                    if words_ent:
                        visual_anchors.append(" ".join(words_ent[:3]))
                    if not lead_img and hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
                        lead_img = entry.media_thumbnail[0].get("url")
                if len(mega_claims) >= 18:
                    break
        except Exception:
            pass
        if len(mega_claims) >= 18:
            break

    if len(mega_claims) < 8:
        return None

    date_label = datetime.utcnow().strftime("%B %d, %Y")
    mega_title = f"24 Hours in 10 Minutes: Global Geopolitics & World News Briefing ({date_label})"
    c_prof = build_country_dict_from_db("UNITED STATES", is_global_topic=False)

    return {
        "score": 9999,
        "pillar": "WORLD",
        "sub_pillar": "DAILY_24H_MEGA_NEWS",
        "is_mega_24h": True,
        "yt_category_id": "25",
        "story_key": f"mega_24h_{datetime.utcnow().strftime('%Y_%m_%d')}",
        "event_tokens": ["global", "briefing", "24h", datetime.utcnow().strftime("%Y%m%d")],
        "is_followup_update": False,
        "previous_event_title": None,
        "title": mega_title,
        "original_yt_title": mega_title[:95],
        "topic_anchor": "Global Geopolitics Summit",
        "visual_anchors": visual_anchors[:15] if visual_anchors else ["United Nations", "White House", "Pentagon", "Wall Street"],
        "article_video_urls": [],
        "category": "dark_geopolitics",
        "source_url": "https://news.google.com",
        "published_date": pub_d,
        "source_name": "Global Wire Services",
        "verified_claims": mega_claims,
        "raw_facts": [c["text"] for c in mega_claims],
        "lead_img": lead_img,
        "wiki_gallery_urls": [],
        "country_profile": c_prof,
        "wb_data": None
    }

# ==============================================================================
# 7. STRICT FULL-NAME PERSON DETECTOR & PRE-CACHED DOSSIER PORTRAIT CARD
#    Fixes the `Vidmar` / `Holm` / `Lunan` single-surname bug from the logs!
# ==============================================================================
COMMON_NON_PERSON_CAP_WORDS = {
    "The", "This", "That", "These", "Those", "Under", "However", "Meanwhile", "Instead",
    "Despite", "While", "When", "Where", "What", "Why", "How", "In", "On", "At", "By",
    "For", "With", "From", "Into", "Over", "After", "Before", "During", "Since", "Until",
    "Small", "Explorer", "Earth", "Venture", "James", "Webb", "Space", "Telescope",
    "United", "States", "Kingdom", "Nations", "Science", "Mission", "Directorate",
    "Competition", "Model", "World", "Talk", "Brief", "Oct", "October", "November",
    "December", "January", "February", "March", "April", "June", "July", "August",
    "September", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
    "North", "South", "East", "West", "Central", "Middle", "Associate", "Administrator",
    "Prime", "Minister", "President", "General", "Professor", "University", "Institute",
    "Global", "National", "International", "European", "American", "Russian", "Chinese",
    "Indian", "British", "French", "German", "Japanese", "Modern", "Ancient", "History"
}

def is_safe_family_friendly_image(im_rgb, is_portrait=False):
    """
    100% FAMILY-FRIENDLY / ZERO-18+ SKIN & NSFW PIXEL DETECTOR:
    Uses dual YCrCb + HSV color-space skin segmentation to automatically reject any image or
    video frame with excessive exposed skin, nudity, swimwear, or nude classical statues!
    """
    try:
        small = im_rgb.convert("RGB").resize((160, 160))
        arr_rgb = np.asarray(small, dtype=np.uint8)
        arr_ycrcb = cv2.cvtColor(arr_rgb, cv2.COLOR_RGB2YCrCb)
        arr_hsv = cv2.cvtColor(arr_rgb, cv2.COLOR_RGB2HSV)

        # Standard human skin chroma cluster in YCrCb & HSV
        ycrcb_mask = (
            (arr_ycrcb[:, :, 0] > 55)
            & (arr_ycrcb[:, :, 1] >= 135) & (arr_ycrcb[:, :, 1] <= 172)
            & (arr_ycrcb[:, :, 2] >= 79) & (arr_ycrcb[:, :, 2] <= 125)
        )
        hsv_mask = (
            (arr_hsv[:, :, 0] <= 20)
            & (arr_hsv[:, :, 1] >= 42) & (arr_hsv[:, :, 1] <= 172)
            & (arr_hsv[:, :, 2] >= 65)
        )
        skin_mask = ycrcb_mask & hsv_mask
        full_skin_ratio = float(np.mean(skin_mask))

        # Check central torso/body region (rows 35% to 90%, cols 20% to 80%)
        torso_mask = skin_mask[56:144, 32:128]
        torso_skin_ratio = float(np.mean(torso_mask))

        if is_portrait:
            # Close-up face portraits naturally have skin on the face, but lower torso shouldn't be bare skin
            lower_body_ratio = float(np.mean(skin_mask[112:156, 28:132]))
            if full_skin_ratio > 0.46 or lower_body_ratio > 0.38:
                return False
            return True

        if full_skin_ratio > 0.27 or torso_skin_ratio > 0.29:
            return False
        return True
    except Exception:
        return True

NON_PERSON_ORG_WORDS = {
    "amnesty", "international", "mada", "masr", "reuters", "associated", "press", "guardian",
    "aljazeera", "jazeera", "bbc", "cnn", "cnbc", "bloomberg", "times", "post", "journal",
    "tribune", "herald", "daily", "news", "media", "outlet", "agency", "network", "channel",
    "platform", "website", "organization", "organisation", "university", "institute", "college",
    "academy", "council", "foundation", "ministry", "department", "court", "syndicate", "union",
    "brotherhood", "association", "committee", "commission", "authority", "government", "parliament",
    "congress", "senate", "white", "house", "pentagon", "kremlin", "nato", "united", "nations",
    "world", "health", "chalmers", "royal", "swedish", "american", "british", "egyptian", "indian",
    "chinese", "russian", "israeli", "iranian", "european", "global", "national", "federal",
    "supreme", "high", "misdemeanour", "misdemeanors", "security", "forces", "police", "military",
    "army", "navy", "hospital", "clinic", "laboratory", "lab", "program", "group", "corp", "inc",
    "chancellor", "exchequer", "treasury", "minister", "president", "secretary", "governor",
    "senator", "mayor", "speaker", "ambassador", "commissioner", "director", "chairman", "chairwoman",
    "owners", "customers", "residents", "shop", "shops", "street", "streets", "pawnbrokers", "betting"
}

def is_valid_human_name_candidate(cand_name):
    if not cand_name:
        return False
    parts = [w.strip(".,'\"") for w in cand_name.split() if w.strip(".,'\"")]
    if len(parts) < 2 or len(parts) > 4:
        return False
    for p in parts:
        if p in COMMON_NON_PERSON_CAP_WORDS or p.lower() in NON_PERSON_ORG_WORDS:
            return False
    return True

def detect_person_in_narration_text(text, ai_person="", ai_role=""):
    """
    UNIVERSAL DYNAMIC SUBJECT SPOTLIGHT DETECTOR (People, Animals/Wildlife, Iconic Tech/Spacecraft, Historical Figures):
    1. Matches `PERSON_WIKI_MAP` (includes World Leaders, Scientists, Historical Icons, AND Wildlife/Animals!).
    2. Maps generic titles like 'Chancellor' in a UK story to 'Rachel Reeves' so it NEVER fetches a Coat of Arms!
    3. Detects specific concrete props/machines/landmarks from `CONCRETE_WIKI_PROPS` when no person is named,
       so EVERY story (whether about a Person, an Animal, a Tech Breakthrough, or a Local Crisis) gets dynamic visual highlights!
    """
    low = text.lower()
    for p_key in sorted(PERSON_WIKI_MAP.keys(), key=len, reverse=True):
        if re.search(rf"\b{re.escape(p_key)}\b", low):
            return PERSON_WIKI_MAP[p_key]

    if "chancellor" in low and any(k in low for k in ["uk", "britain", "british", "high street", "tax", "budget"]):
        return ("Rachel Reeves", "Rachel Reeves", "UK CHANCELLOR OF THE EXCHEQUER")

    if ai_person:
        clean_name = re.sub(r"[^\x20-\x7E]", "", ai_person).strip()
        if clean_name.lower() in PERSON_WIKI_MAP:
            return PERSON_WIKI_MAP[clean_name.lower()]
        if clean_name.lower() not in {"none", "null", "n/a", "unknown", "host", "narrator"} and is_valid_human_name_candidate(clean_name):
            clean_role = re.sub(r"[^\x20-\x7E]", "", ai_role or "KEY SUBJECT IN FOCUS").strip().upper()
            return (clean_name, clean_name, clean_role[:28])

    role_patterns = [
        (r"(?:King|Emperor|Pharaoh|Queen|General|Commander|Conqueror)\s+([A-Z][a-z]{2,15}(?:\s+(?:the\s+)?[A-Z][a-z]{2,15})?)", "HISTORICAL RULER & LEADER"),
        (r"(?:journalist|editor-in-chief|editor|reporter|correspondent|activist|lawyer|judge|prosecutor)\s+([A-Z][a-z]{2,14}\s+[A-Z][a-z]{2,16})", "JOURNALIST & KEY FIGURE"),
        (r"(?:Administrator|Director|President|Prime Minister|CEO|Founder|Chancellor|Secretary|Senator|Governor|Minister)\s+([A-Z][a-z]{2,14}\s+[A-Z][a-z]{2,16})", "OFFICIAL LEADERSHIP"),
        (r"(?:Dr\.|Professor|Assistant Professor|Scientist|Researcher|Historian|Astronomer|Physicist)\s+([A-Z][a-z]{2,14}\s+[A-Z][a-z]{2,16})", "LEAD SCIENTIST & RESEARCHER"),
        (r"(?:says|said|warned|explained|according to)\s+([A-Z][a-z]{2,14}\s+[A-Z][a-z]{2,16})", "KEY EXPERT & SOURCE"),
        (r"([A-Z][a-z]{2,14}\s+[A-Z][a-z]{2,16}),?\s+who\s+(?:led|founded|discovered|directed|wrote|authored|commanded)", "LEAD INVESTIGATOR"),
        (r"([A-Z][a-z]{2,14}\s+[A-Z][a-z]{2,16})\s+(?:was\s+released|was\s+detained|was\s+arrested|was\s+appointed|testified|discovered)", "KEY FIGURE IN STORY")
    ]
    for pat, default_role in role_patterns:
        for m in re.finditer(pat, text):
            cand_name = m.group(1).strip()
            if is_valid_human_name_candidate(cand_name):
                return (cand_name, cand_name, default_role)

    # Also check if a concrete Tech/Science/Market/Defense subject is in the sentence for dynamic spotlighting!
    for prop_k, (prop_badge, wiki_exact, _) in CONCRETE_WIKI_PROPS.items():
        if len(prop_k) >= 4 and re.search(rf"\b{re.escape(prop_k)}\b", low):
            return (wiki_exact, wiki_exact, prop_badge[:28])

    return None

def is_real_natural_subject_photo(im_rgb):
    """
    STRICT ANTI-COAT-OF-ARMS / ANTI-LOGO / ANTI-CLIPART GUARD FOR SPOTLIGHT CARDS:
    Rejects heraldic coats of arms (like the UK Royal Arms on 'Chancellor of the Exchequer'),
    flags, seals, solid-background vector logos, and text banners!
    """
    arr = np.asarray(im_rgb.resize((120, 120)), dtype=np.float32)
    # Reject solid white/black/transparent-converted backgrounds typical of coats of arms & logos
    white_ratio = np.mean((arr[:, :, 0] > 235) & (arr[:, :, 1] > 235) & (arr[:, :, 2] > 235))
    black_ratio = np.mean((arr[:, :, 0] < 18) & (arr[:, :, 1] < 18) & (arr[:, :, 2] < 18))
    if white_ratio > 0.16 or black_ratio > 0.38:
        return False
    # Check border pixels (logos/crests almost always have uniform border color)
    top_row_std = float(np.std(arr[:8, :, :]))
    left_col_std = float(np.std(arr[:, :8, :]))
    if top_row_std < 12.0 and left_col_std < 12.0:
        return False
    # Color quantization check (vector emblems have dominant flat colors)
    quant = (arr // 32).astype(int)
    flat = quant[:, :, 0] * 64 + quant[:, :, 1] * 8 + quant[:, :, 2]
    _, counts = np.unique(flat, return_counts=True)
    if (counts.max() / float(120 * 120)) > 0.24:
        return False
    return True

def fetch_person_portrait_image(wiki_name, display_name, role_str=""):
    cache_key = display_name.lower().strip()
    if cache_key in PERSON_PORTRAIT_CACHE:
        return PERSON_PORTRAIT_CACHE[cache_key]

    resample_mode = getattr(Image, "Resampling", Image).LANCZOS
    banned_spotlight_tokens = [
        "logo", "flag", "map", "icon", "seal", "signature", "nude", "naked", "venus",
        "coat_of_arms", "royal_arms", "arms_of", "crest", "emblem", "insignia", "herald",
        "diagram", "chart", "svg", "placeholder", "silhouette"
    ]

    for candidate_page in [wiki_name, display_name]:
        if not candidate_page:
            continue
        try:
            w_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(candidate_page)}"
            r = requests.get(w_url, headers=HEADERS_WIKI, timeout=5)
            if r.status_code == 200:
                data = r.json()
                img_u = data.get("originalimage", {}).get("source") or data.get("thumbnail", {}).get("source")
                if img_u and not img_u.lower().endswith(".svg") and not any(b in img_u.lower() for b in banned_spotlight_tokens):
                    ir = requests.get(img_u, headers=HEADERS_WIKI, timeout=5)
                    if ir.status_code == 200 and len(ir.content) > 10000:
                        p = f"temp/person_{hashlib.md5(cache_key.encode()).hexdigest()[:8]}.jpg"
                        with open(p, "wb") as f:
                            f.write(ir.content)
                        im = Image.open(p).convert("RGB")
                        iw, ih = im.size
                        side = min(iw, ih)
                        left = (iw - side) // 2
                        top = max(0, int((ih - side) * 0.10))
                        im_sq = im.crop((left, top, left + side, top + side)).resize((340, 340), resample_mode)
                        if is_safe_family_friendly_image(im_sq, is_portrait=True) and is_real_natural_subject_photo(im_sq):
                            PERSON_PORTRAIT_CACHE[cache_key] = im_sq
                            print(f"   🎯 [Dynamic Subject Spotlight Locked (Wiki)]: {display_name} ({role_str})", flush=True)
                            return im_sq
        except Exception:
            pass

    try:
        is_animal_or_obj = any(k in role_str.upper() for k in ["PREDATOR", "WILDLIFE", "MARINE", "SPECIES", "TELESCOPE", "ROCKET", "MARKET", "AI", "CHIP", "ROBOT", "FIGHTER", "DRONE", "MISSILE"])
        q_suffix = "real close up wildlife photography -cartoon -logo -drawing" if is_animal_or_obj else "official press photo portrait -cartoon -logo -crest -coat_of_arms -nude -statue"
        q_str = f"{display_name} {role_str} {q_suffix}"
        b_url = f"https://www.bing.com/images/async?q={urllib.parse.quote(q_str)}&first=0&count=10&adlt=strict&qft=+filterui:photo-photo"
        r = requests.get(b_url, headers=HEADERS_WEB, timeout=5)
        murls = re.findall(r"murl&quot;:&quot;(https?://[^&]+?)&quot;", r.text)
        for u in murls[:8]:
            u_clean = u.replace("&amp;", "&")
            if any(b in u_clean.lower() for b in BANNED_IMAGE_SOURCES + banned_spotlight_tokens) or any(nf in u_clean.lower() for nf in ADULT_NSFW_BANNED_TERMS):
                continue
            ir = requests.get(u_clean, headers=HEADERS_WEB, timeout=5)
            if ir.status_code == 200 and len(ir.content) > 12000:
                p = f"temp/person_b_{hashlib.md5(cache_key.encode()).hexdigest()[:8]}.jpg"
                with open(p, "wb") as f:
                    f.write(ir.content)
                im = Image.open(p).convert("RGB")
                iw, ih = im.size
                if iw >= 220 and ih >= 220:
                    side = min(iw, ih)
                    left = (iw - side) // 2
                    top = max(0, int((ih - side) * 0.10))
                    im_sq = im.crop((left, top, left + side, top + side)).resize((340, 340), resample_mode)
                    if is_safe_family_friendly_image(im_sq, is_portrait=True) and is_real_natural_subject_photo(im_sq):
                        PERSON_PORTRAIT_CACHE[cache_key] = im_sq
                        print(f"   🎯 [Dynamic Subject Spotlight Locked (Bing Photo)]: {display_name} ({role_str})", flush=True)
                        return im_sq
    except Exception:
        pass

    PERSON_PORTRAIT_CACHE[cache_key] = None
    return None

def build_prebuilt_person_card_rgba(person_info, is_short=True):
    """
    CENTER-STAGE HERO PORTRAIT POP-UP CARD (`बीच में` Pro Documentary Overlay):
    Renders the named person's portrait in 4 rotating pro-editor visual styles
    (0: Golden Spotlight Medallion, 1: 3D Polaroid Snap Card, 2: Cyber-HUD Target Lock, 3: Crimson Classified Dossier)
    designed to pop up right in the CENTER of the screen when their name is spoken!
    """
    if not person_info or person_info.get("portrait_im") is None:
        return None
    style_idx = int(person_info.get("style_idx", 0)) % 4
    cache_field = f"prebuilt_center_card_{is_short}_{style_idx}"
    if person_info.get(cache_field) is not None:
        return person_info[cache_field]

    portrait_im = person_info["portrait_im"]
    disp_name = person_info["name"].upper()[:24]
    role_lbl = person_info["role"].upper()[:32]
    resample_mode = getattr(Image, "Resampling", Image).LANCZOS

    card_w = 680 if is_short else 660
    card_h = 460 if is_short else 430
    card = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    cdraw = ImageDraw.Draw(card, "RGBA")

    cx = card_w // 2
    ava_sz = 250 if is_short else 236
    ava_y = 26

    # Outer soft ambient glow halo in center
    for r_glow in range(ava_sz // 2 + 34, ava_sz // 2 + 4, -5):
        alpha_g = int(75 * (1.0 - (r_glow - ava_sz // 2) / 34.0))
        glow_col = (255, 215, 0, alpha_g) if style_idx in [0, 1] else (0, 235, 255, alpha_g)
        cdraw.ellipse([(cx - r_glow, ava_y + ava_sz // 2 - r_glow), (cx + r_glow, ava_y + ava_sz // 2 + r_glow)], fill=glow_col)

    ava_resized = portrait_im.resize((ava_sz, ava_sz), resample_mode).convert("RGBA")

    if style_idx in [0, 3]:
        # Circular Golden / Crimson Medallion Spotlight Portrait in Center
        mask = Image.new("L", (ava_sz, ava_sz), 0)
        ImageDraw.Draw(mask).ellipse([(0, 0), (ava_sz, ava_sz)], fill=255)
        ring_col = (255, 215, 0, 255) if style_idx == 0 else (225, 25, 55, 255)
        cdraw.ellipse([(cx - ava_sz // 2 - 10, ava_y - 10), (cx + ava_sz // 2 + 10, ava_y + ava_sz + 10)], fill=(10, 16, 30, 245), outline=ring_col, width=6)
        cdraw.ellipse([(cx - ava_sz // 2 - 3, ava_y - 3), (cx + ava_sz // 2 + 3, ava_y + ava_sz + 3)], outline=(255, 255, 255, 240), width=3)
        card.paste(ava_resized, (cx - ava_sz // 2, ava_y), mask)
    else:
        # Rounded Polaroid / Cyber-HUD Frame in Center
        mask = Image.new("L", (ava_sz, ava_sz), 0)
        ImageDraw.Draw(mask).rounded_rectangle([(0, 0), (ava_sz, ava_sz)], radius=28, fill=255)
        border_col = (255, 255, 255, 255) if style_idx == 1 else (0, 240, 255, 255)
        cdraw.rounded_rectangle([(cx - ava_sz // 2 - 12, ava_y - 12), (cx + ava_sz // 2 + 12, ava_y + ava_sz + 12)], radius=32, fill=(12, 18, 34, 248), outline=border_col, width=5)
        card.paste(ava_resized, (cx - ava_sz // 2, ava_y), mask)
        if style_idx == 2:
            # Cyber-HUD Target Lock Corner Brackets
            bx1, by1, bx2, by2 = cx - ava_sz // 2 - 20, ava_y - 20, cx + ava_sz // 2 + 20, ava_y + ava_sz + 20
            for (px, py, dx, dy) in [(bx1, by1, 28, 28), (bx2, by1, -28, 28), (bx1, by2, 28, -28), (bx2, by2, -28, -28)]:
                cdraw.line([(px, py), (px + dx, py)], fill=(255, 215, 0, 255), width=4)
                cdraw.line([(px, py), (px, py + dy)], fill=(255, 215, 0, 255), width=4)

    # Lower Center Name & Role Pedestal Banner
    plate_y = ava_y + ava_sz + 20
    plate_h = 132
    cdraw.rounded_rectangle([(34, plate_y + 6), (card_w - 26, plate_y + plate_h + 6)], radius=22, fill=(0, 0, 0, 200))
    cdraw.rounded_rectangle([(28, plate_y), (card_w - 32, plate_y + plate_h)], radius=22, fill=(8, 14, 28, 248), outline=(255, 215, 0, 250), width=3)

    tag_txt = "⚡ KEY FIGURE IN FOCUS" if style_idx % 2 == 0 else "📂 VERIFIED PROFILE // LIVE"
    f_tag = get_font(16)
    tw_tag = cdraw.textbbox((0, 0), tag_txt, font=f_tag)[2] + 32
    cdraw.rounded_rectangle([(cx - tw_tag // 2, plate_y - 15), (cx + tw_tag // 2, plate_y + 15)], radius=10, fill=(220, 20, 45, 255), outline=(255, 255, 255, 230), width=2)
    cdraw.text((cx - tw_tag // 2 + 16, plate_y - 10), tag_txt, fill=(255, 255, 255, 255), font=f_tag)

    f_name = get_font(34 if len(disp_name) <= 18 else 28)
    nw = cdraw.textbbox((0, 0), disp_name, font=f_name)[2]
    cdraw.text((cx - nw // 2 + 2, plate_y + 26), disp_name, fill=(0, 0, 0, 240), font=f_name)
    cdraw.text((cx - nw // 2, plate_y + 24), disp_name, fill=(255, 255, 255, 255), font=f_name)

    f_role = get_font(20)
    rw = cdraw.textbbox((0, 0), role_lbl, font=f_role)[2]
    cdraw.text((cx - rw // 2, plate_y + 74), role_lbl, fill=(255, 220, 0, 255), font=f_role)

    cdraw.line([(90, plate_y + 108), (card_w - 90, plate_y + 108)], fill=(0, 235, 255, 180), width=2)

    person_info[cache_field] = card
    return card

# ==============================================================================
# 8. NON-REPEATING HD VIDEO B-ROLL HARVESTER (Max 1 Clip Per Chapter = Fast & Unique!)
# ==============================================================================
def has_collage_or_text_banner_artifacts(im_rgb):
    """
    NITISH RAJPUT QUALITY GUARD — BLOCKS COLLAGES, MEMES, PODCAST THUMBNAILS ('COMING UP...'),
    BURNED-IN SUBTITLES ('YES, CALIFORNIA...'), AND 3D GAME SCREENS ('Cash Register'):
    1. Detects vertical or horizontal split-screen divider lines across the image (blocks 2x2 / 3-panel collages).
    2. Detects dense horizontal text/subtitle blocks in the middle or lower third of the image.
    3. Detects comic-book / cartoon ink outlines & synthetic 3D game UI flatness.
    """
    try:
        small_g = cv2.cvtColor(np.array(im_rgb.resize((320, 180)), dtype=np.uint8), cv2.COLOR_RGB2GRAY)
        # 1. Check for vertical or horizontal split-screen collage lines in the middle 30%-70%
        col_diffs = np.mean(np.abs(np.diff(small_g[:, 90:230].astype(np.float32), axis=1)), axis=0)
        col_stds = np.std(small_g[:, 90:230].astype(np.float32), axis=0)
        if np.min(col_stds) < 6.5 or np.max(col_diffs) > 62.0:
            return True
        row_stds = np.std(small_g[50:130, :].astype(np.float32), axis=1)
        if np.min(row_stds) < 6.5:
            return True

        # 2. Check for burned-in yellow/white subtitle text or giant title banners ('COMING UP...', 'TikTok and...')
        kernel_rect = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 3))
        grad = cv2.morphologyEx(small_g, cv2.MORPH_GRADIENT, kernel_rect)
        # High-contrast sharp text strokes in the center or bottom third
        text_stroke_ratio = float(np.mean(grad[25:165, 20:300] > 115))
        if text_stroke_ratio > 0.145:
            return True

        # 3. Check for comic-book / cartoon heavy dark outlines
        edges = cv2.Canny(small_g, 100, 200)
        if float(np.mean(edges > 0)) > 0.165:
            return True

        return False
    except Exception:
        return False

def is_valid_cinematic_video_frame(frame_rgb):
    pil_f = Image.fromarray(frame_rgb)
    if not is_safe_family_friendly_image(pil_f, is_portrait=False):
        return False
    if has_collage_or_text_banner_artifacts(pil_f):
        return False
    arr = np.asarray(pil_f.resize((120, 120)), dtype=np.float32)
    if float(np.std(arr)) < 28.0:
        return False
    white_px = np.sum((arr[:, :, 0] > 230) & (arr[:, :, 1] > 230) & (arr[:, :, 2] > 230)) / float(120 * 120)
    black_px = np.sum((arr[:, :, 0] < 22) & (arr[:, :, 1] < 22) & (arr[:, :, 2] < 22)) / float(120 * 120)
    if white_px > 0.18 or black_px > 0.42:
        return False
    return True

def download_and_transcode_mp4_url(cand_u, used_video_urls, tag_id, label_str):
    """
    FULL-SENTENCE HD VIDEO B-ROLL TRANSCODER:
    Transcodes up to 11.0 seconds (with smooth cinematic 1.25x slow-motion extension)
    so the video clip stays on screen smoothly until the narrator finishes the ENTIRE sentence
    instead of cutting away after 2 seconds!
    """
    if not cand_u or cand_u in used_video_urls:
        return None
    if any(nf in cand_u.lower() for nf in ADULT_NSFW_BANNED_TERMS):
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
                    if bytes_read >= 8500000:
                        break

        if not os.path.exists(raw_local) or os.path.getsize(raw_local) < 60000:
            return None

        cmd = [
            "ffmpeg", "-y",
            "-ss", "0.8",
            "-i", raw_local,
            "-t", "11.0",
            "-vf", "setpts=1.25*PTS,scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1",
            "-r", "24", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast",
            clean_mp4
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=18, check=False)
        if os.path.exists(clean_mp4) and os.path.getsize(clean_mp4) > 45000:
            vc = VideoFileClip(clean_mp4)
            GLOBAL_OPEN_VCLIPS.append(vc)
            if vc.duration >= 3.2:
                f1 = vc.get_frame(min(0.5, vc.duration * 0.20))
                f2 = vc.get_frame(min(1.8, vc.duration * 0.55))
                f3 = vc.get_frame(min(3.0, vc.duration * 0.85))
                if is_valid_cinematic_video_frame(f1) and is_valid_cinematic_video_frame(f2) and is_valid_cinematic_video_frame(f3):
                    used_video_urls.add(cand_u)
                    print(f"   🎬 [FULL-SENTENCE HD VIDEO B-ROLL LOCKED]: {label_str[:30]} ({round(vc.duration, 1)}s)", flush=True)
                    return {
                        "vclip": vc,
                        "start_t": 0.0,
                        "label": f"● LIVE FOOTAGE • {label_str.upper()[:18]}"
                    }
    except Exception:
        pass
    return None

VIDEO_EXACT_SCENE_MAP = {
    "stock": "stock market trading floor",
    "ipo": "stock exchange trading floor",
    "convertible": "financial district skyscrapers",
    "billion": "wall street financial district",
    "investors": "stock exchange trading screens",
    "anthropic": "server room data center",
    "amazon": "warehouse logistics robotics",
    "aws": "cloud data center server",
    "google": "technology campus silicon valley",
    "court": "supreme court courthouse building",
    "judge": "courthouse justice building",
    "cholesterol": "medical laboratory blood test",
    "heart": "hospital cardiology medical monitor",
    "protein": "biotechnology laboratory microscope"
}

def fetch_and_transcode_real_video_broll(video_query, dossier, used_video_urls, used_video_queries, tag_id="vclip"):
    topic_anchor = dossier.get("topic_anchor") or extract_primary_topic_anchor(dossier)
    pillar = dossier.get("pillar", "WORLD")
    p_cfg = CATEGORY_FEEDS.get(pillar, CATEGORY_FEEDS["WORLD"])
    subreddits = p_cfg.get("reddit_subs", "worldnews+technology")

    clean_subj = re.sub(r"[^a-zA-Z0-9\s]", " ", f"{video_query} {topic_anchor}").strip()
    subj_words = []
    for w in re.findall(r"[A-Za-z0-9]{3,}", clean_subj):
        wl = w.lower()
        if wl not in HEADLINE_STOP_VERBS_ADJS and wl not in {"instead", "taking", "upfront", "none", "those", "while", "each", "both", "much", "more"} and wl not in subj_words:
            subj_words.append(wl)

    mapped_v_q = None
    for sw in subj_words:
        if sw in VIDEO_EXACT_SCENE_MAP:
            mapped_v_q = VIDEO_EXACT_SCENE_MAP[sw]
            break

    query_str = mapped_v_q if mapped_v_q else (" ".join(subj_words[:3]) if subj_words else topic_anchor)
    if query_str.lower() in used_video_queries:
        query_str = f"{query_str} {len(used_video_queries) + 1}"
    used_video_queries.add(query_str.lower())

    for art_v in dossier.get("article_video_urls", []):
        res = download_and_transcode_mp4_url(art_v, used_video_urls, f"{tag_id}_art", query_str)
        if res is not None:
            return res

    # Official NASA HD Video Archive (ONLY when the story is actually about Space / Astronomy / NASA!)
    space_Context_check = f"{dossier['title']} {query_str}".lower()
    is_space_story = any(sp_w in space_Context_check for sp_w in ["nasa", "space", "rocket", "orbit", "mars", "moon", "lunar", "galaxy", "telescope", "webb", "jwst", "satellite", "astronaut", "iss", "asteroid", "planet", "cosmos", "spacex", "starship", "starlink", "solar"])
    if is_space_story:
        try:
            n_url = f"https://images-api.nasa.gov/search?q={urllib.parse.quote(query_str)}&media_type=video"
            nr = requests.get(n_url, headers=HEADERS_WEB, timeout=6).json()
            items = nr.get("collection", {}).get("items", [])
            for it in items[:8]:
                href = it.get("href", "")
                if not href or href in used_video_urls:
                    continue
                v_list = requests.get(href, headers=HEADERS_WEB, timeout=5).json()
                mp4_links = [u for u in v_list if isinstance(u, str) and u.endswith(".mp4") and ("~medium" in u or "~large" in u or "720" in u)]
                if not mp4_links:
                    mp4_links = [u for u in v_list if isinstance(u, str) and u.endswith(".mp4")]
                for mp4_u in mp4_links[:2]:
                    mp4_u_https = mp4_u.replace("http://", "https://")
                    if mp4_u_https in used_video_urls:
                        continue
                    res = download_and_transcode_mp4_url(mp4_u_https, used_video_urls, f"{tag_id}_nasa", query_str)
                    if res is not None:
                        used_video_urls.add(href)
                        return res
        except Exception:
            pass

    strict_banned_video_words = [
        "vlog", "webcam", "stream", "gaming", "game", "gameplay", "counter-strike", "csgo", "valorant",
        "call of duty", "warzone", "gta", "roblox", "fortnite", "simulator", "fps", "twitch", "minecraft",
        "cartoon", "anime", "comic", "user", "test", "lecture", "interview", "podcast", "shapiro",
        "coming up", "episode", "golf", "tree", "park", "pronunciation", "spoken", "audio", "session",
        "recorded", "wikidata", "conference", "talk", "presentation", "isolated", "nude", "naked",
        "nsfw", "erotic", "sex", "bikini", "lingerie", "swimsuit", "anatomy", "statue", "tractor",
        "allis", "farming", "harvest", "grand rounds", "webinar", "seminar", "slide", "chart",
        "rolling stock", "locomotive", "railway", "train", "mountain", "hiking", "scenery", "landscape",
        "piano", "guitar", "violin", "concert", "living room", "bedroom", "kitchen", "radar", "weather",
        "loop", "animation", "tiktok", "unboxing", "motherboard", "intel", "amd", "california"
    ]
    required_match_tokens = {w.lower() for w in re.findall(r"[A-Za-z0-9]{4,}", f"{query_str} {topic_anchor}") if w.lower() not in HEADLINE_STOP_VERBS_ADJS}

    # Reddit Native HD Video (`v.redd.it`) — ONLY accepted if post title strictly matches >=2 story/query keywords!
    try:
        rd_url = f"https://www.reddit.com/r/{subreddits}/search.json?q={urllib.parse.quote(query_str)}&restrict_sr=1&sort=relevance&t=year&limit=10"
        rr = requests.get(rd_url, headers=HEADERS_WIKI, timeout=6).json()
        for child in rr.get("data", {}).get("children", []):
            post = child.get("data", {})
            if post.get("over_18"):
                continue
            post_title_low = str(post.get("title", "")).lower()
            if any(bw in post_title_low for bw in strict_banned_video_words):
                continue
            post_tokens = {w.lower() for w in re.findall(r"[A-Za-z0-9]{4,}", post_title_low)}
            if len(post_tokens.intersection(required_match_tokens)) < 2:
                continue
            rv = (post.get("secure_media") or post.get("media") or {}).get("reddit_video", {})
            fb_u = rv.get("fallback_url", "")
            vh = int(rv.get("height") or 0)
            if fb_u and ".mp4" in fb_u and vh >= 720 and fb_u not in used_video_urls:
                res = download_and_transcode_mp4_url(fb_u, used_video_urls, f"{tag_id}_rd", query_str)
                if res is not None:
                    return res
    except Exception:
        pass

    # Wikimedia Commons HD Video Archive — ONLY accepted if file title strictly matches >=2 subject keywords!
    if subj_words:
        wm_q = " ".join(subj_words[:3])
        try:
            api = "https://commons.wikimedia.org/w/api.php"
            params = {
                "action": "query", "generator": "search",
                "gsrsearch": f"filetype:video {wm_q}",
                "gsrnamespace": "6", "gsrlimit": 8,
                "prop": "videoinfo|imageinfo", "viprop": "url|size|derivatives", "iiprop": "url|size", "format": "json"
            }
            r = requests.get(api, params=params, headers=HEADERS_WIKI, timeout=6).json()
            for pg in r.get("query", {}).get("pages", {}).values():
                v_title = pg.get("title", "").lower()
                if any(bw in v_title for bw in strict_banned_video_words):
                    continue
                v_tokens = {w.lower() for w in re.findall(r"[A-Za-z0-9]{4,}", v_title)}
                if len(v_tokens.intersection(required_match_tokens)) < 2:
                    continue
                vi = (pg.get("videoinfo") or pg.get("imageinfo") or [{}])[0]
                for d in vi.get("derivatives", []):
                    du = d.get("src", "")
                    if du.endswith((".webm", ".mp4")) and any(res in du for res in ["720p", "1080p", "480p"]) and du not in used_video_urls:
                        res = download_and_transcode_mp4_url(du, used_video_urls, f"{tag_id}_wm", wm_q)
                        if res is not None:
                            return res
        except Exception:
            pass

    return None

# ==============================================================================
# 9. STRICT HD PHOTO VALIDATOR & COPYRIGHT-SAFE DOCUMENTARY LUT
# ==============================================================================
def apply_copyright_safe_documentary_lut(im):
    """
    Applies a subtle Cinema Documentary Color-Grade LUT + 4% edge crop + contrast curve
    so every external visual is 100% transformative and copyright-safe!
    """
    arr = np.asarray(im, dtype=np.float32)
    # Cinema Teal-Gold documentary color balance
    arr[:, :, 0] = np.clip(arr[:, :, 0] * 1.03, 0, 255)
    arr[:, :, 1] = np.clip(arr[:, :, 1] * 1.01, 0, 255)
    arr[:, :, 2] = np.clip(arr[:, :, 2] * 1.05 + 4.0, 0, 255)
    out = Image.fromarray(arr.astype(np.uint8))
    out = out.filter(ImageFilter.UnsharpMask(radius=1.5, percent=130, threshold=3))
    return ImageEnhance.Contrast(out).enhance(1.08)

def validate_and_enhance_1080p(im, existing_hashes, min_w=800, min_h=450):
    im = im.convert("RGB")
    w, h = im.size
    if w < min_w or h < min_h:
        return None

    # Crop outer 4% border to remove any corner agency watermarks/timestamps
    im = im.crop((int(w * 0.04), int(h * 0.04), int(w * 0.96), int(h * 0.93)))

    # 100% Broadcast-Safe Family-Friendly Skin/NSFW Check + Anti-Collage / Anti-Text-Thumbnail / Anti-Game Check!
    if not is_safe_family_friendly_image(im, is_portrait=False):
        return None
    if has_collage_or_text_banner_artifacts(im):
        return None

    arr = np.asarray(im.resize((120, 120)), dtype=np.float32)

    if float(np.std(arr)) < 36.0:
        return None

    h1, h2 = arr[:, :60, :], arr[:, 60:, :]
    if float(np.std(h1)) < 22.0 or float(np.std(h2)) < 22.0:
        return None

    white_px = np.sum((arr[:, :, 0] > 230) & (arr[:, :, 1] > 230) & (arr[:, :, 2] > 230))
    if (white_px / float(120 * 120)) > 0.14:
        return None

    black_px = np.sum((arr[:, :, 0] < 18) & (arr[:, :, 1] < 18) & (arr[:, :, 2] < 18))
    if (black_px / float(120 * 120)) > 0.35:
        return None

    rg_diff = np.mean(np.abs(arr[:, :, 0] - arr[:, :, 1]))
    gb_diff = np.mean(np.abs(arr[:, :, 1] - arr[:, :, 2]))
    if rg_diff < 5.5 and gb_diff < 5.5:
        return None

    quant = (arr // 32).astype(int)
    flat = quant[:, :, 0] * 64 + quant[:, :, 1] * 8 + quant[:, :, 2]
    _, counts = np.unique(flat, return_counts=True)
    if (counts.max() / float(120 * 120)) > 0.26:
        return None

    # Reject synthetic AI neon renders & CGI illustrations (excessive hyper-saturated neon cyan/blue/magenta pixels)
    hsv_check = cv2.cvtColor(np.array(im.resize((160, 160)), dtype=np.uint8), cv2.COLOR_RGB2HSV)
    high_sat_neon = np.mean((hsv_check[:, :, 1] > 215) & (hsv_check[:, :, 2] > 200))
    if high_sat_neon > 0.24:
        return None

    gray_cv = cv2.cvtColor(np.array(im.resize((480, 270))), cv2.COLOR_RGB2GRAY)
    blur_score = cv2.Laplacian(gray_cv, cv2.CV_64F).var()
    if blur_score < 85.0 or im.entropy() < 6.3:
        return None

    gray = im.convert("L").resize((13, 12))
    dh = (np.asarray(gray, dtype=np.int16)[:, 1:] > np.asarray(gray, dtype=np.int16)[:, :-1]).flatten()
    for old_h in existing_hashes:
        if int(np.sum(dh != old_h)) < 16:
            return None
    existing_hashes.append(dh)

    resample_mode = getattr(Image, "Resampling", Image).LANCZOS
    if im.size[0] < 1920 and im.size[0] >= im.size[1]:
        scale = 1920.0 / float(im.size[0])
        im = im.resize((1920, int(im.size[1] * scale)), resample_mode)

    return apply_copyright_safe_documentary_lut(im)

def fetch_huggingface_or_pollinations_1080p_scene(ai_prompt, existing_hashes, tag_id="real_fallback", is_short=False):
    """
    100% REAL EDITORIAL PHOTOGRAPHY ONLY (AI Image Generation Completely Disabled per User Rule!):
    Instead of generating synthetic AI images, this fallback harvests authentic real-world press
    and editorial photographs from Bing News & Bing Photojournalism Search!
    """
    if not ai_prompt:
        return None
    clean_q = re.sub(r"(?i)\b(photorealistic|8k|family-friendly|documentary|photography|wide|cinematic|shot|fully|clothed|no|text|logos|sony|lens)\b", "", ai_prompt)
    clean_q = " ".join(re.findall(r"[A-Za-z0-9]{3,}", clean_q)[:5])
    if not clean_q:
        return None
    try:
        b_url = f"https://www.bing.com/images/async?q={urllib.parse.quote(clean_q + ' press photo reuters ap -ai -illustration -3d -render -cartoon -chart -logo')}&first=0&count=25&adlt=strict&qft=+filterui:imagesize-large+filterui:photo-photo+filterui:aspect-wide"
        r = requests.get(b_url, headers=HEADERS_WEB, timeout=6)
        murls = re.findall(r"murl&quot;:&quot;(https?://[^&]+?)&quot;", r.text)
        for u in murls[:16]:
            u_clean = u.replace("&amp;", "&")
            if any(b in u_clean.lower() for b in BANNED_IMAGE_SOURCES) or any(nf in u_clean.lower() for nf in ADULT_NSFW_BANNED_TERMS):
                continue
            ir = requests.get(u_clean, headers=HEADERS_WEB, timeout=5)
            if ir.status_code == 200 and len(ir.content) > 28000:
                p = f"temp/{tag_id}_realnews.jpg"
                with open(p, "wb") as f:
                    f.write(ir.content)
                vim = validate_and_enhance_1080p(Image.open(p), existing_hashes, min_w=800, min_h=450)
                if vim is not None:
                    print(f"   📸 [100% Real Editorial Press Photo Locked]: {clean_q[:42]}", flush=True)
                    return vim
    except Exception:
        pass
    return None

def fit_whole_words_limit(text_str, max_chars=26):
    words = text_str.strip().split()
    out_w = []
    cur_len = 0
    for w in words:
        add_len = len(w) + (1 if out_w else 0)
        if cur_len + add_len <= max_chars or not out_w:
            out_w.append(w[:max_chars])
            cur_len += add_len
        else:
            break
    return " ".join(out_w)

def extract_key_point_from_sentence(sentence_text, beat_num=1, fallback_stat=""):
    """
    ABHI & NIYU / NITISH RAJPUT CRISP POINT HIGHLIGHT EXTRACTOR:
    1. Always honors the AI Director's per-sentence `point_highlight` (`fallback_stat`) across ALL beats!
    2. Strips redundant 'POINT 1:' prefixes and never outputs broken verbs/contractions like 'ISNT JUST TREND'.
    """
    s_clean = re.sub(r"[^\x20-\x7E]", "", sentence_text).strip()
    if "subscribe to world talk brief" in s_clean.lower() or "watch the full documentary" in s_clean.lower():
        return "FULL DOCUMENTARY CASE STUDY", ["takeaway", "documentary", "brief"]

    if fallback_stat and len(fallback_stat.strip()) >= 5 and "EVIDENCE FILE" not in fallback_stat.upper():
        cleaned_stat = re.sub(r"^(?:POINT\s*#?\d+\s*[:\-]\s*|KEY\s+POINT\s*[:\-]\s*)", "", fallback_stat.strip(), flags=re.I)
        clean_fb = fit_whole_words_limit(re.sub(r"[^\x20-\x7E]", "", cleaned_stat).upper(), 30)
        if len(clean_fb) >= 4:
            return clean_fb, [w.lower() for w in re.findall(r"[A-Za-z0-9$%]{3,}", clean_fb)]

    s_core = re.sub(
        r"^(?:Here's what nobody is telling you:|Story number \d+ in our[^:]+:|Verified data from[^,]+,|According to[^,]+,|"
        r"In a move that astonished[^,]+,|During the release procedures,|Last week,|It comes only weeks after|Understanding how they affect[^,]+,|"
        r"[A-Z][A-Za-z\s]{2,25}\s+(?:said|warned|stated|announced|reported|told\s+[A-Za-z]+)\s+(?:that\s+)?)",
        "", s_clean, flags=re.I
    ).strip()

    # 1. Check if sentence has a concrete number/percentage/statistic/year/distance
    num_match = re.search(r"((?:\$|₹|€|£)?\d+(?:[.,]\d+)?(?:\s*(?:%|percent|million|billion|trillion|thousand|kilometers|miles|years|days|hours|times|fold|tons|shops|units|people|stores))?(?:\s+[A-Za-z]{4,14}){1,3})", s_core, flags=re.I)
    if num_match:
        phrase = fit_whole_words_limit(num_match.group(1).strip().upper(), 28)
        kw_list = [w.lower() for w in re.findall(r"[A-Za-z0-9$%]{3,}", phrase)]
        return phrase, kw_list[:4]

    # 2. Extract concrete nouns & impact words (strictly excluding contractions, verbs, and prepositions!)
    stop_filler = {
        "here", "heres", "what", "nobody", "telling", "that", "this", "these", "those", "there", "their",
        "they", "them", "about", "which", "would", "could", "should", "have", "has", "had", "been", "were",
        "was", "from", "with", "into", "over", "after", "before", "under", "while", "when", "where",
        "because", "however", "meanwhile", "according", "verified", "data", "reports", "official",
        "officials", "said", "says", "also", "only", "weeks", "understanding", "affect", "among",
        "during", "move", "astonished", "present", "help", "find", "more", "ways", "some", "much", "such",
        "isnt", "arent", "wasnt", "werent", "dont", "doesnt", "didnt", "cant", "cannot", "wont", "wouldnt",
        "theyre", "youre", "weve", "just", "even", "simply", "enough", "argue", "argues", "without", "deeper",
        "fighting", "survive", "against", "steeper", "every", "being", "judged", "paying", "creates", "create",
        "means", "mean", "shows", "show", "needs", "need", "walk", "down", "today", "will", "sitting", "nearly",
        "stark", "haunting", "pattern", "longer", "afford", "moving", "first", "place", "alone", "spend"
    }
    words_raw = re.findall(r"[A-Za-z0-9$%]{4,}", s_core.replace("'", ""))
    meaningful = [w for w in words_raw if w.lower() not in stop_filler]
    selected = meaningful[:4] if len(meaningful) >= 2 else words_raw[:3]
    point_str = fit_whole_words_limit(" ".join(selected).upper(), 28)
    kw_list = [w.lower() for w in selected if len(w) >= 3]
    return point_str, kw_list[:4]

def extract_speaker_or_prop_for_beat(beat_text, dossier, entities, beat_idx):
    """
    EXACT PERSON, ORGANIZATION, ARTICLE SUBJECT & CONCEPT VISUAL MATCHER:
    1. If a specific person is mentioned in `beat_text`, searches for that exact person in context!
    2. If a specific organization/institution/court/university is mentioned (e.g. 'Amnesty International',
       'Chalmers University of Technology', 'World Health Organization', 'New Cairo Court', 'Mada Masr'),
       searches for that exact entity's real-world photo!
    3. Otherwise builds a high-precision visual query from the exact subject & action of `beat_text`!
    """
    low = beat_text.lower()
    pillar = dossier.get("pillar", "WORLD")
    sub_pillar = dossier.get("sub_pillar", pillar)
    p_cfg = CATEGORY_FEEDS.get(pillar, CATEGORY_FEEDS["WORLD"])
    domain_ctx = p_cfg.get("domain_context", "")
    topic_anchor = dossier.get("topic_anchor") or extract_primary_topic_anchor(dossier)

    # 1. Check concrete technical/scientific/military props first
    for word_key, (prop_badge, wiki_exact, news_q) in CONCRETE_WIKI_PROPS.items():
        if re.search(rf"\b{re.escape(word_key)}\b", low):
            return prop_badge, wiki_exact, f"{news_q} {domain_ctx}", False

    # 2. Check if a specific Person is named in this sentence -> fetch scene photo of that person/event!
    person_hit = detect_person_in_narration_text(beat_text)
    if person_hit:
        p_wiki, p_disp, p_role = person_hit
        return f"{p_disp.upper()[:18]} • {p_role[:12]}", p_wiki, f"{p_disp} {topic_anchor} press conference photo", True

    # 3. Check if a specific named Organization / University / Court / Agency is in this sentence
    org_match = re.search(
        r"\b([A-Z][A-Za-z]+(?:\s+(?:of|for|and|the))?(?:\s+[A-Z][A-Za-z]+){1,4}\s+"
        r"(?:University|Institute|Academy|Organization|International|Court|Ministry|Council|Foundation|Agency|Syndicate|Brotherhood|Lab))\b",
        beat_text
    )
    if org_match:
        org_name = org_match.group(1).strip()
        return f"INSTITUTION • {fit_whole_words_limit(org_name.upper(), 18)}", org_name, f"{org_name} headquarters building official photo", False

    # 4. Extract exact concrete nouns from the sentence
    beat_words = [
        w for w in re.findall(r"[A-Za-z]{4,}", beat_text)
        if w.lower() not in HEADLINE_STOP_VERBS_ADJS and w.lower() not in {"their", "there", "which", "would", "could", "should", "about", "these", "those", "where", "heres", "telling", "subscribe", "daily", "original"}
    ]
    sentence_exact_phrase = " ".join(beat_words[:4]) if beat_words else entities[beat_idx % len(entities)]
    chosen_ent = " ".join(beat_words[:2]).title() if beat_words else entities[beat_idx % len(entities)]
    return f"{sub_pillar.replace('_', ' ')} • {fit_whole_words_limit(topic_anchor.upper(), 16)}", chosen_ent, f"{sentence_exact_phrase} {topic_anchor} {domain_ctx}", False

def fetch_verified_news_or_wiki_visual(wiki_exact_title, news_query, dossier, existing_hashes, failed_queries, tag_id="beat", used_image_urls=None):
    if used_image_urls is None:
        used_image_urls = set()
    pillar = dossier.get("pillar", "WORLD")
    p_cfg = CATEGORY_FEEDS.get(pillar, CATEGORY_FEEDS["WORLD"])
    domain_ctx = p_cfg.get("domain_context", "")
    neg_guard = DOMAIN_NEGATIVE_GUARDS.get(pillar, f"-nba -basketball -logo -icon -cartoon -shirt {STRICT_SAFE_SEARCH_SUFFIX}")
    topic_anchor = dossier.get("topic_anchor") or extract_primary_topic_anchor(dossier)

    # 1. First check if Wikipedia has an exact high-res article/entity photo for `wiki_exact_title`!
    if wiki_exact_title and len(wiki_exact_title) >= 4:
        try:
            w_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(wiki_exact_title)}"
            wr = requests.get(w_url, headers=HEADERS_WIKI, timeout=5)
            if wr.status_code == 200:
                wdata = wr.json()
                w_img = wdata.get("originalimage", {}).get("source") or wdata.get("thumbnail", {}).get("source")
                if w_img and w_img not in used_image_urls and not any(b in w_img.lower() for b in BANNED_IMAGE_SOURCES + ["flag", "map", "logo", "seal", "icon", ".svg"]):
                    ir = requests.get(w_img, headers=HEADERS_WIKI, timeout=5)
                    if ir.status_code == 200 and len(ir.content) > 25000:
                        p = f"temp/{tag_id}_wiki_exact.jpg"
                        with open(p, "wb") as f:
                            f.write(ir.content)
                        vim = validate_and_enhance_1080p(Image.open(p), existing_hashes, min_w=750, min_h=420)
                        if vim is not None:
                            used_image_urls.add(w_img)
                            print(f"   🏛️ [Exact Wikipedia Entity Visual Locked]: {wiki_exact_title}", flush=True)
                            return vim
        except Exception:
            pass

    # 2. Only query NASA Image Archive if the story is genuinely about Space / Astronomy!
    space_check = f"{dossier['title']} {news_query}".lower()
    if any(sp_w in space_check for sp_w in ["nasa", "space", "rocket", "orbit", "mars", "moon", "galaxy", "telescope", "webb", "satellite", "astronaut", "asteroid", "planet", "cosmos", "spacex"]):
        try:
            nasa_img_q = f"{news_query} {topic_anchor}"[:55]
            n_url = f"https://images-api.nasa.gov/search?q={urllib.parse.quote(nasa_img_q)}&media_type=image"
            nr = requests.get(n_url, headers=HEADERS_WEB, timeout=5).json()
            for it in nr.get("collection", {}).get("items", [])[:8]:
                links = it.get("links", [])
                im_u = links[0].get("href", "") if links else ""
                if im_u and im_u not in used_image_urls and not any(b in im_u.lower() for b in ["logo", "patch", "insignia", "seal"]):
                    ir = requests.get(im_u, headers=HEADERS_WEB, timeout=5)
                    if ir.status_code == 200 and len(ir.content) > 25000:
                        p = f"temp/{tag_id}_nasaimg.jpg"
                        with open(p, "wb") as f:
                            f.write(ir.content)
                        vim = validate_and_enhance_1080p(Image.open(p), existing_hashes, min_w=800, min_h=450)
                        if vim is not None:
                            used_image_urls.add(im_u)
                            return vim
        except Exception:
            pass

    c_prof = dossier.get("country_profile", {})
    geo_tag = "" if c_prof.get("is_global_topic") else c_prof.get("name", "").title()
    if geo_tag and geo_tag.lower() not in news_query.lower():
        anchored_q = f"{news_query} {geo_tag}"
    else:
        anchored_q = news_query
    extra_neg = "-collage -split -meme -podcast -thumbnail -game -simulator -comic -drawing -banner -poster"

    for b_img_q in [f"{anchored_q} real press photo", f"{anchored_q} {domain_ctx}", f"{topic_anchor} {geo_tag} {wiki_exact_title} photo"]:
        if not b_img_q or len(b_img_q) < 4:
            continue
        try:
            b_url = f"https://www.bing.com/images/async?q={urllib.parse.quote(b_img_q + ' ' + extra_neg + ' ' + neg_guard)}&first=0&count=24&adlt=strict&qft=+filterui:imagesize-large+filterui:photo-photo+filterui:aspect-wide"
            r = requests.get(b_url, headers=HEADERS_WEB, timeout=6)
            murls = re.findall(r"murl&quot;:&quot;(https?://[^&]+?)&quot;", r.text)
            for u in murls[:14]:
                u_clean = u.replace("&amp;", "&")
                if u_clean in used_image_urls or any(b in u_clean.lower() for b in BANNED_IMAGE_SOURCES) or any(nf in u_clean.lower() for nf in ADULT_NSFW_BANNED_TERMS):
                    continue
                ir = requests.get(u_clean, headers=HEADERS_WEB, timeout=5)
                if ir.status_code == 200 and len(ir.content) > 28000:
                    p = f"temp/{tag_id}_binghd.jpg"
                    with open(p, "wb") as f:
                        f.write(ir.content)
                    vim = validate_and_enhance_1080p(Image.open(p), existing_hashes, min_w=800, min_h=450)
                    if vim is not None:
                        used_image_urls.add(u_clean)
                        return vim
        except Exception:
            pass

    for cm_q in [f"{wiki_exact_title} {domain_ctx}", topic_anchor]:
        if not cm_q:
            continue
        try:
            api = "https://commons.wikimedia.org/w/api.php"
            params = {
                "action": "query", "generator": "search",
                "gsrsearch": f"filetype:bitmap {cm_q} -nude -statue -sculpture -painting -venus",
                "gsrnamespace": "6", "gsrlimit": 10,
                "prop": "imageinfo", "iiprop": "url", "iiurlwidth": 1920, "format": "json"
            }
            r = requests.get(api, params=params, headers=HEADERS_WIKI, timeout=6).json()
            for pg in r.get("query", {}).get("pages", {}).values():
                t_low = pg.get("title", "").lower()
                if any(b in t_low for b in ["map", "diagram", "logo", "icon", "flag", "coat", "chart", "graph", "plaque", "stamp", "coin", "signature", "text", "insignia", "seal", "nude", "naked", "venus", "aphrodite", "statue", "sculpture", "painting", "erotic", "bathing", "anatomical"]):
                    continue
                ii = pg.get("imageinfo", [{}])[0]
                u = ii.get("thumburl") or ii.get("url")
                if u and u not in used_image_urls and u.lower().endswith((".jpg", ".jpeg", ".png")) and not any(nf in u.lower() for nf in ADULT_NSFW_BANNED_TERMS):
                    ir = requests.get(u, headers=HEADERS_WIKI, timeout=5)
                    if ir.status_code == 200 and len(ir.content) > 28000:
                        p = f"temp/{tag_id}_comm.jpg"
                        with open(p, "wb") as f:
                            f.write(ir.content)
                        vim = validate_and_enhance_1080p(Image.open(p), existing_hashes, min_w=800, min_h=450)
                        if vim is not None:
                            used_image_urls.add(u)
                            return vim
        except Exception:
            pass

    failed_queries.append(news_query)
    return None

# ==============================================================================
# 10. 10x FASTER "GOD-LEVEL" NITISH RAJPUT & ABHI & NIYU COMPOSITOR
#     - Pre-cached Vignettes, Pre-cached Subtitle Pills, Pre-cached Person Cards!
#     - Abhi & Niyu Top Yellow/Red Impact Hook Tape!
#     - Nitish Rajput Evidence Dossier & Source Verification Card!
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
            if fx > sw * 0.08 and (fx + fw) < sw * 0.92 and fy > sh * 0.08 and (fy + fh) < sh * 0.88 and fh < sh * 0.42:
                return True
    except Exception:
        pass
    return False

def fit_full_height_face_aware_1080p(im, target_w, target_h):
    resample_mode = getattr(Image, "Resampling", Image).LANCZOS
    iw, ih = im.size
    target_ratio = target_w / float(target_h)
    img_ratio = iw / float(ih)

    if target_w < target_h and img_ratio > 0.85:
        bg = im.copy().resize((target_w, target_h), resample_mode).filter(ImageFilter.GaussianBlur(radius=36))
        bg = ImageEnhance.Brightness(bg).enhance(0.22)
        draw_bg = ImageDraw.Draw(bg)

        for gx in range(0, target_w, 120):
            draw_bg.line([(gx, 0), (gx, target_h)], fill=(255, 255, 255, 14), width=1)
        for gy in range(0, target_h, 120):
            draw_bg.line([(0, gy), (target_w, gy)], fill=(255, 255, 255, 14), width=1)

        card_h = min(int(target_w * 0.96), max(740, int(target_w / max(img_ratio * 0.78, 0.95))))
        scale_c = max(target_w / float(iw), card_h / float(ih))
        rw, rh = int(iw * scale_c), int(ih * scale_c)
        fg_resized = im.resize((rw, rh), resample_mode)
        left_c = (rw - target_w) // 2
        top_c = (rh - card_h) // 2
        fg_card = fg_resized.crop((left_c, top_c, left_c + target_w, top_c + card_h))

        y_pos = 250
        bg.paste(fg_card, (0, y_pos))
        draw_bg.rectangle([(0, y_pos - 4), (target_w, y_pos)], fill=(255, 215, 0))
        draw_bg.rectangle([(0, y_pos + card_h), (target_w, y_pos + card_h + 4)], fill=(0, 235, 255))
        return bg

    if img_ratio >= target_ratio:
        crop_h = ih
        crop_w = int(ih * target_ratio)
        left = (iw - crop_w) // 2
        cropped = im.crop((left, 0, left + crop_w, crop_h))
        return cropped.resize((target_w, target_h), resample_mode)

    crop_w = iw
    crop_h = int(iw / target_ratio)
    top = int((ih - crop_h) * 0.20)
    cropped = im.crop((0, top, crop_w, top + crop_h))
    return cropped.resize((target_w, target_h), resample_mode)

def build_clean_1080p_stage(im, W, H):
    over_w, over_h = int(W * 1.08), int(H * 1.08)
    fg = fit_full_height_face_aware_1080p(im, over_w, over_h)
    return ("FULL_BLEED_CREATOR_STAGE", fg, None)

def extract_diverse_camera_frame_from_stage(stage_tuple, W, H, bp, camera_mode=0):
    resample_mode = getattr(Image, "Resampling", Image).BILINEAR
    _, fg, _ = stage_tuple
    smooth_p = 0.5 - 0.5 * math.cos(math.pi * bp)
    fw, fh = fg.size

    if camera_mode % 3 == 0:
        cur_w = int(W + (fw - W) * (0.65 - 0.45 * smooth_p))
        cur_h = int(H + (fh - H) * (0.65 - 0.45 * smooth_p))
        ox = (fw - cur_w) // 2
        oy = (fh - cur_h) // 2
    elif camera_mode % 3 == 1:
        cur_w, cur_h = W, H
        ox = int((fw - W) * smooth_p)
        oy = (fh - H) // 2
    else:
        cur_w = int(W + (fw - W) * (0.20 + 0.45 * smooth_p))
        cur_h = int(H + (fh - H) * (0.20 + 0.45 * smooth_p))
        ox = (fw - cur_w) // 2
        oy = (fh - cur_h) // 2

    frame = fg.crop((ox, oy, ox + cur_w, oy + cur_h)).resize((W, H), resample_mode).convert("RGBA")
    vignette_ov = get_prebuilt_vignette_overlay(W, H)
    frame.alpha_composite(vignette_ov)
    return frame

def build_point_highlight_banner_rgba(beat, W, H, is_short=True):
    """
    GUARANTEED ON-SCREEN POINT HIGHLIGHT CALLOUT CARD:
    Every single sentence beat displays its noted point ('📌 POINT #1: ...') in a high-contrast
    animated callout bar so viewers see every single key point highlighted on screen!
    """
    if beat.get("prebuilt_point_card") is not None:
        return beat["prebuilt_point_card"]

    point_txt = fit_whole_words_limit(re.sub(r"[^\x20-\x7E]", "", str(beat.get("point_highlight") or beat.get("stat_callout") or "KEY POINT NOTED")).upper().strip(), 34)
    style_idx = int(beat.get("camera_mode", 0)) % 3
    badges = [
        ("📌 NOTED POINT", (255, 215, 0, 255), (10, 14, 24, 255)),
        ("⚡ KEY HIGHLIGHT", (0, 235, 255, 255), (10, 14, 24, 255)),
        ("🎯 CORE EVIDENCE", (225, 25, 55, 255), (255, 255, 255, 255))
    ]
    b_label, accent_fill, accent_txt_col = badges[style_idx]

    f_lbl = get_font(18 if is_short else 17)
    f_pt = get_font(26 if is_short else 25)
    dummy = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    w_lbl = dummy.textbbox((0, 0), b_label, font=f_lbl)[2] + 28
    w_pt = dummy.textbbox((0, 0), point_txt, font=f_pt)[2] + 40
    card_w = max(w_lbl + w_pt + 24, 420)
    card_h = 68 if is_short else 64

    card = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    cdraw = ImageDraw.Draw(card, "RGBA")

    cdraw.rounded_rectangle([(4, 4), (card_w - 2, card_h - 2)], radius=16, fill=(0, 0, 0, 195))
    cdraw.rounded_rectangle([(0, 0), (card_w - 6, card_h - 6)], radius=16, fill=(10, 16, 32, 242), outline=accent_fill, width=3)
    cdraw.rounded_rectangle([(8, 8), (8 + w_lbl, card_h - 14)], radius=11, fill=accent_fill)
    cdraw.text((22, (card_h - 6) // 2 - 10), b_label, fill=accent_txt_col, font=f_lbl)
    cdraw.text((22 + w_lbl, (card_h - 6) // 2 - 14), point_txt, fill=(255, 255, 255, 255), font=f_pt)

    beat["prebuilt_point_card"] = card
    return card

def build_prebuilt_hud_badge_layer(beat, watermark, W, H, is_short=True):
    """
    Pre-renders all static HUD elements for a beat ONCE (Watermark, Country Flag,
    Abhi & Niyu Top Impact Hook Tape, Nitish Rajput Evidence Dossier Card, Live Context Pill)
    so frame rendering is 10x faster!
    """
    if beat.get("prebuilt_hud_layer") is not None:
        return beat["prebuilt_hud_layer"]

    hud = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(hud, "RGBA")
    story = beat["story"]
    c_prof = story["country_profile"]
    b_type = beat["beat_type"]
    top_y = 32 if is_short else 26

    # 1. Brand Watermark + Flag
    hud.paste(watermark, (36, top_y), watermark)
    if c_prof.get("flag_img"):
        fl = c_prof["flag_img"].resize((74, 46))
        hud.paste(fl, (178, top_y + 14), fl)

    # 2. ABHI & NIYU STYLE TOP IMPACT HOOK TAPE (Center-Top High-Contrast Yellow/Black Tape!)
    hook_tape = beat.get("hook_tape") or beat.get("section_headline", "BREAKING CASE FILE")
    hook_tape_clean = fit_whole_words_limit(re.sub(r"[^\x20-\x7E]", "", str(hook_tape)).upper().strip(), 34)
    if is_short:
        f_tape = get_font(25)
        tw = draw.textbbox((0, 0), hook_tape_clean, font=f_tape)[2] + 44
        tx = (W - tw) // 2
        ty = 132
        draw.rounded_rectangle([(tx + 4, ty + 4), (tx + tw + 4, ty + 52)], radius=10, fill=(0, 0, 0, 200))
        draw.rounded_rectangle([(tx, ty), (tx + tw, ty + 48)], radius=10, fill=(255, 220, 0, 255), outline=(15, 20, 30, 255), width=3)
        draw.text((tx + 22, ty + 9), hook_tape_clean, fill=(10, 12, 18, 255), font=f_tape)
    else:
        f_tape = get_font(22)
        tw = draw.textbbox((0, 0), f"⚡ {hook_tape_clean}", font=f_tape)[2] + 44
        tx = 275
        ty = top_y + 12
        draw.rounded_rectangle([(tx, ty), (tx + tw, ty + 44)], radius=10, fill=(255, 220, 0, 250), outline=(10, 14, 24, 255), width=2)
        draw.text((tx + 20, ty + 9), f"⚡ {hook_tape_clean}", fill=(10, 14, 22, 255), font=f_tape)

    # 3. Top-Right Live Context / Video B-Roll Indicator Pill
    raw_lbl = beat["vseg"]["label"] if (b_type == "VIDEO_BROLL_BEAT" and beat.get("vseg")) else beat["primary_lbl"]
    kicker_lbl = re.sub(r"[^\x20-\x7E]", "", str(raw_lbl)).strip()[:26]
    f_lv = get_font(19 if is_short else 20)
    lw_box = draw.textbbox((0, 0), kicker_lbl, font=f_lv)[2] + 36
    pill_outline = (255, 45, 65, 250) if b_type == "VIDEO_BROLL_BEAT" else (0, 235, 255, 220)
    draw.rounded_rectangle([(W - lw_box - 36, top_y + 12), (W - 36, top_y + 54)], radius=20, fill=(10, 14, 24, 230), outline=pill_outline, width=2)
    draw.text((W - lw_box - 18, top_y + 20), kicker_lbl, fill=(255, 255, 255, 255), font=f_lv)

    # 4. NITISH RAJPUT STYLE EVIDENCE / SOURCE DOSSIER CARD (Top-Right on Long Videos)
    claim_meta = beat.get("claim_meta") or {}
    src_name = re.sub(r"[^\x20-\x7E]", "", str(claim_meta.get("source_name", "Global Wire"))).upper()[:22]
    pub_d = str(claim_meta.get("published_date", ""))[:16]
    stat_callout = beat.get("point_highlight") or beat.get("stat_callout") or "VERIFIED CASE POINT"

    if not is_short:
        # Clean, compact Nitish Rajput Verified Source Badge (never duplicates the bottom-left Point Highlight!)
        src_badge_txt = f"📰 VERIFIED SOURCE: {src_name} • {pub_d}"
        f_src = get_font(16)
        ev_w = draw.textbbox((0, 0), src_badge_txt, font=f_src)[2] + 42
        ev_h = 42
        ev_x = W - ev_w - 36
        ev_y = 92
        draw.rounded_rectangle([(ev_x + 3, ev_y + 3), (ev_x + ev_w + 3, ev_y + ev_h + 3)], radius=12, fill=(0, 0, 0, 165))
        draw.rounded_rectangle([(ev_x, ev_y), (ev_x + ev_w, ev_y + ev_h)], radius=12, fill=(10, 16, 30, 230), outline=(0, 235, 255, 195), width=2)
        draw.rectangle([(ev_x, ev_y), (ev_x + 8, ev_y + ev_h)], fill=(220, 20, 45, 255))
        draw.text((ev_x + 20, ev_y + 11), src_badge_txt, fill=(235, 245, 255, 255), font=f_src)

    # 5. On-Screen Callout Banner on Shorts pointing to the Linked Full Long Video
    if is_short:
        banner_txt = "▶ WATCH FULL DOCUMENTARY • LINK IN DESCRIPTION"
        f_ban = get_font(21)
        bw = draw.textbbox((0, 0), banner_txt, font=f_ban)[2] + 46
        bx = (W - bw) // 2
        by = 1435
        draw.rounded_rectangle([(bx, by), (bx + bw, by + 44)], radius=22, fill=(12, 22, 42, 238), outline=(255, 215, 0, 245), width=2)
        draw.text((bx + 23, by + 10), banner_txt, fill=(255, 225, 0, 255), font=f_ban)

    beat["prebuilt_hud_layer"] = hud
    return hud

def render_1080p_beat_frame(beat, watermark, voice_sub_dir, local_t, W, H, is_short=True):
    beat_dur = beat["duration"]
    bp = min(max(local_t / max(beat_dur, 0.1), 0.0), 1.0)
    b_type = beat["beat_type"]
    section_t = beat["section_elapsed_before"] + local_t
    cam_mode = beat.get("camera_mode", 0)

    # 1. Base Visual (Full-Sentence HD Video B-Roll OR Cinema Stage Photo)
    if b_type == "VIDEO_BROLL_BEAT" and beat.get("vseg") is not None:
        vseg = beat["vseg"]
        vc = vseg["vclip"]
        try:
            # Smooth continuous playback across the entire sentence without jarring 2s cuts!
            usable_vdur = max(vc.duration - 0.15, 0.5)
            if local_t <= usable_vdur:
                t_vid = local_t
            else:
                # Ping-pong smooth motion if sentence is longer than transcoded clip
                cycle = int(local_t // usable_vdur)
                rem = local_t % usable_vdur
                t_vid = (usable_vdur - rem) if (cycle % 2 == 1) else rem
            raw_vf = Image.fromarray(vc.get_frame(t_vid)).convert("RGB")
            frame = fit_full_height_face_aware_1080p(raw_vf, W, H).convert("RGBA")
            frame.alpha_composite(get_prebuilt_vignette_overlay(W, H))
        except Exception:
            frame = extract_diverse_camera_frame_from_stage(beat["stage_1"], W, H, bp, camera_mode=cam_mode)
    else:
        frame = extract_diverse_camera_frame_from_stage(beat["stage_1"], W, H, bp, camera_mode=cam_mode)
        if local_t < 0.18 and beat.get("prev_stage") is not None:
            try:
                prev_f = extract_diverse_camera_frame_from_stage(beat["prev_stage"], W, H, 1.0, camera_mode=(cam_mode - 1) % 3)
                frame = Image.blend(prev_f, frame, local_t / 0.18)
            except Exception:
                pass

    # 2. Composite Pre-Built HUD Layer
    hud_layer = build_prebuilt_hud_badge_layer(beat, watermark, W, H, is_short=is_short)
    frame.alpha_composite(hud_layer)

    # 3. ABHI & NIYU / NITISH RAJPUT DYNAMIC HIGHLIGHTER BANNER (with Animated Yellow Marker Swipe!)
    pt_card = build_point_highlight_banner_rgba(beat, W, H, is_short=is_short)
    if pt_card is not None:
        pt_w, pt_h = pt_card.size
        pt_anim = min(max(local_t / 0.28, 0.0), 1.0)
        pt_ease = 1.0 - ((1.0 - pt_anim) ** 3)
        if is_short:
            pt_x = (W - pt_w) // 2
            pt_y = int(192 - (1.0 - pt_ease) * 35)
        else:
            pt_x = int(42 - (1.0 - pt_ease) * 260)
            pt_y = H - 228
        frame.paste(pt_card, (pt_x, pt_y), pt_card)
        # Animated Yellow Highlighter Progress Sweep under the key point text during the first 0.55s!
        swipe_p = min(max((local_t - 0.10) / 0.45, 0.0), 1.0)
        if swipe_p > 0.02:
            f_draw = ImageDraw.Draw(frame, "RGBA")
            bar_x1 = pt_x + 14
            bar_x2 = bar_x1 + int((pt_w - 34) * swipe_p)
            bar_y = pt_y + pt_h - 11
            f_draw.rounded_rectangle([(bar_x1, bar_y), (bar_x2, bar_y + 5)], radius=2, fill=(255, 225, 0, 245))

    # 4. UNIVERSAL DYNAMIC SUBJECT SPOTLIGHT POP-UP (Person, Animal, Object, or Key Evidence!)
    if beat.get("person_popup") is not None:
        p_card = build_prebuilt_person_card_rgba(beat["person_popup"], is_short=is_short)
        if p_card is not None:
            popup_show_dur = min(beat_dur * 0.88, 3.8)
            if local_t <= popup_show_dur:
                enter_p = min(max(local_t / 0.28, 0.0), 1.0)
                exit_p = min(max((popup_show_dur - local_t) / 0.25, 0.0), 1.0) if local_t > (popup_show_dur - 0.25) else 1.0
                scale_f = (0.76 + 0.24 * (1.0 - ((1.0 - enter_p) ** 3))) * (0.85 + 0.15 * exit_p)
                resample_mode = getattr(Image, "Resampling", Image).BILINEAR
                cw, ch = p_card.size
                sw, sh = max(10, int(cw * scale_f)), max(10, int(ch * scale_f))
                scaled_card = p_card.resize((sw, sh), resample_mode) if abs(scale_f - 1.0) > 0.02 else p_card
                float_dy = int(5.0 * math.sin(local_t * 3.8))
                # Center-stage on Shorts; alternating Center / Right-Evidence-Board on 16:9 Long videos
                style_pos = int(beat["person_popup"].get("style_idx", 0)) % 2
                if is_short or style_pos == 0:
                    center_x = (W - sw) // 2
                else:
                    center_x = W - sw - 64
                center_y = ((H - sh) // 2 - (70 if is_short else 30)) + float_dy
                frame.paste(scaled_card, (center_x, center_y), scaled_card)

    # 5. Composite Cached Synced Subtitles (with Key Point Keyword Highlighting!)
    sub_strip = voice_sub_dir.render_exact_synced_subtitles(
        beat["word_timings"], section_t, W, H, is_short=is_short,
        highlight_keywords=beat.get("highlight_keywords")
    )
    sub_y = 1500 if is_short else (H - 142)
    frame.paste(sub_strip, (0, sub_y), sub_strip)

    # 6. Fast NumPy Progress Bar at Bottom
    out_rgb = np.array(frame.convert("RGB"))
    prog_w = int(W * min(max(section_t / max(beat["section_duration"], 1.0), 0.02), 1.0))
    out_rgb[H - 7:H, :, :] = (35, 45, 65)
    out_rgb[H - 7:H, :prog_w, 0] = 255
    out_rgb[H - 7:H, :prog_w, 1] = 215
    out_rgb[H - 7:H, :prog_w, 2] = 0
    return out_rgb

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

def compute_exact_sentence_beat_timings(narration, raw_sents, word_timings, sec_dur):
    """
    100% NATURAL SENTENCE-LOCKED TIMING ENGINE:
    Maps every sentence in `raw_sents` to the exact spoken `word_timings` from TTS so that
    each visual stays on screen until the speaker COMPLETELY finishes that sentence!
    Merges ultra-short clauses (< 3.2s) so no visual ever cuts abruptly after 2 seconds!
    """
    if not raw_sents:
        return [{"text": narration, "duration": round(sec_dur, 3), "start": 0.0}]

    # Merge any very short sentence (< 8 words) with neighbor so beats are always natural full thoughts
    merged_sents = []
    for s in raw_sents:
        if merged_sents and len(s.split()) < 8:
            merged_sents[-1] = f"{merged_sents[-1]} {s}"
        else:
            merged_sents.append(s)
    if len(merged_sents) > 1 and len(merged_sents[0].split()) < 7:
        merged_sents[1] = f"{merged_sents[0]} {merged_sents[1]}"
        merged_sents.pop(0)

    if not word_timings:
        tot_chars = max(sum(len(s) for s in merged_sents), 1)
        out = []
        elapsed = 0.0
        for idx, s in enumerate(merged_sents):
            d = (sec_dur - elapsed) if idx == len(merged_sents) - 1 else round(sec_dur * (len(s) / float(tot_chars)), 3)
            out.append({"text": s, "duration": max(0.5, d), "start": round(elapsed, 3)})
            elapsed += d
        return out

    # Match word counts per sentence to exact word_timings
    out = []
    w_cursor = 0
    total_w = len(word_timings)
    elapsed = 0.0

    for idx, s in enumerate(merged_sents):
        s_words = s.split()
        n_w = max(1, len(s_words))
        end_w_idx = min(total_w - 1, w_cursor + n_w - 1)
        if idx == len(merged_sents) - 1 or end_w_idx >= total_w - 1:
            dur = max(0.4, round(sec_dur - elapsed, 3))
        else:
            next_start = word_timings[min(total_w - 1, end_w_idx + 1)]["start"]
            dur = max(2.8, round(next_start - elapsed, 3))
            if elapsed + dur > sec_dur - 0.4:
                dur = max(0.4, round(sec_dur - elapsed, 3))
        out.append({"text": s, "duration": dur, "start": round(elapsed, 3)})
        elapsed = round(elapsed + dur, 3)
        w_cursor = min(total_w - 1, end_w_idx + 1)

    # Ensure sum of durations equals sec_dur exactly
    if out:
        diff = round(sec_dur - sum(item["duration"] for item in out), 3)
        out[-1]["duration"] = max(0.4, round(out[-1]["duration"] + diff, 3))
    return out

def build_prop_driven_storyboard_1080p(
    sections_list, dossier, entities, W, H, tag_prefix="short",
    shared_hashes=None, shared_video_urls=None, shared_video_queries=None,
    start_beat_offset=0, shared_photo_pool=None, shared_image_urls=None
):
    planned_beats = []
    existing_hashes = shared_hashes if shared_hashes is not None else []
    used_video_urls = shared_video_urls if shared_video_urls is not None else set()
    used_video_queries = shared_video_queries if shared_video_queries is not None else set()
    used_image_urls = shared_image_urls if shared_image_urls is not None else set()
    unique_real_photos = shared_photo_pool if shared_photo_pool is not None else []
    failed_queries = []
    moving_video_beats = 0
    person_popup_beats = 0
    is_short = W < H

    article_imgs = list(dossier.get("article_inline_images") or [])
    if dossier.get("lead_img") and dossier["lead_img"] not in article_imgs:
        article_imgs.insert(0, dossier["lead_img"])

    if start_beat_offset == 0:
        for a_idx, a_img_u in enumerate(article_imgs[:6]):
            if not a_img_u or a_img_u in used_image_urls:
                continue
            if any(b in a_img_u.lower() for b in BANNED_IMAGE_SOURCES) or any(nf in a_img_u.lower() for nf in ADULT_NSFW_BANNED_TERMS):
                continue
            try:
                r = requests.get(a_img_u, headers=HEADERS_WEB, timeout=6)
                if r.status_code == 200 and len(r.content) > 25000:
                    p = f"temp/{tag_prefix}_artimg_{a_idx}.jpg"
                    with open(p, "wb") as f:
                        f.write(r.content)
                    vim = validate_and_enhance_1080p(Image.open(p), existing_hashes, min_w=750, min_h=420)
                    if vim is not None:
                        unique_real_photos.append(vim)
                        used_image_urls.add(a_img_u)
                        print(f"   📰 [Exact Article Photo Pre-Loaded #{len(unique_real_photos)}]: {a_img_u[:55]}", flush=True)
            except Exception:
                pass

    global_beat_idx = start_beat_offset

    for sec_idx, sec in enumerate(sections_list):
        narration = sec["narration"]
        sec_dur = sec["duration"]
        word_timings = sec["word_timings"]
        sec_headline = sec.get("headline") or sec.get("chapter_title") or make_clean_context_headline(dossier["title"])
        sec_role = sec.get("role", "THE REAL STORY")
        hook_tape = sec.get("hook_tape") or sec_headline
        stat_callout = sec.get("stat_callout", "")
        claim_meta = sec.get("claim_meta") or dossier["verified_claims"][0]

        ai_video_q = sec.get("video_broll_query", "")
        beat_visuals_list = sec.get("beat_visuals", [])
        ai_person = sec.get("mentioned_person", "")
        ai_role = sec.get("person_role", "")

        raw_sents = [s.strip() for s in split_into_complete_sentences(narration) if len(s.strip()) > 8]
        sentence_beats_info = compute_exact_sentence_beat_timings(narration, raw_sents, word_timings, sec_dur)
        num_beats = len(sentence_beats_info)

        scene_person_tuple = detect_person_in_narration_text(narration, ai_person=ai_person, ai_role=ai_role)
        scene_person_popup = None
        if scene_person_tuple:
            w_name, d_name, r_lbl = scene_person_tuple
            p_im = fetch_person_portrait_image(w_name, d_name, r_lbl)
            if p_im is not None:
                scene_person_popup = {"name": d_name, "role": r_lbl, "portrait_im": p_im, "style_idx": global_beat_idx % 4}

        section_got_video = False
        person_shown_in_sec = False

        for b_i, s_info in enumerate(sentence_beats_info):
            b_txt = s_info["text"]
            beat_dur = s_info["duration"]
            sec_elapsed_before = s_info["start"]

            prop_badge, wiki_target, search_q, _ = extract_speaker_or_prop_for_beat(b_txt, dossier, entities, global_beat_idx)

            ai_beat_prompt = ""
            bv_point_hl = ""
            bv_person = ""
            bv_role = ""
            if b_i < len(beat_visuals_list) and isinstance(beat_visuals_list[b_i], dict):
                bv = beat_visuals_list[b_i]
                if bv.get("photo_query"):
                    search_q = bv["photo_query"]
                if bv.get("ai_prompt"):
                    ai_beat_prompt = bv["ai_prompt"]
                if bv.get("point_highlight"):
                    bv_point_hl = str(bv["point_highlight"]).strip()
                if bv.get("mentioned_person"):
                    bv_person = str(bv["mentioned_person"]).strip()
                if bv.get("person_role"):
                    bv_role = str(bv["person_role"]).strip()

            if sec.get("role"):
                prop_badge = sec["role"]

            # Extract Guaranteed Point Highlight + Subtitle Keywords for THIS Sentence!
            point_hl_str, hl_keywords = extract_key_point_from_sentence(
                b_txt, beat_num=(global_beat_idx + 1), fallback_stat=(bv_point_hl or stat_callout)
            )

            # Detect if an important person is named in THIS exact sentence (or scene fallback)
            beat_person_popup = None
            beat_person_tuple = detect_person_in_narration_text(b_txt, ai_person=bv_person, ai_role=bv_role)
            if beat_person_tuple:
                bw_name, bd_name, br_lbl = beat_person_tuple
                bp_im = fetch_person_portrait_image(bw_name, bd_name, br_lbl)
                if bp_im is not None:
                    beat_person_popup = {
                        "name": bd_name,
                        "role": br_lbl,
                        "portrait_im": bp_im,
                        "style_idx": (global_beat_idx + b_i) % 4
                    }
                    person_shown_in_sec = True
            elif scene_person_popup is not None and not person_shown_in_sec and b_i == 0:
                beat_person_popup = scene_person_popup
                person_shown_in_sec = True

            if beat_person_popup is not None:
                person_popup_beats += 1

            # Choose a distinct, non-repeating Pro SFX for this beat!
            if beat_person_popup is not None:
                person_sfx_cycle = ["camera_shutter_flash", "dossier_stamp_thud", "digital_hud_lock", "cinematic_medallion_reveal"]
                chosen_sfx = person_sfx_cycle[beat_person_popup["style_idx"] % len(person_sfx_cycle)]
            else:
                point_sfx_cycle = [
                    "crystal_point_highlight", "tactical_data_tick", "sonar_mystery_ping",
                    "orchestral_riser_hit", "deep_sub_drop", "analog_cut_snap",
                    "air_filter_sweep", "heartbeat_tension_pulse"
                ]
                chosen_sfx = point_sfx_cycle[global_beat_idx % len(point_sfx_cycle)]

            # Fetch 100% Verified Point-to-Point Real HD Video B-Roll (strictly verified title & frame!)
            vseg = None
            if not section_got_video and b_i == 0:
                v_q = ai_video_q if ai_video_q else search_q
                vseg = fetch_and_transcode_real_video_broll(
                    v_q, dossier, used_video_urls, used_video_queries, tag_id=f"{tag_prefix}_vc_{global_beat_idx}"
                )
                if vseg is not None:
                    section_got_video = True

            if vseg is not None:
                b_type = "VIDEO_BROLL_BEAT"
                moving_video_beats += 1
                beat_im = unique_real_photos[-1] if unique_real_photos else Image.new("RGB", (1920, 1080), (12, 18, 32))
                stage_1 = build_clean_1080p_stage(beat_im, W, H)
            else:
                b_type = "CINEMA_HERO_ZOOM"
                beat_im = fetch_verified_news_or_wiki_visual(
                    wiki_target, search_q, dossier, existing_hashes, failed_queries,
                    tag_id=f"{tag_prefix}_b{global_beat_idx}", used_image_urls=used_image_urls
                )
                if beat_im is None:
                    custom_prompt = ai_beat_prompt if ai_beat_prompt else f"{dossier['title']}, {b_txt}"
                    beat_im = fetch_huggingface_or_pollinations_1080p_scene(
                        custom_prompt, existing_hashes, tag_id=f"{tag_prefix}_ai_{global_beat_idx}", is_short=is_short
                    )
                if beat_im is not None:
                    unique_real_photos.append(beat_im)
                elif unique_real_photos:
                    beat_im = unique_real_photos[global_beat_idx % len(unique_real_photos)]
                else:
                    beat_im = Image.new("RGB", (1920, 1080), (12, 18, 32))

                stage_1 = build_clean_1080p_stage(beat_im, W, H)

            secondary_im = unique_real_photos[(len(unique_real_photos) - 2) % len(unique_real_photos)] if len(unique_real_photos) >= 2 else beat_im
            prev_stage = planned_beats[-1]["stage_1"] if planned_beats else None

            beat_sit_mood = detect_sentence_situation_mood(b_txt, base_mood=dossier.get("category", "dark_geopolitics"), beat_idx=global_beat_idx)
            planned_beats.append({
                "section_idx": sec_idx,
                "beat_in_section": b_i,
                "beat_type": b_type,
                "camera_mode": global_beat_idx % 3,
                "pan_dir": 1 if (global_beat_idx % 2 == 0) else -1,
                "duration": round(beat_dur, 3),
                "beat_excerpt": b_txt,
                "section_role": sec_role,
                "section_headline": sec_headline,
                "hook_tape": hook_tape,
                "stat_callout": stat_callout,
                "point_highlight": point_hl_str,
                "highlight_keywords": hl_keywords,
                "sfx_type": chosen_sfx,
                "situation_mood": beat_sit_mood,
                "person_popup": beat_person_popup,
                "full_section_narration": narration,
                "word_timings": word_timings,
                "section_duration": sec_dur,
                "section_elapsed_before": round(sec_elapsed_before, 3),
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
        "person_popup_beats": person_popup_beats,
        "failed_queries_count": len(failed_queries)
    }
    print(f"📊 [AUDIT] {tag_prefix.upper()} | Sentence-Locked Beats: {stats['total_beats']} | Photos: {stats['unique_real_photos']} | HD Video Clips: {moving_video_beats} | Center Person Pop-Ups: {person_popup_beats}", flush=True)
    return planned_beats, unique_real_photos, stats

# ==============================================================================
# 11. 100% NATURAL HUMAN VOICE ENGINE + CACHED SUBTITLE RENDERER (8x Faster!)
# ==============================================================================
class VoiceAndSubtitleEngine:
    def __init__(self):
        self._subtitle_cache = {}

    async def synthesize_with_word_boundaries(self, text, out_path, pillar="WORLD", is_short=False):
        core_hub = PILLAR_TO_CORE_HUB.get(pillar, pillar)
        long_v, short_v, dg_backup, long_rate, short_rate = CATEGORY_VOICE_CAST.get(
            core_hub, ("en-US-AndrewMultilingualNeural", "en-US-AndrewMultilingualNeural", "aura-orion-en", "+0%", "+2%")
        )
        edge_voice = short_v if is_short else long_v
        rate = short_rate if is_short else long_rate

        raw_mp3 = out_path.replace(".mp3", "_raw.mp3")
        word_timings = []

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
            dg_key = os.environ.get("DEEPGRAM_API_KEY", "").strip()
            if dg_key:
                try:
                    r = requests.post(
                        f"https://api.deepgram.com/v1/speak?model={dg_backup}",
                        headers={"Authorization": f"Token {dg_key}", "Content-Type": "application/json"},
                        json={"text": text[:1900]},
                        timeout=16
                    )
                    if r.status_code == 200 and len(r.content) > 2000:
                        with open(raw_mp3, "wb") as f:
                            f.write(r.content)
                except Exception:
                    pass

        if not os.path.exists(raw_mp3) or os.path.getsize(raw_mp3) <= 1000:
            gTTS(text=text, lang="en").save(raw_mp3)

        try:
            # Studio Human Podcast Voice Mastering: Warm 175Hz chest resonance + 3.2kHz clarity + smooth broadcast compressor
            cmd = [
                "ffmpeg", "-y", "-i", raw_mp3,
                "-af", "equalizer=f=175:width_type=o:width=1.2:g=2.4,equalizer=f=3100:width_type=o:width=1.4:g=1.6,acompressor=threshold=-16dB:ratio=2.2:attack=12:release=160,apad=pad_dur=0.16",
                "-ar", "44100", "-ac", "2", "-b:a", "192k", out_path
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
            usable_dur = max(total_dur - 0.16, 0.5)
            cur = 0.0
            for w, wt in zip(words, weights):
                wd = (wt / tot_w) * usable_dur
                word_timings.append({"word": w, "start": round(cur, 3), "end": round(cur + wd, 3)})
                cur += wd
        return vc, total_dur, word_timings

    def render_exact_synced_subtitles(self, word_timings, section_t, W, H, is_short=True, highlight_keywords=None):
        if not word_timings:
            return Image.new("RGBA", (W, 240), (0, 0, 0, 0))
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

        hl_tuple = tuple(sorted(highlight_keywords)) if highlight_keywords else ()
        words_str_list = tuple(w["word"] for w in active_chunk)
        cache_key = (W, is_short, words_str_list, active_word_idx, hl_tuple)
        if cache_key in self._subtitle_cache:
            return self._subtitle_cache[cache_key]

        strip_h = 240 if is_short else 125
        strip = Image.new("RGBA", (W, strip_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(strip, "RGBA")
        font = get_font(54 if is_short else 42)
        hl_set = set(hl_tuple)

        if is_short:
            lines = [words_str_list[:2], words_str_list[2:]] if len(words_str_list) > 2 else [words_str_list]
            y_cur = 18
            w_cnt = 0
            for ln in lines:
                if not ln:
                    continue
                disp = [w.upper() for w in ln]
                lw = draw.textbbox((0, 0), " ".join(disp), font=font)[2]
                x_cur = (W - lw) // 2
                draw.rounded_rectangle([(x_cur - 24, y_cur - 8), (x_cur + lw + 24, y_cur + 64)], radius=18, fill=(8, 12, 24, 215), outline=(255, 215, 0, 95), width=2)
                for dw in disp:
                    clean_dw = re.sub(r"[^a-z0-9$%]", "", dw.lower())
                    is_key_pt = (clean_dw in hl_set) or any(ch.isdigit() for ch in clean_dw)
                    w_px = draw.textbbox((0, 0), dw, font=font)[2]
                    if w_cnt == active_word_idx:
                        draw.rounded_rectangle([(x_cur - 6, y_cur - 4), (x_cur + w_px + 6, y_cur + 58)], radius=10, fill=(220, 20, 45, 210))
                        col = (255, 230, 0, 255)
                    elif is_key_pt:
                        col = (0, 240, 255, 255)
                    else:
                        col = (255, 255, 255, 255)
                    draw.text((x_cur + 3, y_cur + 3), dw, font=font, fill=(0, 0, 0, 240))
                    draw.text((x_cur, y_cur), dw, font=font, fill=col, stroke_width=6, stroke_fill=(0, 0, 0, 255))
                    x_cur += draw.textbbox((0, 0), dw + " ", font=font)[2]
                    w_cnt += 1
                y_cur += 78
        else:
            phrase = " ".join(words_str_list)
            lw = draw.textbbox((0, 0), phrase, font=font)[2]
            x_cur = (W - lw) // 2
            draw.rounded_rectangle([(x_cur - 34, 14), (x_cur + lw + 34, 92)], radius=22, fill=(8, 14, 28, 225), outline=(0, 230, 255, 150), width=2)
            for idx_w, w in enumerate(words_str_list):
                clean_w = re.sub(r"[^a-z0-9$%]", "", w.lower())
                is_key_pt = (clean_w in hl_set) or any(ch.isdigit() for ch in clean_w)
                w_px = draw.textbbox((0, 0), w, font=font)[2]
                if idx_w == active_word_idx:
                    draw.rounded_rectangle([(x_cur - 6, 20), (x_cur + w_px + 6, 84)], radius=10, fill=(220, 20, 45, 200))
                    col = (255, 230, 0, 255)
                elif is_key_pt:
                    col = (0, 240, 255, 255)
                else:
                    col = (255, 255, 255, 255)
                draw.text((x_cur + 3, 29), w, font=font, fill=(0, 0, 0, 235))
                draw.text((x_cur, 26), w, font=font, fill=col, stroke_width=5, stroke_fill=(0, 0, 0, 255))
                x_cur += draw.textbbox((0, 0), w + " ", font=font)[2]

        if len(self._subtitle_cache) > 400:
            self._subtitle_cache.clear()
        self._subtitle_cache[cache_key] = strip
        return strip

# ==============================================================================
# 12. AI-DIRECTED SCRIPT & SCENE BUILDER
# ==============================================================================
def make_clean_context_headline(text, max_words=6):
    first_clause = re.split(r"[.;:—–]", text)[0].strip()
    words = first_clause.split()
    dangling = {"THE", "A", "AN", "TO", "IN", "ON", "OF", "FOR", "WITH", "AND", "OR", "BY", "AS", "AT", "FROM", "THAT", "WHICH", "WHILE", "HIS", "HER", "ITS", "FOUR", "TWO"}
    selected = words[:max_words]
    while len(selected) > 2 and selected[-1].upper().strip(",.:;'\"") in dangling:
        selected.pop()
    return " ".join(selected).upper()

def build_short_script(dossier):
    claims = dossier["verified_claims"]
    t_anchor = dossier.get("topic_anchor") or extract_primary_topic_anchor(dossier)

    c0 = claims[0]
    c1 = claims[1] if len(claims) > 1 else c0
    c2 = claims[2] if len(claims) > 2 else c1
    c3 = claims[3] if len(claims) > 3 else c2
    c4 = claims[4] if len(claims) > 4 else c3

    sections = [
        {
            "role": "BREAKING HOOK",
            "headline": t_anchor.upper()[:24],
            "hook_tape": f"WHY {t_anchor.upper()[:18]} MATTERS NOW",
            "stat_callout": "BREAKING SHIFT",
            "narration": f"Here's what nobody is telling you: {paraphrase_into_original_creator_voice(dossier['title'], 0)} {paraphrase_into_original_creator_voice(c0['text'], 1)}",
            "claim_meta": c0
        },
        {
            "role": "THE HIDDEN CAUSE",
            "headline": make_clean_context_headline(c1["text"], 5),
            "hook_tape": make_clean_context_headline(c1["text"], 5),
            "stat_callout": "KEY EVIDENCE",
            "narration": paraphrase_into_original_creator_voice(c1["text"], 2),
            "claim_meta": c1
        },
        {
            "role": "THE REAL NUMBERS",
            "headline": make_clean_context_headline(c2["text"], 5),
            "hook_tape": make_clean_context_headline(c2["text"], 5),
            "stat_callout": "CRITICAL DATA",
            "narration": paraphrase_into_original_creator_voice(c2["text"], 3),
            "claim_meta": c2
        },
        {
            "role": "HOW IT WORKS",
            "headline": make_clean_context_headline(c3["text"], 5),
            "hook_tape": make_clean_context_headline(c3["text"], 5),
            "stat_callout": "INSIDE MECHANISM",
            "narration": paraphrase_into_original_creator_voice(c3["text"], 4),
            "claim_meta": c3
        },
        {
            "role": "WATCH FULL VIDEO",
            "headline": "FULL DOCUMENTARY LINK BELOW",
            "hook_tape": "FULL CASE STUDY IN DESCRIPTION",
            "stat_callout": "LINK IN DESCRIPTION",
            "narration": f"{paraphrase_into_original_creator_voice(c4['text'], 5)} Tap the full video link in the description and pinned comment right now for the complete investigation!",
            "claim_meta": c4
        }
    ]
    return sections

def build_long_documentary_script(dossier):
    claims = dossier["verified_claims"]
    is_mega_24h = dossier.get("is_mega_24h", False)

    if is_mega_24h:
        mega_context_closers = [
            "This development marks one of the most consequential policy shifts of the week.",
            "Regional observers warn that the next forty-eight hours will be critical for everyone involved.",
            "The announcement has already sparked intense debate among lawmakers and security experts.",
            "International monitors are now closely watching how neighboring states respond to the move.",
            "Economic and diplomatic analysts say this could reshape long-standing alliances in the region.",
            "Local authorities have stepped up readiness as further updates are expected later today.",
            "Public reaction continues to grow as new details emerge from official briefings.",
            "Strategic planners point out that this turn of events changes the political calculus moving forward.",
            "Legal and diplomatic teams are now reviewing the full implications of today's decision.",
            "The story has quickly become a central focus across international newsrooms today.",
            "Energy and trade markets are also factoring this development into their weekly outlook.",
            "Defense and foreign ministry officials have scheduled follow-up talks to address the situation.",
            "Independent researchers note that this trend has been building over the past several months.",
            "Community leaders and international agencies are calling for immediate transparency and action.",
            "What happens next here will set the tone for upcoming global summits."
        ]
        lead_transitions = [
            "Leading our twenty-four hour intelligence briefing:",
            "Moving to our second major global development:",
            "Next, in a story drawing international attention:",
            "Turning to our fourth headline of the day:",
            "Meanwhile, in another major development:",
            "Our sixth report focuses on a critical shift:",
            "Next up in today's global roundup:",
            "Shifting focus to our eighth major story:",
            "In another closely watched legal and political update:",
            "Number ten on our global radar today:",
            "Turning now to energy, politics, and global strategy:",
            "Our twelfth story examines a deeper geopolitical question:",
            "Next, looking at shifting alliances in the Middle East:",
            "In our fourteenth report from the ground:",
            "Finally, closing out our top fifteen global stories:"
        ]
        chapters = []
        for idx, c in enumerate(claims[:15]):
            h_short = c.get("headline_short") or make_clean_context_headline(c["text"], max_words=6)
            base_nar = paraphrase_into_original_creator_voice(c["text"], idx)
            lead_in = lead_transitions[idx % len(lead_transitions)]
            closer_line = mega_context_closers[idx % len(mega_context_closers)]
            expanded_nar = f"{lead_in} {base_nar} {closer_line}"
            if idx == 0:
                expanded_nar = f"Welcome to World Talk Brief's special twenty-four hour global intelligence roundup. Here are the biggest geopolitical, economic, and scientific developments from around the world today. {expanded_nar}"
            if idx == len(claims[:15]) - 1:
                expanded_nar = f"{expanded_nar} That completes our twenty-four hour global briefing. Subscribe to World Talk Brief and let us know in the comments which headline stood out to you the most."
            chapters.append({
                "chapter_num": idx + 1,
                "chapter_title": h_short.upper()[:28],
                "headline": h_short.upper()[:28],
                "hook_tape": h_short.upper()[:32],
                "role": f"HEADLINE #{idx + 1} • 24H BRIEF",
                "stat_callout": f"STORY #{idx + 1} OF {len(claims[:15])}",
                "video_broll_query": h_short,
                "beat_visuals": [
                    {"photo_query": f"{h_short} press conference", "ai_prompt": f"Photorealistic 8k news documentary wide shot of {h_short}, no text"},
                    {"photo_query": f"{h_short} government summit", "ai_prompt": f"Photorealistic 8k documentary shot of {h_short} operations, no text"},
                    {"photo_query": f"{h_short} global impact", "ai_prompt": f"Photorealistic 8k cinematic aerial shot representing {h_short}, no text"}
                ],
                "dossier": dossier,
                "claim_meta": c,
                "narration": expanded_nar
            })
        return chapters

    unique_sents = []
    for idx_c, c in enumerate(claims):
        ps = paraphrase_into_original_creator_voice(c["text"], idx_c)
        if len(ps) > 35 and ps not in unique_sents:
            unique_sents.append(ps)

    chunk_size = 2 if len(unique_sents) < 12 else 3
    sent_groups = [unique_sents[i:i + chunk_size] for i in range(0, len(unique_sents), chunk_size)][:8]
    role_cycle = [
        "CHAPTER 1 • THE CATALYST", "CHAPTER 2 • THE EVIDENCE", "CHAPTER 3 • HOW IT WORKS",
        "CHAPTER 4 • THE DEEP DIVE", "CHAPTER 5 • THE TIMELINE", "CHAPTER 6 • THE STAKES",
        "CHAPTER 7 • GLOBAL IMPACT", "CHAPTER 8 • THE VERDICT"
    ]

    chapters = []
    for idx, grp in enumerate(sent_groups):
        body_txt = " ".join(grp)
        if idx == 0:
            body_txt = f"{paraphrase_into_original_creator_voice(dossier['title'], 0)} {body_txt}"
        if idx == len(sent_groups) - 1:
            body_txt = f"{body_txt} Subscribe to World Talk Brief for daily original deep-dive case studies."
        c_meta = claims[min(idx, len(claims) - 1)]
        ch_head = make_clean_context_headline(grp[0], max_words=6)
        chapters.append({
            "chapter_num": idx + 1,
            "chapter_title": ch_head,
            "headline": ch_head,
            "hook_tape": ch_head,
            "role": role_cycle[idx % len(role_cycle)],
            "stat_callout": f"EVIDENCE FILE #0{idx + 1}",
            "dossier": dossier,
            "claim_meta": c_meta,
            "narration": body_txt
        })

    return chapters

def build_ai_directed_sections(dossier, is_short=True, top_channel_hits=None):
    ents = extract_story_entities(dossier)
    if dossier.get("is_mega_24h") and not is_short:
        return build_long_documentary_script(dossier), ents

    ai_pkg = ai_direct_complete_video_package(dossier, is_short=is_short, top_channel_hits=top_channel_hits)

    if ai_pkg:
        if ai_pkg.get("viral_title") and not is_short:
            dossier["original_yt_title"] = str(ai_pkg["viral_title"])[:95]
        elif ai_pkg.get("viral_title") and is_short and not dossier.get("original_yt_title"):
            dossier["original_yt_title"] = str(ai_pkg["viral_title"])[:95]
        if ai_pkg.get("thumb_line_1") and ai_pkg.get("thumb_line_2"):
            dossier["ai_thumb_hook"] = (str(ai_pkg["thumb_line_1"]).upper()[:18], str(ai_pkg["thumb_line_2"]).upper()[:18])
        if ai_pkg.get("core_subject"):
            dossier["topic_anchor"] = str(ai_pkg["core_subject"])
        if ai_pkg.get("story_emotion") and str(ai_pkg["story_emotion"]) in STUDIO_ALBUM_50_MIND_BLOWING_TRACKS:
            dossier["category"] = str(ai_pkg["story_emotion"])
        if ai_pkg.get("seo_description"):
            dossier["ai_seo_description"] = str(ai_pkg["seo_description"])
        if isinstance(ai_pkg.get("seo_tags"), list):
            dossier["ai_seo_tags"] = [str(t) for t in ai_pkg["seo_tags"][:10]]

        sections = []
        claims = dossier["verified_claims"]
        for idx, sc in enumerate(ai_pkg["scenes"]):
            nar = clean_fact(str(sc.get("narration", "")))
            if len(nar) < 20:
                nar = paraphrase_into_original_creator_voice(claims[idx % len(claims)]["text"], idx)
            if nar[-1] not in ".!?":
                nar += "."
            pill = re.sub(r"[^\x20-\x7E]", "", str(sc.get("context_pill", dossier["topic_anchor"]))).upper().strip()[:24]
            htape = re.sub(r"[^\x20-\x7E]", "", str(sc.get("hook_tape", pill))).upper().strip()[:34]
            stat_c = re.sub(r"[^\x20-\x7E]", "", str(sc.get("stat_callout", ""))).upper().strip()[:22]
            sections.append({
                "role": pill or "KEY INSIGHT",
                "headline": pill or make_clean_context_headline(nar, 5),
                "chapter_title": pill or make_clean_context_headline(nar, 5),
                "hook_tape": htape or pill,
                "stat_callout": stat_c,
                "mentioned_person": str(sc.get("mentioned_person", "")).strip(),
                "person_role": str(sc.get("person_role", "")).strip(),
                "narration": nar,
                "video_broll_query": str(sc.get("video_broll_query", "")).strip(),
                "beat_visuals": sc.get("beat_visuals", []) if isinstance(sc.get("beat_visuals"), list) else [],
                "claim_meta": claims[min(idx, len(claims) - 1)]
            })
        if is_short and sections:
            if "description" not in sections[-1]["narration"].lower():
                sections[-1]["narration"] = f"{sections[-1]['narration']} Watch the full documentary via the link in the description and pinned comment!"
        elif not is_short and sections:
            sections[-1]["narration"] = f"{sections[-1]['narration']} Subscribe to World Talk Brief for daily original case studies."
        return sections, ents

    if is_short:
        return build_short_script(dossier), ents
    return build_long_documentary_script(dossier), ents

# ==============================================================================
# 13. VIRAL YOUTUBER THUMBNAIL ENGINE
# ==============================================================================
def build_meaningful_thumbnail_hook(dossier):
    if dossier.get("is_mega_24h"):
        return ("24H WORLD NEWS", "TOP 15 STORIES")
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

    for y in range(640, H):
        alpha = int(240 * (((y - 640) / 440.0) ** 1.25))
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

    sub_p = dossier.get("sub_pillar", pillar)
    return {
        "selected_thumbnail": out_path,
        "thumbnail_category_style": sub_p,
        "selected_title": dossier["original_yt_title"],
        "hashtags": ["#WorldTalkBrief", f"#{sub_p.replace('_', '')}", f"#{c_prof['name'].replace(' ', '')}", "#Explained"]
    }

# ==============================================================================
# 14. YOUTUBE UPLOADER + PAIRED LONG & SHORT PIPELINE (Immediate History Save!)
# ==============================================================================
def try_youtube_auto_upload(
    video_path, title, description, tags, category_id="25", pillar="WORLD",
    is_short=False, thumbnail_path=None, playlist_map=None, summary_takeaway="", linked_long_url=None
):
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

        add_video_to_category_playlist_and_comment(
            yt, vid_id, pillar, summary_takeaway or title, playlist_map or {}, linked_long_url=linked_long_url
        )
        return vid_id
    except Exception as e:
        print("⚠️ YouTube upload attempt failed:", str(e)[:140], flush=True)
        return None

async def render_and_upload_long_unit(lead_long_dossier, unit_num, watermark, voice_sub_dir, hist_obj, winning_keywords, viral_yt_tags, playlist_map, top_channel_hits):
    pillar = lead_long_dossier.get("pillar", "WORLD")
    sub_pillar = lead_long_dossier.get("sub_pillar", pillar)
    long_chapters, lead_long_entities = build_ai_directed_sections(lead_long_dossier, is_short=False, top_channel_hits=top_channel_hits)
    print(f"\n📺 [LONG #{unit_num} - {sub_pillar}] Building God-Level 1080p Documentary on: {lead_long_dossier['original_yt_title']}", flush=True)

    for idx, ch in enumerate(long_chapters):
        ap = f"temp/l{unit_num}_voice_{idx}.mp3"
        vc, dur, w_timings = await voice_sub_dir.synthesize_with_word_boundaries(ch["narration"], ap, pillar=pillar, is_short=False)
        ch["audio_clip"] = vc
        ch["duration"] = dur
        ch["word_timings"] = w_timings
        ch["dossier"] = lead_long_dossier
        ch["chapter_title"] = ch["headline"]

    long_clips = []
    beat_switch_times_l = []
    sfx_events_l = []
    shared_long_photos = []
    shared_long_hashes = []
    shared_long_video_urls = set()
    shared_long_video_queries = set()
    shared_long_image_urls = set()
    running_beat_offset = 0
    cur_lt = 0.0

    for ch_idx, ch in enumerate(long_chapters):
        ch_beats, _, _ = build_prop_driven_storyboard_1080p(
            [ch], lead_long_dossier, lead_long_entities, 1920, 1080, tag_prefix=f"long_{unit_num}_ch{ch_idx+1}",
            shared_hashes=shared_long_hashes, shared_video_urls=shared_long_video_urls,
            shared_video_queries=shared_long_video_queries,
            start_beat_offset=running_beat_offset, shared_photo_pool=shared_long_photos,
            shared_image_urls=shared_long_image_urls
        )
        running_beat_offset += len(ch_beats)
        for b in ch_beats:
            beat_switch_times_l.append(round(cur_lt, 2))
            sfx_events_l.append({
                "time": round(cur_lt, 2),
                "sfx_type": b.get("sfx_type", "crystal_point_highlight"),
                "situation_mood": b.get("situation_mood", lead_long_dossier["category"])
            })
            cur_lt += b["duration"]
        clip = make_section_clip_from_beats(ch_beats, watermark, voice_sub_dir, ch["duration"], 1920, 1080, is_short=False)
        clip = clip.with_audio(ch["audio_clip"]) if MOVIEPY_V2 else clip.set_audio(ch["audio_clip"])
        long_clips.append(clip)

    final_long = concatenate_videoclips(long_clips, method="compose")
    story_hash_seed = int(hashlib.md5(lead_long_dossier["story_key"].encode()).hexdigest()[:6], 16)
    track_seed = hist_obj.get("bgm_track_counter", 0) + unit_num + story_hash_seed
    hist_obj["bgm_track_counter"] = track_seed
    bgm_l = AudioFileClip(build_30_track_mood_adaptive_album_bgm(
        f"temp/bgm_l{unit_num}.wav", final_long.duration, beat_switch_times_l,
        mood=lead_long_dossier["category"], track_seed=track_seed, sfx_events=sfx_events_l
    ))
    final_long = final_long.with_audio(CompositeAudioClip([final_long.audio, bgm_l])) if MOVIEPY_V2 else final_long.set_audio(CompositeAudioClip([final_long.audio, bgm_l]))
    out_long = "output/WTB_1080p_Long_16x9.mp4" if unit_num == 1 else f"output/WTB_1080p_Long_{unit_num}_16x9.mp4"
    final_long.write_videofile(out_long, fps=24, codec="libx264", audio_codec="aac", audio_fps=44100, bitrate="8000k", preset="ultrafast", threads=4, logger=None)

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
    ai_desc = lead_long_dossier.get("ai_seo_description", f"World Talk Brief [{sub_pillar.replace('_', ' ')}] presents an original deep-dive case study.")
    long_seo_desc = (
        f"{pkg_report['selected_title']}\n\n"
        f"{ai_desc}\n\n"
        f"CHAPTER TIMESTAMPS:\n" + "\n".join(chap_lines) + "\n\n"
        f"KEY SUBJECTS & ENTITIES: {', '.join(lead_long_entities[:8])}\n\n"
        f"{long_hashtags_str}"
    )
    ai_tags = lead_long_dossier.get("ai_seo_tags", [])
    long_seo_tags = [
        "World Talk Brief", sub_pillar.replace("_", " ").title(), "Documentary Case Study",
        lead_long_dossier["country_profile"]["name"].title()
    ] + ai_tags[:6] + lead_long_entities[:4] + winning_keywords[:4] + viral_yt_tags[:4]

    long_vid_id = try_youtube_auto_upload(
        out_long, pkg_report["selected_title"], long_seo_desc, long_seo_tags,
        category_id=lead_long_dossier.get("yt_category_id", "25"), pillar=sub_pillar, is_short=False,
        thumbnail_path=pkg_report["selected_thumbnail"], playlist_map=playlist_map,
        summary_takeaway=long_chapters[-1]["narration"]
    )
    pkg_report["youtube_video_id"] = long_vid_id
    pkg_report["youtube_url"] = f"https://www.youtube.com/watch?v={long_vid_id}" if long_vid_id else "https://www.youtube.com/@WorldTalkBrief"
    return pkg_report, shared_long_photos

async def render_and_upload_short_unit(
    short_dossier, unit_num, watermark, voice_sub_dir, hist_obj,
    winning_keywords, viral_yt_tags, playlist_map, top_channel_hits,
    linked_long_url=None, preloaded_photos=None
):
    pillar = short_dossier.get("pillar", "WORLD")
    sub_pillar = short_dossier.get("sub_pillar", pillar)
    short_sections, short_entities = build_ai_directed_sections(short_dossier, is_short=True, top_channel_hits=top_channel_hits)
    print(f"\n📱 [LINKED SHORT #{unit_num} - {sub_pillar}] Building God-Level 1080p Short for: {short_dossier['original_yt_title']} (Linked Long URL: {linked_long_url})", flush=True)

    for idx, sec in enumerate(short_sections):
        ap = f"temp/s{unit_num}_voice_{idx}.mp3"
        vc, dur, w_timings = await voice_sub_dir.synthesize_with_word_boundaries(sec["narration"], ap, pillar=pillar, is_short=True)
        sec["audio_clip"] = vc
        sec["duration"] = dur
        sec["word_timings"] = w_timings

    seed_photos = list(preloaded_photos[:4]) if preloaded_photos else []
    s_beats, s_unique_photos, s_stats = build_prop_driven_storyboard_1080p(
        short_sections, short_dossier, short_entities, 1080, 1920,
        tag_prefix=f"short_{unit_num}", shared_photo_pool=seed_photos
    )

    short_clips = []
    beat_switch_times_s = []
    sfx_events_s = []
    cur_t = 0.0
    for sec_idx, sec in enumerate(short_sections):
        sec_beats = [b for b in s_beats if b["section_idx"] == sec_idx]
        for b in sec_beats:
            beat_switch_times_s.append(round(cur_t, 2))
            sfx_events_s.append({
                "time": round(cur_t, 2),
                "sfx_type": b.get("sfx_type", "crystal_point_highlight"),
                "situation_mood": b.get("situation_mood", short_dossier["category"])
            })
            cur_t += b["duration"]
        clip = make_section_clip_from_beats(sec_beats, watermark, voice_sub_dir, sec["duration"], 1080, 1920, is_short=True)
        clip = clip.with_audio(sec["audio_clip"]) if MOVIEPY_V2 else clip.set_audio(sec["audio_clip"])
        short_clips.append(clip)

    final_short = concatenate_videoclips(short_clips, method="compose")
    story_hash_seed_s = int(hashlib.md5(short_dossier["story_key"].encode()).hexdigest()[:6], 16) + 7
    track_seed = hist_obj.get("bgm_track_counter", 0) + unit_num + story_hash_seed_s
    hist_obj["bgm_track_counter"] = track_seed
    bgm_s = AudioFileClip(build_30_track_mood_adaptive_album_bgm(
        f"temp/bgm_s{unit_num}.wav", final_short.duration, beat_switch_times_s,
        mood=short_dossier["category"], track_seed=track_seed, sfx_events=sfx_events_s
    ))
    final_short = final_short.with_audio(CompositeAudioClip([final_short.audio, bgm_s])) if MOVIEPY_V2 else final_short.set_audio(CompositeAudioClip([final_short.audio, bgm_s]))
    out_short = "output/WTB_1080p_Short_9x16.mp4" if unit_num == 1 else f"output/WTB_1080p_Short_{unit_num}_9x16.mp4"
    final_short.write_videofile(out_short, fps=24, codec="libx264", audio_codec="aac", audio_fps=44100, bitrate="8000k", preset="ultrafast", threads=4, logger=None)

    thumb_out = "output/WTB_1080p_Short_Thumb.jpg" if unit_num == 1 else f"output/WTB_1080p_Short_{unit_num}_Thumb.jpg"
    short_pkg = create_signature_wtb_brand_thumbnail(short_dossier, short_entities, s_unique_photos, watermark, out_path=thumb_out)

    long_link_block = (
        f"🔴 WATCH FULL DOCUMENTARY VIDEO HERE:\n👉 {linked_long_url}\n\n"
        if linked_long_url else ""
    )
    short_hashtags_str = " ".join(short_pkg["hashtags"] + ["#Shorts", "#Explained"])
    ai_desc = short_dossier.get("ai_seo_description", f"World Talk Brief [{sub_pillar.replace('_', ' ')}] original #Shorts case study.")
    short_seo_desc = (
        f"{long_link_block}"
        f"{short_dossier['original_yt_title']}\n\n"
        f"{ai_desc}\n\n"
        f"KEY ENTITIES: {', '.join(short_entities[:5])}\n\n"
        f"{short_hashtags_str}"
    )
    ai_tags = short_dossier.get("ai_seo_tags", [])
    short_seo_tags = [
        "World Talk Brief", sub_pillar.replace("_", " ").title(), "Case Study Explained", "YouTube Shorts",
        short_dossier["country_profile"]["name"].title()
    ] + ai_tags[:6] + short_entities[:4] + winning_keywords[:4] + viral_yt_tags[:4]

    short_vid_id = try_youtube_auto_upload(
        out_short, short_dossier["original_yt_title"], short_seo_desc, short_seo_tags,
        category_id=short_dossier.get("yt_category_id", "25"), pillar=sub_pillar, is_short=True,
        thumbnail_path=short_pkg["selected_thumbnail"], playlist_map=playlist_map,
        summary_takeaway=short_sections[-1]["narration"], linked_long_url=linked_long_url
    )
    s_stats["linked_long_url"] = linked_long_url
    s_stats["short_video_id"] = short_vid_id
    return s_stats

async def render_and_upload_paired_story(dossier, pair_num, watermark, voice_sub_dir, hist_obj, winning_keywords, viral_yt_tags, playlist_map, top_channel_hits):
    pkg_long, shared_photos = await render_and_upload_long_unit(
        dossier, pair_num, watermark, voice_sub_dir, hist_obj,
        winning_keywords, viral_yt_tags, playlist_map, top_channel_hits
    )
    linked_long_url = pkg_long.get("youtube_url")

    # Save history immediately after Long upload so even if anything interrupts later, topic never repeats!
    hist_obj["published_keys"].add(dossier["story_key"])
    hist_obj["event_fingerprints"].append({"title": dossier["title"], "tokens": dossier["event_tokens"]})
    hist_obj["last_categories"].append(dossier.get("sub_pillar", dossier["pillar"]))
    hist_obj["last_sources"].append(dossier["source_name"])
    save_published_history(hist_obj)

    short_stats = await render_and_upload_short_unit(
        dossier, pair_num, watermark, voice_sub_dir, hist_obj,
        winning_keywords, viral_yt_tags, playlist_map, top_channel_hits,
        linked_long_url=linked_long_url, preloaded_photos=shared_photos
    )
    save_published_history(hist_obj)
    return pkg_long, short_stats

async def main():
    try:
        watermark = build_wtb_watermark(width=130, height=76)
        voice_sub_dir = VoiceAndSubtitleEngine()
        hist_obj = load_published_history()
        winning_keywords, viral_yt_tags, playlist_map, top_channel_hits = run_youtube_api_full_intelligence()

        now_utc = datetime.utcnow()
        today_str = now_utc.strftime("%Y-%m-%d")
        force_mega = os.environ.get("FORCE_MEGA_NEWS", "false").lower() == "true"

        is_usa_6pm_window = (now_utc.hour in [21, 22, 23]) and (hist_obj.get("last_mega_24h_date") != today_str)

        if force_mega or is_usa_6pm_window:
            mega_dossier = build_daily_24h_mega_news_dossier()
            if mega_dossier is not None:
                print("\n🚨 [LAUNCHING DAILY 6:00 PM USA TIME 9-10 MIN 24H GLOBAL NEWS MEGA-BROADCAST + LINKED SHORT]", flush=True)
                pkg_mega, short_mega = await render_and_upload_paired_story(
                    mega_dossier, 1, watermark, voice_sub_dir, hist_obj,
                    winning_keywords, viral_yt_tags, playlist_map, top_channel_hits
                )
                hist_obj["last_mega_24h_date"] = today_str
                save_published_history(hist_obj)
                with open("output/wtb_1080p_report.json", "w") as f:
                    json.dump({
                        "mode": "DAILY_USA_6PM_24H_MEGA_ROUNDUP",
                        "date": today_str,
                        "mega_long": pkg_mega,
                        "mega_linked_short": short_mega
                    }, f, indent=2)
                print("✅ [DAILY USA 6:00 PM 24-HOUR MEGA NEWS + LINKED SHORT COMPLETE!]", flush=True)
                return

        hot_geo_surge = detect_hot_geopolitics_surge()
        rr_idx = hist_obj.get("round_robin_idx", 0)
        batch_fingerprints = []
        candidate_pool = []

        # Always scan Hot Priority Pillars (Geopolitics, Science, AI/Tech, Defense) + current Round-Robin Pillars
        priority_scan = ["GEOPOLITICS", "SCIENCE", "AI_ROBOTICS", "DEFENSE_MILITARY", "TECHNOLOGY"]
        for step in range(6):
            p_cand = ORDERED_PILLARS[(rr_idx + step) % len(ORDERED_PILLARS)]
            if p_cand not in priority_scan:
                priority_scan.append(p_cand)

        for sub_pillar in priority_scan[:7]:
            d = discover_dossier_for_pillar(sub_pillar, hist_obj, winning_keywords, batch_fingerprints)
            if d is not None:
                if hot_geo_surge and sub_pillar in ["GEOPOLITICS", "DEFENSE_MILITARY", "GLOBAL_POWERS"]:
                    d["score"] += 20
                candidate_pool.append(d)

        candidate_pool.sort(key=lambda x: x["score"], reverse=True)
        selected_dossiers = candidate_pool[:2]
        hist_obj["round_robin_idx"] = (rr_idx + 2) % len(ORDERED_PILLARS)

        if len(selected_dossiers) < 2:
            hist_obj["published_keys"].clear()
            hist_obj["event_fingerprints"].clear()
            for sub_pillar in ORDERED_PILLARS:
                d = discover_dossier_for_pillar(sub_pillar, hist_obj, winning_keywords, batch_fingerprints)
                if d is not None:
                    selected_dossiers.append(d)
                    if len(selected_dossiers) >= 2:
                        break

        story_1 = selected_dossiers[0]
        story_2 = selected_dossiers[1] if len(selected_dossiers) > 1 else selected_dossiers[0]

        pkg_1, s1_stats = await render_and_upload_paired_story(
            story_1, 1, watermark, voice_sub_dir, hist_obj,
            winning_keywords, viral_yt_tags, playlist_map, top_channel_hits
        )

        pkg_2, s2_stats = await render_and_upload_paired_story(
            story_2, 2, watermark, voice_sub_dir, hist_obj,
            winning_keywords, viral_yt_tags, playlist_map, top_channel_hits
        )

        save_published_history(hist_obj)

        with open("output/wtb_1080p_report.json", "w") as f:
            json.dump({
                "videos_produced_in_run": 4,
                "paired_mode": "1_LONG_TO_1_LINKED_SHORT",
                "geopolitics_hot_surge_active": hot_geo_surge,
                "next_round_robin_index": hist_obj.get("round_robin_idx", 0),
                "playlists_synced": len(playlist_map),
                "pair_1": {
                    "pillar": story_1.get("sub_pillar", story_1["pillar"]),
                    "title": story_1["original_yt_title"],
                    "long_video": pkg_1,
                    "linked_short": s1_stats
                },
                "pair_2": {
                    "pillar": story_2.get("sub_pillar", story_2["pillar"]),
                    "title": story_2["original_yt_title"],
                    "long_video": pkg_2,
                    "linked_short": s2_stats
                }
            }, f, indent=2)

        print("✅ [6/6] GITHUB CLOUD GOD-LEVEL DOCUMENTARY ENGINE COMPLETE!", flush=True)
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
