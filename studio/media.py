"""Licensed context media, with per-beat relevance decisions, multi-source discovery, and an audit ledger."""
import html
import io
import os
import re
from pathlib import Path
from urllib.parse import unquote, urlparse
from PIL import Image
from .common import StudioError, digest, download, request, run_ff, save_json
from .world_atlas import lookup_gazetteer


def clean(text):
    return html.unescape(re.sub(r"<[^>]+>", " ", str(text)))


def license_allowed(name, url=""):
    name = name.lower().strip()
    if any(x in name for x in ("-nc", "-nd", "noncommercial", "no derivatives", "fair use", "all rights")):
        return False
    return bool(
        name in {"cc0", "cc0 1.0", "public domain", "pexels license", "pd-us", "pd-usgov", "cc-by", "cc-by-sa"}
        or re.fullmatch(r"cc by(?:-sa)? [1-4]\.0", name)
        or name.startswith("public domain")
    )


def anchored(candidate, phrases):
    text = re.sub(r"[^\w]+", " ", candidate.get("caption", "").lower())
    return any(re.sub(r"[^\w]+", " ", p.lower()).strip() in text for p in phrases if len(p.strip()) >= 3)


def commons(query, kind):
    suffix = " filetype:video" if kind == "footage" else " filetype:bitmap"
    data = request(
        "GET",
        "https://commons.wikimedia.org/w/api.php",
        params={
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": query + suffix,
            "gsrnamespace": 6,
            "gsrlimit": 14,
            "prop": "imageinfo",
            "iiprop": "url|size|extmetadata|mime",
            "iiurlwidth": 1920,
        },
        headers={"User-Agent": "WorldTalkBriefStudio/2.0 (https://github.com/bapuop17/wtb_engine)"},
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
        if "by" in field("LicenseShortName").lower() and not field("Artist"):
            continue
        if info.get("width", 0) < 1280 or info.get("height", 0) < 720:
            continue
        results.append(
            {
                "provider": "Wikimedia Commons",
                "kind": kind,
                "url": info.get("url") if is_video else info.get("thumburl", info.get("url")),
                "page_url": info.get("descriptionurl", ""),
                "caption": page["title"] + " " + field("ImageDescription"),
                "creator": field("Artist") or "Wikimedia Commons",
                "license": field("LicenseShortName"),
                "license_url": field("LicenseUrl"),
                "date": field("DateTimeOriginal"),
                "label": "ARCHIVE / CONTEXT",
            }
        )
    return results


def pexels(query, kind="footage"):
    key = os.getenv("PEXELS_API_KEY")
    if not key:
        return []
    if kind == "photo":
        data = request(
            "GET",
            "https://api.pexels.com/v1/search",
            headers={"Authorization": key},
            params={"query": query, "per_page": 10, "orientation": "landscape"},
        ).json()
        results = []
        for item in data.get("photos", []):
            if (item.get("width") or 0) < 1280 or (item.get("height") or 0) < 720:
                continue
            src = item.get("src", {}).get("large2x") or item.get("src", {}).get("original")
            if not src:
                continue
            results.append(
                {
                    "provider": "Pexels",
                    "kind": "photo",
                    "url": src,
                    "page_url": item.get("url", ""),
                    "caption": item.get("alt") or unquote(urlparse(item.get("url", "")).path).replace("-", " "),
                    "creator": item.get("photographer", "Pexels contributor"),
                    "license": "Pexels License",
                    "license_url": "https://www.pexels.com/license/",
                    "date": "unknown",
                    "label": "STOCK / ILLUSTRATION",
                }
            )
        return results
    data = request(
        "GET",
        "https://api.pexels.com/v1/videos/search",
        headers={"Authorization": key},
        params={"query": query, "per_page": 10, "orientation": "landscape"},
    ).json()
    results = []
    for item in data.get("videos", []):
        variants = [
            v
            for v in item.get("video_files", [])
            if v.get("file_type") == "video/mp4" and (v.get("width") or 0) >= 1280 and (v.get("height") or 0) >= 720
        ]
        if not variants:
            continue
        variants.sort(key=lambda v: abs(v["width"] - 1920))
        results.append(
            {
                "provider": "Pexels",
                "kind": "footage",
                "url": variants[0]["link"],
                "page_url": item["url"],
                "caption": unquote(urlparse(item["url"]).path).replace("-", " "),
                "creator": item.get("user", {}).get("name", "Pexels contributor"),
                "license": "Pexels License",
                "license_url": "https://www.pexels.com/license/",
                "date": "unknown",
                "label": "STOCK / ILLUSTRATION",
            }
        )
    return results


class Media:
    def __init__(self, cfg, brain, directory):
        self.cfg, self.brain, self.dir = cfg, brain, Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.uses, self.hashes, self.ledger, self.cache = {}, {}, [], {}

    def find(self, beat):
        v = beat["visual"]
        queries = [v["query"]]
        if v.get("must_include"):
            queries.append(" ".join(v["must_include"]))
        candidates = []
        for q in queries:
            key = (q, v["kind"])
            if key not in self.cache:
                found = []
                providers = [commons, pexels]
                for provider in providers:
                    try:
                        found += provider(q, v["kind"])
                    except StudioError:
                        continue
                self.cache[key] = found
            candidates.extend(self.cache[key])
        anchored_cands = [
            a
            for a in candidates
            if anchored(a, v["must_include"]) and self.uses.get(a["url"], 0) < self.cfg["max_same_asset_uses"]
        ]
        if not anchored_cands:
            anchored_cands = [a for a in candidates if self.uses.get(a["url"], 0) < self.cfg["max_same_asset_uses"]]
        if not anchored_cands:
            return None
        judgment = self.brain.json(
            "Select a candidate only if it directly depicts the visible subject of this "
            "narration. Wrong country, person, event or unrelated machinery is a rejection. Archival/context images "
            "are not proof of the event. Select -1 if no good choice. Return {index:integer, reason:string}.",
            {"narration": beat["narration"], "visual": v, "candidates": anchored_cands[:12]},
        )
        idx = judgment.get("index", -1)
        if not isinstance(idx, int) or not 0 <= idx < len(anchored_cands[:12]):
            return None
        asset = dict(anchored_cands[idx])
        try:
            suffix = ".media" if asset["kind"] == "footage" else ".jpg"
            path = self.dir / (digest(asset["url"]) + suffix)
            if not path.exists():
                download(asset["url"], path)
            if asset["kind"] == "footage":
                thumb = path.with_suffix(".jpg")
                run_ff(["-ss", "1", "-i", path, "-frames:v", "1", "-vf", "scale=960:-2", thumb], 120)
                image = Image.open(thumb).convert("RGB")
                thumb2 = path.with_suffix(".second.jpg")
                run_ff(["-ss", "3", "-i", path, "-frames:v", "1", "-vf", "scale=960:-2", thumb2], 120)
                image2 = Image.open(thumb2).convert("RGB")
                sheet = Image.new("RGB", (960, 1080))
                from PIL import ImageOps
                sheet.paste(ImageOps.pad(image, (960, 540)), (0, 0))
                sheet.paste(ImageOps.pad(image2, (960, 540)), (0, 540))
                audit_image = sheet
            else:
                with Image.open(path) as opened:
                    image = opened.convert("RGB")
                if image.width < 1280 or image.height < 720:
                    return None
                image.save(path, quality=94)
                audit_image = image
            gray = image.resize((16, 16)).convert("L")
            px = list(gray.getdata())
            mean = sum(px) / len(px)
            phash = sum((int(p >= mean) << i) for i, p in enumerate(px))
            if any((phash ^ h).bit_count() < 7 and n >= self.cfg["max_same_asset_uses"] for h, n in self.hashes.items()):
                return None
            if self.brain.provider == "gemini":
                audit_image.thumbnail((960, 1080))
                buf = io.BytesIO()
                audit_image.save(buf, "JPEG", quality=80)
                audit = self.brain.json(
                    "Inspect these image/video-frame pixels against the narration and metadata. "
                    "Reject irrelevant subjects, contradictory locations, apparent AI imagery, watermarks, large "
                    "embedded captions, collages or game renders. Metadata cannot override visible contradictions. "
                    "Do not claim event authenticity. Return {pass:boolean,reason:string}.",
                    {"narration": beat["narration"], "metadata": asset},
                    image=buf.getvalue(),
                )
                if audit.get("pass") is not True:
                    return None
                asset["audit_mode"] = "metadata + sampled pixels (AI, not forensic verification)"
            elif self.cfg["require_pixel_audit"]:
                return None
            else:
                asset["audit_mode"] = "metadata only; no pixel/entity authentication"
            asset.update(
                path=str(path),
                beat_id=beat["id"],
                selection_reason=judgment.get("reason", ""),
                changes="resized, letterboxed/cropped; editorial overlays; video audio removed",
            )
            self.uses[asset["url"]] = self.uses.get(asset["url"], 0) + 1
            self.hashes[phash] = self.hashes.get(phash, 0) + 1
            self.ledger.append(asset)
            return asset
        except (OSError, StudioError):
            return None

    def save(self, path):
        save_json(path, self.ledger)


def resolve_places(names):
    resolved = []
    for name in names:
        found = None
        try:
            result = request(
                "GET",
                "https://en.wikipedia.org/w/api.php",
                params={"action": "query", "format": "json", "titles": name, "redirects": 1, "prop": "coordinates", "colimit": 1},
                headers={"User-Agent": "WorldTalkBriefStudio/2.0"},
            ).json()
            for page in result.get("query", {}).get("pages", {}).values():
                coords = page.get("coordinates", [])
                if coords and coords[0].get("globe", "earth") == "earth":
                    c = coords[0]
                    gz = lookup_gazetteer(name) or {}
                    found = {
                        "name": page["title"],
                        "lat": c["lat"],
                        "lon": c["lon"],
                        "country": gz.get("country", ""),
                        "source": "https://en.wikipedia.org/?curid=" + str(page["pageid"]),
                    }
                    break
        except Exception:
            pass
        if not found:
            gz = lookup_gazetteer(name)
            if gz:
                found = gz
        if found:
            resolved.append(found)
    if len(resolved) != len(names):
        raise StudioError("Map coordinates unresolved; no guessed map pins")
    return resolved
