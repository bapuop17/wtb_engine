"""V98 After-Effects-Grade Cinema FX: OpenCV Directional Motion-Blur Whip-Pans, Anamorphic Light-Leaks, Spring Physics & 35mm Film Finish."""
import math
import numpy as np
from PIL import Image

try:
    import cv2
except Exception:
    cv2 = None

_VIGNETTE_CACHE = {}


def spring_ease(t):
    """After-Effects-style damped spring curve with subtle crisp overshoot."""
    t = max(0.0, min(1.0, float(t)))
    if t <= 0.0:
        return 0.0
    if t >= 1.0:
        return 1.0
    return 1.0 - math.exp(-7.2 * t) * math.cos(9.5 * t)


def get_vignette_mask(w, h, strength=0.34):
    key = (w, h, round(strength, 2))
    if key not in _VIGNETTE_CACHE:
        y = np.linspace(-1.0, 1.0, h, dtype=np.float32)[:, None]
        x = np.linspace(-1.0, 1.0, w, dtype=np.float32)[None, :]
        r2 = x * x + y * y
        mask = np.clip(1.0 - strength * (r2 ** 1.35), 0.42, 1.0)[..., None]
        _VIGNETTE_CACHE[key] = mask
    return _VIGNETTE_CACHE[key]


def apply_cinema_film_finish(pil_img, frame_seed=0, grain_amount=4.2, vignette_strength=0.30):
    """Applies Netflix/BBC documentary color grade (crisp S-curve contrast + teal shadows/amber highlights + radial vignette + subtle 35mm grain)."""
    arr = np.asarray(pil_img, dtype=np.float32)
    h, w = arr.shape[:2]
    # Subtle S-curve contrast & editorial color balance
    arr = (arr - 128.0) * 1.09 + 128.0
    # Warm highlight lift + cool shadow depth
    luma = (0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2])[..., None] / 255.0
    arr[..., 0] += (luma[..., 0] - 0.35) * 7.5
    arr[..., 2] += (0.55 - luma[..., 0]) * 8.5
    # Radial cinema vignette
    arr *= get_vignette_mask(w, h, vignette_strength)
    # Subtle organic 35mm luminance grain (prevents flat digital banding)
    if grain_amount > 0:
        rng = np.random.default_rng((frame_seed * 2654435761) & 0xFFFFFFFF)
        # Fast coarse grain upsampled 2x for authentic film texture
        gh, gw = max(1, h // 2), max(1, w // 2)
        g = rng.normal(0.0, grain_amount, (gh, gw, 1)).astype(np.float32)
        g = np.repeat(np.repeat(g, 2, axis=0), 2, axis=1)[:h, :w, :]
        arr += g
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), mode="RGB")


def directional_whip_pan(prev_im, next_im, alpha):
    """True Premiere Pro / After Effects horizontal whip-pan with OpenCV 1D directional motion blur."""
    w, h = next_im.size
    a = max(0.0, min(1.0, float(alpha)))
    eased = a * a * (3.0 - 2.0 * a)
    shift = int(w * (1.0 - eased))
    comp = Image.new("RGB", (w, h), (8, 13, 22))
    comp.paste(prev_im, (shift - w, 0))
    comp.paste(next_im, (shift, 0))
    blur_intensity = math.sin(math.pi * a)
    if cv2 is not None and blur_intensity > 0.08:
        k = max(3, int(blur_intensity * 45) | 1)
        kernel = np.zeros((1, k), dtype=np.float32)
        kernel[0, :] = 1.0 / k
        blurred = cv2.filter2D(np.asarray(comp), -1, kernel)
        return Image.fromarray(blurred, mode="RGB")
    return comp


def anamorphic_light_leak_transition(prev_im, next_im, alpha):
    """Smooth optical zoom-blend with warm amber/cyan anamorphic cinema light-leak bloom."""
    w, h = next_im.size
    a = max(0.0, min(1.0, float(alpha)))
    blended = Image.blend(prev_im, next_im, a)
    peak = math.sin(math.pi * a) ** 1.6
    if peak < 0.05:
        return blended
    arr = np.asarray(blended, dtype=np.float32)
    x = np.linspace(-1.0, 1.0, w, dtype=np.float32)[None, :]
    y = np.linspace(-1.0, 1.0, h, dtype=np.float32)[:, None]
    # Horizontal anamorphic streak + warm golden side bloom
    streak = np.exp(-((y * 4.5) ** 2)) * (0.45 + 0.55 * np.exp(-(((x - (a - 0.5) * 1.4) * 1.8) ** 2)))
    bloom = peak * 135.0 * streak
    arr[..., 0] += bloom * 1.05   # Warm amber red
    arr[..., 1] += bloom * 0.72   # Golden mid
    arr[..., 2] += bloom * 0.28   # Subtle cyan tail
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), mode="RGB")


_FACE_CASCADE = None
_FACE_CENTER_CACHE = {}


def detect_face_focus_center(pil_img):
    """V99 OpenCV Face-Aware Smart Crop: returns normalized (cx, cy) centered on the primary human face/eyes, or (0.5, 0.45) if no face."""
    key = id(pil_img)
    if key in _FACE_CENTER_CACHE:
        return _FACE_CENTER_CACHE[key]
    default = (0.5, 0.45)
    if cv2 is None:
        return default
    global _FACE_CASCADE
    try:
        if _FACE_CASCADE is None:
            import os as _os
            xml = _os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
            if _os.path.exists(xml):
                _FACE_CASCADE = cv2.CascadeClassifier(xml)
        if _FACE_CASCADE is None or _FACE_CASCADE.empty():
            return default
        w, h = pil_img.size
        scale = min(1.0, 480.0 / max(1, w))
        small = pil_img.resize((max(32, int(w * scale)), max(32, int(h * scale))))
        gray = cv2.cvtColor(np.asarray(small), cv2.COLOR_RGB2GRAY)
        faces = _FACE_CASCADE.detectMultiScale(gray, scaleFactor=1.15, minNeighbors=5, minSize=(28, 28))
        if len(faces) > 0:
            # Pick largest prominent face (leader, suspect, speaker)
            x, y, fw, fh = max(faces, key=lambda r: r[2] * r[3])
            sw, sh = small.size
            cx = max(0.18, min(0.82, (x + fw * 0.5) / max(1, sw)))
            cy = max(0.15, min(0.75, (y + fh * 0.38) / max(1, sh)))
            _FACE_CENTER_CACHE[key] = (cx, cy)
            return (cx, cy)
    except Exception:
        pass
    _FACE_CENTER_CACHE[key] = default
    return default
