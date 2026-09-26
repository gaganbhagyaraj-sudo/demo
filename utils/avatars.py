# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  utils/avatars.py  ·  Avatar generation + loading
# =============================================================

from __future__ import annotations

import os
import sys

# --- make project root importable ---
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import hashlib
import shutil
from typing import Optional

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from config import (
    AVATAR_DIR, GRADIENT_START, GRADIENT_END,
    COLORS, STATUS, ZONE_COLORS,
)


# =============================================================
# 1. PALETTE (deterministic per-student)
# =============================================================

# A rich set of gradients — one is picked based on the student's name hash,
# so the same student always gets the same avatar color.
_AVATAR_GRADIENTS = [
    ("#6D28D9", "#F59E0B"),   # brand (purple → gold)
    ("#7C3AED", "#EC4899"),   # violet → pink
    ("#8B5CF6", "#06B6D4"),   # violet → cyan
    ("#EC4899", "#F59E0B"),   # pink → amber
    ("#10B981", "#3B82F6"),   # emerald → blue
    ("#F59E0B", "#EF4444"),   # amber → red
    ("#3B82F6", "#8B5CF6"),   # blue → violet
    ("#14B8A6", "#84CC16"),   # teal → lime
    ("#F43F5E", "#8B5CF6"),   # rose → violet
    ("#0EA5E9", "#6366F1"),   # sky → indigo
]


def _hash_index(name: str, modulo: int) -> int:
    """Deterministic index for a name → same result every time."""
    if not name:
        return 0
    h = hashlib.md5(name.encode("utf-8")).hexdigest()
    return int(h, 16) % modulo


def gradient_for_name(name: str) -> tuple:
    """Return a deterministic (start, end) gradient pair for a name."""
    return _AVATAR_GRADIENTS[_hash_index(name, len(_AVATAR_GRADIENTS))]


# =============================================================
# 2. INITIALS
# =============================================================

def initials_from_name(name: str, max_letters: int = 2) -> str:
    """'Rahul Sharma' → 'RS',  'Priya' → 'P'."""
    if not name:
        return "?"
    parts = [p for p in name.strip().split() if p]
    letters = "".join(p[0].upper() for p in parts[:max_letters])
    return letters or "?"


# =============================================================
# 3. PIL FONTS (PIL-safe, never use Tkinter fonts)
# =============================================================

_FONT_CANDIDATES = [
    "arialbd.ttf", "Arial-Bold.ttf", "Arial.ttf",
    "segoeuib.ttf", "SegoeUI-Bold.ttf",
    "DejaVuSans-Bold.ttf", "DejaVuSans.ttf",
    "calibrib.ttf", "Calibri-Bold.ttf",
]

_font_cache = {}


def _pil_font(size: int):
    size = max(6, int(size))
    if size in _font_cache:
        return _font_cache[size]
    for name in _FONT_CANDIDATES:
        try:
            f = ImageFont.truetype(name, size)
            _font_cache[size] = f
            return f
        except Exception:
            continue
    f = ImageFont.load_default()
    _font_cache[size] = f
    return f


# =============================================================
# 4. CORE AVATAR GENERATION
# =============================================================

def _make_gradient(size: int, start: str, end: str) -> Image.Image:
    """Diagonal gradient image."""
    base = Image.new("RGB", (size, size), start)
    top = Image.new("RGB", (size, size), end)
    mask = Image.new("L", (size, size))
    pixels = mask.load()
    for y in range(size):
        for x in range(size):
            pixels[x, y] = int(255 * ((x + y) / (2 * size)))
    return Image.composite(top, base, mask)


def generate_initials_avatar(name: str,
                             size: int = 256,
                             shape: str = "circle",
                             ring_color: Optional[str] = None,
                             ring_width: int = 0,
                             bg_fallback: Optional[str] = None) -> Image.Image:
    """
    Return a PIL RGBA image — a gradient avatar with the person's initials.

    Parameters
    ----------
    name        : full name (used for initials + gradient color)
    size        : output size in px (square)
    shape       : 'circle' or 'square' or 'rounded'
    ring_color  : optional outer ring (e.g. zone color)
    ring_width  : pixels for the ring (0 = none)
    bg_fallback : background behind transparency (default transparent)
    """
    size = max(32, int(size))
    start, end = gradient_for_name(name)

    # Base gradient
    grad = _make_gradient(size, start, end)

    # Mask for shape
    mask = Image.new("L", (size, size), 0)
    mdraw = ImageDraw.Draw(mask)

    if shape == "circle":
        mdraw.ellipse((0, 0, size, size), fill=255)
    elif shape == "rounded":
        radius = int(size * 0.22)
        mdraw.rounded_rectangle((0, 0, size, size), radius=radius, fill=255)
    else:  # square
        mdraw.rectangle((0, 0, size, size), fill=255)

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    img.paste(grad, (0, 0), mask)

    # Initials
    d = ImageDraw.Draw(img)
    text = initials_from_name(name)
    # Slightly bigger for 1-letter initials
    base_font = int(size * (0.46 if len(text) == 1 else 0.40))
    font = _pil_font(base_font)

    bbox = d.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = (size - tw) / 2 - bbox[0]
    ty = (size - th) / 2 - bbox[1]

    # Subtle text shadow for depth
    d.text((tx + 1, ty + 1), text, fill=(0, 0, 0, 80), font=font)
    d.text((tx, ty), text, fill="white", font=font)

    # Optional outer ring
    if ring_color and ring_width > 0:
        ring = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        rdraw = ImageDraw.Draw(ring)
        pad = ring_width // 2
        rdraw.ellipse((pad, pad, size - pad, size - pad),
                      outline=ring_color, width=ring_width)
        img = Image.alpha_composite(img, ring)

    return img


def _safe_zone_color(zone_or_hex: Optional[str]) -> Optional[str]:
    """Accept 'red'|'yellow'|'green'|'gold' or a #hex string."""
    if not zone_or_hex:
        return None
    if isinstance(zone_or_hex, str) and zone_or_hex.startswith("#"):
        return zone_or_hex
    return ZONE_COLORS.get(zone_or_hex, None)


# =============================================================
# 5. FILE PATHS + CACHE
# =============================================================

def avatar_path(user_id: str) -> str:
    """Canonical file path for a user's uploaded avatar."""
    return os.path.join(AVATAR_DIR, f"{user_id}.png")


def has_uploaded_avatar(user_id: str) -> bool:
    return os.path.exists(avatar_path(user_id))


# In-memory cache: key → CTkImage
_CTK_AVATAR_CACHE = {}


# =============================================================
# 6. PUBLIC LOADERS  (return CTkImage for the UI)
# =============================================================

def load_avatar(user_id: str,
                name: str,
                size: int = 64,
                shape: str = "circle",
                zone: Optional[str] = None,
                ring_width: int = 0,
                use_cache: bool = True):
    """
    Return a CTkImage for the given user.

    - If an uploaded PNG exists at assets/avatars/<user_id>.png, uses it.
    - Otherwise auto-generates an initials avatar.
    - `zone` (red/yellow/green/gold) adds a colored status ring.
    """
    ring_color = _safe_zone_color(zone) if ring_width > 0 else None
    key = (user_id, name, size, shape, ring_color, ring_width)

    if use_cache and key in _CTK_AVATAR_CACHE:
        return _CTK_AVATAR_CACHE[key]

    # Prefer an uploaded avatar
    img = None
    up_path = avatar_path(user_id)
    if os.path.exists(up_path):
        try:
            img = Image.open(up_path).convert("RGBA")
            img = _apply_shape_and_ring(img, size, shape,
                                        ring_color, ring_width)
        except Exception:
            img = None

    # Fallback to generated
    if img is None:
        img = generate_initials_avatar(name, size=size, shape=shape,
                                       ring_color=ring_color,
                                       ring_width=ring_width)

    ctk_img = ctk.CTkImage(light_image=img, dark_image=img,
                           size=(img.width, img.height))
    if use_cache:
        _CTK_AVATAR_CACHE[key] = ctk_img
    return ctk_img


def _apply_shape_and_ring(img: Image.Image, size: int, shape: str,
                          ring_color: Optional[str],
                          ring_width: int) -> Image.Image:
    """Resize + apply shape mask + optional ring to an uploaded photo."""
    size = max(32, int(size))
    img = img.resize((size, size), Image.LANCZOS)

    # Shape mask
    mask = Image.new("L", (size, size), 0)
    md = ImageDraw.Draw(mask)
    if shape == "circle":
        md.ellipse((0, 0, size, size), fill=255)
    elif shape == "rounded":
        md.rounded_rectangle((0, 0, size, size),
                             radius=int(size * 0.22), fill=255)
    else:
        md.rectangle((0, 0, size, size), fill=255)

    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)

    if ring_color and ring_width > 0:
        ring = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        rd = ImageDraw.Draw(ring)
        pad = ring_width // 2
        rd.ellipse((pad, pad, size - pad, size - pad),
                   outline=ring_color, width=ring_width)
        out = Image.alpha_composite(out, ring)

    return out


# =============================================================
# 7. UPLOAD / SAVE
# =============================================================

def save_uploaded_avatar(user_id: str, src_path: str,
                         size: int = 400) -> str:
    """
    Copy the file at `src_path` into the avatars folder as
    `<user_id>.png`, resized to `size`. Returns the saved path.
    """
    if not os.path.exists(src_path):
        raise FileNotFoundError(src_path)

    img = Image.open(src_path).convert("RGBA")
    img = _square_crop(img)
    img = img.resize((size, size), Image.LANCZOS)

    dst = avatar_path(user_id)
    img.save(dst, "PNG")
    clear_cache(user_id)   # invalidate cache for this user
    return dst


def _square_crop(img: Image.Image) -> Image.Image:
    """Crop to the largest centered square."""
    w, h = img.size
    s = min(w, h)
    left = (w - s) // 2
    top = (h - s) // 2
    return img.crop((left, top, left + s, top + s))


def delete_uploaded_avatar(user_id: str) -> bool:
    """Remove a user's uploaded avatar; falls back to generated."""
    p = avatar_path(user_id)
    if os.path.exists(p):
        try:
            os.remove(p)
            clear_cache(user_id)
            return True
        except Exception:
            return False
    return False


# =============================================================
# 8. CACHE MANAGEMENT
# =============================================================

def clear_cache(user_id: Optional[str] = None):
    """Clear the CTkImage cache; pass a user_id to clear just that user."""
    if user_id is None:
        _CTK_AVATAR_CACHE.clear()
    else:
        to_remove = [k for k in _CTK_AVATAR_CACHE if k[0] == user_id]
        for k in to_remove:
            _CTK_AVATAR_CACHE.pop(k, None)


# =============================================================
# 9. PIL-ONLY HELPERS  (for PDF, certificates)
# =============================================================

def pil_avatar(user_id: str, name: str, size: int = 128,
               shape: str = "circle",
               zone: Optional[str] = None,
               ring_width: int = 0) -> Image.Image:
    """
    Return a PIL image (not CTkImage).
    Used by certificates.py and PDF exporters.
    """
    ring_color = _safe_zone_color(zone) if ring_width else None

    up_path = avatar_path(user_id)
    if os.path.exists(up_path):
        try:
            img = Image.open(up_path).convert("RGBA")
            return _apply_shape_and_ring(img, size, shape,
                                         ring_color, ring_width)
        except Exception:
            pass

    return generate_initials_avatar(name, size=size, shape=shape,
                                    ring_color=ring_color,
                                    ring_width=ring_width)


# =============================================================
# 10. SANITY CHECK
# =============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  SHRUTHI JHARI — utils/avatars.py sanity check")
    print("=" * 60)

    names = ["Rahul Sharma", "Priya Nair", "Arjun Reddy",
             "Meera Iyer", "Kiran Das", "A"]

    print("\n🎨 Initials + gradient:")
    for n in names:
        gi = initials_from_name(n)
        g = gradient_for_name(n)
        print(f"   {n:<16}  →  initials='{gi}'  gradient={g[0]} → {g[1]}")

    print("\n🖼️  Generating sample avatars to assets/avatars/_preview/...")
    prev_dir = os.path.join(AVATAR_DIR, "_preview")
    os.makedirs(prev_dir, exist_ok=True)

    # Different sizes + shapes + rings
    samples = [
        ("rahul",  "Rahul Sharma", 256, "circle",  None,       0,  "01_plain.png"),
        ("priya",  "Priya Nair",   256, "circle",  "gold",     8,  "02_ring_gold.png"),
        ("arjun",  "Arjun Reddy",  256, "circle",  "red",      8,  "03_ring_red.png"),
        ("meera",  "Meera Iyer",   256, "rounded", "yellow",   8,  "04_rounded_yellow.png"),
        ("kiran",  "Kiran Das",    256, "square",  "green",    8,  "05_square_green.png"),
        ("kavya",  "Kavya Rao",    256, "circle",  "#8B5CF6",  6,  "06_custom_ring.png"),
    ]

    for uid, name, size, shape, ring, rw, out_name in samples:
        img = generate_initials_avatar(
            name, size=size, shape=shape,
            ring_color=_safe_zone_color(ring), ring_width=rw)
        path = os.path.join(prev_dir, out_name)
        img.save(path, "PNG")
        print(f"   💾  {out_name:<28} shape={shape:<7} ring={ring or '—'}")

    # Multi-size test
    print("\n📐 Multi-size generation test:")
    for s in (32, 48, 64, 96, 128, 256):
        img = generate_initials_avatar("Rahul Sharma", size=s)
        assert img.size == (s, s), f"size mismatch at {s}"
        print(f"   ✓ {s}×{s}")

    # Cache test
    print("\n🧠 Cache behavior:")
    clear_cache()
    a1 = generate_initials_avatar("Test User", size=128)
    a2 = generate_initials_avatar("Test User", size=128)
    print(f"   deterministic: same colors → "
          f"{a1.tobytes() == a2.tobytes()}")

    # PIL-only helper
    print("\n📄 PIL-only avatar (for PDF/certificates):")
    pil_img = pil_avatar("rahul", "Rahul Sharma", size=200, ring_width=6,
                         zone="red")
    pdf_path = os.path.join(prev_dir, "07_pil_helper.png")
    pil_img.save(pdf_path, "PNG")
    print(f"   💾  {pdf_path}")

    print(f"\n📁 Preview folder: {prev_dir}")
    print("\n✅ utils/avatars.py OK")
    print("=" * 60)