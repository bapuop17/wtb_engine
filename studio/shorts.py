"""V94 Dedicated Retention-Engineered YouTube Shorts Production Workflow (1080x1920, 9:16)."""
import math
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageOps
from .common import ffmpeg, save_json
from .audio_engine import generate_documentary_score, master_video_with_sound_design
from .render import Canvas, ease, font, wrap, text_block, WHITE, STYLE_THEMES


SHORTS_DIRECTOR_PROMPT = """Write a high-retention 38-to-48 second YouTube Short (105-135 words) for World Talk Brief.
CRITICAL SHORTS RULES (2026-2027 Retention Standard):
- Beat S01 (0-3s HOOK): Start with a shocking concrete number, paradox, or immediate visual stakes — ZERO greetings or slow intros!
- Beats S02-S06 (3-40s): Fast-paced escalating story beats (16-24 words each, ~5-7s per beat with 2 visual cuts each = visual change every 2.8 seconds!).
- Beat S07 (last 4s PAYOFF/CTA): Sharp unforgettable twist or punchline + natural 4-word CTA ("Follow for daily breakdowns.").
- Visual kinds: 'photo', 'footage', 'globe', 'stat_callout', 'actor_split'.
- Return JSON: {"title":"punchy under-75-char title #Shorts","hook_banner":"2-4 CAPS WORDS","beats":[{"id":"S01","chapter":"HOOK","narration":"...","fact_ids":["F1"],"visual":{"kind":"photo","headline":"3-5 words","query":"specific vertical-friendly visual query","must_include":["entity"],"reason":"why","data":{}}}]}
"""


def draw_shorts_word_highlight_captions(im, cues, t, accent_color=(250, 204, 21)):
    """Draws 2026-2027 retention-style active word-by-word highlighted vertical captions in the safe center-lower zone."""
    cue = next((c for c in cues if c["start"] <= t <= c["end"] + 0.06), None)
    if not cue:
        return im
    w, h = im.size
    s = w / 1080.0
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    f = font(int(54 * s), True)
    words = str(cue["text"]).upper().split()
    if not words:
        return im

    # Determine which word is actively spoken right now
    dur = max(0.15, cue["end"] - cue["start"])
    prog = max(0.0, min(0.999, (t - cue["start"]) / dur))
    active_idx = min(len(words) - 1, int(prog * len(words)))

    # Group into 1 or 2 crisp lines (max 3-4 words per line for huge readable Shorts impact)
    lines = []
    cur = []
    cur_w = 0
    max_w = w * 0.84
    space_w = d.textlength(" ", font=f)
    for idx, wd in enumerate(words):
        ww = d.textlength(wd, font=f)
        if cur and cur_w + space_w + ww > max_w:
            lines.append(cur)
            cur = [(idx, wd, ww)]
            cur_w = ww
        else:
            cur.append((idx, wd, ww))
            cur_w += (space_w if len(cur) > 1 else 0) + ww
    if cur:
        lines.append(cur)

    line_h = int(72 * s)
    total_h = len(lines) * line_h
    y = int(h * 0.74 - total_h / 2)

    for line in lines:
        lw = sum(item[2] for item in line) + space_w * max(0, len(line) - 1)
        x = (w - lw) / 2.0
        for idx, wd, ww in line:
            is_active = (idx == active_idx)
            if is_active:
                pad_x, pad_y = int(14 * s), int(6 * s)
                d.rounded_rectangle(
                    (x - pad_x, y - pad_y, x + ww + pad_x, y + int(56 * s) + pad_y),
                    radius=int(12 * s),
                    fill=(*accent_color, 245),
                )
                d.text((x, y), wd, font=f, fill=(10, 14, 22, 255))
            else:
                # Heavy black stroke/shadow for ultra-clean legibility over bright footage
                for ox, oy in [(-3, -3), (3, -3), (-3, 3), (3, 3), (0, 5)]:
                    d.text((x + ox, y + oy), wd, font=f, fill=(0, 0, 0, 235))
                d.text((x, y), wd, font=f, fill=(255, 255, 255, 255))
            x += ww + space_w
        y += line_h
    return Image.alpha_composite(im.convert("RGBA"), layer).convert("RGB")


def render_dedicated_short(short_beats, dossier, audio_by_id, out_mp4, cfg, style="think_school"):
    """
    Renders a native 1080x1920 9:16 YouTube Short with:
    - Fast 2.8-second multi-shot visual cuts + Whip-Pan/Zoom-Flash transitions
    - Top hook banner & smooth retention progress bar
    - Word-by-word active highlighted captions
    - Dedicated 120 BPM Shorts musical score + cut whoosh/impact SFX mastered to -14 LUFS
    """
    w, h, fps = 1080, 1920, int(cfg.get("fps", 24))
    out_mp4 = Path(out_mp4)
    raw_mp4 = out_mp4.with_suffix(".raw.mp4")
    voice_concat = out_mp4.with_suffix(".voice.wav")
    score_wav = out_mp4.with_suffix(".score.wav")

    # Concatenate beat voiceovers cleanly into one voice track
    v_list = out_mp4.with_suffix(".vlist.txt")
    v_list.write_text(
        "\n".join("file '" + Path(audio_by_id[b["id"]]["path"]).resolve().as_posix().replace("'", "'\\''") + "'" for b in short_beats),
        encoding="utf-8",
    )
    subprocess.run(
        [ffmpeg(), "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(v_list), "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(voice_concat)],
        check=True,
    )

    total_dur = sum(float(b["duration"]) for b in short_beats)
    sfx_events = [{"time": 0.05, "kind": "impact_boom", "gain": 0.85}]
    elapsed = 0.0

    encoder = subprocess.Popen(
        [
            ffmpeg(), "-y", "-v", "error", "-nostdin",
            "-f", "rawvideo", "-vcodec", "rawvideo", "-s", f"{w}x{h}", "-r", str(fps), "-pix_fmt", "rgb24", "-i", "-",
            "-c:v", "libx264", "-preset", cfg.get("preset", "fast"), "-crf", str(cfg.get("crf", 19)), "-pix_fmt", "yuv420p",
            str(raw_mp4),
        ],
        stdin=subprocess.PIPE,
    )

    theme = STYLE_THEMES.get(style, STYLE_THEMES["think_school"])
    accent = theme["accent"]

    try:
        for b_idx, beat in enumerate(short_beats):
            dur = float(beat["duration"])
            nframes = max(1, int(round(dur * fps)))
            if b_idx > 0:
                sfx_events.append({"time": elapsed, "kind": "whoosh", "gain": 0.75})
            if beat["visual"]["kind"] in {"stat_callout", "chart"}:
                sfx_events.append({"time": elapsed + 0.35, "kind": "data_tick", "gain": 0.80})
            if beat["visual"]["kind"] == "evidence":
                sfx_events.append({"time": elapsed + 0.35, "kind": "highlighter", "gain": 0.80})

            canvas = Canvas(beat, dossier, w, h)
            words = beat["narration"].split()
            chunk_sz = 5
            n_chunks = max(1, (len(words) + chunk_sz - 1) // chunk_sz)
            c_dur = dur / n_chunks
            cues = [
                {"text": " ".join(words[i * chunk_sz : (i + 1) * chunk_sz]), "start": i * c_dur, "end": (i + 1) * c_dur}
                for i in range(n_chunks)
            ]

            # V103: Decode real HD footage MP4 clips natively in 9:16 Shorts (no more beige cards replacing video!)
            decoder = None
            frame_bytes = w * h * 3
            asset = beat.get("asset") or {}
            if asset.get("kind") == "footage" and asset.get("path") and Path(asset["path"]).exists():
                decoder = subprocess.Popen(
                    [
                        ffmpeg(), "-v", "error", "-nostdin", "-stream_loop", "-1", "-i", str(asset["path"]),
                        "-an", "-vf", f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps={fps}",
                        "-t", str(dur + 0.5), "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1",
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                )

            try:
                for f_i in range(nframes):
                    t_local = f_i / float(fps)
                    t_global = elapsed + t_local
                    v_data = None
                    if decoder:
                        raw_f = decoder.stdout.read(frame_bytes)
                        if len(raw_f) == frame_bytes:
                            v_data = raw_f
                    im = canvas.frame(t_local, dur, v_data)
                    # Sleek top retention progress bar across full Short duration
                    d = ImageDraw.Draw(im)
                    d.rectangle((0, 0, w, 10), fill=(15, 23, 42))
                    d.rectangle((0, 0, int(w * min(1.0, t_global / max(0.1, total_dur))), 10), fill=accent)
                    # Active word-by-word highlighted vertical captions
                    im = draw_shorts_word_highlight_captions(im, cues, t_local, accent_color=(250, 204, 21))
                    if b_idx > 0 and t_local < 0.14:
                        im = Image.blend(Image.new("RGB", (w, h), theme["ink"]), im, t_local / 0.14)
                    encoder.stdin.write(im.tobytes())
            finally:
                if decoder:
                    if decoder.poll() is None:
                        decoder.kill()
                    decoder.wait()
                    decoder.stdout.close()
            elapsed += dur
        encoder.stdin.close()
        encoder.wait(timeout=240)
    finally:
        if encoder.poll() is None:
            encoder.kill()
            encoder.wait()

    generate_documentary_score(score_wav, total_dur + 2.0, style=style, sfx_events=sfx_events, is_short=True)
    master_video_with_sound_design(raw_mp4, voice_concat, score_wav, out_mp4, is_short=True)
    for tmp in (raw_mp4, voice_concat, score_wav, v_list):
        tmp.unlink(missing_ok=True)
    return out_mp4
