"""Native-resolution 4-Format broadcast motion graphics, 208-country vector cartography, and full-frame media."""
import functools
import math
import os
import subprocess
import wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
from .common import StudioError, ffmpeg, run_ff
from .voice import captions
from .world_atlas import load_world_polygons, lookup_gazetteer
from .satellite_map import fetch_satellite_basemap
from .v107_minimal_cinema import render_v107_beat_frame
from .v98_cinema_fx import (
    anamorphic_light_leak_transition,
    apply_cinema_film_finish,
    directional_whip_pan,
    detect_face_focus_center,
    spring_ease,
)

INK = (12, 19, 30)
PANEL = (23, 34, 49)
WHITE = (242, 239, 228)
MUTED = (151, 167, 182)
ACCENT = (255, 139, 83)
TEAL = (95, 211, 200)

STYLE_THEMES = {
    "bbc_dispatch": {
        "ink": (11, 17, 28),
        "panel": (20, 30, 46),
        "accent": (225, 29, 72),
        "secondary": (56, 189, 248),
        "badge": "BBC GLOBAL DISPATCH • LIVE",
    },
    "think_school": {
        "ink": (9, 18, 32),
        "panel": (18, 33, 56),
        "accent": (16, 185, 129),
        "secondary": (245, 158, 11),
        "badge": "STRATEGIC CASE STUDY",
    },
    "nitish_rajput": {
        "ink": (10, 12, 20),
        "panel": (22, 26, 40),
        "accent": (239, 68, 68),
        "secondary": (245, 158, 11),
        "badge": "FORENSIC DOSSIER • EVIDENCE FILE",
    },
    "abhi_niyu": {
        "ink": (11, 21, 32),
        "panel": (21, 37, 54),
        "accent": (20, 184, 166),
        "secondary": (255, 107, 107),
        "badge": "WHY THIS MATTERS • IMPACT EXPLAINER",
    },
}


@functools.lru_cache(maxsize=120)
def font(size, bold=False):
    choices = [
        os.getenv("WTB_FONT_BOLD" if bold else "WTB_FONT", ""),
        "/usr/share/fonts/opentype/inter/InterDisplay-" + ("ExtraBold" if bold else "Medium") + ".otf",
        "/usr/share/fonts/truetype/inter/InterDisplay-" + ("ExtraBold" if bold else "Medium") + ".ttf",
        "/usr/share/fonts/truetype/inter/Inter-" + ("Bold" if bold else "Regular") + ".ttf",
        "/usr/share/fonts/opentype/inter/Inter-" + ("Bold" if bold else "Regular") + ".otf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans" + ("-Bold" if bold else "") + ".ttf",
        "C:/Windows/Fonts/" + ("arialbd.ttf" if bold else "arial.ttf"),
    ]
    for path in choices:
        if path and Path(path).exists():
            return ImageFont.truetype(path, max(10, int(size)))
    return ImageFont.load_default(size=max(10, int(size)))


def wrap(draw, text, f, width):
    lines, current = [], ""
    for word in str(text).split():
        test = (current + " " + word).strip()
        if draw.textlength(test, font=f) > width and current:
            lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)
    return lines


def text_block(im, text, box, size, color=WHITE, bold=False, max_lines=4):
    d = ImageDraw.Draw(im)
    x, y, w, h = box
    lines = [str(text)]
    f = font(max(12, int(size)), bold)
    for s in range(max(12, int(size)), 11, -2):
        f = font(s, bold)
        lines = wrap(d, text, f, w)
        if len(lines) <= max_lines and len(lines) * s * 1.28 <= h:
            break
    for line in lines[:max_lines]:
        d.text((x, y), line, font=f, fill=color)
        y += f.size * 1.28
    return y


def ease(t):
    t = max(0.0, min(1.0, float(t)))
    return 1.0 - (1.0 - t) ** 3


class Canvas:
    def __init__(self, beat, dossier, width, height):
        self.beat, self.w, self.h = beat, width, height
        self.s = min(width / 1920, height / 1080)
        self.portrait = height > width
        if self.portrait:
            self.s = width / 1080
        self.pad = int(width * 0.055)
        self.style_key = beat.get("style") or dossier.get("style") or "think_school"
        self.theme = STYLE_THEMES.get(self.style_key, STYLE_THEMES["think_school"])
        self.ink = self.theme["ink"]
        self.panel = self.theme["panel"]
        self.accent = self.theme["accent"]
        self.secondary = self.theme["secondary"]
        self.facts = {f["id"]: f for f in dossier["facts"]}
        self.sources = {s["id"]: s for s in dossier["sources"]}
        self.bg = Image.new("RGB", (width, height), self.ink)
        d = ImageDraw.Draw(self.bg)
        for y in range(height):
            glow = max(0.0, 1.0 - abs(y / height - 0.42))
            d.line(
                (0, y, width, y),
                fill=(
                    int(self.ink[0] + 6 * glow),
                    int(self.ink[1] + 10 * glow),
                    int(self.ink[2] + 16 * glow),
                ),
            )
        step = max(32, int(88 * self.s))
        for x in range(0, width, step):
            d.line((x, 0, x, height), fill=(self.ink[0] + 12, self.ink[1] + 16, self.ink[2] + 22))
        for y in range(0, height, step):
            d.line((0, y, width, y), fill=(self.ink[0] + 12, self.ink[1] + 16, self.ink[2] + 22))
        self.still = None
        self.extra_stills = []
        self.secondary_still = None
        if beat.get("asset") and beat["asset"]["kind"] == "photo" and Path(beat["asset"]["path"]).exists():
            self.still = Image.open(beat["asset"]["path"]).convert("RGB")
            self.extra_stills.append(self.still)
        for ea in beat.get("extra_assets", []):
            if ea.get("kind") == "photo" and ea.get("path") and Path(ea["path"]).exists():
                try:
                    self.extra_stills.append(Image.open(ea["path"]).convert("RGB"))
                except Exception:
                    pass
        self.beat_num = int("".join(ch for ch in str(beat.get("id", "1")) if ch.isdigit()) or 1)
        sec_path = beat["visual"].get("data", {}).get("secondary_photo_path")
        if sec_path and Path(sec_path).exists():
            self.secondary_still = Image.open(sec_path).convert("RGB")
        self.overlay = self.make_overlay()

    def make_overlay(self):
        w, h, p, s = self.w, self.h, self.pad, self.s
        layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        kind = self.beat["visual"]["kind"]
        media = (kind in {"photo", "footage"} and (self.beat.get("asset") or self.still is not None)) or kind == "globe"
        if media:
            # 100% Full-Screen Cinema Footage/Photo: only a light bottom gradient for crisp captions!
            top_h = int(h * 0.12)
            bot_y = int(h * 0.76)
            for y in range(top_h):
                alpha = int(125 * max(0.0, 1.0 - y / top_h) ** 1.5)
                d.line((0, y, w, y), fill=(*self.ink, alpha))
            for y in range(bot_y, h):
                alpha = int(205 * ((y - bot_y) / max(1, h - bot_y)) ** 1.3)
                d.line((0, y, w, y), fill=(*self.ink, alpha))
        else:
            # Clean top header bar for graphic beats
            d.rectangle((0, 0, w, int(h * 0.25)), fill=(*self.ink, 210))
            d.line((p, int(h * 0.25), w - p, int(h * 0.25)), fill=(*self.accent, 110), width=max(1, int(2 * s)))

        # Mode badge pill at top-left
        badge_text = self.beat["visual"].get("data", {}).get("mode_badge") or self.theme["badge"]
        bf = font(int(19 * s), True)
        bw = int(d.textlength(badge_text, font=bf) + 28 * s)
        bh = int(34 * s)
        bx, by = p, int(h * 0.042)
        d.rounded_rectangle((bx, by, bx + bw, by + bh), radius=int(6 * s), fill=(*self.accent, 235))
        d.text((bx + int(14 * s), by + int(6 * s)), badge_text, font=bf, fill=WHITE)

        # Chapter & Channel tag to the right of badge
        chap = (self.beat.get("chapter") or "WORLD TALK BRIEF").upper()
        text_block(
            layer,
            f"WORLD TALK BRIEF  //  {chap}",
            (bx + bw + int(18 * s), int(h * 0.047), w - (bx + bw + p * 2), int(36 * s)),
            21 * s,
             self.secondary if not media else WHITE,
            True,
            1,
        )

        # Only draw top headline on graphic beats; on full-screen footage/photo beats keep the picture 100% unobstructed!
        if not media or kind == "globe":
            hl_size = 54 * s if not self.portrait else 44 * s
            hl_y = int(h * 0.095)
            hl_h = int(h * 0.145)
            text_block(layer, self.beat["visual"]["headline"], (p, hl_y, w - p * 2, hl_h), hl_size, WHITE, True, 2)

        # Bottom attribution & source bar
        source_ids = []
        for fid in self.beat["fact_ids"]:
            if fid in self.facts:
                for e in self.facts[fid]["evidence"]:
                    if e["source_id"] not in source_ids:
                        source_ids.append(e["source_id"])
        names = "  •  ".join(self.sources[x].get("domain", x) for x in source_ids[:3] if x in self.sources)
        if not names:
            names = "VERIFIED BROADCAST DOSSIER"
        asset = self.beat.get("asset")
        label = (
            asset["label"]
            if asset
            else {
                "chart": "VERIFIED DATA SCALE",
                "stat_callout": "KEY IMPACT METRICS",
                "actor_split": "HEAD-TO-HEAD STRATEGIC COMPARISON",
                "evidence_board": "FORENSIC EVIDENCE NETWORK",
                "evidence": "PRIMARY SOURCE RECORD",
                "timeline": "DOCUMENTED CHRONOLOGY",
                "diagram": "CAUSAL MECHANISM CHAIN",
                "globe": "208-COUNTRY TACTICAL CARTOGRAPHY",
                "model3d": "3D TELEMETRY MODEL",
            }.get(kind, "VERIFIED SOURCE RECORD")
        )
        text_block(layer, f"{label}   |   SOURCES: {names}", (p, int(h * 0.935), w - p * 2, int(h * 0.045)), 18 * s, self.secondary, True, 1)
        if asset and asset.get("creator"):
            credit = f"{asset['creator'][:80]} ({asset.get('license', 'Verified')})"
            text_block(layer, credit, (p, int(h * 0.895), w - p * 2, int(h * 0.035)), 16 * s, MUTED, False, 1)
        return layer

    def _camera_shot(self, img_src, local_t, shot_dur, shot_idx):
        w, h = self.w, self.h
        prog = min(1.0, max(0.0, local_t / max(0.2, shot_dur)))
        mode = (self.beat_num + shot_idx) % 4
        if mode == 0:  # Dramatic push-in zoom
            z = 1.03 + 0.11 * ease(prog)
            px_r, py_r = 0.5, 0.45
        elif mode == 1:  # Smooth pull-out reveal
            z = 1.14 - 0.09 * ease(prog)
            px_r, py_r = 0.45 + 0.1 * prog, 0.45
        elif mode == 2:  # Left-to-right documentary pan
            z = 1.10
            px_r, py_r = 0.20 + 0.60 * ease(prog), 0.45
        else:  # Right-to-left pan + slight zoom
            z = 1.06 + 0.06 * prog
            px_r, py_r = 0.80 - 0.60 * ease(prog), 0.42
        fcx, fcy = detect_face_focus_center(img_src)
        fitted = ImageOps.fit(img_src, (int(w * z), int(h * z)), method=Image.Resampling.BICUBIC, centering=(fcx, fcy))
        pan_x = max(0, min(fitted.width - w, int((fitted.width - w) * px_r)))
        pan_y = max(0, min(fitted.height - h, int((fitted.height - h) * (fcy if fcy != 0.45 else py_r))))
        shot = fitted.crop((pan_x, pan_y, pan_x + w, pan_y + h))
        # V98 Cinema Film Finish: S-curve contrast + teal/amber grade + radial vignette + 35mm grain
        seed = int(self.beat_num * 1000 + shot_idx * 100 + local_t * 24)
        return apply_cinema_film_finish(shot, frame_seed=seed, grain_amount=3.8, vignette_strength=0.28)

    def _render_full_bleed_still(self, img_src, t, duration):
        w, h, s, p = self.w, self.h, self.s, self.pad
        stills = self.extra_stills if self.extra_stills else [img_src]
        n_shots = len(stills)
        shot_dur = max(3.2, duration / max(1, n_shots))
        shot_idx = min(n_shots - 1, int(t / shot_dur))
        local_t = t - shot_idx * shot_dur
        cropped = self._camera_shot(stills[shot_idx], local_t, shot_dur, shot_idx)

        # V98 After-Effects-Grade 0.30s Transition: OpenCV 1D Motion-Blur Whip-Pan or Anamorphic Light-Leak
        if shot_idx > 0 and local_t < 0.30:
            prev_im = self._camera_shot(stills[shot_idx - 1], shot_dur, shot_dur, shot_idx - 1)
            alpha = local_t / 0.30
            if shot_idx % 2 == 1:
                cropped = directional_whip_pan(prev_im, cropped, alpha)
            else:
                cropped = anamorphic_light_leak_transition(prev_im, cropped, alpha)

        return self._draw_kinetic_callout_vfx(cropped, t, duration)

    def _draw_kinetic_callout_vfx(self, base_im, t, duration):
        """V103 Kinetic Draw-On VFX: animated stroke border drawing itself, sweeping gold underline, pulsing live dot & spring pop-in."""
        w, h, s, p = self.w, self.h, self.s, self.pad
        data = self.beat["visual"].get("data", {})
        callout = data.get("callout") or data.get("metric_badge")
        if not callout and t >= 0.35 and t <= min(4.8, duration - 0.3):
            hl_words = [w_s for w_s in str(self.beat["visual"].get("headline", "")).split() if len(w_s) > 2][:4]
            callout = " ".join(hl_words) if hl_words else ""
        layer = base_im.convert("RGBA")
        d = ImageDraw.Draw(layer)
        # V104 Vox / Johnny Harris Draw-On Corner Focus Brackets (animating smoothly inward during first 0.55s)
        brk_p = ease(min(1.0, max(0.0, t / 0.55)))
        inset = int((42 - 18 * brk_p) * s)
        blen = int(34 * s * brk_p)
        b_col = (*self.accent, int(195 * brk_p))
        bw = max(2, int(3 * s))
        if blen > 4:
            # Top-left & Top-right brackets
            d.line((inset, inset, inset + blen, inset), fill=b_col, width=bw)
            d.line((inset, inset, inset, inset + blen), fill=b_col, width=bw)
            d.line((w - inset, inset, w - inset - blen, inset), fill=b_col, width=bw)
            d.line((w - inset, inset, w - inset, inset + blen), fill=b_col, width=bw)
            # Bottom-left & Bottom-right brackets above safe caption zone
            by = int(h * (0.86 if self.portrait else 0.90))
            d.line((inset, by, inset + blen, by), fill=b_col, width=bw)
            d.line((inset, by, inset, by - blen), fill=b_col, width=bw)
            d.line((w - inset, by, w - inset - blen, by), fill=b_col, width=bw)
            d.line((w - inset, by, w - inset, by - blen), fill=b_col, width=bw)
        # Subtle pulsing live editorial telemetry dot in top-right corner
        pulse = 0.55 + 0.45 * math.sin(t * 5.2)
        rx, ry = w - p - int(18 * s), int(34 * s)
        d.ellipse((rx - int(10 * s), ry - int(10 * s), rx + int(10 * s), ry + int(10 * s)), fill=(*self.accent, int(90 * pulse)))
        d.ellipse((rx - int(5 * s), ry - int(5 * s), rx + int(5 * s), ry + int(5 * s)), fill=(*self.accent, 245))
        if callout and t >= 0.30:
            pop = max(0.0, min(1.04, spring_ease(min(1.0, (t - 0.30) / 0.48))))
            draw_prog = ease(min(1.0, max(0.0, (t - 0.35) / 0.65)))
            cw, ch = int(w * (0.66 if self.portrait else 0.36)), int(88 * s)
            cx = int(p - (1.0 - pop) * 110 * s)
            cy = int(h * (0.115 if self.portrait else 0.60))
            # Glass panel + animated draw-on accent bar & bottom sweeping underline
            d.rounded_rectangle((cx, cy, cx + cw, cy + ch), radius=int(10 * s), fill=(*self.ink, int(224 * pop)))
            # Vertical bar draws top-to-bottom
            bar_h = int(ch * draw_prog)
            d.rectangle((cx, cy, cx + int(9 * s), cy + bar_h), fill=(*self.accent, 255))
            # Top & bottom glowing border lines draw left-to-right
            line_w = int(cw * draw_prog)
            d.line((cx, cy, cx + line_w, cy), fill=(*self.accent, 240), width=max(2, int(3 * s)))
            d.line((cx, cy + ch, cx + line_w, cy + ch), fill=(250, 204, 21, 220), width=max(2, int(3 * s)))
            text_block(layer, str(callout).upper(), (cx + int(22 * s), cy + int(12 * s), cw - int(32 * s), int(34 * s)), 24 * s, (254, 240, 138), True, 1)
            sub = (data.get("callout_sub") or self.beat.get("chapter", "WORLD TALK BRIEF")).upper()[:54]
            text_block(layer, sub, (cx + int(22 * s), cy + int(50 * s), cw - int(32 * s), int(26 * s)), 16 * s, WHITE, False, 1)
        return layer.convert("RGB")

    def frame(self, t, duration, video_frame=None):
        w, h, s, p = self.w, self.h, self.s, self.pad
        kind = self.beat["visual"]["kind"]
        data = self.beat["visual"].get("data", {})
        im = self.bg.copy()
        if video_frame is not None and kind == "footage":
            im = Image.frombytes("RGB", (w, h), video_frame)
            im = apply_cinema_film_finish(im, frame_seed=int(t * 24), grain_amount=2.5, vignette_strength=0.25)
            im = self._draw_kinetic_callout_vfx(im, t, duration)
        elif self.still is not None and kind in {"photo", "footage"}:
            im = self._render_full_bleed_still(self.still, t, duration)
        elif self.extra_stills and kind in {"photo", "footage"}:
            im = self._render_full_bleed_still(self.extra_stills[0], t, duration)
        else:
            d = ImageDraw.Draw(im)
            top, bottom = (int(h * 0.24), int(h * 0.60)) if self.portrait else (int(h * 0.285), int(h * 0.775))
            if kind == "chart":
                self.draw_chart(im, d, t, top, bottom, data)
            elif kind == "stat_callout":
                self.draw_stat_callout(im, d, t, top, bottom, data)
            elif kind == "actor_split":
                self.draw_actor_split(im, d, t, top, bottom, data)
            elif kind == "evidence_board":
                self.draw_evidence_board(im, d, t, top, bottom, data)
            elif kind in {"timeline", "diagram"}:
                self.draw_timeline_or_diagram(im, d, t, top, bottom, kind, data)
            elif kind == "model3d":
                self.container(im, t, top, bottom)
            elif kind == "globe" and data.get("resolved_places"):
                self.globe(im, t, top, bottom, data["resolved_places"])
            else:
                self.draw_evidence_card(im, d, t, top, bottom, data)

        im = Image.alpha_composite(im.convert("RGBA"), self.overlay)
        d = ImageDraw.Draw(im)
        d.rectangle((0, h - int(5 * s), int(w * min(1.0, t / max(0.1, duration))), h), fill=self.accent)
        return im.convert("RGB")

    def _paint_cinema_backdrop(self, im, blur_radius=18, tint_alpha=188):
        """Paints a rich blurred cinema image behind graphic cards so nothing ever looks like a flat PowerPoint slide."""
        w, h = self.w, self.h
        src = self.still or self.secondary_still
        if src is not None:
            bg_blur = ImageOps.fit(src, (w, h), method=Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(radius=blur_radius))
            tint = Image.new("RGBA", (w, h), (*self.ink, tint_alpha))
            comp = Image.alpha_composite(bg_blur.convert("RGBA"), tint).convert("RGB")
            im.paste(comp, (0, 0))
            return ImageDraw.Draw(im)
        return ImageDraw.Draw(im)

    def draw_chart(self, im, d, t, top, bottom, data):
        w, h, s, p = self.w, self.h, self.s, self.pad
        points = data["points"]
        values = [x["value"] for x in points]
        lo, hi = min(0, min(values)), max(0, max(values))
        span = (hi - lo) or 1
        left, right = p + int(w * 0.22), w - p - int(w * 0.10)
        zero = left + (0 - lo) / span * (right - left)
        d.rounded_rectangle((p, top - int(35 * s), w - p, bottom + int(35 * s)), radius=int(14 * s), fill=self.panel, outline=(*self.secondary, 80), width=max(1, int(2 * s)))
        d.line((zero, top - int(10 * s), zero, bottom + int(15 * s)), fill=MUTED, width=max(1, int(s * 2)))
        text_block(im, f"UNIT: {data['unit'].upper()}", (left, top - int(28 * s), right - left, int(32 * s)), 21 * s, self.secondary, True, 1)
        row = (bottom - top - int(20 * s)) / len(points)
        for i, point in enumerate(points):
            y = top + int(18 * s) + i * row
            pos = left + (point["value"] - lo) / span * (right - left)
            end = zero + (pos - zero) * ease(max(0.0, t - i * 0.12) / 1.0)
            bar_col = self.accent if i == len(points) - 1 else self.secondary
            d.rounded_rectangle(
                (min(zero, end), y, max(zero, end) + max(4, int(4 * s)), y + row * 0.54),
                radius=max(1, int(6 * s)),
                fill=bar_col,
            )
            text_block(im, point["label"], (p + int(22 * s), y, int(w * 0.19), row * 0.7), 26 * s, WHITE, True, 2)
            text_block(
                im,
                f"{point['value']:g} {data['unit']}",
                (min(w - p - int(190 * s), max(end, zero) + int(16 * s)), y + int(2 * s), int(180 * s), row * 0.7),
                26 * s,
                WHITE,
                True,
                1,
            )

    def draw_stat_callout(self, im, d, t, top, bottom, data):
        import re as _re
        d = self._paint_cinema_backdrop(im, blur_radius=16, tint_alpha=182)
        w, h, s, p = self.w, self.h, self.s, self.pad
        metrics = data.get("metrics", [{"value": "100%", "label": "Verified Metric"}])
        n = len(metrics)
        gap = int(24 * s)

        def _animate_val(raw_val, frac):
            m = _re.match(r"^([^0-9.-]*)([0-9]+(?:\.[0-9]+)?)(.*)$", str(raw_val).strip())
            if not m:
                return str(raw_val)
            pref, num_s, suff = m.groups()
            target_n = float(num_s)
            cur_n = target_n * frac
            if "." in num_s:
                return f"{pref}{cur_n:.1f}{suff}"
            return f"{pref}{int(round(cur_n)):,}{suff}"

        if self.portrait:
            # Vertical stacked glassmorphism impact cards filling the safe portrait frame cleanly!
            card_h = min(int(265 * s), int((bottom - top - gap * (n - 1)) / max(1, n)))
            total_stack = n * card_h + (n - 1) * gap
            start_y = top + max(0, (bottom - top - total_stack) // 2)
            for i, m in enumerate(metrics):
                frac = ease(max(0.0, t - i * 0.20) / 0.95)
                y = start_y + i * (card_h + gap) + int(16 * s * (1.0 - frac))
                col = self.accent if i == 0 else self.secondary
                d.rounded_rectangle((p, y, w - p, y + card_h), radius=int(16 * s), fill=(*self.panel, 235), outline=col, width=max(2, int(3 * s)))
                d.rectangle((p, y, p + int(12 * s), y + card_h), fill=col)
                anim_v = _animate_val(m.get("value", ""), frac)
                text_block(im, anim_v, (p + int(34 * s), y + int(24 * s), int((w - p * 2) * 0.44), int(120 * s)), 84 * s, WHITE, True, 1)
                rx = p + int((w - p * 2) * 0.46)
                rw = w - p - rx - int(22 * s)
                text_block(im, str(m.get("label", "")).upper(), (rx, y + int(34 * s), rw, int(74 * s)), 30 * s, col, True, 2)
                if m.get("sub"):
                    text_block(im, str(m["sub"]), (rx, y + int(116 * s), rw, int(72 * s)), 22 * s, MUTED, False, 2)
                bar_w = int((w - p * 2 - 68 * s) * frac)
                d.rounded_rectangle((p + int(34 * s), y + card_h - int(28 * s), p + int(34 * s) + bar_w, y + card_h - int(14 * s)), radius=int(5 * s), fill=col)
            return

        cw = (w - p * 2 - gap * (n - 1)) / n
        ch = bottom - top
        for i, m in enumerate(metrics):
            frac = ease(max(0.0, t - i * 0.18) / 0.95)
            x = p + i * (cw + gap)
            y = top + int(18 * s * (1.0 - frac))
            col = self.accent if i == 0 else self.secondary
            d.rounded_rectangle((x, y, x + cw, y + ch), radius=int(16 * s), fill=self.panel, outline=col, width=max(2, int(3 * s)))
            d.rectangle((x, y, x + cw, y + int(10 * s)), fill=col)
            text_block(im, f"KEY METRIC 0{i+1}", (x + int(26 * s), y + int(28 * s), cw - int(52 * s), int(34 * s)), 19 * s, MUTED, True, 1)
            anim_v = _animate_val(m.get("value", ""), frac)
            text_block(im, anim_v, (x + int(26 * s), y + int(76 * s), cw - int(52 * s), int(125 * s)), 74 * s, WHITE, True, 1)
            text_block(im, str(m.get("label", "")).upper(), (x + int(26 * s), y + int(212 * s), cw - int(52 * s), int(80 * s)), 26 * s, col, True, 2)
            if m.get("sub"):
                text_block(im, str(m["sub"]), (x + int(26 * s), y + int(294 * s), cw - int(52 * s), int(75 * s)), 20 * s, MUTED, False, 2)
            bar_w = int((cw - 52 * s) * frac)
            d.rounded_rectangle((x + int(26 * s), y + ch - int(36 * s), x + int(26 * s) + bar_w, y + ch - int(22 * s)), radius=int(5 * s), fill=col)

    def draw_actor_split(self, im, d, t, top, bottom, data):
        d = self._paint_cinema_backdrop(im, blur_radius=20, tint_alpha=198)
        w, h, s, p = self.w, self.h, self.s, self.pad
        gap = int(64 * s)
        cw = (w - p * 2 - gap) / 2
        ch = bottom - top
        sides = [
            (p, data.get("left_title", "CONTENDER A"), data.get("left_points", []), self.accent, self.still),
            (p + cw + gap, data.get("right_title", "CONTENDER B"), data.get("right_points", []), self.secondary, self.secondary_still),
        ]
        for idx, (x, title, pts, col, thumb) in enumerate(sides):
            frac = ease(max(0.0, t - idx * 0.2) / 0.8)
            y = top + int(14 * s * (1.0 - frac))
            d.rounded_rectangle((x, y, x + cw, y + ch), radius=int(14 * s), fill=self.panel, outline=col, width=max(1, int(3 * s)))
            d.rounded_rectangle((x, y, x + cw, y + int(68 * s)), radius=int(14 * s), fill=col)
            text_block(im, str(title).upper(), (x + int(22 * s), y + int(16 * s), cw - int(44 * s), int(42 * s)), 28 * s, WHITE if idx == 0 else self.ink, True, 1)
            content_y = y + int(86 * s)
            if thumb is not None:
                th_h = int(ch * 0.36)
                th_im = ImageOps.fit(thumb, (int(cw - 36 * s), th_h), method=Image.Resampling.BICUBIC)
                im.paste(th_im, (int(x + 18 * s), int(content_y)))
                content_y += th_h + int(18 * s)
            for p_i, pt in enumerate(pts[:3]):
                d.ellipse((x + int(24 * s), content_y + int(8 * s), x + int(36 * s), content_y + int(20 * s)), fill=col)
                text_block(im, str(pt), (x + int(48 * s), content_y, cw - int(68 * s), int(58 * s)), 23 * s, WHITE, True, 2)
                content_y += int(62 * s)
        # Center VS medallion
        cx, cy = w // 2, (top + bottom) // 2
        r = int(34 * s)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=self.ink, outline=WHITE, width=max(2, int(3 * s)))
        vf = font(int(24 * s), True)
        tw = d.textlength("VS", font=vf)
        d.text((cx - tw / 2, cy - int(14 * s)), "VS", font=vf, fill=WHITE)

    def draw_evidence_board(self, im, d, t, top, bottom, data):
        w, h, s, p = self.w, self.h, self.s, self.pad
        nodes = data.get("nodes", [])
        n = len(nodes)
        gap = int(32 * s)
        cw = (w - p * 2 - gap * (n - 1)) / max(1, n)
        ch = (bottom - top) * 0.84
        centers = []
        for i, node in enumerate(nodes):
            x = p + i * (cw + gap)
            y = top + (int(28 * s) if i % 2 == 1 else 0)
            centers.append((x + cw / 2, y + int(18 * s)))
        # Red forensic connecting threads between pins
        for i in range(len(centers) - 1):
            c1, c2 = centers[i], centers[i + 1]
            prog = ease(max(0.0, t - i * 0.25) / 0.7)
            ex = c1[0] + (c2[0] - c1[0]) * prog
            ey = c1[1] + (c2[1] - c1[1]) * prog
            d.line((c1[0], c1[1], ex, ey), fill=(239, 68, 68), width=max(2, int(4 * s)))
        for i, node in enumerate(nodes):
            frac = ease(max(0.0, t - i * 0.22) / 0.75)
            x = p + i * (cw + gap)
            y = top + (int(28 * s) if i % 2 == 1 else 0)
            d.rounded_rectangle((x, y, x + cw, y + ch), radius=int(12 * s), fill=self.panel, outline=(239, 68, 68) if i == n - 1 else self.secondary, width=max(1, int(2 * s)))
            # Forensic pin at top center
            px, py = centers[i]
            d.ellipse((px - int(9 * s), py - int(9 * s), px + int(9 * s), py + int(9 * s)), fill=(239, 68, 68), outline=WHITE, width=max(1, int(2 * s)))
            tag = str(node.get("tag", f"EVIDENCE 0{i+1}")).upper()
            text_block(im, tag, (x + int(20 * s), y + int(34 * s), cw - int(40 * s), int(32 * s)), 19 * s, self.secondary, True, 1)
            text_block(im, str(node.get("title", "")), (x + int(20 * s), y + int(70 * s), cw - int(40 * s), int(75 * s)), 28 * s, WHITE, True, 2)
            text_block(im, str(node.get("detail", "")), (x + int(20 * s), y + int(155 * s), cw - int(40 * s), ch - int(175 * s)), 21 * s, MUTED, False, 4)

    def draw_timeline_or_diagram(self, im, d, t, top, bottom, kind, data):
        w, h, s, p = self.w, self.h, self.s, self.pad
        items = data["events"] if kind == "timeline" else [{"label": x} for x in data["steps"]]
        vertical = self.portrait
        for i, item in enumerate(items):
            frac = ease(max(0.0, t - i * 0.28) / 0.75)
            if frac <= 0:
                continue
            cw = (w - p * 2 - 28 * s * (len(items) - 1)) / len(items) if not vertical else w - p * 2
            ch = (bottom - top) * 0.84 if not vertical else (bottom - top) / len(items) - 18 * s
            x = p + i * (cw + 28 * s) if not vertical else p
            y = top if not vertical else top + i * (ch + 18 * s)
            d.rounded_rectangle(
                (x, y + 15 * s * (1 - frac), x + cw, y + ch + 15 * s * (1 - frac)),
                radius=int(12 * s),
                fill=self.panel,
                outline=self.accent if i == len(items) - 1 else self.secondary,
                width=max(1, int(2 * s)),
            )
            d.rectangle((x, y + 15 * s * (1 - frac), x + cw, y + int(8 * s) + 15 * s * (1 - frac)), fill=self.accent if i == len(items) - 1 else self.secondary)
            badge_str = item.get("date", f"STAGE 0{i+1}")
            text_block(im, badge_str, (x + 20 * s, y + 24 * s, cw - 40 * s, 45 * s), 23 * s, self.secondary, True, 1)
            text_block(im, item["label"], (x + 20 * s, y + 76 * s, cw - 40 * s, max(55 * s, ch - 95 * s)), 28 * s, WHITE, True, 4)
            if i < len(items) - 1 and not vertical:
                ax1, ay = x + cw + 4 * s, y + ch / 2
                ax2 = x + cw + 24 * s
                d.line((ax1, ay, ax2, ay), fill=self.accent, width=max(2, int(4 * s)))

    def draw_evidence_card(self, im, d, t, top, bottom, data):
        """Nitish Rajput / Abhi & Niyu style Newspaper Clipping with animated yellow highlighter sweep!"""
        w, h, s, p = self.w, self.h, self.s, self.pad
        fid = data.get("fact_id", self.beat["fact_ids"][0])
        fact = self.facts.get(fid, {"claim": self.beat["narration"], "status": "reported"})
        # Subtle blurred photo backdrop if available
        if self.still is not None:
            bg_blur = ImageOps.fit(self.still, (w, h), method=Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(radius=14))
            dark_tint = Image.new("RGBA", (w, h), (*self.ink, 195))
            im.paste(Image.alpha_composite(bg_blur.convert("RGBA"), dark_tint).convert("RGB"), (0, 0))
            d = ImageDraw.Draw(im)
        card_w = int((w - p * 2) * (0.58 if self.still is not None and not self.portrait else 0.78))
        cx1 = p if (self.still is not None and not self.portrait) else int((w - card_w) // 2)
        cx2 = cx1 + card_w
        # Compact, balanced editorial newspaper cutout (never an empty slab!)
        d.rounded_rectangle((cx1 + int(10 * s), top + int(12 * s), cx2 + int(10 * s), bottom + int(12 * s)), radius=int(10 * s), fill=(4, 8, 14))
        d.rounded_rectangle((cx1, top, cx2, bottom), radius=int(10 * s), fill=(244, 241, 232), outline=self.accent, width=max(2, int(3 * s)))
        d.rectangle((cx1, top, cx2, top + int(50 * s)), fill=(20, 29, 43))
        status_tag = f"VERIFIED REPORT  •  {str(self.beat['visual'].get('headline', 'PRIMARY SOURCE')).upper()[:42]}"
        text_block(im, status_tag, (cx1 + int(24 * s), top + int(13 * s), card_w - int(48 * s), int(30 * s)), 19 * s, (254, 240, 138), True, 1)
        # Animated yellow highlighter bar sweeping cleanly behind the key quote
        sweep = ease(min(1.0, max(0.0, (t - 0.3) / 1.1)))
        hl_w = int((card_w - int(68 * s)) * sweep)
        if hl_w > 4:
            d.rectangle((cx1 + int(28 * s), top + int(76 * s), cx1 + int(28 * s) + hl_w, top + int(124 * s)), fill=(253, 224, 71))
        text_block(
            im,
            f"“{fact['claim']}”",
            (cx1 + int(32 * s), top + int(76 * s), card_w - int(64 * s), int(165 * s)),
            36 * s if not self.portrait else 30 * s,
            (15, 23, 42),
            True,
            3,
        )
        # Divider rule + rich editorial context paragraph below quote so card feels like a real magazine/newspaper clipping
        div_y = top + int(245 * s)
        if div_y < bottom - int(80 * s):
            d.line((cx1 + int(32 * s), div_y, cx2 - int(32 * s), div_y), fill=(195, 190, 178), width=max(1, int(2 * s)))
            text_block(
                im,
                str(self.beat.get("narration", "")),
                (cx1 + int(32 * s), div_y + int(18 * s), card_w - int(64 * s), bottom - div_y - int(32 * s)),
                22 * s if not self.portrait else 20 * s,
                (55, 65, 81),
                False,
                4,
            )
        if self.still is not None and not self.portrait:
            rx = cx2 + int(24 * s)
            rw = w - p - rx
            rh = bottom - top
            fit_im = ImageOps.fit(self.still, (rw, rh), method=Image.Resampling.BICUBIC)
            im.paste(fit_im, (rx, top))
            d.rounded_rectangle((rx, top, rx + rw, bottom), radius=int(10 * s), outline=self.accent, width=max(2, int(3 * s)))

    def container(self, im, t, top, bottom):
        w, h, s = self.w, self.h, self.s
        angle = -0.55 + 0.18 * math.sin(t * 0.35)
        vertices = np.array(
            [[-2, -0.8, -0.8], [2, -0.8, -0.8], [2, 0.8, -0.8], [-2, 0.8, -0.8],
             [-2, -0.8, 0.8], [2, -0.8, 0.8], [2, 0.8, 0.8], [-2, 0.8, 0.8]],
            dtype=float,
        )
        rot = np.array([[math.cos(angle), 0, math.sin(angle)], [0, 1, 0], [-math.sin(angle), 0, math.cos(angle)]])
        tilt = 0.24
        rx = np.array([[1, 0, 0], [0, math.cos(tilt), -math.sin(tilt)], [0, math.sin(tilt), math.cos(tilt)]])
        v = vertices @ rot.T @ rx.T
        scale = min(w * 0.15, (bottom - top) * 0.40)

        def project(pt):
            return (w * 0.5 + pt[0] * scale * 5 / (pt[2] + 6), (top + bottom) * 0.5 + pt[1] * scale * 5 / (pt[2] + 6))

        pts = [project(x) for x in v]
        faces = [
            ([0, 1, 2, 3], (45, 93, 105)),
            ([4, 5, 6, 7], (53, 139, 150)),
            ([0, 1, 5, 4], (108, 200, 199)),
            ([2, 3, 7, 6], (30, 69, 82)),
            ([1, 2, 6, 5], self.accent),
            ([0, 3, 7, 4], (39, 89, 102)),
        ]
        d = ImageDraw.Draw(im)
        for indexes, col in sorted(faces, key=lambda f: sum(v[i][2] for i in f[0]), reverse=True):
            d.polygon([pts[i] for i in indexes], fill=col, outline= self.ink, width=max(1, int(2 * s)))
        for x in np.linspace(-1.9, 1.9, 22):
            line = np.array([[x, -0.76, -0.81], [x, 0.76, -0.81]]) @ rot.T @ rx.T
            d.line([project(a) for a in line], fill=(105, 181, 185), width=max(1, int(2 * s)))
        text_block(im, "3D TELEMETRY MODEL • LOGISTICS PAYLOAD", (self.pad, bottom + 12 * s, w - self.pad * 2, 40 * s), 22 * s, self.secondary, True, 1)

    def globe(self, im, t, top, bottom, places):
        """
        V95 FULL-FRAME ZOOMED TACTICAL ROUTE MAP + CORNER MINI-GLOBE PiP:
        Fills the canvas in BOTH 16:9 Long-Form and 9:16 Shorts, tightly zoomed onto the exact
        route bounding box so the complete route line, country borders, and chokepoints are huge,
        crystal-clear, and continuously animated with a glowing traveling pulse!
        """
        d = ImageDraw.Draw(im)
        w, h, s, p = self.w, self.h, self.s, self.pad
        polys = load_world_polygons()
        target_countries = {str(pl.get("country", "")).upper() for pl in places if pl.get("country")}
        for pl in places:
            gz = lookup_gazetteer(pl.get("name", ""))
            if gz and gz.get("country"):
                target_countries.add(gz["country"].upper())

        # Full-bleed tactical map area (filling the entire frame cleanly in both 16:9 and 9:16!)
        map_x1, map_y1 = (0, 0)
        map_x2, map_y2 = (w, h)
        mw, mh = w, h

        lats = [pl["lat"] for pl in places]
        lons = [pl["lon"] for pl in places]
        mean_lat = (min(lats) + max(lats)) / 2.0
        mean_lon = (min(lons) + max(lons)) / 2.0
        # Shift center slightly upward in portrait so the complete route sits cleanly above Shorts captions!
        if self.portrait:
            mean_lat -= 3.5
        else:
            mean_lat -= 2.2

        raw_dlat = max(6.0, max(lats) - min(lats))
        raw_dlon = max(8.0, max(lons) - min(lons))
        # Subtle smooth cinematic zoom-in over the beat duration (1.0x -> 1.14x closer!)
        zoom_factor = 1.0 + 0.14 * ease(min(1.0, t / 5.5))
        pad_mult = (1.85 if self.portrait else 2.55) / zoom_factor
        span_lat = raw_dlat * pad_mult
        span_lon = raw_dlon * pad_mult

        # Maintain geographic aspect ratio (accounting for cos(lat) foreshortening)
        cos_lat = max(0.35, math.cos(math.radians(mean_lat)))
        target_ratio = mw / max(1.0, mh)
        if (span_lon * cos_lat) / max(0.1, span_lat) < target_ratio:
            span_lon = (span_lat * target_ratio) / cos_lat
        else:
            span_lat = (span_lon * cos_lat) / target_ratio

        lat_min, lat_max = mean_lat - span_lat / 2.0, mean_lat + span_lat / 2.0
        lon_min, lon_max = mean_lon - span_lon / 2.0, mean_lon + span_lon / 2.0

        # V98.3: Attempt real Google-Earth-style Esri World Imagery satellite tiles (cached once per beat); clean fallback to 208-country vector atlas
        if not hasattr(self, "_sat_checked"):
            self._sat_checked = True
            self._sat_img, self._sat_proj = fetch_satellite_basemap(places, mw, mh, cache_dir="cache/sat_tiles")

        if self._sat_img is not None and self._sat_proj is not None:
            # Apply smooth cinematic 1.0x -> 1.14x zoom-in on real satellite imagery
            zw, zh = int(mw * zoom_factor), int(mh * zoom_factor)
            sat_zoomed = self._sat_img.resize((zw, zh), Image.Resampling.BICUBIC)
            ox, oy = (zw - mw) // 2, (zh - mh) // 2
            map_layer = sat_zoomed.crop((ox, oy, ox + mw, oy + mh)).convert("RGBA")
            md = ImageDraw.Draw(map_layer)
            def project_map(lat, lon):
                bx, by = self._sat_proj(lat, lon)
                return bx * zoom_factor - ox, by * zoom_factor - oy
            # Subtle tactical grid overlay on top of real satellite terrain
            for gy in range(0, mh, max(48, int(96 * s))):
                md.line((0, gy, mw, gy), fill=(255, 255, 255, 26), width=1)
            for gx in range(0, mw, max(48, int(96 * s))):
                md.line((gx, 0, gx, mh), fill=(255, 255, 255, 26), width=1)
        else:
            def project_map(lat, lon):
                rx = map_x1 + (lon - lon_min) / max(0.01, lon_max - lon_min) * mw
                ry = map_y2 - (lat - lat_min) / max(0.01, lat_max - lat_min) * mh
                return rx, ry

            # Deep bathymetric ocean base + glowing latitude/longitude tactical grid
            map_layer = Image.new("RGBA", (mw, mh), (8, 22, 38, 255))
            md = ImageDraw.Draw(map_layer)
            for gy in range(0, mh, max(36, int(72 * s))):
                md.line((0, gy, mw, gy), fill=(17, 42, 66, 255), width=1)
            for gx in range(0, mw, max(36, int(72 * s))):
                md.line((gx, 0, gx, mh), fill=(17, 42, 66, 255), width=1)

            # Draw crisp 208-Country Natural Earth Landmasses
            for cname, rings in polys.items():
                if cname.startswith("ISO_") or cname == "_LOADED":
                    continue
                is_target = cname in target_countries or any(cname in pl["name"].upper() for pl in places)
                fill_col = (*self.accent, 155) if is_target else (24, 52, 76, 255)
                out_col = (*WHITE, 245) if is_target else (72, 126, 158, 215)
                for ring in rings:
                    if not any(lat_min - 25 <= lat <= lat_max + 25 and lon_min - 35 <= lon <= lon_max + 35 for lat, lon in ring[::2]):
                        continue
                    pts_2d = [project_map(lat, lon) for lat, lon in ring]
                    if len(pts_2d) >= 3:
                        md.polygon(pts_2d, fill=fill_col, outline=out_col)

        # Glowing Animated Multi-Segment Route Arc + Traveling Signal Pulse!
        if len(places) >= 2:
            route_pts = []
            segs = len(places) - 1
            for idx in range(segs):
                p1, p2 = places[idx], places[idx + 1]
                steps = 40
                for k in range(steps + 1):
                    u = k / steps
                    # Smooth curved maritime/flight arc
                    bend = (1.6 if idx % 2 == 0 else -1.4) * math.sin(math.pi * u)
                    lat_i = p1["lat"] + (p2["lat"] - p1["lat"]) * u + bend
                    lon_i = p1["lon"] + (p2["lon"] - p1["lon"]) * u
                    route_pts.append(project_map(lat_i, lon_i))

            draw_prog = ease(min(1.0, max(0.05, t / 2.2)))
            n_active = max(2, int(len(route_pts) * draw_prog))
            active_pts = route_pts[:n_active]
            # Outer neon glow + bright core route line
            md.line(active_pts, fill=(*self.secondary, 110), width=max(8, int(14 * s)))
            md.line(active_pts, fill=(254, 240, 138, 255), width=max(4, int(6 * s)))
            md.line(active_pts, fill=(255, 255, 255, 240), width=max(2, int(2.5 * s)))

            # Continuously traveling glowing data/flight pulse along the complete route!
            pulse_idx = int(((t * 0.45) % 1.0) * (len(active_pts) - 1))
            px_p, py_p = active_pts[pulse_idx]
            pr = int(10 * s)
            md.ellipse((px_p - pr * 2.2, py_p - pr * 2.2, px_p + pr * 2.2, py_p + pr * 2.2), fill=(250, 204, 21, 95))
            md.ellipse((px_p - pr, py_p - pr, px_p + pr, py_p + pr), fill=(255, 255, 255, 255), outline=(*self.accent, 255), width=max(2, int(3 * s)))

        # Crisp Pulsing City / Chokepoint Pins & Non-Overlapping Labels
        placed_boxes = []
        for i, place in enumerate(places):
            lx, ly = project_map(place["lat"], place["lon"])
            pulse = (14 + 7 * math.sin(t * 4.0 + i)) * s
            md.ellipse((lx - pulse, ly - pulse, lx + pulse, ly + pulse), outline=(254, 240, 138, 220), width=max(2, int(2.5 * s)))
            md.ellipse((lx - int(8 * s), ly - int(8 * s), lx + int(8 * s), ly + int(8 * s)), fill=(*self.accent, 255), outline=WHITE, width=max(2, int(2.5 * s)))

            lbl = f"{place['name'].upper()}"
            coord_lbl = f"{place['lat']:.1f}°N, {place['lon']:.1f}°E"
            lf = font(int((24 if self.portrait else 22) * s), True)
            cf = font(int((16 if self.portrait else 15) * s), False)
            tw = max(int(md.textlength(lbl, font=lf)), int(md.textlength(coord_lbl, font=cf)))
            bw = tw + int(24 * s)
            bh = int(54 * s)

            # Smart offset so labels never collide with pins or screen edges
            bx = int(lx + 16 * s) if lx < mw * 0.58 else int(lx - bw - 16 * s)
            by = int(ly - bh / 2)
            bx = max(p, min(mw - p - bw, bx))
            by = max(int(h * 0.22), min(int(h * (0.64 if self.portrait else 0.76)) - bh, by))
            for ox1, oy1, ox2, oy2 in placed_boxes:
                if not (bx + bw < ox1 or bx > ox2 or by + bh < oy1 or by > oy2):
                    by = min(int(h * (0.65 if self.portrait else 0.78)) - bh, oy2 + int(10 * s))
            placed_boxes.append((bx, by, bx + bw, by + bh))

            md.rounded_rectangle((bx, by, bx + bw, by + bh), radius=int(8 * s), fill=(8, 15, 26, 232), outline=(*self.secondary, 225), width=max(2, int(2 * s)))
            md.rectangle((bx, by, bx + int(6 * s), by + bh), fill=self.accent)
            md.text((bx + int(14 * s), by + int(7 * s)), lbl, font=lf, fill=WHITE)
            md.text((bx + int(14 * s), by + int(32 * s)), coord_lbl, font=cf, fill=(254, 240, 138))

        # Sleek Corner Mini-Globe PiP (Top-Right in 16:9, Bottom-Right above captions in 9:16) for Global Context!
        gr = int((76 if not self.portrait else 68) * s)
        gcx = w - p - gr - int(10 * s)
        gcy = int(h * 0.34) if not self.portrait else int(h * 0.25)
        md.ellipse((gcx - gr - 4 * s, gcy - gr - 4 * s, gcx + gr + 4 * s, gcy + gr + 4 * s), fill=(8, 16, 28, 225), outline=(*self.secondary, 190), width=max(2, int(2 * s)))
        lon0 = mean_lon + 6.0 * math.sin(t * 0.3)
        lat0 = max(-45.0, min(45.0, mean_lat * 0.8))

        def proj_mini(lat, lon):
            a, b, c = map(math.radians, [lat, lon - lon0, lat0])
            x = math.cos(a) * math.sin(b)
            y = math.cos(c) * math.sin(a) - math.sin(c) * math.cos(a) * math.cos(b)
            z = math.sin(c) * math.sin(a) + math.cos(c) * math.cos(a) * math.cos(b)
            return gcx + gr * x, gcy - gr * y, z

        for cname, rings in polys.items():
            if cname.startswith("ISO_") or cname == "_LOADED":
                continue
            is_t = cname in target_countries
            fc = (*self.accent, 230) if is_t else (38, 76, 102, 230)
            for ring in rings:
                pts_m = []
                for lat, lon in ring[::4] if len(ring) > 24 else ring:
                    mx, my, mz = proj_mini(lat, lon)
                    if mz > 0.05:
                        pts_m.append((mx, my))
                if len(pts_m) >= 3:
                    md.polygon(pts_m, fill=fc)
        mx0, my0, mz0 = proj_mini(mean_lat, mean_lon)
        if mz0 > 0:
            md.ellipse((mx0 - 5 * s, my0 - 5 * s, mx0 + 5 * s, my0 + 5 * s), fill=(254, 240, 138, 255))

        # Subtle top/bottom gradient vignette so header & captions stay ultra-legible over full-bleed map
        for y in range(int(h * 0.22)):
            a = int(195 * max(0.0, 1.0 - y / max(1.0, h * 0.22)) ** 1.3)
            md.line((0, y, mw, y), fill=(*self.ink, a))
        for y in range(int(h * 0.72), mh):
            a = int(215 * max(0.0, (y - h * 0.72) / max(1.0, h * 0.28)) ** 1.2)
            md.line((0, y, mw, y), fill=(*self.ink, a))

        im.paste(map_layer.convert("RGB"), (0, 0))


def caption_frame(im, cues, t, portrait=False):
    cue = next((c for c in cues if c["start"] <= t <= c["end"] + 0.08), None)
    if not cue:
        return im
    w, h = im.size
    s = w / (1080 if portrait else 1920)
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    f = font(32 * s, True)
    lines = wrap(d, cue["text"], f, w * 0.80)
    bh = len(lines) * 42 * s + 24 * s
    y = h * 0.875 - bh
    d.rounded_rectangle((w * 0.10, y, w * 0.90, y + bh), radius=int(10 * s), fill=(6, 10, 18, 210), outline=(250, 204, 21, 90), width=max(1, int(2 * s)))
    all_words = str(cue["text"]).split()
    dur_c = max(0.15, cue["end"] - cue["start"])
    active_w_idx = min(max(0, len(all_words) - 1), int(max(0.0, min(0.999, (t - cue["start"]) / dur_c)) * len(all_words)))
    w_cursor = 0
    sp_w = d.textlength(" ", font=f)
    for line in lines:
        l_words = line.split()
        tw = d.textlength(line, font=f)
        lx = (w - tw) / 2
        for wd in l_words:
            ww = d.textlength(wd, font=f)
            is_act = (w_cursor == active_w_idx)
            d.text((lx + 2, y + 12 * s), wd, font=f, fill=(0, 0, 0, 230))
            d.text((lx, y + 10 * s), wd, font=f, fill=(250, 204, 21) if is_act else (248, 250, 252))
            lx += ww + sp_w
            w_cursor += 1
        y += 42 * s
    return Image.alpha_composite(im.convert("RGBA"), layer).convert("RGB")


def render_beat(beat, dossier, audio, out, cfg, portrait=False):
    w, h = (1080, 1920) if portrait else (cfg["width"], cfg["height"])
    fps = cfg["fps"]
    nframes = math.ceil(audio["duration"] * fps)
    duration = nframes / fps
    canvas = Canvas(beat, dossier, w, h)
    cues = captions(beat["narration"], audio)
    decoder = None
    frame_bytes = w * h * 3
    if beat.get("asset", {}).get("kind") == "footage":
        decoder = subprocess.Popen(
            [
                ffmpeg(), "-v", "error", "-nostdin", "-stream_loop", "-1", "-i", beat["asset"]["path"],
                "-an", "-vf", f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps={fps}",
                "-t", str(duration), "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    log_path = Path(out).with_suffix(".ffmpeg.log")
    with log_path.open("wb") as log:
        encoder = subprocess.Popen(
            [
                ffmpeg(), "-v", "error", "-nostdin", "-y", "-f", "rawvideo", "-vcodec", "rawvideo",
                "-s", f"{w}x{h}", "-r", str(fps), "-pix_fmt", "rgb24", "-i", "pipe:0", "-i", audio["path"],
                "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-preset", cfg["preset"], "-crf", str(cfg["crf"]),
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-af", "apad", "-t", str(duration),
                "-movflags", "+faststart", str(out),
            ],
            stdin=subprocess.PIPE,
            stderr=log,
        )
        use_v107 = (not portrait) and bool(beat.get("visual", {}).get("v107_archetype"))
        still_rgb = np.array(canvas.still.convert("RGB"), dtype=np.uint8) if (use_v107 and canvas.still is not None) else None
        try:
            for frame in range(nframes):
                data = None
                if decoder:
                    data = decoder.stdout.read(frame_bytes)
                    if len(data) != frame_bytes:
                        raise StudioError("Footage decode ended unexpectedly")
                t_now = frame / fps
                if use_v107:
                    bg_arr = np.frombuffer(data, dtype=np.uint8).reshape((h, w, 3)) if data is not None else still_rgb
                    im = render_v107_beat_frame(
                        beat, dossier, t_now, duration, bg_arr, w, h,
                        frame_idx=frame, is_live_video=(data is not None),
                    )
                else:
                    im = canvas.frame(t_now, duration, data)
                    im = caption_frame(im, cues, t_now, portrait)
                if t_now < 0.18:
                    fade_a = t_now / 0.18
                    im = Image.blend(Image.new("RGB", (w, h), canvas.ink), im, fade_a)
                encoder.stdin.write(im.tobytes())
            encoder.stdin.close()
            if encoder.wait(timeout=180):
                raise StudioError("Video encoding failed; see per-clip FFmpeg log")
        finally:
            if encoder.poll() is None:
                encoder.kill()
                encoder.wait()
            if decoder:
                if decoder.poll() is None:
                    decoder.kill()
                decoder.wait()
                decoder.stdout.close()
    return duration


def ensure_studio_soundtrack(path, duration_sec=60.0, style="think_school", sfx_events=None, is_short=False):
    """Generates V94 multi-layer stereo musical documentary score with scene-synced SFX."""
    from .audio_engine import generate_documentary_score
    return generate_documentary_score(path, duration_sec, style=style, sfx_events=sfx_events, is_short=is_short)


def _legacy_sine_soundtrack_unused(path, duration_sec=60.0, style="think_school"):
    path = Path(path)
    if path.exists() and path.stat().st_size > 1000:
        return path
    sr = 48000
    n = int(max(12.0, min(120.0, duration_sec)) * sr)
    t = np.arange(n, dtype=np.float32) / sr
    base_freq = {"bbc_dispatch": 65.41, "think_school": 55.0, "nitish_rajput": 49.0, "abhi_niyu": 73.42}.get(style, 55.0)
    drone = 0.45 * np.sin(2 * np.pi * base_freq * t) + 0.25 * np.sin(2 * np.pi * (base_freq * 1.5) * t)
    pad = 0.20 * np.sin(2 * np.pi * (base_freq * 2.0) * t) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.15 * t))
    pulse = 0.18 * np.sin(2 * np.pi * (base_freq * 3.0) * t) * (np.maximum(0.0, np.sin(2 * np.pi * 1.25 * t)) ** 4)
    wave_mono = np.clip((drone + pad + pulse) * 0.28, -0.95, 0.95)
    pcm = (wave_mono * 32767).astype("<i2")
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return path


def concatenate(paths, output, music=None):
    listing = Path(output).with_suffix(".concat.txt")
    listing.write_text(
        "\n".join("file '" + p.resolve().as_posix().replace("'", "'\\''") + "'" for p in paths),
        encoding="utf-8",
    )
    if music:
        run_ff(
            [
                "-f", "concat", "-safe", "0", "-i", listing, "-stream_loop", "-1", "-i", music,
                "-filter_complex",
                "[0:a]asplit=2[voice][side];[1:a]volume=0.08[m];[m][side]sidechaincompress=threshold=0.015:ratio=8:attack=25:release=350[duck];[voice][duck]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=9[a]",
                "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", output,
            ]
        )
    else:
        run_ff(["-f", "concat", "-safe", "0", "-i", listing, "-c", "copy", "-movflags", "+faststart", output])


def make_thumbnail(plan, dossier, path):
    """V102 Viral High-CTR YouTube Thumbnail (1280x720): Vivid full-bleed event photo + face-aware framing + auto-fitted giant outlined text + red impact badge."""
    from PIL import ImageEnhance
    style_key = plan.get("style") or dossier.get("style") or "think_school"
    theme = STYLE_THEMES.get(style_key, STYLE_THEMES["think_school"])
    photo_beats = [b for b in plan["beats"] if b.get("asset", {}).get("kind") == "photo" and Path(b["asset"]["path"]).exists()]
    beat = photo_beats[0] if photo_beats else plan["beats"][0]

    im = Image.new("RGB", (1280, 720), theme["ink"])
    if beat.get("asset", {}).get("kind") == "photo" and Path(beat["asset"]["path"]).exists():
        photo = Image.open(beat["asset"]["path"]).convert("RGB")
        fcx, fcy = detect_face_focus_center(photo)
        im = ImageOps.fit(photo, (1280, 720), method=Image.Resampling.BICUBIC, centering=(fcx, fcy))
        im = ImageEnhance.Color(im).enhance(1.26)
        im = ImageEnhance.Contrast(im).enhance(1.22)
        im = ImageEnhance.Sharpness(im).enhance(1.30)
    else:
        c = Canvas(beat, dossier, 1280, 720)
        im = c.frame(2, 5)

    # Rich cinematic left-and-bottom vignette (keeps right 65% of the dramatic photo bright and clear!)
    overlay = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for x in range(740):
        a = int(218 * (max(0.0, 1.0 - x / 740.0) ** 1.35))
        od.line((x, 0, x, 720), fill=(6, 10, 18, a))
    for y in range(440, 720):
        a = int(175 * (((y - 440) / 280.0) ** 1.4))
        od.line((0, y, 1280, y), fill=(6, 10, 18, a))
    im = Image.alpha_composite(im.convert("RGBA"), overlay)
    d = ImageDraw.Draw(im)

    # Crisp red/accent top-left impact pill badge
    badge = str(theme.get("badge") or "SPECIAL REPORT").upper()[:24]
    f_badge = font(26, True)
    bb = d.textbbox((0, 0), badge, font=f_badge)
    bw = (bb[2] - bb[0]) + 44
    d.rounded_rectangle((56, 54, 56 + bw, 106), radius=8, fill=(220, 38, 38, 250))
    d.text((78, 64), badge, font=f_badge, fill=(255, 255, 255, 255))

    # Auto-fitted giant 2-line hook text (NEVER clips off screen!)
    raw_hook = str(plan.get("thumbnail_text") or plan.get("title") or "INSIDE THE CRISIS").upper()
    words = [w for w in raw_hook.replace(":", "").split() if len(w) > 1][:4]
    if len(words) <= 2:
        lines = [" ".join(words)]
    else:
        mid = len(words) // 2
        lines = [" ".join(words[:mid]), " ".join(words[mid:])]

    max_w = 780
    fsize = 122
    while fsize > 62:
        f_big = font(fsize, True)
        if all((d.textbbox((0, 0), ln, font=f_big)[2] - d.textbbox((0, 0), ln, font=f_big)[0]) <= max_w for ln in lines):
            break
        fsize -= 6
    f_big = font(fsize, True)
    line_h = int(fsize * 1.18)
    y_start = 220 if len(lines) == 2 else 285

    for idx_l, ln in enumerate(lines):
        yy = y_start + idx_l * line_h
        col = (250, 204, 21, 255) if idx_l == 0 else (255, 255, 255, 255)
        # Hard shadow + thick crisp black stroke for instant mobile legibility
        d.text((62, yy + 10), ln, font=f_big, fill=(0, 0, 0, 210))
        d.text((56, yy), ln, font=f_big, fill=col, stroke_width=8, stroke_fill=(0, 0, 0, 255))

    # Clean bottom accent strip + subtle channel mark
    d.rectangle((0, 706, 1280, 720), fill=theme["accent"])
    f_sub = font(24, True)
    d.text((58, 648), "WORLD TALK BRIEF  •  DEEP INVESTIGATION", font=f_sub, fill=(226, 232, 240, 235), stroke_width=3, stroke_fill=(0, 0, 0, 220))
    im.convert("RGB").save(path, quality=95, optimize=True)
