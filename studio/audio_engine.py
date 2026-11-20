"""V94 Professional Documentary & Shorts Audio Engine: Multi-Layer Musical Score, Scene-Synced SFX & EBU R128 Mastering."""
import math
import wave
from pathlib import Path
import numpy as np
from .common import run_ff

SR = 48000


def _write_stereo_wav(path, stereo_float):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    clipped = np.clip(stereo_float, -0.96, 0.96)
    pcm = (clipped * 32767.0).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return path


def synthesize_sfx(kind, duration_sec=0.55):
    """Synthesizes crisp, broadcast-grade stereo sound effects (whoosh, impact_boom, riser, data_tick, highlighter)."""
    n = max(1, int(duration_sec * SR))
    t = np.arange(n, dtype=np.float32) / SR
    rng = np.random.default_rng(abs(hash(kind)) % 100000)

    if kind == "whoosh":
        # Band-swept cinematic air whoosh with stereo pan
        noise = rng.standard_normal(n).astype(np.float32)
        env = np.sin(np.pi * (t / max(0.01, duration_sec))) ** 1.8
        # Simple moving-average lowpass sweep for smooth air texture
        kernel = np.ones(18, dtype=np.float32) / 18.0
        smooth = np.convolve(noise, kernel, mode="same")
        tone = 0.25 * np.sin(2 * np.pi * (120 + 260 * (t / max(0.01, duration_sec))) * t)
        sig = (smooth * 0.85 + tone) * env * 0.42
        pan_l = np.linspace(0.9, 0.3, n, dtype=np.float32)
        pan_r = np.linspace(0.3, 0.9, n, dtype=np.float32)
        return np.stack([sig * pan_l, sig * pan_r], axis=1)

    if kind == "impact_boom":
        # Deep cinematic sub-bass hit (85Hz -> 32Hz pitch drop + crisp transient click)
        freq = 88.0 * np.exp(-t * 5.2) + 32.0
        phase = 2 * np.pi * np.cumsum(freq) / SR
        sub = np.sin(phase) * np.exp(-t * 3.8)
        punch = rng.standard_normal(n).astype(np.float32) * np.exp(-t * 42.0) * 0.35
        sig = (sub * 0.85 + punch) * 0.55
        return np.stack([sig, sig], axis=1)

    if kind == "riser":
        # Tension synth riser swelling into a reveal
        p = t / max(0.01, duration_sec)
        freq = 110.0 + 380.0 * (p ** 2)
        phase = 2 * np.pi * np.cumsum(freq) / SR
        sig = (np.sin(phase) + 0.35 * np.sin(2 * phase)) * (p ** 2.2) * np.exp(-np.maximum(0, p - 0.92) * 30.0) * 0.30
        return np.stack([sig, sig], axis=1)

    if kind == "data_tick":
        # Crisp modern UI glass pop/tick for stat counters & charts
        sig = (np.sin(2 * np.pi * 1320 * t) * 0.6 + np.sin(2 * np.pi * 2640 * t) * 0.4) * np.exp(-t * 55.0) * 0.32
        return np.stack([sig, sig], axis=1)

    if kind == "highlighter":
        # Soft marker swipe sound for newspaper highlight reveals
        noise = rng.standard_normal(n).astype(np.float32)
        kernel = np.ones(10, dtype=np.float32) / 10.0
        band = np.convolve(noise, kernel, mode="same") - np.convolve(noise, np.ones(40, dtype=np.float32) / 40.0, mode="same")
        env = np.sin(np.pi * (t / max(0.01, duration_sec))) ** 1.4
        sig = band * env * 0.45
        return np.stack([sig, sig], axis=1)

    # Default subtle click
    sig = np.sin(2 * np.pi * 880 * t) * np.exp(-t * 45.0) * 0.25
    return np.stack([sig, sig], axis=1)


def generate_documentary_score(path, duration_sec, style="think_school", sfx_events=None, is_short=False):
    """
    Generates a rich, multi-layered stereo cinematic documentary score with chord progression,
    warm sub-bass, subtle rhythmic tension pulse, and exact timestamped SFX cues!
    """
    n = max(SR, int(math.ceil(duration_sec * SR)))
    t = np.arange(n, dtype=np.float32) / SR

    # Musical minor/cinematic chord progressions per show format (Hz)
    progressions = {
        "think_school": [(110.0, 130.81, 164.81, 220.0), (87.31, 130.81, 174.61, 220.0), (98.0, 146.83, 196.0, 246.94), (82.41, 123.47, 164.81, 196.0)],  # Am - F - G - Em
        "nitish_rajput": [(98.0, 116.54, 146.83, 196.0), (77.78, 116.54, 155.56, 196.0), (87.31, 130.81, 174.61, 207.65), (73.42, 110.0, 146.83, 185.0)],  # Gm - Eb - Fm - D
        "bbc_dispatch": [(130.81, 155.56, 196.0, 261.63), (116.54, 146.83, 174.61, 233.08), (103.83, 130.81, 155.56, 207.65), (98.0, 146.83, 196.0, 246.94)],  # Cm - Bb - Ab - G
        "abhi_niyu": [(146.83, 174.61, 220.0, 293.66), (116.54, 146.83, 174.61, 233.08), (130.81, 164.81, 196.0, 261.63), (110.0, 130.81, 164.81, 220.0)],  # Dm - Bb - C - Am
    }
    chords = progressions.get(style, progressions["think_school"])
    bar_sec = 3.0 if is_short else 4.0

    left = np.zeros(n, dtype=np.float32)
    right = np.zeros(n, dtype=np.float32)

    # Layer 1: Warm evolving string/synth pad with smooth crossfaded chord bars
    num_bars = int(math.ceil(duration_sec / bar_sec))
    for b_idx in range(num_bars):
        s_i = int(b_idx * bar_sec * SR)
        e_i = min(n, int((b_idx + 1) * bar_sec * SR))
        if e_i <= s_i:
            continue
        tb = t[s_i:e_i]
        seg_len = e_i - s_i
        # Smooth raised-cosine fade at bar edges
        fade_n = min(seg_len // 4, int(0.35 * SR))
        env = np.ones(seg_len, dtype=np.float32)
        if fade_n > 0:
            env[:fade_n] = np.linspace(0.25, 1.0, fade_n, dtype=np.float32)
            env[-fade_n:] = np.linspace(1.0, 0.25, fade_n, dtype=np.float32)

        f0, f1, f2, f3 = chords[b_idx % len(chords)]
        # Deep warm bass + stereo detuned pad voices
        bass = 0.34 * np.sin(2 * np.pi * (f0 * 0.5) * tb)
        pad_l = (0.20 * np.sin(2 * np.pi * f0 * tb) + 0.16 * np.sin(2 * np.pi * (f1 * 1.003) * tb) + 0.14 * np.sin(2 * np.pi * f2 * tb))
        pad_r = (0.20 * np.sin(2 * np.pi * (f0 * 0.997) * tb) + 0.16 * np.sin(2 * np.pi * f1 * tb) + 0.14 * np.sin(2 * np.pi * (f3 * 1.002) * tb))
        left[s_i:e_i] += (bass + pad_l) * env * 0.26
        right[s_i:e_i] += (bass + pad_r) * env * 0.26

    # Layer 2: Subtle journalistic rhythmic pulse (faster 120 BPM for Shorts, measured 90 BPM for Long Documentary)
    bpm = 120.0 if is_short else 90.0
    beat_sec = 60.0 / bpm
    n_pulses = int(duration_sec / beat_sec)
    for p_idx in range(n_pulses):
        pos = int(p_idx * beat_sec * SR)
        plen = min(int(0.14 * SR), n - pos)
        if plen <= 0:
            continue
        tp = np.arange(plen, dtype=np.float32) / SR
        if p_idx % 4 == 0:
            # Soft muted kick pulse
            pf = 75.0 * np.exp(-tp * 14.0) + 42.0
            kick = np.sin(2 * np.pi * np.cumsum(pf) / SR) * np.exp(-tp * 18.0) * 0.18
            left[pos : pos + plen] += kick
            right[pos : pos + plen] += kick
        elif p_idx % 2 == 1:
            # Subtle investigative clock tick
            tick = np.sin(2 * np.pi * 1650 * tp) * np.exp(-tp * 75.0) * 0.055
            left[pos : pos + plen] += tick * (0.7 if p_idx % 4 == 1 else 1.0)
            right[pos : pos + plen] += tick * (1.0 if p_idx % 4 == 1 else 0.7)

    # Layer 3: Mix exact timestamped Cinematic SFX cues (whooshes, booms, ticks, highlighters)
    for ev in sfx_events or []:
        t_ev = float(ev.get("time", 0.0))
        kind = str(ev.get("kind", "whoosh"))
        gain = float(ev.get("gain", 0.75))
        dur = float(ev.get("duration", 0.55 if kind in {"whoosh", "impact_boom", "riser"} else 0.28))
        sfx = synthesize_sfx(kind, dur) * gain
        pos = max(0, int(t_ev * SR))
        end = min(n, pos + len(sfx))
        if end > pos:
            left[pos:end] += sfx[: end - pos, 0]
            right[pos:end] += sfx[: end - pos, 1]

    # Smooth 1.2s fade-in and 1.5s fade-out on master bed
    fi = min(n // 5, int(1.2 * SR))
    fo = min(n // 5, int(1.5 * SR))
    if fi > 0:
        fade_in = np.linspace(0.0, 1.0, fi, dtype=np.float32)
        left[:fi] *= fade_in
        right[:fi] *= fade_in
    if fo > 0:
        fade_out = np.linspace(1.0, 0.0, fo, dtype=np.float32)
        left[-fo:] *= fade_out
        right[-fo:] *= fade_out

    stereo = np.stack([left, right], axis=1)
    return _write_stereo_wav(path, stereo)


def master_video_with_sound_design(video_in, voice_in, score_wav, output_mp4, is_short=False):
    """
    Broadcast-grade FFmpeg mastering:
    - Voiceover EQ (warm low-shelf + presence boost + highpass rumble cut)
    - Sidechain ducking (score automatically ducks -10dB under narration and rises cleanly in pauses)
    - EBU R128 loudness normalization (-16 LUFS for Long Documentary, -14 LUFS for Shorts)
    """
    target_lufs = -14 if is_short else -16
    score_vol = 0.24 if is_short else 0.20
    run_ff(
        [
            "-i", str(video_in),
            "-i", str(voice_in),
            "-i", str(score_wav),
            "-filter_complex",
            (
                f"[1:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,"
                f"highpass=f=75,equalizer=f=220:width_type=o:width=1.2:g=1.8,"
                f"equalizer=f=3200:width_type=o:width=1.5:g=2.2,asplit=2[voice][side];"
                f"[2:a]volume={score_vol}[bed];"
                f"[bed][side]sidechaincompress=threshold=0.018:ratio=7:attack=20:release=320[duck];"
                f"[voice][duck]amix=inputs=2:duration=first:normalize=0,"
                f"loudnorm=I={target_lufs}:TP=-1.5:LRA=8[aout]"
            ),
            "-map", "0:v:0", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-ar", "48000",
            "-shortest", "-movflags", "+faststart", str(output_mp4),
        ]
    )
    return output_mp4
