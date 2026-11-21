"""V98 Remotion React Video Bridge: exports WTB storyboards to remotion_studio/ and renders via headless Remotion CLI when enabled."""
import json
import os
import shutil
import subprocess
from pathlib import Path


def remotion_available(repo_root=None):
    root = Path(repo_root or Path(__file__).resolve().parent.parent)
    rem_dir = root / "remotion_studio"
    return (rem_dir / "package.json").exists() and (rem_dir / "node_modules").exists() and shutil.which("npx") is not None


def export_remotion_props(plan, audio_clips, out_json, fps=24):
    """Converts WTB documentary plan + audio durations into Remotion DocumentaryProps JSON."""
    scenes = []
    for beat, aud in zip(plan.get("beats", []), audio_clips):
        vis = beat.get("visual", {})
        data = vis.get("data", {})
        img_path = ""
        asset = beat.get("asset", {})
        if asset.get("path") and Path(asset["path"]).exists():
            img_path = Path(asset["path"]).resolve().as_uri()
        scenes.append({
            "id": beat.get("id", ""),
            "chapter": beat.get("chapter", "WORLD TALK BRIEF"),
            "headline": vis.get("headline", ""),
            "callout": data.get("callout") or data.get("metric_badge") or "",
            "statValue": str(data.get("value") or data.get("stat") or ""),
            "statLabel": str(data.get("label") or ""),
            "narration": beat.get("narration", ""),
            "durationInFrames": max(24, int(round(float(aud.get("duration", 4.0)) * fps))),
            "imageSrc": img_path,
            "kind": vis.get("kind", "photo"),
        })
    payload = {
        "title": plan.get("title", "World Talk Brief"),
        "style": plan.get("style", "think_school"),
        "fps": fps,
        "scenes": scenes,
    }
    Path(out_json).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return Path(out_json)


def render_with_remotion(props_json, output_mp4, repo_root=None, timeout=600):
    """Renders WTBDocumentary via Remotion CLI if node_modules are installed; returns True on success."""
    root = Path(repo_root or Path(__file__).resolve().parent.parent)
    if not remotion_available(root):
        return False
    rem_dir = root / "remotion_studio"
    cmd = [
        "npx", "remotion", "render",
        "src/index.ts", "WTBDocumentary",
        str(Path(output_mp4).resolve()),
        "--props", str(Path(props_json).resolve()),
        "--codec", "h264",
        "--pixel-format", "yuv420p",
    ]
    res = subprocess.run(cmd, cwd=str(rem_dir), capture_output=True, text=True, timeout=timeout)
    return res.returncode == 0 and Path(output_mp4).exists() and Path(output_mp4).stat().st_size > 10_000
