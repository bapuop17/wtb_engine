from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import socket
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]


class StudioError(RuntimeError):
    pass


def load_json(path, default=None):
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()[:20]


def config():
    cfg = load_json(ROOT / "studio_config.json")
    for key in ("llm_provider", "llm_model", "voice_provider", "voice", "privacy"):
        if os.getenv("WTB_" + key.upper()):
            cfg[key] = os.environ["WTB_" + key.upper()]
    return cfg


class Budget:
    def __init__(self, minutes=270, max_calls=140):
        self.deadline = time.monotonic() + minutes * 60
        self.calls = 0
        self.max_calls = max_calls

    def check(self):
        if time.monotonic() >= self.deadline:
            raise StudioError("Run time budget exhausted. Checkpoints retained; upload blocked.")

    def spend(self):
        self.check()
        self.calls += 1
        if self.calls > self.max_calls:
            raise StudioError("AI request budget exhausted; upload blocked.")


def public_url(url):
    p = urlparse(url)
    if p.scheme not in {"http", "https"} or not p.hostname or p.username or p.password:
        raise StudioError("Only public HTTP(S) source URLs are allowed")
    for info in socket.getaddrinfo(p.hostname, p.port or (443 if p.scheme == "https" else 80)):
        if not ipaddress.ip_address(info[4][0]).is_global:
            raise StudioError("Private-network source URL rejected")
    return url


def request(method, url, *, retries=2, **kwargs):
    import requests
    last = "connection failed"
    for attempt in range(retries + 1):
        try:
            r = requests.request(method, url, timeout=(12, 90), **kwargs)
            if r.status_code in (408, 429, 500, 502, 503, 504):
                last = f"HTTP {r.status_code}"
                r.close()
                if attempt < retries:
                    time.sleep(min(2 ** attempt * 2, 8))
                continue
            if not r.ok:
                status = r.status_code
                r.close()
                raise StudioError(f"{urlparse(url).hostname}: HTTP {status}")
            return r
        except requests.RequestException:
            # Never log request headers, credentials or query-string API keys.
            last = "network request failed"
    raise StudioError(f"{urlparse(url).hostname}: {last}")


def download(url, path, max_bytes=120_000_000):
    """Bounded public download; validate every redirect before following it."""
    target = url
    for _ in range(6):
        public_url(target)
        r = request("GET", target, stream=True, allow_redirects=False,
                    headers={"User-Agent": "WTBStudio/1.0 (documentary research)"})
        if 300 <= r.status_code < 400:
            from urllib.parse import urljoin
            target = urljoin(target, r.headers.get("Location", ""))
            r.close()
            continue
        dest = Path(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        partial = dest.with_suffix(dest.suffix + ".part")
        try:
            count = 0
            with partial.open("wb") as out:
                for chunk in r.iter_content(128 * 1024):
                    count += len(chunk)
                    if count > max_bytes:
                        raise StudioError("Download exceeds size budget")
                    out.write(chunk)
            partial.replace(dest)
            return dest
        finally:
            r.close()
            partial.unlink(missing_ok=True)
    raise StudioError("Too many source redirects")


def ffmpeg():
    import shutil
    executable = os.getenv("FFMPEG_BINARY") or shutil.which("ffmpeg")
    if executable:
        return executable
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def run_ff(args, timeout=900):
    r = subprocess.run([ffmpeg(), "-hide_banner", "-nostdin", "-y", *map(str, args)],
                       capture_output=True, timeout=timeout)
    if r.returncode:
        raise StudioError("FFmpeg failed: " + r.stderr.decode(errors="replace")[-1600:])
    return r
