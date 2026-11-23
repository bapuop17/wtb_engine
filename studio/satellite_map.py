"""V98.3 Real Satellite Imagery Map Engine (Google-Earth-style Esri World Imagery XYZ Tiles — 100% Free, Zero API Key)."""
import io
import math
from pathlib import Path
from PIL import Image, ImageEnhance
from .common import digest, request

# Public Esri World Imagery XYZ tile server (high-res real satellite/aerial imagery, zero API key)
ESRI_SAT_URL = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"


def _latlon_to_tile_xy(lat, lon, zoom):
    lat_c = max(-85.0511, min(85.0511, float(lat)))
    lat_rad = math.radians(lat_c)
    n = 2.0 ** zoom
    x = (float(lon) + 180.0) / 360.0 * n
    y = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n
    return x, y


def _choose_zoom(lats, lons, w, h):
    lat_span = max(0.35, max(lats) - min(lats))
    lon_span = max(0.50, max(lons) - min(lons))
    # Pad bounding box so pins never touch edges
    lat_span *= 2.1
    lon_span *= 2.1
    for z in range(11, 2, -1):
        n = 2.0 ** z
        px_lon = (lon_span / 360.0) * n * 256.0
        px_lat = (lat_span / 170.0) * n * 256.0
        if px_lon <= w * 0.88 and px_lat <= h * 0.88:
            return z
    return 3


def fetch_satellite_basemap(places, width, height, cache_dir=None):
    """
    Fetches and stitches real Esri World Imagery satellite tiles around `places`.
    Returns (pil_image, project_fn) where project_fn(lat, lon) -> (px, py),
    or (None, None) if offline / network unavailable (triggers clean vector atlas fallback).
    """
    if not places:
        return None, None
    lats = [float(p["lat"]) for p in places]
    lons = [float(p["lon"]) for p in places]
    c_lat = (min(lats) + max(lats)) / 2.0
    c_lon = (min(lons) + max(lons)) / 2.0
    zoom = _choose_zoom(lats, lons, width, height)

    cx_f, cy_f = _latlon_to_tile_xy(c_lat, c_lon, zoom)
    cx_px, cy_px = cx_f * 256.0, cy_f * 256.0
    left_px = cx_px - width / 2.0
    top_px = cy_px - height / 2.0

    tx0 = int(math.floor(left_px / 256.0))
    tx1 = int(math.floor((left_px + width) / 256.0))
    ty0 = int(math.floor(top_px / 256.0))
    ty1 = int(math.floor((top_px + height) / 256.0))

    # Cap total tiles so it's always fast (max ~48 tiles)
    if (tx1 - tx0 + 1) * (ty1 - ty0 + 1) > 64:
        zoom = max(2, zoom - 1)
        cx_f, cy_f = _latlon_to_tile_xy(c_lat, c_lon, zoom)
        cx_px, cy_px = cx_f * 256.0, cy_f * 256.0
        left_px, top_px = cx_px - width / 2.0, cy_px - height / 2.0
        tx0, tx1 = int(math.floor(left_px / 256.0)), int(math.floor((left_px + width) / 256.0))
        ty0, ty1 = int(math.floor(top_px / 256.0)), int(math.floor((top_px + height) / 256.0))

    def project_fn(lat, lon):
        fx, fy = _latlon_to_tile_xy(lat, lon, zoom)
        return fx * 256.0 - left_px, fy * 256.0 - top_px

    cache_file = None
    if cache_dir:
        cdir = Path(cache_dir)
        cdir.mkdir(parents=True, exist_ok=True)
        key = digest([round(c_lat, 3), round(c_lon, 3), zoom, width, height])
        cache_file = cdir / f"sat_{key}.jpg"
        if cache_file.exists() and cache_file.stat().st_size > 10_000:
            try:
                return Image.open(cache_file).convert("RGB"), project_fn
            except Exception:
                pass

    n_tiles = 1 << zoom
    canvas = Image.new("RGB", (width, height), (10, 18, 30))
    fetched = 0
    for tx in range(tx0, tx1 + 1):
        wx = tx % n_tiles
        for ty in range(ty0, ty1 + 1):
            if ty < 0 or ty >= n_tiles:
                continue
            url = ESRI_SAT_URL.format(z=zoom, y=ty, x=wx)
            try:
                resp = request("GET", url, timeout=8, retries=0)
                tile = Image.open(io.BytesIO(resp.content)).convert("RGB")
                px = int(round(tx * 256.0 - left_px))
                py = int(round(ty * 256.0 - top_px))
                canvas.paste(tile, (px, py))
                fetched += 1
            except Exception:
                if fetched == 0:
                    # Fast fail if offline so rendering never stalls
                    return None, None

    if fetched < 2:
        return None, None

    # Apply subtle documentary tactical contrast grade so glowing route lines & pins pop cleanly
    canvas = ImageEnhance.Brightness(canvas).enhance(0.76)
    canvas = ImageEnhance.Contrast(canvas).enhance(1.18)
    canvas = ImageEnhance.Color(canvas).enhance(0.92)
    if cache_file:
        try:
            canvas.save(cache_file, quality=92)
        except Exception:
            pass
    return canvas, project_fn
