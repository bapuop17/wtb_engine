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
        "/usr/share/fonts/truetype/inter/Inter-" + ("Bold" if bold else "Regular") + ".ttf",
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
        self.secondary_still = None
        if beat.get("asset") and beat["asset"]["kind"] == "photo" and Path(beat["asset"]["path"]).exists():
            self.still = Image.open(beat["asset"]["path"]).convert("RGB")
        sec_path = beat["visual"].get("data", {}).get("secondary_photo_path")
        if sec_path and Path(sec_path).exists():
            self.secondary_still = Image.open(sec_path).convert("RGB")
        self.overlay = self.make_overlay()

    def make_overlay(self):
        w, h, p, s = self.w, self.h, self.pad, self.s
        layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        kind = self.beat["visual"]["kind"]
        media = kind in {"photo", "footage"} and (self.beat.get("asset") or self.still is not None)
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
        if not media:
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

    def _render_full_bleed_still(self, img_src, t, duration):
        w, h, s, p = self.w, self.h, self.s, self.pad
        prog = min(1.0, max(0.0, t / max(0.1, duration)))
        z = 1.04 + 0.085 * ease(prog)
        # Full-bleed cover crop with subtle pan so there are zero ugly black sidebars
        fitted = ImageOps.fit(img_src, (int(w * z), int(h * z)), method=Image.Resampling.BICUBIC, centering=(0.5, 0.45))
        pan_x = int((fitted.width - w) * (0.35 + 0.3 * prog))
        pan_y = int((fitted.height - h) * 0.45)
        cropped = fitted.crop((pan_x, pan_y, pan_x + w, pan_y + h))
        # If data has a callout pill (e.g., location or key metric), draw a sleek floating glass card on bottom-left
        data = self.beat["visual"].get("data", {})
        callout = data.get("callout") or data.get("metric_badge")
        if callout:
            layer = cropped.convert("RGBA")
            d = ImageDraw.Draw(layer)
            cw, ch = int(w * 0.34), int(86 * s)
            cx, cy = p, int(h * 0.61)
            d.rounded_rectangle((cx, cy, cx + cw, cy + ch), radius=int(10 * s), fill=(*self.ink, 215), outline=(*self.accent, 230), width=max(1, int(2 * s)))
            d.rectangle((cx, cy, cx + int(8 * s), cy + ch), fill=self.accent)
            text_block(layer, str(callout).upper(), (cx + int(22 * s), cy + int(12 * s), cw - int(32 * s), int(34 * s)), 24 * s, self.secondary, True, 1)
            sub = data.get("callout_sub") or self.beat["visual"].get("reason", "")[:68]
            text_block(layer, sub, (cx + int(22 * s), cy + int(44 * s), cw - int(32 * s), int(34 * s)), 18 * s, WHITE, False, 1)
            return layer.convert("RGB")
        return cropped

    def frame(self, t, duration, video_frame=None):
        w, h, s, p = self.w, self.h, self.s, self.pad
        kind = self.beat["visual"]["kind"]
        data = self.beat["visual"].get("data", {})
        im = self.bg.copy()
        if video_frame is not None and kind == "footage":
            im = Image.frombytes("RGB", (w, h), video_frame)
        elif self.still is not None and kind in {"photo", "footage"}:
            im = self._render_full_bleed_still(self.still, t, duration)
        else:
            d = ImageDraw.Draw(im)
            top, bottom = int(h * 0.285), int(h * 0.775)
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
        w, h, s, p = self.w, self.h, self.s, self.pad
        metrics = data.get("metrics", [{"value": "100%", "label": "Verified Metric"}])
        n = len(metrics)
        gap = int(24 * s)
        cw = (w - p * 2 - gap * (n - 1)) / n
        ch = bottom - top
        for i, m in enumerate(metrics):
            frac = ease(max(0.0, t - i * 0.18) / 0.85)
            x = p + i * (cw + gap)
            y = top + int(18 * s * (1.0 - frac))
            d.rounded_rectangle((x, y, x + cw, y + ch), radius=int(14 * s), fill=self.panel, outline=self.accent if i == 0 else self.secondary, width=max(1, int(3 * s)))
            d.rectangle((x, y, x + cw, y + int(10 * s)), fill=self.accent if i == 0 else self.secondary)
            text_block(im, f"METRIC 0{i+1}", (x + int(24 * s), y + int(26 * s), cw - int(48 * s), int(34 * s)), 20 * s, MUTED, True, 1)
            text_block(im, str(m.get("value", "")), (x + int(24 * s), y + int(72 * s), cw - int(48 * s), int(115 * s)), 64 * s, WHITE, True, 1)
            text_block(im, str(m.get("label", "")).upper(), (x + int(24 * s), y + int(195 * s), cw - int(48 * s), int(80 * s)), 26 * s, self.secondary if i == 0 else WHITE, True, 2)
            if m.get("sub"):
                text_block(im, str(m["sub"]), (x + int(24 * s), y + int(275 * s), cw - int(48 * s), int(75 * s)), 20 * s, MUTED, False, 2)
            # Animated gauge bar at bottom of card
            bar_w = int((cw - 48 * s) * frac)
            d.rounded_rectangle((x + int(24 * s), y + ch - int(36 * s), x + int(24 * s) + bar_w, y + ch - int(22 * s)), radius=int(4 * s), fill=self.accent if i == 0 else self.secondary)

    def draw_actor_split(self, im, d, t, top, bottom, data):
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
        w, h, s, p = self.w, self.h, self.s, self.pad
        fid = data.get("fact_id", self.beat["fact_ids"][0])
        fact = self.facts.get(fid, {"claim": self.beat["narration"], "status": "reported"})
        card_w = int((w - p * 2) * (0.58 if self.still is not None and not self.portrait else 1.0))
        d.rounded_rectangle((p, top, p + card_w, bottom), radius=int(14 * s), fill=self.panel, outline=(*self.secondary, 120), width=max(1, int(2 * s)))
        d.rectangle((p, top, p + int(10 * s), bottom), fill=self.accent)
        status_tag = f"VERIFIED RECORD ({str(fact.get('status', 'reported')).upper()})  •  FACT {fid}"
        text_block(im, status_tag, (p + int(34 * s), top + int(24 * s), card_w - int(60 * s), int(34 * s)), 20 * s, self.secondary, True, 1)
        text_block(
            im,
            f"“{fact['claim']}”",
            (p + int(34 * s), top + int(72 * s), card_w - int(68 * s), bottom - top - int(110 * s)),
            36 * s if not self.portrait else 32 * s,
            WHITE,
            True,
            6,
        )
        if self.still is not None and not self.portrait:
            rx = p + card_w + int(24 * s)
            rw = w - p - rx
            rh = bottom - top
            fit_im = ImageOps.fit(self.still, (rw, rh), method=Image.Resampling.BICUBIC)
            im.paste(fit_im, (rx, top))
            d.rounded_rectangle((rx, top, rx + rw, bottom), radius=int(12 * s), outline=self.accent, width=max(2, int(3 * s)))

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
        """Renders a 208-Country Natural Earth 3D Orthographic Globe + Zoomed Regional Tactical Map."""
        d = ImageDraw.Draw(im)
        w, h, s, p = self.w, self.h, self.s, self.pad
        polys = load_world_polygons()
        target_countries = {str(pl.get("country", "")).upper() for pl in places if pl.get("country")}
        for pl in places:
            gz = lookup_gazetteer(pl.get("name", ""))
            if gz and gz.get("country"):
                target_countries.add(gz["country"].upper())

        # Center lat/lon from resolved places
        mean_lat = sum(pl["lat"] for pl in places) / len(places)
        mean_lon = sum(pl["lon"] for pl in places) / len(places)
        r = min(w * 0.19, (bottom - top) * 0.48)
        cx = w * 0.25 if not self.portrait else w * 0.5
        cy = (top + bottom) * 0.5
        lon0 = mean_lon + 6.0 * math.sin(t * 0.25)
        lat0 = max(-55.0, min(55.0, mean_lat * 0.85))

        def project_ortho(lat, lon):
            a, b, c = map(math.radians, [lat, lon - lon0, lat0])
            x = math.cos(a) * math.sin(b)
            y = math.cos(c) * math.sin(a) - math.sin(c) * math.cos(a) * math.cos(b)
            z = math.sin(c) * math.sin(a) + math.cos(c) * math.cos(a) * math.cos(b)
            return cx + r * x, cy - r * y, z

        # Ocean sphere + outer atmospheric glow
        d.ellipse((cx - r - 6 * s, cy - r - 6 * s, cx + r + 6 * s, cy + r + 6 * s), fill=(16, 36, 56), outline=(*self.secondary, 120), width=max(1, int(2 * s)))
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(14, 34, 52), outline=self.secondary, width=max(2, int(2.5 * s)))

        # Graticule lines
        for axis in (0, 1):
            for fixed in range(-150, 180, 30) if axis else range(-60, 90, 30):
                seg = []
                for moving in range(-180, 181, 6) if not axis else range(-90, 91, 6):
                    x, y, z = project_ortho(fixed, moving) if not axis else project_ortho(moving, fixed)
                    if z > 0:
                        seg.append((x, y))
                    elif len(seg) > 1:
                        d.line(seg, fill=(28, 62, 84), width=max(1, int(s)))
                        seg = []
                    else:
                        seg = []
                if len(seg) > 1:
                    d.line(seg, fill=(28, 62, 84), width=max(1, int(s)))

        # Real 208-Country Natural Earth Landmasses on the 3D Globe!
        for cname, rings in polys.items():
            if cname.startswith("ISO_") or cname == "_LOADED":
                continue
            is_target = cname in target_countries or any(cname in pl["name"].upper() for pl in places)
            fill_col = self.accent if is_target else (34, 74, 96)
            out_col = WHITE if is_target else (64, 118, 142)
            for ring in rings:
                pts_2d = []
                for lat, lon in ring[::2] if len(ring) > 40 else ring:
                    px, py, pz = project_ortho(lat, lon)
                    if pz > 0.02:
                        pts_2d.append((px, py))
                if len(pts_2d) >= 3:
                    d.polygon(pts_2d, fill=fill_col, outline=out_col)

        # Great-circle arc & pins on 3D Globe
        if len(places) >= 2:
            for idx in range(len(places) - 1):
                p1, p2 = places[idx], places[idx + 1]
                arc_pts = []
                steps = 28
                active_steps = max(2, int(steps * ease(min(1.0, t / 1.2))))
                for k in range(active_steps + 1):
                    u = k / steps
                    lat_i = p1["lat"] + (p2["lat"] - p1["lat"]) * u + 3.5 * math.sin(math.pi * u)
                    lon_i = p1["lon"] + (p2["lon"] - p1["lon"]) * u
                    px, py, pz = project_ortho(lat_i, lon_i)
                    if pz > 0:
                        arc_pts.append((px, py))
                if len(arc_pts) >= 2:
                    d.line(arc_pts, fill=self.secondary, width=max(2, int(3.5 * s)))

        for place in places:
            x, y, z = project_ortho(place["lat"], place["lon"])
            if z > 0:
                rr = (7 + 3 * math.sin(t * 3.0)) * s
                d.ellipse((x - rr * 1.8, y - rr * 1.8, x + rr * 1.8, y + rr * 1.8), outline=self.secondary, width=max(1, int(2 * s)))
                d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=self.accent, outline=WHITE, width=max(1, int(2 * s)))

        if self.portrait:
            for i, place in enumerate(places):
                y0 = bottom - int((len(places) - i) * 44 * s)
                text_block(im, f"• {place['name'].upper()} ({place['lat']:.2f}°, {place['lon']:.2f}°)", (p, y0, w - p * 2, 42 * s), 24 * s, WHITE, True, 1)
            return

        # RIGHT PANEL: Zoomed Regional Tactical Map with Real Country Borders & Telemetry Cards
        map_x1 = int(w * 0.46)
        map_x2 = w - p
        map_y1 = top
        map_y2 = bottom
        mw, mh = map_x2 - map_x1, map_y2 - map_y1
        d.rounded_rectangle((map_x1, map_y1, map_x2, map_y2), radius=int(14 * s), fill=(11, 26, 42), outline=self.secondary, width=max(2, int(2.5 * s)))

        lats = [pl["lat"] for pl in places]
        lons = [pl["lon"] for pl in places]
        span_lat = max(8.0, (max(lats) - min(lats)) * 2.2)
        span_lon = max(12.0, (max(lons) - min(lons)) * 2.4)
        span_lon = max(span_lon, span_lat * (mw / max(1, mh)))
        span_lat = span_lon * (mh / max(1, mw))
        lat_min, lat_max = mean_lat - span_lat / 2, mean_lat + span_lat / 2
        lon_min, lon_max = mean_lon - span_lon / 2, mean_lon + span_lon / 2

        def project_reg(lat, lon):
            rx = map_x1 + (lon - lon_min) / max(0.01, lon_max - lon_min) * mw
            ry = map_y2 - (lat - lat_min) / max(0.01, lat_max - lat_min) * mh
            return rx, ry

        # Clip regional map to panel
        reg_layer = Image.new("RGBA", (mw, mh), (11, 26, 42, 255))
        rd = ImageDraw.Draw(reg_layer)
        for gx in range(0, mw, max(24, int(64 * s))):
            rd.line((gx, 0, gx, mh), fill=(22, 46, 68, 255), width=1)
        for gy in range(0, mh, max(24, int(64 * s))):
            rd.line((0, gy, mw, gy), fill=(22, 46, 68, 255), width=1)

        for cname, rings in polys.items():
            if cname.startswith("ISO_") or cname == "_LOADED":
                continue
            is_target = cname in target_countries or any(cname in pl["name"].upper() for pl in places)
            fill_col = (*self.accent, 115) if is_target else (29, 58, 82, 255)
            out_col = (*WHITE, 235) if is_target else (78, 128, 158, 200)
            for ring in rings:
                if not any(lat_min - 15 <= lat <= lat_max + 15 and lon_min - 20 <= lon <= lon_max + 20 for lat, lon in ring[::3]):
                    continue
                pts_reg = []
                for lat, lon in ring:
                    rx, ry = project_reg(lat, lon)
                    pts_reg.append((rx - map_x1, ry - map_y1))
                if len(pts_reg) >= 3:
                    rd.polygon(pts_reg, fill=fill_col, outline=out_col)

        # Animated trajectory vector on regional map
        if len(places) >= 2:
            for idx in range(len(places) - 1):
                p1, p2 = places[idx], places[idx + 1]
                x1, y1 = project_reg(p1["lat"], p1["lon"])
                x2, y2 = project_reg(p2["lat"], p2["lon"])
                x1 -= map_x1; y1 -= map_y1; x2 -= map_x1; y2 -= map_y1
                prog = ease(min(1.0, max(0.0, (t - idx * 0.25) / 1.0)))
                cx_end = x1 + (x2 - x1) * prog
                cy_end = y1 + (y2 - y1) * prog
                rd.line((x1, y1, cx_end, cy_end), fill=(*self.secondary, 255), width=max(3, int(4 * s)))

        # Pins & labels on regional map
        for i, place in enumerate(places):
            rx, ry = project_reg(place["lat"], place["lon"])
            lx, ly = rx - map_x1, ry - map_y1
            pulse = (10 + 5 * math.sin(t * 3.5 + i)) * s
            rd.ellipse((lx - pulse, ly - pulse, lx + pulse, ly + pulse), outline=(*self.secondary, 220), width=max(1, int(2 * s)))
            rd.ellipse((lx - int(6 * s), ly - int(6 * s), lx + int(6 * s), ly + int(6 * s)), fill=(*self.accent, 255), outline=(*WHITE, 255), width=max(1, int(2 * s)))
            lbl = f"{place['name'].upper()} ({place['lat']:.1f}°, {place['lon']:.1f}°)"
            lf = font(int(18 * s), True)
            tw = int(rd.textlength(lbl, font=lf))
            bx = max(int(10 * s), min(mw - tw - int(24 * s), int(lx + 12 * s)))
            by = max(int(44 * s), min(mh - int(42 * s), int(ly - 18 * s + (i % 2) * 28 * s)))
            rd.rounded_rectangle((bx, by, bx + tw + int(16 * s), by + int(28 * s)), radius=int(5 * s), fill=(*self.ink, 225), outline=(*self.secondary, 190), width=1)
            rd.text((bx + int(8 * s), by + int(4 * s)), lbl, font=lf, fill=WHITE)

        # Header strip inside regional map
        rd.rectangle((0, 0, mw, int(38 * s)), fill=(*self.ink, 225))
        rd.text((int(16 * s), int(8 * s)), "TACTICAL REGIONAL SECTOR  •  NATURAL EARTH 208-COUNTRY VECTOR ATLAS", font=font(int(17 * s), True), fill=self.secondary)
        im.paste(reg_layer.convert("RGB"), (map_x1, map_y1))
        d.rounded_rectangle((map_x1, map_y1, map_x2, map_y2), radius=int(14 * s), outline=self.secondary, width=max(2, int(2.5 * s)))


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
    for line in lines:
        tw = d.textlength(line, font=f)
        d.text(((w - tw) / 2 + 2, y + 12 * s), line, font=f, fill=(0, 0, 0, 220))
        d.text(((w - tw) / 2, y + 10 * s), line, font=f, fill=(254, 240, 138))
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
        try:
            for frame in range(nframes):
                data = None
                if decoder:
                    data = decoder.stdout.read(frame_bytes)
                    if len(data) != frame_bytes:
                        raise StudioError("Footage decode ended unexpectedly")
                im = canvas.frame(frame / fps, duration, data)
                im = caption_frame(im, cues, frame / fps, portrait)
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


def ensure_studio_soundtrack(path, duration_sec=60.0, style="think_school"):
    """Synthesizes a warm, broadcast-grade 48kHz atmospheric documentary score with subtle pulse."""
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
    style_key = plan.get("style") or dossier.get("style") or "think_school"
    theme = STYLE_THEMES.get(style_key, STYLE_THEMES["think_school"])
    beat = next((b for b in plan["beats"] if b.get("asset", {}).get("kind") == "photo"), plan["beats"][0])
    im = Image.new("RGB", (1280, 720), theme["ink"])
    if beat.get("asset", {}).get("kind") == "photo" and Path(beat["asset"]["path"]).exists():
        photo = Image.open(beat["asset"]["path"]).convert("RGB")
        im.paste(ImageOps.fit(photo, (760, 720)), (520, 0))
    else:
        c = Canvas(beat, dossier, 1280, 720)
        im = c.frame(2, 5)
    overlay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    for x in range(1280):
        alpha = int(252 * max(0.0, 1.0 - max(0, x - 440) / 680))
        d.line((x, 0, x, 720), fill=(*theme["ink"], alpha))
    im = Image.alpha_composite(im.convert("RGBA"), overlay)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((65, 52, 420, 92), radius=8, fill=theme["accent"])
    text_block(im, theme["badge"], (80, 60, 330, 32), 20, WHITE, True, 1)
    text_block(im, plan["thumbnail_text"].upper(), (65, 155, 760, 420), 94, WHITE, True, 4)
    d.rectangle((65, 635, 320, 647), fill=theme["secondary"])
    im.convert("RGB").save(path, quality=94, optimize=True)
