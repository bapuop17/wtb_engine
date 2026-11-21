"""V97 Headless Chromium HTML5/CSS3/SVG Broadcast Motion Graphics Renderer (Vox / Johnny Harris / Think School Glassmorphism)."""
import base64
import html
import shutil
import subprocess
import tempfile
from pathlib import Path
from PIL import Image


def _find_chrome():
    for name in ("chromium", "google-chrome", "chromium-browser"):
        p = shutil.which(name)
        if p:
            return p
    return None


def _img_to_data_uri(img_path):
    if not img_path or not Path(img_path).is_file():
        return ""
    raw = Path(img_path).read_bytes()
    ext = Path(img_path).suffix.lower().lstrip(".") or "jpeg"
    if ext == "jpg":
        ext = "jpeg"
    return f"data:image/{ext};base64,{base64.b64encode(raw).decode('ascii')}"


def render_html_card(html_doc, width=1920, height=1080):
    """Renders any HTML5/CSS3/SVG broadcast graphic via headless Chromium into a crisp PIL RGB Image."""
    chrome = _find_chrome()
    if not chrome:
        return None
    with tempfile.TemporaryDirectory() as td:
        html_p = Path(td) / "card.html"
        png_p = Path(td) / "card.png"
        html_p.write_text(html_doc, encoding="utf-8")
        cmd = [
            chrome, "--headless=new", "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
            "--disable-crash-reporter", "--no-first-run", f"--user-data-dir={td}/prof",
            "--hide-scrollbars", f"--window-size={width},{height}",
            f"--screenshot={png_p}", html_p.as_uri(),
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, timeout=8)
        except Exception:
            return None
        if res.returncode == 0 and png_p.is_file() and png_p.stat().st_size > 5000:
            return Image.open(png_p).convert("RGB")
    return None


def render_v97_high_ctr_thumbnail(title_hook, bg_img_path, accent_hex="#10B981", badge_text="WORLD TALK BRIEF"):
    """Renders a studio-grade 1280x720 YouTube thumbnail using CSS3 glassmorphism, neon glow, and Inter Display Black."""
    bg_uri = _img_to_data_uri(bg_img_path)
    words = str(title_hook or "BREAKING SHIFT").upper().split()[:4]
    line1 = html.escape(" ".join(words[:2]))
    line2 = html.escape(" ".join(words[2:])) if len(words) > 2 else ""
    doc = f"""<!doctype html><html><head><meta charset="utf-8"><style>
    *{{margin:0;padding:0;box-sizing:border-box;font-family:'Inter Display','Inter','DejaVu Sans',sans-serif;}}
    body{{width:1280px;height:720px;overflow:hidden;position:relative;background:#070d19;}}
    .bg{{position:absolute;inset:0;background:url('{bg_uri}') center/cover no-repeat;filter:contrast(1.18) saturate(1.15);transform:scale(1.04);}}
    .grad{{position:absolute;inset:0;background:linear-gradient(95deg, rgba(6,11,22,0.96) 0%, rgba(6,11,22,0.82) 45%, rgba(6,11,22,0.12) 100%);}}
    .bar{{position:absolute;left:0;top:0;bottom:0;width:18px;background:{accent_hex};box-shadow:0 0 36px {accent_hex};}}
    .wrap{{position:relative;z-index:2;padding:74px 72px;height:100%;display:flex;flex-direction:column;justify-content:center;max-width:820px;}}
    .pill{{display:inline-block;align-self:flex-start;padding:10px 22px;border-radius:8px;background:{accent_hex};color:#050b14;font-weight:900;font-size:24px;letter-spacing:2px;margin-bottom:26px;box-shadow:0 10px 30px rgba(0,0,0,0.45);}}
    .l1{{font-size:122px;font-weight:900;line-height:0.96;color:#FACC15;text-shadow:0 10px 32px rgba(0,0,0,0.95);letter-spacing:-2px;}}
    .l2{{font-size:112px;font-weight:900;line-height:0.98;color:#FFFFFF;text-shadow:0 10px 32px rgba(0,0,0,0.95);letter-spacing:-2px;margin-top:8px;}}
    </style></head><body>
    <div class="bg"></div><div class="grad"></div><div class="bar"></div>
    <div class="wrap">
      <div class="pill">{html.escape(badge_text)}</div>
      <div class="l1">{line1}</div>
      {f'<div class="l2">{line2}</div>' if line2 else ''}
    </div></body></html>"""
    return render_html_card(doc, 1280, 720)


def render_v97_glass_stat_board(headline, metrics, bg_img_path, badge="KEY IMPACT METRICS", accent_hex="#14B8A6", width=1920, height=1080):
    """Renders an After-Effects-grade frosted-glass (backdrop-filter: blur) metric dashboard via Chromium."""
    bg_uri = _img_to_data_uri(bg_img_path)
    cards_html = ""
    for i, m in enumerate(metrics[:3]):
        col = accent_hex if i % 2 == 0 else "#F59E0B"
        cards_html += f"""
        <div class="card" style="border-top:6px solid {col};">
          <div class="tag">METRIC 0{i+1}</div>
          <div class="val">{html.escape(str(m.get('value','')))}</div>
          <div class="lbl" style="color:{col};">{html.escape(str(m.get('label','')).upper())}</div>
          <div class="sub">{html.escape(str(m.get('sub','')))}</div>
          <div class="track"><div class="fill" style="background:{col};"></div></div>
        </div>"""
    doc = f"""<!doctype html><html><head><meta charset="utf-8"><style>
    *{{margin:0;padding:0;box-sizing:border-box;font-family:'Inter Display','Inter','DejaVu Sans',sans-serif;}}
    body{{width:{width}px;height:{height}px;overflow:hidden;position:relative;background:#08101e;color:#f8fafc;}}
    .bg{{position:absolute;inset:0;background:url('{bg_uri}') center/cover no-repeat;filter:blur(14px) brightness(0.42) saturate(1.25);transform:scale(1.08);}}
    .grid{{position:absolute;inset:0;background-image:linear-gradient(rgba(255,255,255,0.03) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,0.03) 1px,transparent 1px);background-size:64px 64px;}}
    .wrap{{position:relative;z-index:2;padding:56px 96px;height:100%;display:flex;flex-direction:column;}}
    .top{{display:flex;align-items:center;gap:18px;margin-bottom:18px;}}
    .pill{{padding:8px 18px;border-radius:6px;background:{accent_hex};color:#050b14;font-weight:900;font-size:20px;letter-spacing:1.5px;}}
    .brand{{color:#94a3b8;font-weight:700;font-size:20px;letter-spacing:2px;}}
    h1{{font-size:56px;font-weight:900;letter-spacing:-1px;margin-bottom:46px;text-shadow:0 6px 24px rgba(0,0,0,0.6);}}
    .row{{display:flex;gap:32px;flex:1;max-height:520px;}}
    .card{{flex:1;background:rgba(15,25,42,0.72);backdrop-filter:blur(24px);border-radius:20px;padding:38px 34px;border:1px solid rgba(255,255,255,0.12);box-shadow:0 24px 60px rgba(0,0,0,0.55);display:flex;flex-direction:column;justify-content:space-between;}}
    .tag{{font-size:18px;font-weight:800;color:#94a3b8;letter-spacing:2px;}}
    .val{{font-size:96px;font-weight:900;line-height:1.0;color:#ffffff;letter-spacing:-3px;margin:14px 0;text-shadow:0 8px 28px rgba(0,0,0,0.5);}}
    .lbl{{font-size:26px;font-weight:800;line-height:1.2;margin-bottom:10px;}}
    .sub{{font-size:21px;color:#cbd5e1;line-height:1.35;}}
    .track{{height:10px;border-radius:6px;background:rgba(255,255,255,0.12);overflow:hidden;margin-top:24px;}}
    .fill{{width:100%;height:100%;border-radius:6px;}}
    </style></head><body>
    <div class="bg"></div><div class="grid"></div>
    <div class="wrap">
      <div class="top"><div class="pill">{html.escape(badge)}</div><div class="brand">WORLD TALK BRIEF</div></div>
      <h1>{html.escape(headline)}</h1>
      <div class="row">{cards_html}</div>
    </div></body></html>"""
    return render_html_card(doc, width, height)
