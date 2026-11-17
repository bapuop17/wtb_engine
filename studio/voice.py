import asyncio
import base64
import os
import wave
import numpy as np
from .common import StudioError, digest, load_json, request, run_ff, save_json


class Voice:
    def __init__(self, cfg, directory):
        self.cfg, self.dir = cfg, directory
        directory.mkdir(parents=True, exist_ok=True)
        self.provider = cfg["voice_provider"]
        if self.provider == "auto":
            self.provider = ("elevenlabs" if os.getenv("ELEVENLABS_API_KEY") and os.getenv("ELEVENLABS_VOICE_ID")
                             else "deepgram" if os.getenv("DEEPGRAM_API_KEY") else "edge")
        self.voice = cfg.get("voice") or {"elevenlabs": os.getenv("ELEVENLABS_VOICE_ID", ""),
            "deepgram": "aura-2-odysseus-en", "edge": "en-US-AndrewNeural"}.get(self.provider, "")
        if not self.voice:
            raise StudioError("Invalid voice provider/voice configuration")
        self.characters = 0

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
            try:
                asyncio.run(asyncio.wait_for(synth(), timeout=90))
            except Exception as e:
                raise StudioError("Edge TTS failed; narrator will not switch and silence will not be substituted") from e
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
