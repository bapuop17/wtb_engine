"""V92 Real Event Video & News Photo Harvester (YouTube News Clips via yt-dlp + Web News Photos via DDGS + Wikimedia + Pexels)."""
import html
import io
import os
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlparse
from PIL import Image
from .common import StudioError, digest, download, request, run_ff, save_json
from .world_atlas import lookup_gazetteer

BAD_IMG_DOMAINS = (
    "shutterstock.com", "gettyimages.com", "alamy.com", "istockphoto.com",
    "dreamstime.com", "123rf.com", "depositphotos.com", "vecteezy.com",
    "stock.adobe.com", "pinimg.com", "tiktok.com", "facebook.com", "instagram.com",
)


def clean(text):
    return html.unescape(re.sub(r"<[^>]+>", " ", str(text)))


def license_allowed(name, url=""):
    name = name.lower().strip()
    if any(x in name for x in ("-nc", "-nd", "noncommercial", "no derivatives", "fair use", "all rights")):
        return False
    return bool(
        name in {"cc0", "cc0 1.0", "public domain", "pexels license", "pd-us", "pd-usgov", "cc-by", "cc-by-sa", "editorial news"}
        or re.fullmatch(r"cc by(?:-sa)? [1-4]\.0", name)
        or name.startswith("public domain")
    )


def anchored(candidate, phrases):
    text = re.sub(r"[^\w]+", " ", candidate.get("caption", "").lower())
    return any(re.sub(r"[^\w]+", " ", p.lower()).strip() in text for p in phrases if len(p.strip()) >= 3)


def youtube_event_clips(query, work_dir, max_clips=3):
    """Fetches real event/news footage clips from YouTube using yt-dlp and trims a clean 12s 1080p HD segment."""
    yt_dlp_bin = shutil.which("yt-dlp")
    if not yt_dlp_bin:
        return []
    clean_q = re.sub(r"[^\w\s-]", " ", str(query or "")).strip()
    if not clean_q:
        return []
    search_q = f"ytsearch5:{clean_q} news footage"
    results = []
    try:
        proc = subprocess.run(
            [
                yt_dlp_bin, "--flat-playlist", "--dump-json", "--no-warnings",
                "--match-filter", "duration >= 20 & duration <= 600 & !is_live",
                search_q,
            ],
            capture_output=True, text=True, timeout=25,
        )
        if proc.returncode != 0:
            return []
        entries = []
        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                import json as _json
                entries.append(_json.loads(line))
            except Exception:
                continue
        for entry in entries[:max_clips]:
            vid = entry.get("id") or ""
            title = entry.get("title") or clean_q
            if not vid or "#shorts" in title.lower():
                continue
            url = f"https://www.youtube.com/watch?v={vid}"
            uploader = entry.get("channel") or entry.get("uploader") or "News Broadcast"
            out_raw = Path(work_dir) / f"yt_{vid}.mp4"
            out_clean = Path(work_dir) / f"yt_{vid}_clean.mp4"
            if not out_clean.exists():
                try:
                    dl = subprocess.run(
                        [
                            yt_dlp_bin, "--no-warnings", "--no-playlist",
                            "-f", "bestvideo[height<=1080][height>=480][ext=mp4]/best[height<=1080][ext=mp4]/best",
                            "--download-sections", "*00:08-00:22",
                            "--force-keyframes-at-cuts",
                            "-o", str(out_raw),
                            url,
                        ],
                        capture_output=True, text=True, timeout=45,
                    )
                    if dl.returncode != 0 or not out_raw.exists() or out_raw.stat().st_size < 50_000:
                        out_raw.unlink(missing_ok=True)
                        continue
                    # Crop out bottom TV news ticker (bottom 12%) & top corner bug, normalize to 1920x1080 24fps silent mp4
                    run_ff(
                        [
                            "-i", str(out_raw), "-an", "-t", "12",
                            "-vf", "crop=iw:ih*0.84:0:ih*0.04,scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=24",
                            "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p",
                            str(out_clean),
                        ],
                        timeout=60,
                    )
                    out_raw.unlink(missing_ok=True)
                except Exception:
                    out_raw.unlink(missing_ok=True)
                    out_clean.unlink(missing_ok=True)
                    continue
            if out_clean.exists() and out_clean.stat().st_size > 50_000:
                results.append({
                    "provider": "Broadcast News Clip",
                    "kind": "footage",
                    "url": url,
                    "page_url": url,
                    "path": str(out_clean),
                    "caption": f"{title} ({uploader})",
                    "creator": uploader,
                    "license": "Editorial News",
                    "license_url": url,
                    "date": "recent",
                    "label": "REAL EVENT FOOTAGE",
                })
    except Exception:
        pass
    return results


def ddgs_news_photos(query, max_results=10):
    """Fetches real, up-to-date event and news photographs from the web via DuckDuckGo Images."""
    results = []
    try:
        from ddgs import DDGS
        items = DDGS(timeout=15).images(str(query), max_results=max_results, safesearch="moderate")
        for item in items or []:
            img_url = item.get("image") or ""
            page_url = item.get("url") or img_url
            title = str(item.get("title") or query).strip()
            w = int(item.get("width") or 0)
            h = int(item.get("height") or 0)
            if not img_url.startswith("http"):
                continue
            dom = (urlparse(img_url).hostname or "").lower()
            if any(bad in dom for bad in BAD_IMG_DOMAINS):
                continue
            if w and h and (w < 720 or h < 400 or (w / max(1, h)) < 1.15):
                continue
            results.append({
                "provider": "News Photo Archive",
                "kind": "photo",
                "url": img_url,
                "page_url": page_url,
                "caption": title,
                "creator": urlparse(page_url).hostname or "News Agency",
                "license": "Editorial News",
                "license_url": page_url,
                "date": "recent",
                "label": "EVENT PHOTO",
            })
    except Exception:
        pass
    return results


def commons(query, kind):
    suffix = " filetype:video" if kind == "footage" else " filetype:bitmap"
    data = request(
        "GET",
        "https://commons.wikimedia.org/w/api.php",
        params={
            "action": "query", "format": "json", "generator": "search", "gsrsearch": query + suffix,
            "gsrnamespace": 6, "gsrlimit": 12, "prop": "imageinfo",
            "iiprop": "url|size|extmetadata|mime", "iiurlwidth": 1920,
        },
        headers={"User-Agent": "WorldTalkBriefStudio/3.0 (https://github.com/bapuop17/wtb_engine)"},
    ).json()
    results = []
    for page in data.get("query", {}).get("pages", {}).values():
        if not page.get("imageinfo"):
            continue
        info = page["imageinfo"][0]
        ext = info.get("extmetadata", {})

        def field(k):
            return clean(ext.get(k, {}).get("value", ""))

        is_video = info.get("mime", "").startswith("video/")
        if is_video != (kind == "footage"):
            continue
        if not license_allowed(field("LicenseShortName"), field("LicenseUrl")):
            continue
        if info.get("width", 0) < 960 or info.get("height", 0) < 540:
            continue
        results.append({
            "provider": "Wikimedia Commons",
            "kind": kind,
            "url": info.get("url") if is_video else info.get("thumburl", info.get("url")),
            "page_url": info.get("descriptionurl", ""),
            "caption": page["title"] + " " + field("ImageDescription"),
            "creator": field("Artist") or "Wikimedia Commons",
            "license": field("LicenseShortName") or "CC0",
            "license_url": field("LicenseUrl"),
            "date": field("DateTimeOriginal"),
            "label": "ARCHIVE / CONTEXT",
        })
    return results


def pexels(query, kind="footage"):
    key = os.getenv("PEXELS_API_KEY")
    if not key:
        return []
    if kind == "photo":
        data = request(
            "GET", "https://api.pexels.com/v1/search",
            headers={"Authorization": key}, params={"query": query, "per_page": 8, "orientation": "landscape"},
        ).json()
        results = []
        for item in data.get("photos", []):
            src = item.get("src", {}).get("large2x") or item.get("src", {}).get("original")
            if not src or (item.get("width") or 0) < 1200:
                continue
            results.append({
                "provider": "Pexels", "kind": "photo", "url": src, "page_url": item.get("url", ""),
                "caption": item.get("alt") or unquote(urlparse(item.get("url", "")).path).replace("-", " "),
                "creator": item.get("photographer", "Pexels contributor"),
                "license": "Pexels License", "license_url": "https://www.pexels.com/license/",
                "date": "unknown", "label": "STOCK / ILLUSTRATION",
            })
        return results
    data = request(
        "GET", "https://api.pexels.com/v1/videos/search",
        headers={"Authorization": key}, params={"query": query, "per_page": 8, "orientation": "landscape"},
    ).json()
    results = []
    for item in data.get("videos", []):
        variants = [
            v for v in item.get("video_files", [])
            if v.get("file_type") == "video/mp4" and (v.get("width") or 0) >= 1280 and (v.get("height") or 0) >= 720
        ]
        if not variants:
            continue
        variants.sort(key=lambda v: abs(v["width"] - 1920))
        results.append({
            "provider": "Pexels", "kind": "footage", "url": variants[0]["link"], "page_url": item["url"],
            "caption": unquote(urlparse(item["url"]).path).replace("-", " "),
            "creator": item.get("user", {}).get("name", "Pexels contributor"),
            "license": "Pexels License", "license_url": "https://www.pexels.com/license/",
            "date": "unknown", "label": "STOCK / ILLUSTRATION",
        })
    return results


class Media:
    def __init__(self, cfg, brain, directory):
        self.cfg, self.brain, self.dir = cfg, brain, Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.uses, self.hashes, self.ledger, self.cache = {}, {}, [], {}

    def find(self, beat):
        v = beat["visual"]
        kind = v["kind"]
        query = str(v.get("query") or v.get("headline") or "").strip()
        must_inc = v.get("must_include") or []
        key = (query.lower(), kind)

        if key not in self.cache:
            found = []
            if kind == "footage":
                # 1. REAL EVENT VIDEO FOOTAGE FIRST (YouTube news clips via yt-dlp)
                found.extend(youtube_event_clips(query, self.dir, max_clips=3))
                # 2. Pexels & Wikimedia Commons video fallback
                for prov in (pexels, commons):
                    if len(found) >= 4:
                        break
                    try:
                        found.extend(prov(query, "footage"))
                    except Exception:
                        continue
            else:
                # 1. REAL EVENT NEWS PHOTOS FIRST (DuckDuckGo Images)
                found.extend(ddgs_news_photos(query, max_results=10))
                # 2. Wikimedia Commons & Pexels photo backup
                for prov in (commons, pexels):
                    if len(found) >= 8:
                        break
                    try:
                        found.extend(prov(query, "photo"))
                    except Exception:
                        continue
            self.cache[key] = found

        candidates = [a for a in self.cache[key] if self.uses.get(a["url"], 0) < self.cfg.get("max_same_asset_uses", 2)]
        if not candidates:
            return None

        # Prefer anchored candidates, then rank best match
        anc = [a for a in candidates if anchored(a, must_inc)]
        pool = anc if anc else candidates

        # Try top 3 candidates until one downloads cleanly and passes resolution/duplicate check
        for asset_raw in pool[:4]:
            asset = dict(asset_raw)
            try:
                if asset.get("path") and Path(asset["path"]).exists():
                    path = Path(asset["path"])
                else:
                    suffix = ".mp4" if asset["kind"] == "footage" else ".jpg"
                    path = self.dir / (digest(asset["url"]) + suffix)
                    if not path.exists():
                        download(asset["url"], path)

                if asset["kind"] == "footage":
                    thumb = path.with_suffix(".jpg")
                    if not thumb.exists():
                        run_ff(["-ss", "1", "-i", path, "-frames:v", "1", "-vf", "scale=960:-2", thumb], 90)
                    image = Image.open(thumb).convert("RGB")
                else:
                    with Image.open(path) as opened:
                        image = opened.convert("RGB")
                    if image.width < 720 or image.height < 400:
                        continue
                    image.save(path, quality=94)

                gray = image.resize((16, 16)).convert("L")
                px = list(gray.getdata())
                mean = sum(px) / len(px)
                phash = sum((int(p >= mean) << i) for i, p in enumerate(px))
                if any((phash ^ h).bit_count() < 6 and n >= self.cfg.get("max_same_asset_uses", 2) for h, n in self.hashes.items()):
                    continue

                asset.update(
                    path=str(path),
                    beat_id=beat["id"],
                    selection_reason=f"Matched event query: {query}",
                    changes="cropped/scaled to 1920x1080 broadcast frame",
                )
                self.uses[asset["url"]] = self.uses.get(asset["url"], 0) + 1
                self.hashes[phash] = self.hashes.get(phash, 0) + 1
                self.ledger.append(asset)
                return asset
            except Exception:
                continue
        return None

    def save(self, path):
        save_json(path, self.ledger)


def resolve_places(names):
    resolved = []
    for name in names:
        found = None
        gz = lookup_gazetteer(name)
        if gz:
            found = gz
        else:
            try:
                result = request(
                    "GET", "https://en.wikipedia.org/w/api.php",
                    params={"action": "query", "format": "json", "titles": name, "redirects": 1, "prop": "coordinates", "colimit": 1},
                    headers={"User-Agent": "WorldTalkBriefStudio/3.0"},
                ).json()
                for page in result.get("query", {}).get("pages", {}).values():
                    coords = page.get("coordinates", [])
                    if coords and coords[0].get("globe", "earth") == "earth":
                        c = coords[0]
                        found = {
                            "name": page["title"], "lat": c["lat"], "lon": c["lon"],
                            "country": "", "source": "https://en.wikipedia.org/?curid=" + str(page["pageid"]),
                        }
                        break
            except Exception:
                pass
        if found:
            resolved.append(found)
    if len(resolved) != len(names):
        raise StudioError("Map coordinates unresolved; no guessed map pins")
    return resolved
