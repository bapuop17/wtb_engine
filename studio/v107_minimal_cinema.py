#!/usr/bin/env python3
"""
WTB Studio V107 — 20-Scene Adaptive Documentary Cinema & Motion Graphics Engine

Design Philosophy (World Talk Brief):
  Every story, category, and beat dictates its own visual grammar, palette, and pacing.
  Includes 20 distinct, non-repeating documentary scene archetypes + a strict anti-repeat
  episode scheduler so 10-12 minute documentaries (36-46 beats) never look repetitive.

Zero constant bottom caption bar on 16:9 long-form cinema beats.
Works per-frame directly inside studio/render.py with live HD decoded footage MP4 frames,
downloaded real press photos, or pitch-black (#07090F) minimalist vector data canvases.
"""

from __future__ import annotations

import math
import os
import re
import subprocess
import tempfile
import wave
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Palette & 5 Category-Adaptive Themes
# ---------------------------------------------------------------------------
BG_BLACK = (7, 9, 15)          # #07090F pitch-black cinema canvas
TEXT_WHITE = (244, 246, 251)   # #F4F6FB crisp editorial white
TEXT_MUTED = (148, 163, 184)   # #94A3B8 slate muted
TEXT_DIM = (71, 85, 105)       # #475569 dim slate
ACCENT_AMBER = (245, 158, 11)  # #F59E0B warm investigative amber
ACCENT_GREEN = (16, 185, 129)  # #10B981 neon emerald
ACCENT_PINK = (236, 72, 153)   # #EC4899 electric pink
ACCENT_RED = (239, 68, 68)     # #EF4444 crimson alert
ACCENT_BLUE = (59, 130, 246)   # #3B82F6 cool slate-blue
ACCENT_CYAN = (6, 182, 212)    # #06B6D4 science cyan
ACCENT_VIOLET = (168, 85, 247) # #A855F7 tech violet
TILE_IDLE = (28, 37, 56)       # #1C2538 dark tile base
CARD_DARK = (14, 19, 31)       # #0E131F dark glass card

CATEGORY_THEMES: Dict[str, Dict[str, Any]] = {
    "geopolitics": {
        "primary": ACCENT_AMBER,
        "secondary": ACCENT_RED,
        "positive": ACCENT_GREEN,
        "bpm": 112.0,
        "root_hz": 73.42,
    },
    "business_economy": {
        "primary": ACCENT_GREEN,
        "secondary": ACCENT_AMBER,
        "positive": ACCENT_CYAN,
        "bpm": 118.0,
        "root_hz": 65.41,
    },
    "science_climate": {
        "primary": ACCENT_CYAN,
        "secondary": ACCENT_AMBER,
        "positive": ACCENT_GREEN,
        "bpm": 98.0,
        "root_hz": 69.30,
    },
    "tech_ai": {
        "primary": ACCENT_VIOLET,
        "secondary": ACCENT_PINK,
        "positive": ACCENT_GREEN,
        "bpm": 122.0,
        "root_hz": 82.41,
    },
    "global_society": {
        "primary": ACCENT_PINK,
        "secondary": ACCENT_AMBER,
        "positive": ACCENT_GREEN,
        "bpm": 104.0,
        "root_hz": 61.74,
    },
}

# All 20 Distinct Visual Archetypes (Zero-Repeat Documentary Grammar)
V107_ARCHETYPES: Tuple[str, ...] = (
    "pull_quote_highlight",     # 01: Thin accent dash + bold white quote + sweeping highlight over live footage
    "filmstrip_chapter",        # 02: Zoom-out rounded card -> horizontal filmstrip slide -> chapter title -> zoom-in
    "news_evidence_card",       # 03: Dark-glass serif news/report card + animated highlighter over blurred footage
    "geopolitical_route_map",   # 04: Tactical coordinate grid + animated glowing corridor + pulsing chokepoints
    "market_shock_curve",       # 05: Pitch-black animated spline curve + glowing area fill + peak spike badge
    "vertical_event_timeline",  # 06: Chronological vertical spine animating step-by-step over live footage
    "giant_counting_number",    # 07: Massive bold counting KPI over dark-vignetted footage + tracked mono subtitle
    "strikethrough_punchline",  # 08: Pitch-black giant question slashed in red -> neon punchline popping below
    "tile_flip_matrix",         # 09: Pitch-black 12x8 tile matrix flipping slate-blue -> accent + live % counter
    "floating_breakdown_bar",   # 10: Proportional horizontal bar over live footage lighting up active segment
    "floating_checklist",       # 11: Sequential green check / red X status lines floating over moving footage
    "split_versus_panel",       # 12: Dark-glass 2-column VS comparison sliding in from opposite sides
    "quote_vs_reality",         # 13: Top claim dims & gets flagged -> bottom verified reality illuminates
    "ranking_bar_race",         # 14: Pitch-black animated horizontal comparative bars with live numeric counters
    "network_node_web",         # 15: Dark-canvas investigative node-link diagram with animated glowing edges
    "process_flow_steps",       # 16: Horizontal 3-4 stage domino/mechanism chain with animated arrows
    "radar_alert_sweep",        # 17: Tactical rotating radar sweep over live footage + pulsing epicenter tag
    "spotlight_zoom_frame",     # 18: Full-bleed cinema frame + minimal corner viewfinder + sleek left dateline
    "kinetic_statement_stack",  # 19: Pitch-black 3-line kinetic typography slamming in with accent keyword pop
    "two_stat_split_screen",    # 20: Two contrasting giant metrics (BEFORE -> AFTER) over dark-vignetted footage
)


def get_category_theme(category: str) -> Dict[str, Any]:
    return CATEGORY_THEMES.get(str(category or "").strip().lower(), CATEGORY_THEMES["geopolitics"])


# ---------------------------------------------------------------------------
# Easing & Math Helpers
# ---------------------------------------------------------------------------
def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if v < lo else (hi if v > hi else v)


def ease_out_cubic(t: float) -> float:
    t = clamp(t)
    return 1.0 - (1.0 - t) ** 3


def ease_in_out_cubic(t: float) -> float:
    t = clamp(t)
    return 4 * t * t * t if t < 0.5 else 1 - ((-2 * t + 2) ** 3) / 2


def ease_out_expo(t: float) -> float:
    t = clamp(t)
    return 1.0 if t >= 1.0 else 1.0 - (2.0 ** (-10.0 * t))


def ease_out_back(t: float) -> float:
    t = clamp(t)
    c1 = 1.70158
    c3 = c1 + 1.0
    return 1.0 + c3 * ((t - 1.0) ** 3) + c1 * ((t - 1.0) ** 2)


def _fade_color(fg: Tuple[int, int, int], bg: Tuple[int, int, int], alpha: float) -> Tuple[int, int, int]:
    a = clamp(alpha)
    return tuple(int(bg[i] * (1.0 - a) + fg[i] * a) for i in range(3))


# ---------------------------------------------------------------------------
# Font Discovery (Ubuntu / Debian / Sandbox safe)
# ---------------------------------------------------------------------------
_FONT_CACHE: Dict[Tuple[str, int], ImageFont.FreeTypeFont] = {}
_BG_CACHE: Dict[Tuple[int, int, Tuple[int, int, int]], Image.Image] = {}

_SANS_BOLD_CANDIDATES = [
    "/usr/share/fonts/truetype/inter/Inter-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
]
_SANS_REG_CANDIDATES = [
    "/usr/share/fonts/truetype/inter/Inter-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
]
_MONO_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/freefont/FreeMonoBold.ttf",
]
_SERIF_BOLD_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf",
]


def _pick_font_path(candidates: Sequence[str]) -> Optional[str]:
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None


def get_font(kind: str, size: int) -> ImageFont.FreeTypeFont:
    key = (kind, max(10, int(size)))
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    if kind == "bold":
        path = _pick_font_path(_SANS_BOLD_CANDIDATES)
    elif kind == "mono":
        path = _pick_font_path(_MONO_CANDIDATES)
    elif kind == "serif":
        path = _pick_font_path(_SERIF_BOLD_CANDIDATES) or _pick_font_path(_SANS_BOLD_CANDIDATES)
    else:
        path = _pick_font_path(_SANS_REG_CANDIDATES)
    font = ImageFont.truetype(path, key[1]) if path else ImageFont.load_default()
    _FONT_CACHE[key] = font
    return font


def wrap_lines(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_w: float, max_lines: int = 3) -> List[str]:
    words = str(text or "").split()
    lines: List[str] = []
    cur = ""
    for w in words:
        cand = f"{cur} {w}".strip()
        if draw.textlength(cand, font=font) <= max_w:
            cur = cand
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines[:max_lines] if lines else [""]


# ---------------------------------------------------------------------------
# Background & Visual Helpers
# ---------------------------------------------------------------------------
def load_cover_image(path: str, width: int, height: int, overscan: float = 1.12) -> np.ndarray:
    tw = int(round(width * overscan))
    th = int(round(height * overscan))
    if path and os.path.isfile(path):
        img = Image.open(path).convert("RGB")
        iw, ih = img.size
        scale = max(tw / max(1, iw), th / max(1, ih))
        nw, nh = int(round(iw * scale)), int(round(ih * scale))
        img = img.resize((nw, nh), Image.Resampling.LANCZOS)
        left = max(0, (nw - tw) // 2)
        top = max(0, (nh - th) // 2)
        img = img.crop((left, top, left + tw, top + th))
        return np.array(img, dtype=np.uint8)
    y = np.linspace(0, 1, th, dtype=np.float32)[:, None]
    x = np.linspace(0, 1, tw, dtype=np.float32)[None, :]
    r = np.clip(10 + 18 * (1 - y) * (1 - abs(x - 0.5)), 0, 255).astype(np.uint8)
    g = np.clip(15 + 28 * (1 - y) * (1 - abs(x - 0.5)), 0, 255).astype(np.uint8)
    b = np.clip(28 + 44 * (1 - y) * (1 - abs(x - 0.5)), 0, 255).astype(np.uint8)
    return np.stack([r, g, b], axis=-1)


def grade_live_backdrop(
    src_rgb: Optional[np.ndarray],
    width: int,
    height: int,
    progress: float,
    is_live_video: bool = False,
    darken: float = 0.48,
    left_scrim: float = 0.0,
    vignette: float = 0.55,
    blur_sigma: float = 0.0,
    grain_seed: int = 0,
) -> Image.Image:
    """Grade either a live decoded MP4 frame or a high-res still with Ken Burns + cinema vignette."""
    if src_rgb is None or src_rgb.size == 0:
        return make_pitch_black_canvas(width, height, halo_color=ACCENT_AMBER, halo_strength=0.14)

    sh, sw = src_rgb.shape[:2]
    if is_live_video:
        if (sw, sh) != (width, height):
            frame = cv2.resize(src_rgb, (width, height), interpolation=cv2.INTER_LINEAR)
        else:
            frame = src_rgb.copy()
    else:
        p = clamp(progress)
        z = 1.01 + 0.09 * p
        crop_w = min(sw, int(round(sw / z)))
        crop_h = min(sh, int(round(sh / z)))
        target_ar = width / float(height)
        if crop_w / float(max(1, crop_h)) > target_ar:
            crop_w = int(round(crop_h * target_ar))
        else:
            crop_h = int(round(crop_w / target_ar))
        cx = sw * (0.5 + (-0.015 + 0.030 * p))
        cy = sh * (0.5 + (0.008 - 0.016 * p))
        x0 = int(clamp(cx - crop_w / 2, 0, max(0, sw - crop_w)))
        y0 = int(clamp(cy - crop_h / 2, 0, max(0, sh - crop_h)))
        frame = cv2.resize(src_rgb[y0 : y0 + crop_h, x0 : x0 + crop_w], (width, height), interpolation=cv2.INTER_LINEAR)

    if blur_sigma > 0.5:
        k = int(blur_sigma * 4) | 1
        frame = cv2.GaussianBlur(frame, (k, k), blur_sigma)
    arr = frame.astype(np.float32)
    arr *= (1.0 - clamp(darken, 0.0, 0.92))

    if vignette > 0:
        yy = np.linspace(-1.0, 1.0, height, dtype=np.float32)[:, None]
        xx = np.linspace(-1.0, 1.0, width, dtype=np.float32)[None, :]
        dist = np.clip((xx * xx * 0.85 + yy * yy * 1.15), 0.0, 1.8)
        arr *= np.clip(1.0 - vignette * 0.55 * dist, 0.16, 1.0)[..., None]

    if left_scrim > 0:
        x_grad = np.linspace(0.0, 1.0, width, dtype=np.float32)[None, :]
        scrim = np.clip(1.0 - left_scrim * np.clip(1.0 - x_grad / 0.68, 0.0, 1.0) ** 1.4, 0.10, 1.0)
        arr *= scrim[..., None]

    rng = np.random.default_rng(grain_seed + 1337)
    noise = rng.normal(0.0, 1.8, (height // 2, width // 2, 1)).astype(np.float32)
    noise = cv2.resize(noise, (width, height), interpolation=cv2.INTER_NEAREST)[..., None]
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, mode="RGB")


def make_pitch_black_canvas(
    width: int,
    height: int,
    halo_color: Tuple[int, int, int] = ACCENT_GREEN,
    halo_strength: float = 0.15,
) -> Image.Image:
    key = (width, height, halo_color)
    if key in _BG_CACHE:
        return _BG_CACHE[key].copy()
    yy = np.linspace(0.0, 1.0, height, dtype=np.float32)[:, None]
    xx = np.linspace(0.0, 1.0, width, dtype=np.float32)[None, :]
    dx = (xx - 0.5) * 1.15
    dy = (yy - 0.12) * 1.45
    glow = np.exp(-(dx * dx + dy * dy) * 3.8) * halo_strength
    arr = np.zeros((height, width, 3), dtype=np.float32)
    for c in range(3):
        arr[:, :, c] = BG_BLACK[c] + glow * halo_color[c]
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), mode="RGB")
    _BG_CACHE[key] = im
    return im.copy()


def draw_source_attribution(
    draw: ImageDraw.ImageDraw,
    text: str,
    width: int,
    height: int,
    dot_color: Tuple[int, int, int] = ACCENT_AMBER,
) -> None:
    if not text:
        return
    font = get_font("mono", max(13, int(height * 0.0165)))
    x = int(width * 0.042)
    y = int(height * 0.935)
    r = max(3, int(height * 0.0042))
    draw.ellipse([x, y + 6, x + 2 * r, y + 6 + 2 * r], fill=dot_color)
    draw.text((x + 2 * r + 10, y), str(text).upper()[:64], font=font, fill=TEXT_MUTED)


def draw_tracked_text(
    draw: ImageDraw.ImageDraw,
    xy: Tuple[float, float],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: Tuple[int, ...],
    tracking: float = 2.0,
    anchor: str = "la",
) -> float:
    widths = [draw.textlength(ch, font=font) for ch in text]
    total_w = sum(widths) + tracking * max(0, len(text) - 1)
    x, y = xy
    if anchor.startswith("m"):
        x -= total_w / 2.0
    elif anchor.startswith("r"):
        x -= total_w
    cur_x = x
    for ch, w in zip(text, widths):
        draw.text((cur_x, y), ch, font=font, fill=fill)
        cur_x += w + tracking
    return total_w


# ---------------------------------------------------------------------------
# Anti-Repeat Episode Scheduler (Assigns All 20 Archetypes Across 10-12 Min)
# ---------------------------------------------------------------------------
def assign_v107_scene_archetypes(beats: List[Dict[str, Any]], category: str = "geopolitics") -> List[Dict[str, Any]]:
    """
    Assigns a content-matched, non-repeating V107 visual archetype to every beat.
    Guarantees:
      - Zero consecutive repeats
      - Exhausts fresh archetypes across the episode before ever reusing one
      - Matches visual.kind & narrative content (maps -> route_map/radar, charts -> shock_curve/bar_race, etc.)
    """
    used_counts: Dict[str, int] = {a: 0 for a in V107_ARCHETYPES}
    recent_window: List[str] = []
    last_chapter = ""
    chapter_num = 0

    def pick_best(candidates: Sequence[str]) -> str:
        # Prefer candidates not in recent_window (last 6 beats), then lowest episode usage count
        pool = [c for c in candidates if c not in recent_window[-6:]]
        if not pool:
            pool = [c for c in V107_ARCHETYPES if c not in recent_window[-4:]]
        if not pool:
            pool = list(V107_ARCHETYPES)
        pool.sort(key=lambda c: (used_counts.get(c, 0), candidates.index(c) if c in candidates else 99))
        chosen = pool[0]
        used_counts[chosen] = used_counts.get(chosen, 0) + 1
        recent_window.append(chosen)
        return chosen

    total_chapters = max(1, len({str(b.get("chapter", "")).strip() for b in beats if b.get("chapter")}))

    for idx, b in enumerate(beats):
        vis = b.setdefault("visual", {})
        kind = str(vis.get("kind", "footage")).strip().lower()
        chapter = str(b.get("chapter", "")).strip()
        nar = str(b.get("narration", ""))
        has_num = bool(re.search(r"\b\d[\d,\.]*(?:%|T|B|M|K|\s*(?:million|billion|trillion|percent|days|hours|km|miles))", nar, re.I))

        is_new_chapter = bool(chapter and chapter != last_chapter and idx > 0)
        if chapter and chapter != last_chapter:
            chapter_num += 1
            last_chapter = chapter

        if idx == 0:
            cands = ["pull_quote_highlight", "spotlight_zoom_frame", "kinetic_statement_stack"]
        elif is_new_chapter and used_counts["filmstrip_chapter"] < max(3, total_chapters // 2):
            cands = ["filmstrip_chapter", "kinetic_statement_stack", "spotlight_zoom_frame"]
        elif kind == "globe":
            cands = ["geopolitical_route_map", "radar_alert_sweep", "spotlight_zoom_frame"]
        elif kind == "chart":
            cands = ["market_shock_curve", "ranking_bar_race", "floating_breakdown_bar"]
        elif kind == "timeline":
            cands = ["vertical_event_timeline", "process_flow_steps", "floating_checklist"]
        elif kind == "actor_split":
            cands = ["split_versus_panel", "quote_vs_reality", "two_stat_split_screen"]
        elif kind == "evidence":
            cands = ["news_evidence_card", "quote_vs_reality", "pull_quote_highlight"]
        elif kind == "evidence_board":
            cands = ["network_node_web", "news_evidence_card", "floating_checklist"]
        elif kind == "diagram":
            cands = ["process_flow_steps", "network_node_web", "tile_flip_matrix"]
        elif kind == "stat_callout":
            cands = ["giant_counting_number", "two_stat_split_screen", "tile_flip_matrix", "floating_breakdown_bar"]
        elif idx == len(beats) - 1:
            cands = ["strikethrough_punchline", "kinetic_statement_stack", "pull_quote_highlight"]
        elif has_num:
            cands = [
                "giant_counting_number", "tile_flip_matrix", "floating_breakdown_bar",
                "two_stat_split_screen", "ranking_bar_race", "market_shock_curve",
                "pull_quote_highlight", "spotlight_zoom_frame",
            ]
        else:
            cands = [
                "spotlight_zoom_frame", "pull_quote_highlight", "floating_checklist",
                "news_evidence_card", "radar_alert_sweep", "vertical_event_timeline",
                "strikethrough_punchline", "kinetic_statement_stack", "quote_vs_reality",
                "process_flow_steps", "split_versus_panel", "network_node_web",
            ]

        chosen = pick_best(cands)
        vis["v107_archetype"] = chosen
        vis["v107_category"] = category
        vis["v107_chapter_index"] = f"{chapter_num:02d} / {total_chapters:02d}"
    return beats


# ---------------------------------------------------------------------------
# Per-Frame Renderer for ALL 20 Archetypes (Used Live by studio/render.py)
# ---------------------------------------------------------------------------
def _extract_key_number(text: str) -> Tuple[str, float, str]:
    """Extract (prefix, value, suffix) from beat narration/headline for animated counters."""
    m = re.search(r"([$€£]?)(\d[\d,]*(?:\.\d+)?)\s*(%|trillion|billion|million|T|B|M|K|days|hours|years|km|miles)?", text or "", re.I)
    if not m:
        return ("", 80.0, "%")
    pref = m.group(1) or ""
    raw_num = float(m.group(2).replace(",", ""))
    suf = (m.group(3) or "").strip()
    short_map = {"trillion": "T", "billion": "B", "million": "M"}
    suf = short_map.get(suf.lower(), suf.upper())
    return (pref, raw_num, suf)


def render_v107_beat_frame(
    beat: Dict[str, Any],
    dossier: Dict[str, Any],
    t_now: float,
    duration: float,
    bg_rgb: Optional[np.ndarray],
    width: int,
    height: int,
    frame_idx: int = 0,
    is_live_video: bool = False,
) -> Image.Image:
    """
    Render a single cinema-grade 16:9 frame for ANY of the 20 V107 archetypes.
    Clean, minimal, zero constant bottom caption bar, zero corporate chrome.
    """
    vis = beat.get("visual") or {}
    archetype = str(vis.get("v107_archetype") or "spotlight_zoom_frame")
    category = str(vis.get("v107_category") or dossier.get("category") or "geopolitics")
    theme = get_category_theme(category)
    accent: Tuple[int, int, int] = theme["primary"]
    secondary: Tuple[int, int, int] = theme["secondary"]
    positive: Tuple[int, int, int] = theme["positive"]

    headline = str(vis.get("headline") or beat.get("chapter") or dossier.get("topic") or "GLOBAL BRIEF").strip()
    narration = str(beat.get("narration") or "").strip()
    chapter = str(beat.get("chapter") or "KEY BRIEFING").strip()
    chapter_idx = str(vis.get("v107_chapter_index") or "01 / 06")
    data = vis.get("data") if isinstance(vis.get("data"), dict) else {}
    source_tag = str(beat.get("asset", {}).get("credit") or dossier.get("topic") or "World Talk Brief")[:56]

    dur = max(0.5, float(duration))
    prog = clamp(t_now / dur)

    # Helper to extract short sentences from narration
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", narration) if s.strip()]
    first_sent = sentences[0] if sentences else headline
    second_sent = sentences[1] if len(sentences) > 1 else headline

    # ------------------------------------------------------------------
    # 01. pull_quote_highlight
    # ------------------------------------------------------------------
    if archetype == "pull_quote_highlight":
        img = grade_live_backdrop(bg_rgb, width, height, prog, is_live_video, darken=0.48, left_scrim=0.70, grain_seed=frame_idx).convert("RGBA")
        ov = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        font = get_font("bold", int(height * 0.052))
        lines = wrap_lines(d, first_sent, font, width * 0.78, max_lines=3)
        line_h = int(height * 0.080)
        mx = int(width * 0.085)
        sy = int((height - len(lines) * line_h) * 0.50)

        dash_w = int(width * 0.044 * ease_out_expo(t_now / 0.45))
        if dash_w > 2:
            d.rounded_rectangle([mx, sy - int(height * 0.036), mx + dash_w, sy - int(height * 0.036) + 6], radius=3, fill=accent + (255,))
        hl_p = ease_out_cubic((t_now - 0.85) / 0.65)
        for idx, ln in enumerate(lines):
            ap = ease_out_cubic((t_now - 0.14 - idx * 0.16) / 0.38)
            if ap <= 0.01:
                continue
            y = sy + idx * line_h + int((1.0 - ap) * 22)
            ab = int(255 * ap)
            if idx == min(1, len(lines) - 1) and hl_p > 0.01:
                words = ln.split()
                hl_seg = " ".join(words[: max(2, len(words) // 2)])
                lw = d.textlength(hl_seg, font=font)
                d.rounded_rectangle([mx - 12, y - 6, mx - 12 + (lw + 24) * hl_p, y + int(height * 0.062)], radius=8, fill=accent + (int(240 * ap),))
                d.text((mx, y), hl_seg, font=font, fill=(BG_BLACK if hl_p > 0.45 else TEXT_WHITE) + (ab,))
                rest = ln[len(hl_seg):]
                if rest:
                    d.text((mx + lw, y), rest, font=font, fill=TEXT_WHITE + (ab,))
            else:
                d.text((mx, y), ln, font=font, fill=TEXT_WHITE + (ab,))
        draw_source_attribution(d, source_tag, width, height, dot_color=accent)
        return Image.alpha_composite(img, ov).convert("RGB")

    # ------------------------------------------------------------------
    # 02. filmstrip_chapter
    # ------------------------------------------------------------------
    if archetype == "filmstrip_chapter":
        base = make_pitch_black_canvas(width, height, halo_color=accent, halo_strength=0.14).convert("RGBA")
        cw, ch = int(width * 0.56), int(width * 0.56 * height / width)
        cy = int(height * 0.34)
        src_im = grade_live_backdrop(bg_rgb, cw, ch, prog, is_live_video, darken=0.18, vignette=0.35, grain_seed=frame_idx).convert("RGBA")
        mask = Image.new("L", (cw, ch), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, cw - 1, ch - 1], radius=22, fill=255)
        card = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        card.paste(src_im, (0, 0), mask)
        ImageDraw.Draw(card).rounded_rectangle([2, 2, cw - 3, ch - 3], radius=22, outline=accent + (255,), width=5)

        slide_p = ease_out_cubic(t_now / 0.85)
        cx = int((width - cw) // 2 + (1.0 - slide_p) * width * 0.35)
        base.alpha_composite(card, (cx, cy))

        ov = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        tp = ease_out_cubic((t_now - 0.30) / 0.55)
        if tp > 0.01:
            ab = int(255 * tp)
            draw_tracked_text(d, (width / 2.0, height * 0.115 + int((1 - tp) * 18)), chapter_idx, get_font("mono", int(height * 0.024)), accent + (ab,), tracking=6.0, anchor="ma")
            draw_tracked_text(d, (width / 2.0, height * 0.168 + int((1 - tp) * 18)), chapter.upper()[:40], get_font("bold", int(height * 0.062)), TEXT_WHITE + (ab,), tracking=3.0, anchor="ma")
        draw_source_attribution(d, source_tag, width, height, dot_color=accent)
        return Image.alpha_composite(base, ov).convert("RGB")

    # ------------------------------------------------------------------
    # 03. news_evidence_card
    # ------------------------------------------------------------------
    if archetype == "news_evidence_card":
        img = grade_live_backdrop(bg_rgb, width, height, prog, is_live_video, darken=0.68, blur_sigma=4.0, grain_seed=frame_idx).convert("RGBA")
        ov = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        card_w, card_h = int(width * 0.72), int(height * 0.60)
        cx0, cy0 = (width - card_w) // 2, int(height * 0.19)
        cp = ease_out_cubic(t_now / 0.45)
        y_off = int((1.0 - cp) * 30)
        at = int(255 * cp)
        d.rounded_rectangle([cx0 + 10, cy0 + y_off + 14, cx0 + card_w + 10, cy0 + card_h + y_off + 14], radius=20, fill=(0, 0, 0, int(130 * cp)))
        d.rounded_rectangle([cx0, cy0 + y_off, cx0 + card_w, cy0 + card_h + y_off], radius=20, fill=CARD_DARK + (int(238 * cp),), outline=(56, 72, 102, at), width=2)
        d.rounded_rectangle([cx0 + 48, cy0 + y_off + 42, cx0 + 116, cy0 + y_off + 48], radius=3, fill=accent + (at,))
        draw_tracked_text(d, (cx0 + 134, cy0 + y_off + 33), f"VERIFIED REPORT  •  {chapter}".upper()[:52], get_font("mono", int(height * 0.020)), accent + (at,), tracking=3.0, anchor="la")
        f_head = get_font("serif", int(height * 0.042))
        h_lines = wrap_lines(d, headline, f_head, card_w - 96, max_lines=2)
        hy = cy0 + y_off + 86
        for hl in h_lines:
            d.text((cx0 + 48, hy), hl, font=f_head, fill=TEXT_WHITE + (at,))
            hy += int(height * 0.054)
        div_y = hy + 16
        d.line([(cx0 + 48, div_y), (cx0 + card_w - 48, div_y)], fill=(45, 58, 82, at), width=2)
        f_body = get_font("reg", int(height * 0.027))
        b_lines = wrap_lines(d, narration, f_body, card_w - 104, max_lines=4)
        hl_p = ease_out_cubic((t_now - 0.85) / 0.65)
        ly = div_y + 30
        for idx, bl in enumerate(b_lines):
            if idx == min(1, len(b_lines) - 1) and hl_p > 0.01:
                lw = d.textlength(bl, font=f_body)
                d.rounded_rectangle([cx0 + 42, ly - 5, cx0 + 42 + (lw + 20) * hl_p, ly + 38], radius=6, fill=accent + (int(240 * cp),))
                d.text((cx0 + 50, ly), bl, font=f_body, fill=(BG_BLACK if hl_p > 0.45 else TEXT_WHITE) + (at,))
            else:
                d.text((cx0 + 50, ly), bl, font=f_body, fill=(TEXT_MUTED if hl_p > 0.35 else TEXT_WHITE) + (at,))
            ly += 52
        draw_source_attribution(d, source_tag, width, height, dot_color=accent)
        return Image.alpha_composite(img, ov).convert("RGB")

    # ------------------------------------------------------------------
    # 04. geopolitical_route_map
    # ------------------------------------------------------------------
    if archetype == "geopolitical_route_map":
        img = grade_live_backdrop(bg_rgb, width, height, prog, is_live_video, darken=0.60, grain_seed=frame_idx).convert("RGBA")
        ov = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        for gx in range(160, width, 200):
            d.line([(gx, 0), (gx, height)], fill=(148, 163, 184, 24), width=1)
        for gy in range(140, height, 180):
            d.line([(0, gy), (width, gy)], fill=(148, 163, 184, 24), width=1)
        places = [str(p) for p in (data.get("places") or []) if str(p).strip()][:3]
        if len(places) < 2:
            places = [chapter[:18] or "ORIGIN", "FLASHPOINT", "GLOBAL IMPACT"]
        coords = [(0.24, 0.56), (0.52, 0.44), (0.78, 0.36)][: len(places)]
        pts = [(int(nx * width), int(ny * height)) for nx, ny in coords]
        draw_tracked_text(d, (int(width * 0.06), int(height * 0.085)), headline.upper()[:42], get_font("bold", int(height * 0.042)), TEXT_WHITE + (255,), tracking=2.5, anchor="la")
        rp = ease_out_cubic((t_now - 0.25) / 1.8)
        for s_idx in range(len(pts) - 1):
            loc = clamp(rp * (len(pts) - 1) - s_idx)
            if loc > 0:
                p0, p1 = pts[s_idx], pts[s_idx + 1]
                cur = (int(p0[0] + (p1[0] - p0[0]) * loc), int(p0[1] + (p1[1] - p0[1]) * loc))
                d.line([p0, cur], fill=accent + (80,), width=14)
                d.line([p0, cur], fill=accent + (255,), width=5)
        f_node = get_font("mono", int(height * 0.021))
        for idx, pl in enumerate(places):
            ap = ease_out_cubic((t_now - 0.2 - idx * 0.45) / 0.35)
            if ap <= 0.01:
                continue
            px, py = pts[idx]
            col = secondary if idx == 1 else accent
            ab = int(255 * ap)
            pulse = (t_now * 1.6 + idx * 0.35) % 1.0
            rr = int(14 + 34 * pulse)
            d.ellipse([px - rr, py - rr, px + rr, py + rr], outline=col + (int(180 * (1 - pulse) * ap),), width=3)
            d.ellipse([px - 10, py - 10, px + 10, py + 10], fill=col + (ab,), outline=BG_BLACK + (ab,), width=3)
            lw = d.textlength(pl.upper(), font=f_node) + 28
            lx = int(clamp(px - lw / 2, 40, width - lw - 40))
            d.rounded_rectangle([lx, py - 56, lx + lw, py - 20], radius=8, fill=CARD_DARK + (int(225 * ap),), outline=col + (ab,), width=2)
            d.text((lx + 14, py - 50), pl.upper(), font=f_node, fill=TEXT_WHITE + (ab,))
        draw_source_attribution(d, source_tag, width, height, dot_color=accent)
        return Image.alpha_composite(img, ov).convert("RGB")

    # ------------------------------------------------------------------
    # 05. market_shock_curve
    # ------------------------------------------------------------------
    if archetype == "market_shock_curve":
        canvas = make_pitch_black_canvas(width, height, halo_color=accent, halo_strength=0.14).convert("RGBA")
        ov = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        pts_data = data.get("points") or []
        vals = [float(p.get("value", i + 1)) for i, p in enumerate(pts_data) if isinstance(p, dict)] if pts_data else []
        x_lbls = [str(p.get("label", f"P{i+1}"))[:8] for i, p in enumerate(pts_data) if isinstance(p, dict)] if pts_data else []
        if len(vals) < 3:
            vals = [100, 108, 114, 132, 215, 295, 270]
            x_lbls = ["T-6", "T-5", "T-4", "T-3", "T-2", "PEAK", "NOW"]
        gx0, gx1, gy0, gy1 = int(width * 0.11), int(width * 0.89), int(height * 0.30), int(height * 0.80)
        vmin, vmax = min(vals) * 0.85, max(vals) * 1.12
        raw_pts = [
            (gx0 + (gx1 - gx0) * (k / max(1, len(vals) - 1)), gy1 - (gy1 - gy0) * ((v - vmin) / max(1e-6, vmax - vmin)))
            for k, v in enumerate(vals)
        ]
        d.text((gx0, int(height * 0.11)), headline[:44], font=get_font("bold", int(height * 0.052)), fill=TEXT_WHITE + (255,))
        draw_tracked_text(d, (gx0, int(height * 0.185)), str(data.get("unit") or chapter).upper()[:48], get_font("mono", int(height * 0.022)), accent + (235,), tracking=3.5, anchor="la")
        for g in range(5):
            gy = int(gy0 + (gy1 - gy0) * (g / 4.0))
            d.line([(gx0, gy), (gx1, gy)], fill=(45, 58, 82, 90), width=1)
        f_ax = get_font("mono", int(height * 0.020))
        for k, xl in enumerate(x_lbls):
            xx = gx0 + (gx1 - gx0) * (k / max(1, len(x_lbls) - 1))
            draw_tracked_text(d, (xx, gy1 + 22), xl.upper(), f_ax, TEXT_MUTED + (210,), tracking=1.5, anchor="ma")
        dp = ease_out_cubic((t_now - 0.25) / 1.85)
        cur_f = dp * (len(raw_pts) - 1)
        cur_pts = [raw_pts[0]]
        for s in range(len(raw_pts) - 1):
            if cur_f >= s + 1:
                cur_pts.append(raw_pts[s + 1])
            elif cur_f > s:
                frac = cur_f - s
                p0, p1 = raw_pts[s], raw_pts[s + 1]
                cur_pts.append((p0[0] + (p1[0] - p0[0]) * frac, p0[1] + (p1[1] - p0[1]) * frac))
        if len(cur_pts) >= 2:
            d.polygon(list(cur_pts) + [(cur_pts[-1][0], gy1), (cur_pts[0][0], gy1)], fill=accent + (42,))
            d.line(cur_pts, fill=accent + (90,), width=14, joint="curve")
            d.line(cur_pts, fill=accent + (255,), width=5, joint="curve")
            lx, ly = cur_pts[-1]
            d.ellipse([lx - 9, ly - 9, lx + 9, ly + 9], fill=TEXT_WHITE + (255,), outline=accent + (255,), width=4)
        draw_source_attribution(d, source_tag, width, height, dot_color=accent)
        return Image.alpha_composite(canvas, ov).convert("RGB")

    # ------------------------------------------------------------------
    # 06. vertical_event_timeline
    # ------------------------------------------------------------------
    if archetype == "vertical_event_timeline":
        img = grade_live_backdrop(bg_rgb, width, height, prog, is_live_video, darken=0.52, left_scrim=0.78, grain_seed=frame_idx).convert("RGBA")
        ov = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        evs = data.get("events") or []
        items = [(str(e.get("date", f"STEP 0{i+1}")), str(e.get("label", ""))) for i, e in enumerate(evs) if isinstance(e, dict)][:3]
        if len(items) < 2:
            items = [(f"PHASE 0{i+1}", s[:56]) for i, s in enumerate((sentences + [headline, chapter])[:3])]
        sx = int(width * 0.14)
        row_h = int(height * 0.17)
        sy = int((height - (len(items) - 1) * row_h) * 0.46)
        sp = ease_out_cubic((t_now - 0.15) / 1.8)
        if sp > 0.01:
            d.line([(sx, sy), (sx, sy + int((len(items) - 1) * row_h * sp))], fill=(100, 116, 139, 190), width=4)
        f_dt = get_font("mono", int(height * 0.024))
        f_ev = get_font("bold", int(height * 0.040))
        for idx, (dt_str, lbl) in enumerate(items):
            p = ease_out_cubic((t_now - 0.22 - idx * 0.55) / 0.40)
            if p <= 0.01:
                continue
            y = sy + idx * row_h
            ab = int(255 * p)
            col = secondary if idx == len(items) - 1 else accent
            d.ellipse([sx - 11, y - 11, sx + 11, y + 11], fill=col + (ab,), outline=BG_BLACK + (ab,), width=3)
            tx = sx + 48 + int((1 - p) * 24)
            draw_tracked_text(d, (tx, y - 34), dt_str.upper(), f_dt, col + (ab,), tracking=3.5, anchor="la")
            d.text((tx, y - 2), lbl[:54], font=f_ev, fill=TEXT_WHITE + (ab,))
        draw_source_attribution(d, source_tag, width, height, dot_color=accent)
        return Image.alpha_composite(img, ov).convert("RGB")

    # ------------------------------------------------------------------
    # 07. giant_counting_number
    # ------------------------------------------------------------------
    if archetype == "giant_counting_number":
        img = grade_live_backdrop(bg_rgb, width, height, prog, is_live_video, darken=0.58, vignette=0.68, grain_seed=frame_idx).convert("RGBA")
        ov = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        metrics = data.get("metrics") or []
        if metrics and isinstance(metrics[0], dict):
            pref, end_v, suf = _extract_key_number(str(metrics[0].get("value", "")))
            sub = str(metrics[0].get("label") or headline)
        else:
            pref, end_v, suf = _extract_key_number(narration + " " + headline)
            sub = headline
        val = end_v * ease_out_expo(t_now / 1.45)
        num_str = f"{pref}{val:,.1f}{suf}" if (end_v < 100 and end_v != int(end_v)) else f"{pref}{int(round(val)):,}{suf}"
        f_big = get_font("bold", int(height * 0.18))
        ap = ease_out_cubic(t_now / 0.35)
        nw = d.textlength(num_str, font=f_big)
        nx, ny = (width - nw) / 2.0, height * 0.35 + int((1 - ap) * 24)
        d.text((nx, ny + 6), num_str, font=f_big, fill=(0, 0, 0, int(145 * ap)))
        d.text((nx, ny), num_str, font=f_big, fill=accent + (int(255 * ap),))
        sp = ease_out_cubic((t_now - 0.35) / 0.40)
        if sp > 0.01:
            draw_tracked_text(d, (width / 2.0, height * 0.595), sub.upper()[:52], get_font("mono", int(height * 0.024)), TEXT_WHITE + (int(230 * sp),), tracking=5.0, anchor="ma")
        draw_source_attribution(d, source_tag, width, height, dot_color=accent)
        return Image.alpha_composite(img, ov).convert("RGB")

    # ------------------------------------------------------------------
    # 08. strikethrough_punchline
    # ------------------------------------------------------------------
    if archetype == "strikethrough_punchline":
        canvas = make_pitch_black_canvas(width, height, halo_color=positive, halo_strength=0.14)
        d = ImageDraw.Draw(canvas)
        words = headline.split()
        mid = max(1, len(words) // 2)
        top_txt = " ".join(words[:mid])[:24] + "?"
        bot_txt = " ".join(words[mid:])[:26] or "THE REAL SHIFT."
        f_top = get_font("bold", int(height * 0.105))
        f_bot = get_font("bold", int(height * 0.112))
        tp = ease_out_cubic(t_now / 0.35)
        sp = ease_out_expo((t_now - 0.75) / 0.40)
        bp = ease_out_back((t_now - 1.20) / 0.45) if t_now > 1.20 else 0.0
        tw = d.textlength(top_txt, font=f_top)
        tx, ty = (width - tw) / 2.0, height * 0.28 + int((1 - tp) * 18)
        d.text((tx, ty), top_txt, font=f_top, fill=_fade_color(TEXT_WHITE, BG_BLACK, tp * (1 - 0.62 * sp)))
        if sp > 0.01:
            d.line([(tx - 24, ty + int(height * 0.062) + 6), (tx - 24 + (tw + 48) * sp, ty + int(height * 0.062) - 6)], fill=ACCENT_RED, width=12)
        if bp > 0.01:
            bw = d.textlength(bot_txt, font=f_bot)
            d.text(((width - bw) / 2.0, height * 0.505 + int((1 - clamp(bp)) * 22)), bot_txt, font=f_bot, fill=_fade_color(positive, BG_BLACK, clamp(bp)))
        draw_source_attribution(d, source_tag, width, height, dot_color=positive)
        return canvas

    # ------------------------------------------------------------------
    # 09. tile_flip_matrix
    # ------------------------------------------------------------------
    if archetype == "tile_flip_matrix":
        canvas = make_pitch_black_canvas(width, height, halo_color=positive, halo_strength=0.15)
        d = ImageDraw.Draw(canvas)
        _, end_v, _ = _extract_key_number(narration + " " + headline)
        target_pct = int(clamp(end_v if 5 <= end_v <= 98 else 78, 12, 96))
        cols, rows = 12, 8
        total = cols * rows
        active_n = int(round(total * target_pct / 100.0))
        sw_p = ease_out_cubic((t_now - 0.25) / 2.0)
        lit_f = active_n * sw_p
        gw = int(width * 0.62)
        gap = 12
        tw = (gw - (cols - 1) * gap) // cols
        th = int(tw * 0.62)
        gx0 = (width - (cols * tw + (cols - 1) * gap)) // 2
        gy0 = int(height * 0.34)
        f_pct = get_font("bold", int(height * 0.11))
        pct_s = f"{int(round(target_pct * sw_p))}%"
        d.text((gx0, int(height * 0.125)), pct_s, font=f_pct, fill=positive)
        pw = d.textlength(pct_s, font=f_pct)
        draw_tracked_text(d, (gx0 + pw + 32, int(height * 0.162)), headline.upper()[:36], get_font("mono", int(height * 0.024)), TEXT_WHITE, tracking=4.0, anchor="la")
        d.text((gx0 + pw + 32, int(height * 0.212)), first_sent[:62], font=get_font("reg", int(height * 0.024)), fill=TEXT_MUTED)
        for idx in range(total):
            r, c = idx // cols, idx % cols
            tx, ty = gx0 + c * (tw + gap), gy0 + r * (th + gap)
            loc = clamp(lit_f - idx)
            if idx < active_n and loc > 0:
                sy_scale = max(0.14, abs(math.cos(loc * math.pi)))
                hn = max(4, int(th * sy_scale))
                d.rounded_rectangle([tx, ty + (th - hn) // 2, tx + tw, ty + (th + hn) // 2], radius=8, fill=positive if loc >= 0.5 else ACCENT_BLUE)
            else:
                d.rounded_rectangle([tx, ty, tx + tw, ty + th], radius=8, fill=TILE_IDLE, outline=(42, 54, 78), width=1)
        draw_source_attribution(d, source_tag, width, height, dot_color=positive)
        return canvas

    # ------------------------------------------------------------------
    # 10. floating_breakdown_bar
    # ------------------------------------------------------------------
    if archetype == "floating_breakdown_bar":
        img = grade_live_backdrop(bg_rgb, width, height, prog, is_live_video, darken=0.58, vignette=0.65, grain_seed=frame_idx).convert("RGBA")
        ov = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        segs = [("STAGE 01", 22.0), ("CORE IMPACT", 54.0), ("FALLOUT", 24.0)]
        f_m = get_font("bold", int(height * 0.072))
        mw = d.textlength(headline[:32], font=f_m)
        d.text(((width - mw) / 2.0, height * 0.30), headline[:32], font=f_m, fill=TEXT_WHITE + (255,))
        bw, bh = int(width * 0.78), int(height * 0.090)
        bx0, by0 = (width - bw) // 2, int(height * 0.50)
        bp = ease_out_expo((t_now - 0.25) / 0.85)
        fp = ease_out_cubic((t_now - 1.10) / 0.50)
        cx = bx0
        usable = bw - 16
        for idx, (sn, sh) in enumerate(segs):
            sw = int(usable * (sh / 100.0) * bp)
            if sw < 6:
                continue
            is_act = idx == 1
            col = accent + (255,) if is_act else (51, 65, 85, max(60, int(165 - 80 * fp)))
            d.rounded_rectangle([cx, by0, cx + sw, by0 + bh], radius=10, fill=col)
            draw_tracked_text(d, (cx + sw / 2.0, by0 + bh + 22), sn, get_font("mono", int(height * 0.021)), (accent if is_act else TEXT_MUTED) + (240,), tracking=2.5, anchor="ma")
            cx += sw + 8
        draw_source_attribution(d, source_tag, width, height, dot_color=accent)
        return Image.alpha_composite(img, ov).convert("RGB")

    # ------------------------------------------------------------------
    # 11. floating_checklist
    # ------------------------------------------------------------------
    if archetype == "floating_checklist":
        img = grade_live_backdrop(bg_rgb, width, height, prog, is_live_video, darken=0.48, left_scrim=0.76, grain_seed=frame_idx).convert("RGBA")
        ov = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        pts_list = (sentences + [headline, chapter])[:3]
        mx = int(width * 0.09)
        rh = int(height * 0.15)
        sy = int((height - len(pts_list) * rh) * 0.50)
        f_main = get_font("bold", int(height * 0.044))
        for idx, txt in enumerate(pts_list):
            p = ease_out_cubic((t_now - 0.25 - idx * 0.65) / 0.38)
            if p <= 0.01:
                continue
            y = sy + idx * rh + int((1 - p) * 22)
            ab = int(255 * p)
            passed = idx < len(pts_list) - 1
            bc = positive if passed else ACCENT_RED
            cx, cy = mx + 22, y + 26
            if passed:
                d.line([(cx - 14, cy + 2), (cx - 3, cy + 12), (cx + 16, cy - 10)], fill=bc + (ab,), width=7, joint="curve")
            else:
                d.line([(cx - 12, cy - 12), (cx + 12, cy + 12)], fill=bc + (ab,), width=7)
                d.line([(cx + 12, cy - 12), (cx - 12, cy + 12)], fill=bc + (ab,), width=7)
            d.text((mx + 68, y), txt[:52], font=f_main, fill=TEXT_WHITE + (ab,))
        draw_source_attribution(d, source_tag, width, height, dot_color=positive)
        return Image.alpha_composite(img, ov).convert("RGB")

    # ------------------------------------------------------------------
    # 12. split_versus_panel
    # ------------------------------------------------------------------
    if archetype == "split_versus_panel":
        canvas = make_pitch_black_canvas(width, height, halo_color=accent, halo_strength=0.14).convert("RGBA")
        ov = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        lt = str(data.get("left_title") or "SIDE A").upper()[:26]
        rt = str(data.get("right_title") or "SIDE B").upper()[:26]
        lp = [str(x) for x in (data.get("left_points") or [first_sent[:48]])][:3]
        rp = [str(x) for x in (data.get("right_points") or [second_sent[:48]])][:3]
        sp = ease_out_cubic(t_now / 0.55)
        cw, ch = int(width * 0.40), int(height * 0.56)
        cy = int(height * 0.24)
        lx = int(width * 0.07 - (1 - sp) * 80)
        rx = int(width * 0.53 + (1 - sp) * 80)
        ab = int(255 * sp)
        for bx, title_s, pts_s, col in [(lx, lt, lp, accent), (rx, rt, rp, secondary)]:
            d.rounded_rectangle([bx, cy, bx + cw, cy + ch], radius=18, fill=CARD_DARK + (int(235 * sp),), outline=col + (ab,), width=3)
            d.rounded_rectangle([bx + 32, cy + 32, bx + 96, cy + 38], radius=3, fill=col + (ab,))
            d.text((bx + 32, cy + 58), title_s, font=get_font("bold", int(height * 0.042)), fill=TEXT_WHITE + (ab,))
            py = cy + 140
            for pt in pts_s:
                d.text((bx + 32, py), f"•  {pt[:44]}", font=get_font("reg", int(height * 0.028)), fill=TEXT_MUTED + (ab,))
                py += 68
        # VS badge in center
        d.ellipse([width // 2 - 36, cy + ch // 2 - 36, width // 2 + 36, cy + ch // 2 + 36], fill=accent + (ab,))
        draw_tracked_text(d, (width / 2.0, cy + ch // 2 - 14), "VS", get_font("bold", int(height * 0.028)), BG_BLACK + (ab,), tracking=2.0, anchor="ma")
        draw_source_attribution(d, source_tag, width, height, dot_color=accent)
        return Image.alpha_composite(canvas, ov).convert("RGB")

    # ------------------------------------------------------------------
    # 13. quote_vs_reality
    # ------------------------------------------------------------------
    if archetype == "quote_vs_reality":
        canvas = make_pitch_black_canvas(width, height, halo_color=secondary, halo_strength=0.14).convert("RGBA")
        ov = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        mx, cw = int(width * 0.14), int(width * 0.72)
        p1 = ease_out_cubic(t_now / 0.45)
        p2 = ease_out_cubic((t_now - 0.95) / 0.50)
        # Top official claim (dims when reality appears)
        dim = 1.0 - 0.45 * p2
        d.rounded_rectangle([mx, int(height * 0.18), mx + cw, int(height * 0.42)], radius=16, fill=CARD_DARK + (int(220 * p1 * dim),), outline=(71, 85, 105, int(200 * p1)), width=2)
        draw_tracked_text(d, (mx + 36, int(height * 0.21)), "THE CLAIM", get_font("mono", int(height * 0.021)), TEXT_MUTED + (int(220 * p1),), tracking=4.0, anchor="la")
        d.text((mx + 36, int(height * 0.27)), first_sent[:68], font=get_font("bold", int(height * 0.036)), fill=TEXT_WHITE + (int(240 * p1 * dim),))
        if p2 > 0.01:
            d.rounded_rectangle([mx, int(height * 0.49), mx + cw, int(height * 0.76)], radius=16, fill=CARD_DARK + (int(245 * p2),), outline=positive + (int(255 * p2),), width=3)
            draw_tracked_text(d, (mx + 36, int(height * 0.52)), "VERIFIED REALITY", get_font("mono", int(height * 0.022)), positive + (int(255 * p2),), tracking=4.0, anchor="la")
            d.text((mx + 36, int(height * 0.59)), second_sent[:68], font=get_font("bold", int(height * 0.038)), fill=TEXT_WHITE + (int(255 * p2),))
        draw_source_attribution(d, source_tag, width, height, dot_color=positive)
        return Image.alpha_composite(canvas, ov).convert("RGB")

    # ------------------------------------------------------------------
    # 14. ranking_bar_race
    # ------------------------------------------------------------------
    if archetype == "ranking_bar_race":
        canvas = make_pitch_black_canvas(width, height, halo_color=accent, halo_strength=0.14)
        d = ImageDraw.Draw(canvas)
        pts_data = data.get("points") or []
        bars = [(str(p.get("label", f"ITEM {i+1}")), float(p.get("value", 80 - i * 18))) for i, p in enumerate(pts_data) if isinstance(p, dict)][:4]
        if len(bars) < 2:
            bars = [("PRIMARY EXPOSURE", 88.0), ("REGIONAL SPILLOVER", 62.0), ("GLOBAL SUPPLY CHAIN", 44.0), ("BACKUP CAPACITY", 19.0)]
        mx_v = max(1.0, max(v for _, v in bars))
        d.text((int(width * 0.10), int(height * 0.12)), headline[:44], font=get_font("bold", int(height * 0.052)), fill=TEXT_WHITE)
        bp = ease_out_expo((t_now - 0.25) / 1.45)
        y = int(height * 0.28)
        max_bw = int(width * 0.58)
        for idx, (lbl, val) in enumerate(bars):
            bw = max(14, int(max_bw * (val / mx_v) * bp))
            col = accent if idx == 0 else ACCENT_BLUE
            draw_tracked_text(d, (int(width * 0.10), y), lbl.upper()[:24], get_font("mono", int(height * 0.022)), TEXT_WHITE, tracking=2.5, anchor="la")
            d.rounded_rectangle([int(width * 0.10), y + 36, int(width * 0.10) + bw, y + 84], radius=10, fill=col)
            d.text((int(width * 0.10) + bw + 20, y + 40), f"{val * bp:,.0f}", font=get_font("bold", int(height * 0.034)), fill=col)
            y += int(height * 0.145)
        draw_source_attribution(d, source_tag, width, height, dot_color=accent)
        return canvas

    # ------------------------------------------------------------------
    # 15. network_node_web
    # ------------------------------------------------------------------
    if archetype == "network_node_web":
        canvas = make_pitch_black_canvas(width, height, halo_color=accent, halo_strength=0.14)
        d = ImageDraw.Draw(canvas)
        nodes = data.get("nodes") or []
        labels = [(str(n.get("tag", f"NODE 0{i+1}")), str(n.get("title", ""))) for i, n in enumerate(nodes) if isinstance(n, dict)][:4]
        if len(labels) < 3:
            labels = [("ACTOR 01", chapter[:20] or "ORIGIN"), ("ACTOR 02", "MECHANISM"), ("ACTOR 03", "GLOBAL FALLOUT")]
        pos = [(0.25, 0.42), (0.50, 0.28), (0.75, 0.44), (0.50, 0.68)][: len(labels)]
        pts = [(int(px * width), int(py * height)) for px, py in pos]
        d.text((int(width * 0.08), int(height * 0.09)), headline[:44], font=get_font("bold", int(height * 0.048)), fill=TEXT_WHITE)
        ep = ease_out_cubic((t_now - 0.25) / 1.2)
        for i in range(len(pts) - 1):
            p0, p1 = pts[i], pts[i + 1]
            cur = (int(p0[0] + (p1[0] - p0[0]) * ep), int(p0[1] + (p1[1] - p0[1]) * ep))
            d.line([p0, cur], fill=accent, width=4)
        for idx, (tag, ttl) in enumerate(labels):
            px, py = pts[idx]
            d.rounded_rectangle([px - 150, py - 52, px + 150, py + 52], radius=14, fill=CARD_DARK, outline=accent if idx == 0 else ACCENT_BLUE, width=3)
            draw_tracked_text(d, (px, py - 34), tag.upper()[:18], get_font("mono", int(height * 0.019)), accent, tracking=3.0, anchor="ma")
            draw_tracked_text(d, (px, py + 2), ttl.upper()[:20], get_font("bold", int(height * 0.026)), TEXT_WHITE, tracking=1.0, anchor="ma")
        draw_source_attribution(d, source_tag, width, height, dot_color=accent)
        return canvas

    # ------------------------------------------------------------------
    # 16. process_flow_steps
    # ------------------------------------------------------------------
    if archetype == "process_flow_steps":
        canvas = make_pitch_black_canvas(width, height, halo_color=accent, halo_strength=0.14)
        d = ImageDraw.Draw(canvas)
        steps = [str(s) for s in (data.get("steps") or []) if str(s).strip()][:4]
        if len(steps) < 3:
            steps = ["TRIGGER", "CHAIN REACTION", "GLOBAL IMPACT"]
        d.text((int(width * 0.08), int(height * 0.14)), headline[:46], font=get_font("bold", int(height * 0.050)), fill=TEXT_WHITE)
        n = len(steps)
        gap = 54
        bw = int((width * 0.84 - gap * (n - 1)) / n)
        bh = int(height * 0.30)
        x0 = int(width * 0.08)
        y0 = int(height * 0.38)
        for idx, st in enumerate(steps):
            p = ease_out_cubic((t_now - 0.20 - idx * 0.45) / 0.40)
            if p <= 0.01:
                continue
            bx = x0 + idx * (bw + gap)
            col = accent if idx == n - 1 else ACCENT_BLUE
            d.rounded_rectangle([bx, y0 + int((1 - p) * 24), bx + bw, y0 + bh + int((1 - p) * 24)], radius=16, fill=CARD_DARK, outline=col, width=3)
            draw_tracked_text(d, (bx + 26, y0 + 28), f"STEP 0{idx+1}", get_font("mono", int(height * 0.021)), col, tracking=3.5, anchor="la")
            d.text((bx + 26, y0 + 82), st.upper()[:20], font=get_font("bold", int(height * 0.034)), fill=TEXT_WHITE)
            if idx < n - 1:
                ax = bx + bw + 10
                d.line([(ax, y0 + bh // 2), (ax + gap - 20, y0 + bh // 2)], fill=accent, width=5)
        draw_source_attribution(d, source_tag, width, height, dot_color=accent)
        return canvas

    # ------------------------------------------------------------------
    # 17. radar_alert_sweep
    # ------------------------------------------------------------------
    if archetype == "radar_alert_sweep":
        img = grade_live_backdrop(bg_rgb, width, height, prog, is_live_video, darken=0.56, vignette=0.65, grain_seed=frame_idx).convert("RGBA")
        ov = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        cx, cy = int(width * 0.68), int(height * 0.50)
        for r in (90, 175, 260):
            d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=accent + (115,), width=2)
        ang = t_now * 2.1
        d.line([(cx, cy), (cx + int(260 * math.cos(ang)), cy + int(260 * math.sin(ang)))], fill=accent + (235,), width=4)
        d.ellipse([cx - 10, cy - 10, cx + 10, cy + 10], fill=secondary + (255,))
        mx = int(width * 0.08)
        draw_tracked_text(d, (mx, int(height * 0.34)), f"MONITORING  •  {chapter}".upper()[:36], get_font("mono", int(height * 0.022)), secondary + (255,), tracking=3.5, anchor="la")
        f_h = get_font("bold", int(height * 0.054))
        for i_l, ln in enumerate(wrap_lines(d, headline, f_h, width * 0.44, max_lines=3)):
            d.text((mx, int(height * 0.40) + i_l * int(height * 0.072)), ln, font=f_h, fill=TEXT_WHITE + (255,))
        draw_source_attribution(d, source_tag, width, height, dot_color=secondary)
        return Image.alpha_composite(img, ov).convert("RGB")

    # ------------------------------------------------------------------
    # 18. spotlight_zoom_frame (Pure Cinema Footage + Minimal Corner Brackets)
    # ------------------------------------------------------------------
    if archetype == "spotlight_zoom_frame":
        img = grade_live_backdrop(bg_rgb, width, height, prog, is_live_video, darken=0.28, vignette=0.50, grain_seed=frame_idx).convert("RGBA")
        ov = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        # Subtle editorial viewfinder corners
        m, L = 54, 34
        col = accent + (190,)
        for (x1, y1, dx, dy) in [(m, m, L, L), (width - m, m, -L, L), (m, height - m, L, -L), (width - m, height - m, -L, -L)]:
            d.line([(x1, y1), (x1 + dx, y1)], fill=col, width=3)
            d.line([(x1, y1), (x1, y1 + dy)], fill=col, width=3)
        tp = ease_out_cubic(t_now / 0.50)
        d.rounded_rectangle([int(width * 0.06), int(height * 0.78), int(width * 0.06) + 6, int(height * 0.87)], radius=3, fill=accent + (int(255 * tp),))
        draw_tracked_text(d, (int(width * 0.075), int(height * 0.78)), chapter.upper()[:38], get_font("mono", int(height * 0.020)), accent + (int(240 * tp),), tracking=3.5, anchor="la")
        d.text((int(width * 0.075), int(height * 0.815)), headline[:54], font=get_font("bold", int(height * 0.042)), fill=TEXT_WHITE + (int(255 * tp),))
        draw_source_attribution(d, source_tag, width, height, dot_color=accent)
        return Image.alpha_composite(img, ov).convert("RGB")

    # ------------------------------------------------------------------
    # 19. kinetic_statement_stack
    # ------------------------------------------------------------------
    if archetype == "kinetic_statement_stack":
        canvas = make_pitch_black_canvas(width, height, halo_color=accent, halo_strength=0.16)
        d = ImageDraw.Draw(canvas)
        f_big = get_font("bold", int(height * 0.076))
        lines = wrap_lines(d, headline.upper(), f_big, width * 0.82, max_lines=3)
        lh = int(height * 0.115)
        sy = int((height - len(lines) * lh) * 0.48)
        for idx, ln in enumerate(lines):
            p = ease_out_back((t_now - 0.15 - idx * 0.35) / 0.42) if t_now > 0.15 + idx * 0.35 else 0.0
            if p <= 0.01:
                continue
            lw = d.textlength(ln, font=f_big)
            col = accent if idx == len(lines) - 1 else TEXT_WHITE
            d.text(((width - lw) / 2.0, sy + idx * lh + int((1 - clamp(p)) * 26)), ln, font=f_big, fill=_fade_color(col, BG_BLACK, clamp(p)))
        draw_source_attribution(d, source_tag, width, height, dot_color=accent)
        return canvas

    # ------------------------------------------------------------------
    # 20. two_stat_split_screen
    # ------------------------------------------------------------------
    img = grade_live_backdrop(bg_rgb, width, height, prog, is_live_video, darken=0.60, vignette=0.68, grain_seed=frame_idx).convert("RGBA")
    ov = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    metrics = data.get("metrics") or []
    if len(metrics) >= 2 and isinstance(metrics[0], dict) and isinstance(metrics[1], dict):
        m1_v, m1_l = str(metrics[0].get("value", "BEFORE")), str(metrics[0].get("label", "BASELINE"))
        m2_v, m2_l = str(metrics[1].get("value", "AFTER")), str(metrics[1].get("label", "NEW REALITY"))
    else:
        pref, end_v, suf = _extract_key_number(narration + " " + headline)
        m1_v, m1_l = f"{pref}{int(round(end_v * 0.4)):,}{suf}", "BASELINE"
        m2_v, m2_l = f"{pref}{int(round(end_v)):,}{suf}", headline[:24]
    p1 = ease_out_cubic(t_now / 0.45)
    p2 = ease_out_cubic((t_now - 0.65) / 0.50)
    f_v = get_font("bold", int(height * 0.125))
    f_l = get_font("mono", int(height * 0.023))
    draw_tracked_text(d, (width * 0.27, height * 0.37), m1_v, f_v, TEXT_MUTED + (int(240 * p1),), tracking=1.0, anchor="ma")
    draw_tracked_text(d, (width * 0.27, height * 0.56), m1_l.upper(), f_l, TEXT_WHITE + (int(220 * p1),), tracking=3.5, anchor="ma")
    if p2 > 0.01:
        d.line([(width * 0.45, height * 0.46), (width * 0.55, height * 0.46)], fill=accent + (int(255 * p2),), width=6)
        draw_tracked_text(d, (width * 0.73, height * 0.37), m2_v, f_v, accent + (int(255 * p2),), tracking=1.0, anchor="ma")
        draw_tracked_text(d, (width * 0.73, height * 0.56), m2_l.upper(), f_l, TEXT_WHITE + (int(240 * p2),), tracking=3.5, anchor="ma")
    draw_source_attribution(d, source_tag, width, height, dot_color=accent)
    return Image.alpha_composite(img, ov).convert("RGB")


# ===========================================================================
# V108 WORD-SYNCED LIVE CHOREOGRAPHY & INSTANT ANIMATED PROPS ENGINE
# ===========================================================================
# Fixes the "10-15 second static visual" problem by:
#   1. Computing exact per-word and per-sentence timestamps from audio["timings"].
#   2. Detecting spoken props (clock times like 12:00, years like 1958, locations
#      like Norway/Arctic, numbers/percentages like 51%, and key action stamps)
#      and popping animated vector props onto screen at the EXACT millisecond spoken.
#   3. Evolving the active sentence text & camera cadence on EVERY spoken sentence
#      so the screen is alive every 2-3 seconds instead of freezing for 12 seconds.

_COMMON_NON_PLACES = {
    "The", "This", "That", "These", "Those", "There", "Their", "They", "When", "Where",
    "What", "Which", "While", "With", "Without", "Within", "After", "Before", "Because",
    "However", "Although", "Meanwhile", "Inside", "Outside", "Under", "Over", "Across",
    "Between", "Through", "During", "Since", "Until", "About", "Against", "Around",
    "Today", "Tomorrow", "Yesterday", "Now", "Here", "Just", "Even", "Still", "Only",
    "Many", "Most", "Some", "More", "Less", "Every", "Each", "Both", "Such", "Into",
    "From", "For", "And", "But", "Not", "Yet", "All", "One", "Two", "Three", "Four",
    "Five", "First", "Second", "Third", "Last", "Next", "New", "Old", "Big", "High",
}


def _compute_word_timings(narration: str, audio: Optional[Dict[str, Any]], duration: float) -> List[Dict[str, Any]]:
    """Return exact [{text, start, end}] word timings from provider/Whisper or syllable-weighted fallback."""
    if audio and isinstance(audio.get("timings"), list) and len(audio["timings"]) >= 2:
        out = []
        for w in audio["timings"]:
            txt = str(w.get("text") or "").strip()
            if not txt:
                continue
            st = float(w.get("start", 0.0))
            en = float(w.get("end", st + 0.25))
            out.append({"text": txt, "start": st, "end": max(en, st + 0.08)})
        if out:
            return out

    tokens = [tok for tok in str(narration or "").split() if tok.strip()]
    if not tokens:
        return []
    weights = [max(2.0, float(len(re.sub(r"[^A-Za-z0-9]", "", tok))) + (2.5 if tok.endswith((".", "!", "?")) else 0.0)) for tok in tokens]
    total_w = sum(weights) or 1.0
    cur = 0.0
    dur = max(0.5, float(duration))
    out = []
    for tok, wgt in zip(tokens, weights):
        dt = dur * (wgt / total_w)
        out.append({"text": tok, "start": cur, "end": cur + dt})
        cur += dt
    return out


def build_beat_choreography(beat: Dict[str, Any], audio: Optional[Dict[str, Any]], duration: float) -> Dict[str, Any]:
    """
    Pre-compute per-sentence windows AND instant word-timed visual props for a beat.
    Called ONCE per beat before the frame loop in render_beat().
    """
    narration = str(beat.get("narration") or "").strip()
    words = _compute_word_timings(narration, audio, duration)

    # 1. Group words into exact timed sentences
    sentences: List[Dict[str, Any]] = []
    cur_words: List[Dict[str, Any]] = []
    for w in words:
        cur_words.append(w)
        if w["text"].endswith((".", "!", "?")) or len(cur_words) >= 16:
            sentences.append({
                "text": " ".join(x["text"] for x in cur_words),
                "start": cur_words[0]["start"],
                "end": cur_words[-1]["end"],
            })
            cur_words = []
    if cur_words:
        sentences.append({
            "text": " ".join(x["text"] for x in cur_words),
            "start": cur_words[0]["start"],
            "end": cur_words[-1]["end"],
        })
    if not sentences:
        sentences = [{"text": narration or str(beat.get("visual", {}).get("headline", "")), "start": 0.0, "end": max(0.5, duration)}]

    # 2. Scan timed words for instant visual props (Clock, Year, Metric, Location Pin)
    props: List[Dict[str, Any]] = []
    last_prop_t = -10.0
    for idx, w in enumerate(words):
        raw = w["text"]
        clean = raw.strip('.,!?;:"\'()[]')
        t_st = float(w["start"])
        is_high_prio = bool(re.match(r"^(\d{1,2}:\d{2}|18\d\d|19\d\d|20\d\d|[$€£]?\d[\d,\.]*(?:%|x|X|T|B|M|K)?)$", clean) or clean.lower() in {"midnight", "noon"})
        min_gap = 1.10 if is_high_prio else 1.95
        if t_st - last_prop_t < min_gap:
            continue
        # Cleanly end previous prop right before the new prop enters so they NEVER overlap
        if props and props[-1]["end"] > max(0.0, t_st - 0.14):
            props[-1]["end"] = max(props[-1]["start"] + 0.45, t_st - 0.14)

        # A) Clock time (e.g., 12:00, 3:30, midnight, noon)
        m_clock = re.match(r"^(\d{1,2}):(\d{2})$", clean)
        if m_clock or clean.lower() in {"midnight", "noon"}:
            hr = 12 if clean.lower() in {"midnight", "noon"} else int(m_clock.group(1))
            mn = 0 if clean.lower() in {"midnight", "noon"} else int(m_clock.group(2))
            props.append({
                "kind": "clock",
                "hour": hr % 12,
                "minute": mn % 60,
                "label": f"{hr:02d}:{mn:02d}" if m_clock else clean.upper(),
                "start": max(0.0, t_st - 0.12),
                "end": min(duration, t_st + 2.35),
            })
            last_prop_t = t_st
            continue

        # B) Historical / calendar year (e.g., 1958, 2026)
        if re.match(r"^(18\d\d|19\d\d|20\d\d)$", clean):
            props.append({
                "kind": "year",
                "value": clean,
                "label": "HISTORICAL MARKER" if int(clean) < 2020 else "TIMELINE YEAR",
                "start": max(0.0, t_st - 0.12),
                "end": min(duration, t_st + 2.30),
            })
            last_prop_t = t_st
            continue

        # C) Concrete figure / % / $ / multiplier (e.g. 51%, $10.4T, 38x, 1,200)
        if re.match(r"^([$€£]?\d[\d,\.]*(?:%|x|X|T|B|M|K)?)$", clean) and len(clean) <= 10:
            nxt = words[idx + 1]["text"].strip(".,!?;:") if idx + 1 < len(words) else ""
            unit = nxt.upper() if nxt.lower() in {"percent", "million", "billion", "trillion", "days", "hours", "years", "tons", "km", "miles", "mines", "ships"} else "KEY FIGURE"
            props.append({
                "kind": "metric",
                "value": clean.upper(),
                "label": unit,
                "start": max(0.0, t_st - 0.12),
                "end": min(duration, t_st + 2.25),
            })
            last_prop_t = t_st
            continue

        # D) Named location / country / proper noun (not sentence-initial filler)
        is_sent_start = (idx == 0) or words[idx - 1]["text"].endswith((".", "!", "?"))
        if (not is_sent_start) and re.match(r"^[A-Z][a-z]{3,}$", clean) and clean not in _COMMON_NON_PLACES:
            props.append({
                "kind": "location_pin",
                "value": clean.upper(),
                "label": "LOCATION FOCUS",
                "start": max(0.0, t_st - 0.10),
                "end": min(duration, t_st + 2.15),
            })
            last_prop_t = t_st
            continue

    return {
        "words": words,
        "sentences": sentences,
        "props": props,
        "duration": duration,
    }


def draw_live_prop_overlay(
    im: Image.Image,
    choreography: Dict[str, Any],
    t_now: float,
    accent: Tuple[int, int, int],
    secondary: Tuple[int, int, int],
) -> Image.Image:
    """
    Composite word-timed animated vector props (Clock Dial, Year Flip-Stamp,
    Radar Location Pin, Live Metric Pill) + live sentence focus tracker onto the frame.
    """
    if not choreography:
        return im
    w, h = im.size
    ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)

    # 1. Subtle top-right active prop widget synchronized to the EXACT spoken word
    active_prop = None
    for pr in choreography.get("props", []):
        if pr["start"] <= t_now <= pr["end"]:
            active_prop = pr
            break

    if active_prop is not None:
        p_dur = max(0.25, active_prop["end"] - active_prop["start"])
        local_t = t_now - active_prop["start"]
        enter = ease_out_back(local_t / 0.32) if local_t < 0.32 else 1.0
        exit_a = clamp((active_prop["end"] - t_now) / 0.25)
        alpha = clamp(min(enter, exit_a))
        ab = int(255 * alpha)
        card_a = int(232 * alpha)
        kind = active_prop["kind"]

        px1 = int(w * 0.955)
        py0 = int(h * 0.065) + int((1.0 - clamp(enter)) * 18)

        if kind == "clock":
            # Animated vector analog clock dial sweeping hands to the exact spoken hour:minute!
            box_w, box_h = int(w * 0.19), int(h * 0.165)
            px0 = px1 - box_w
            d.rounded_rectangle([px0, py0, px1, py0 + box_h], radius=16, fill=CARD_DARK + (card_a,), outline=accent + (ab,), width=3)
            cx = px0 + int(box_h * 0.50)
            cy = py0 + int(box_h * 0.50)
            r = int(box_h * 0.34)
            d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=TEXT_WHITE + (ab,), width=3)
            # 12 tick marks
            for tk in range(12):
                ang = math.radians(tk * 30 - 90)
                d.line([(cx + int((r - 7) * math.cos(ang)), cy + int((r - 7) * math.sin(ang))), (cx + int(r * math.cos(ang)), cy + int(r * math.sin(ang)))], fill=TEXT_MUTED + (ab,), width=2)
            # Hands sweep smoothly into exact spoken time!
            sweep = ease_out_expo(local_t / 0.65)
            target_h_deg = (active_prop["hour"] * 30 + active_prop["minute"] * 0.5) - 90
            target_m_deg = (active_prop["minute"] * 6) - 90
            h_ang = math.radians(-180 + (target_h_deg + 180) * sweep)
            m_ang = math.radians(-270 + (target_m_deg + 270) * sweep)
            d.line([(cx, cy), (cx + int(r * 0.52 * math.cos(h_ang)), cy + int(r * 0.52 * math.sin(h_ang)))], fill=TEXT_WHITE + (ab,), width=5)
            d.line([(cx, cy), (cx + int(r * 0.78 * math.cos(m_ang)), cy + int(r * 0.78 * math.sin(m_ang)))], fill=accent + (ab,), width=3)
            d.ellipse([cx - 5, cy - 5, cx + 5, cy + 5], fill=accent + (ab,))
            tx = cx + r + 22
            draw_tracked_text(d, (tx, py0 + int(box_h * 0.24)), "TIME MARKER", get_font("mono", int(h * 0.015)), TEXT_MUTED + (ab,), tracking=2.0, anchor="la")
            d.text((tx, py0 + int(box_h * 0.44)), active_prop["label"], font=get_font("bold", int(h * 0.044)), fill=accent + (ab,))

        elif kind == "year":
            # Flipping year stamp (e.g., 1958)
            box_w, box_h = int(w * 0.165), int(h * 0.135)
            px0 = px1 - box_w
            d.rounded_rectangle([px0, py0, px1, py0 + box_h], radius=14, fill=CARD_DARK + (card_a,), outline=accent + (ab,), width=3)
            draw_tracked_text(d, (px0 + 22, py0 + 18), active_prop["label"], get_font("mono", int(h * 0.015)), TEXT_MUTED + (ab,), tracking=2.5, anchor="la")
            d.text((px0 + 22, py0 + 44), active_prop["value"], font=get_font("bold", int(h * 0.058)), fill=accent + (ab,))
            bar_w = int((box_w - 44) * ease_out_expo(local_t / 0.55))
            if bar_w > 2:
                d.rounded_rectangle([px0 + 22, py0 + box_h - 14, px0 + 22 + bar_w, py0 + box_h - 8], radius=3, fill=accent + (ab,))

        elif kind == "metric":
            # Instant glowing stat pill
            box_w, box_h = int(w * 0.185), int(h * 0.135)
            px0 = px1 - box_w
            d.rounded_rectangle([px0, py0, px1, py0 + box_h], radius=14, fill=CARD_DARK + (card_a,), outline=accent + (ab,), width=3)
            draw_tracked_text(d, (px0 + 22, py0 + 18), active_prop["label"][:18], get_font("mono", int(h * 0.015)), TEXT_MUTED + (ab,), tracking=2.5, anchor="la")
            d.text((px0 + 22, py0 + 44), active_prop["value"], font=get_font("bold", int(h * 0.056)), fill=accent + (ab,))

        elif kind == "location_pin":
            # Pulsing radar pin + location badge
            f_loc = get_font("bold", int(h * 0.030))
            lw = int(d.textlength(active_prop["value"], font=f_loc))
            box_w = max(int(w * 0.16), lw + 96)
            box_h = int(h * 0.095)
            px0 = px1 - box_w
            d.rounded_rectangle([px0, py0, px1, py0 + box_h], radius=14, fill=CARD_DARK + (card_a,), outline=secondary + (ab,), width=2)
            pcx, pcy = px0 + 38, py0 + box_h // 2
            pulse = (local_t * 2.2) % 1.0
            rr = int(10 + 18 * pulse)
            d.ellipse([pcx - rr, pcy - rr, pcx + rr, pcy + rr], outline=secondary + (int(190 * (1 - pulse) * alpha),), width=2)
            d.ellipse([pcx - 8, pcy - 8, pcx + 8, pcy + 8], fill=secondary + (ab,))
            draw_tracked_text(d, (px0 + 68, py0 + 16), "LOCATION", get_font("mono", int(h * 0.014)), TEXT_MUTED + (ab,), tracking=2.5, anchor="la")
            d.text((px0 + 68, py0 + 38), active_prop["value"], font=f_loc, fill=TEXT_WHITE + (ab,))

    # 2. Subtle hairline beat progress bar at very top edge (2px) so viewer feels continuous motion
    dur = max(0.5, float(choreography.get("duration", 4.0)))
    pw = int(w * clamp(t_now / dur))
    if pw > 2:
        d.rectangle([0, 0, pw, 4], fill=accent + (200,))

    return Image.alpha_composite(im.convert("RGBA"), ov).convert("RGB")


def render_v108_synced_beat_frame(
    beat: Dict[str, Any],
    dossier: Dict[str, Any],
    t_now: float,
    duration: float,
    bg_rgb: Optional[np.ndarray],
    width: int,
    height: int,
    choreography: Optional[Dict[str, Any]] = None,
    frame_idx: int = 0,
    is_live_video: bool = False,
) -> Image.Image:
    """
    V108 Word-Synced Wrapper around the 20 V107 archetypes:
      - Automatically rotates the displayed narration/highlight to the EXACT sentence
        currently being spoken at t_now (resetting local animation time on each sentence
        so visuals stay alive and punchy every 2.5-4.0 seconds instead of freezing!).
      - Composites instant word-timed vector props (Clock, Year, Metric, Location Pin)
        at the exact millisecond each trigger word is spoken.
    """
    vis = beat.get("visual") or {}
    category = str(vis.get("v107_category") or dossier.get("category") or "geopolitics")
    theme = get_category_theme(category)
    accent = theme["primary"]
    secondary = theme["secondary"]

    active_beat = beat
    local_t = t_now
    local_dur = duration
    if choreography and len(choreography.get("sentences", [])) >= 2:
        sents = choreography["sentences"]
        cur_s = sents[-1]
        for s in sents:
            if s["start"] <= t_now <= s["end"] + 0.12:
                cur_s = s
                break
        # Feed ONLY the currently spoken sentence + its local elapsed time so
        # pull-quotes, headlines, highlights & checklists re-animate on EVERY sentence!
        active_beat = dict(beat)
        active_beat["narration"] = cur_s["text"]
        local_t = max(0.0, t_now - cur_s["start"])
        local_dur = max(0.8, cur_s["end"] - cur_s["start"])

    frame = render_v107_beat_frame(
        active_beat, dossier, local_t, local_dur, bg_rgb, width, height,
        frame_idx=frame_idx, is_live_video=is_live_video,
    )
    if choreography:
        frame = draw_live_prop_overlay(frame, choreography, t_now, accent, secondary)
    return frame
