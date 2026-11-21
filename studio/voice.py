import asyncio
import base64
import os
import wave
from pathlib import Path
import numpy as np
from .common import StudioError, digest, load_json, request, run_ff, save_json


def _kokoro_available():
    """Returns (model_path, voices_path) if Kokoro-82M ONNX weights & package are installed locally."""
    try:
        import kokoro_onnx  # noqa: F401
        import soundfile  # noqa: F401
    except Exception:
        return None
    candidates = [
        Path(os.getenv("WTB_KOKORO_DIR", "cache/kokoro")),
        Path("cache/kokoro"),
        Path.home() / ".cache" / "kokoro",
    ]
    for d in candidates:
        m = d / "kokoro-v1.0.onnx"
        v = d / "voices-v1.0.bin"
        if m.exists() and v.exists() and m.stat().st_size > 1_000_000:
            return (m, v)
    return None


class Voice:
    _kokoro_engine = None

    def __init__(self, cfg, directory):
        self.cfg, self.dir = cfg, directory
        directory.mkdir(parents=True, exist_ok=True)
        self.provider = cfg["voice_provider"]
        if self.provider == "auto":
            if os.getenv("ELEVENLABS_API_KEY") and os.getenv("ELEVENLABS_VOICE_ID"):
                self.provider = "elevenlabs"
            elif os.getenv("DEEPGRAM_API_KEY"):
                self.provider = "deepgram"
            elif _kokoro_available() is not None:
                self.provider = "kokoro"
            else:
                self.provider = "edge"
        self.voice = cfg.get("voice") or {
            "elevenlabs": os.getenv("ELEVENLABS_VOICE_ID", ""),
            "deepgram": "aura-2-odysseus-en",
            "kokoro": os.getenv("WTB_KOKORO_VOICE", "am_michael"),
            "edge": "en-US-AndrewNeural",
        }.get(self.provider, "")
        if not self.voice:
            raise StudioError("Invalid voice provider/voice configuration")
        self.characters = 0

    def _get_kokoro(self):
        if Voice._kokoro_engine is None:
            paths = _kokoro_available()
            if not paths:
                raise StudioError("Kokoro-82M ONNX weights not found in cache/kokoro/")
            from kokoro_onnx import Kokoro
            Voice._kokoro_engine = Kokoro(str(paths[0]), str(paths[1]))
        return Voice._kokoro_engine

    def synthesize(self, text):
        self.characters += len(text)
        if self.characters > self.cfg["max_tts_characters"]:
            raise StudioError("TTS character budget exceeded")
        key = digest([self.provider, self.voice, text])
        wav, meta_path = self.dir / (key + ".wav"), self.dir / (key + ".json")
        if wav.exists() and meta_path.exists():
            meta = load_json(meta_path)
            inspect_audio(wav)
            return {**meta, "path": str(wav)}
        raw = self.dir / (key + ".mp3")
        timings = []
        if self.provider == "elevenlabs":
            api_key = os.getenv("ELEVENLABS_API_KEY")
            if not api_key:
                raise StudioError("ELEVENLABS_API_KEY is missing")
            data = request("POST", f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice}/with-timestamps",
                headers={"xi-api-key": api_key}, json={"text": text,
                "model_id": os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2"),
                "voice_settings": {"stability": 0.48, "similarity_boost": 0.75, "style": 0.15, "use_speaker_boost": True}}).json()
            raw.write_bytes(base64.b64decode(data["audio_base64"]))
            align = data.get("normalized_alignment") or data.get("alignment") or {}
            word, start, end = "", None, 0
            for ch, a, b in zip(align.get("characters", []), align.get("character_start_times_seconds", []),
                                align.get("character_end_times_seconds", [])):
                if ch.isspace():
                    if word: timings.append({"text": word, "start": start, "end": end})
                    word, start = "", None
                else:
                    start = a if start is None else start
                    word += ch; end = b
            if word: timings.append({"text": word, "start": start, "end": end})
        elif self.provider == "deepgram":
            if not os.getenv("DEEPGRAM_API_KEY"):
                raise StudioError("DEEPGRAM_API_KEY is missing")
            r = request("POST", "https://api.deepgram.com/v1/speak",
                params={"model": self.voice, "encoding": "mp3"},
                headers={"Authorization": "Token " + os.environ["DEEPGRAM_API_KEY"]}, json={"text": text})
            raw.write_bytes(r.content)
        elif self.provider == "kokoro":
            import soundfile as sf
            kokoro = self._get_kokoro()
            voice_id = self.voice if self.voice in {"am_michael", "am_adam", "am_fenrir", "bm_george", "bm_lewis", "af_heart", "af_bella", "bf_emma"} else "am_michael"
            lang = "en-gb" if voice_id.startswith("b") else "en-us"
            samples, sr = kokoro.create(text, voice=voice_id, speed=1.02, lang=lang)
            raw = self.dir / (key + "_raw.wav")
            sf.write(str(raw), samples, sr)
        elif self.provider == "edge":
            async def synth():
                import edge_tts
                comm = edge_tts.Communicate(text, self.voice, rate="-3%", pitch="+0Hz", boundary="WordBoundary")
                with raw.open("wb") as audio:
                    async for chunk in comm.stream():
                        if chunk["type"] == "audio": audio.write(chunk["data"])
                        elif chunk["type"] == "WordBoundary":
                            timings.append({"text": chunk["text"], "start": chunk["offset"] / 1e7,
                                            "end": (chunk["offset"] + chunk["duration"]) / 1e7})
            last_tts_err = None
            for attempt_tts in range(3):
                try:
                    timings.clear()
                    asyncio.run(asyncio.wait_for(synth(), timeout=90))
                    if raw.exists() and raw.stat().st_size > 500:
                        last_tts_err = None
                        break
                except Exception as e:
                    last_tts_err = e
            if last_tts_err is not None:
                try:
                    from gtts import gTTS
                    gTTS(text=text, lang="en").save(str(raw))
                except Exception:
                    raise StudioError("Edge TTS failed; narrator will not switch and silence will not be substituted") from last_tts_err
        else:
            raise StudioError("Unsupported voice provider")
        run_ff(["-i", raw, "-af", "highpass=f=60,loudnorm=I=-16:TP=-1.5:LRA=9,apad=pad_dur=0.16",
                "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", wav])
        duration = inspect_audio(wav)
        meta = {"duration": duration, "provider": self.provider, "voice": self.voice, "timings": timings,
                "timing_mode": "provider word timings" if timings else "beat-level exact; captions estimated within beat"}
        save_json(meta_path, meta)
        return {**meta, "path": str(wav)}


def inspect_audio(path):
    with wave.open(str(path), "rb") as w:
        if w.getsampwidth() != 2:
            raise StudioError("Audio must be 16-bit PCM")
        duration = w.getnframes() / w.getframerate()
        a = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(float) / 32768
    if duration < 1 or not len(a) or np.sqrt(np.mean(a * a)) < 0.003:
        raise StudioError("Missing/silent speech; upload blocked")
    if float(np.mean(np.abs(a) >= 0.999)) > 0.002:
        raise StudioError("Clipped voice audio")
    return duration


def captions(text, audio):
    words = list(audio.get("timings", []))
    if not words:
        tokens = text.split()
        weights = [max(2, len(w)) + (3 if w.endswith((".", "?", "!", ",")) else 0) for w in tokens]
        total = sum(weights); t = 0
        for token, weight in zip(tokens, weights):
            end = t + (audio["duration"] - 0.16) * weight / total
            words.append({"text": token, "start": t, "end": end}); t = end
    return [{"text": " ".join(w["text"] for w in words[i:i+7]), "start": words[i]["start"],
             "end": words[min(i+6, len(words)-1)]["end"]} for i in range(0, len(words), 7)]
