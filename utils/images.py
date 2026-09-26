# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  utils/images.py  ·  Badge / seal / banner / icon generators
# =============================================================

from __future__ import annotations

import os
import sys

# --- make project root importable ---
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import math
from typing import Optional, Tuple

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from config import (
    BADGE_DIR, CERT_DIR, GRADIENT_DIR,
    GRADIENT_START, GRADIENT_END, GRADIENT_SOFT, GRADIENT_DEEP,
    COLORS, STATUS, ZONE_COLORS, ZONE_LABELS,
    FONT_FAMILY, LOGO_PATH,
)


# =============================================================
# 0. ENSURE DIRS
# =============================================================

for _d in (BADGE_DIR, CERT_DIR, GRADIENT_DIR):
    os.makedirs(_d, exist_ok=True)


# =============================================================
# 1. HELPERS  (color + font + gradient)
# =============================================================

def hex_to_rgb(h: str) -> Tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def lerp(c1: str, c2: str, t: float) -> Tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    a, b = hex_to_rgb(c1), hex_to_rgb(c2)
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


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


def _radial_gradient(size: int, inner: str, outer: str,
                     center_bias: float = 0.5) -> Image.Image:
    """
    Radial gradient — bright inner color → darker outer.
    `center_bias`: 0.0 = centered, positive = shifted up-left.
    """
    img = Image.new("RGB", (size, size), outer)
    px = img.load()
    cx = size * (0.5 - center_bias * 0.3)
    cy = size * (0.5 - center_bias * 0.3)
    max_d = math.sqrt((size - cx) ** 2 + (size - cy) ** 2)
    for y in range(size):
        for x in range(size):
            d = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
            t = min(1.0, d / max_d)
            px[x, y] = lerp(inner, outer, t)
    return img


def _linear_gradient(size: int, c1: str, c2: str,
                     angle_deg: float = 135) -> Image.Image:
    base = Image.new("RGB", (size, size), c1)
    top = Image.new("RGB", (size, size), c2)
    mask = Image.new("L", (size, size))
    px = mask.load()
    rad = math.radians(angle_deg)
    dx, dy = math.cos(rad), math.sin(rad)
    denom = abs(dx) * size + abs(dy) * size or 1
    for y in range(size):
        for x in range(size):
            v = max(0.0, min(1.0, (x * dx + y * dy) / denom))
            px[x, y] = int(v * 255)
    return Image.composite(top, base, mask)


def _circle_mask(size: int, pad: int = 0) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((pad, pad, size - pad, size - pad), fill=255)
    return mask


# =============================================================
# 2. BADGE ICON GENERATOR
# =============================================================

def badge_icon(icon: str, color: str, size: int = 128,
               earned: bool = True, bg: str = COLORS["surface_hi"]) -> Image.Image:
    """
    Generate a single badge image — glowing medallion with emoji inside.
    Locked badges are grayscale.

    Returns PIL RGBA image of size × size.
    """
    size = max(48, int(size))
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    # Outer glow ring
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    pad = int(size * 0.06)
    gd.ellipse((pad, pad, size - pad, size - pad),
               outline=color, width=max(3, size // 28))
    glow = glow.filter(ImageFilter.GaussianBlur(size // 22))
    img = Image.alpha_composite(img, glow)

    # Inner disc
    disc_pad = int(size * 0.14)
    disc_mask = _circle_mask(size, disc_pad)

    if earned:
        disc = _radial_gradient(size, color, bg, center_bias=0.35)
    else:
        # Grayscale inner
        disc = _radial_gradient(size, "#555566", "#2A2A3A", center_bias=0.35)
        disc = disc.convert("L").convert("RGB")

    disc_rgba = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    disc_rgba.paste(disc, (0, 0), disc_mask)
    img = Image.alpha_composite(img, disc_rgba)

    # Thin bright ring on top
    ring = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    rd = ImageDraw.Draw(ring)
    rd.ellipse((disc_pad, disc_pad, size - disc_pad, size - disc_pad),
               outline=color if earned else "#4A4A5A",
               width=max(2, size // 40))
    img = Image.alpha_composite(img, ring)

    # Emoji / symbol in the center
    d = ImageDraw.Draw(img)
    font = _pil_font(int(size * 0.42))
    bbox = d.textbbox((0, 0), icon, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (size - tw) / 2 - bbox[0]
    y = (size - th) / 2 - bbox[1]

    if earned:
        d.text((x + 1, y + 1), icon, font=font, fill=(0, 0, 0, 90))
        d.text((x, y), icon, font=font, fill="white")
    else:
        d.text((x, y), icon, font=font, fill="#6B6B7A")

    return img


def badge_icon_ctk(icon: str, color: str, size: int = 96,
                   earned: bool = True):
    """CTkImage wrapper for badge_icon."""
    img = badge_icon(icon, color, size=size, earned=earned)
    return ctk.CTkImage(light_image=img, dark_image=img,
                        size=(img.width, img.height))


def save_badge_icon(badge_id: str, icon: str, color: str,
                    size: int = 256) -> str:
    """Save a badge PNG into assets/badges/<badge_id>.png."""
    path = os.path.join(BADGE_DIR, f"{badge_id}.png")
    badge_icon(icon, color, size=size, earned=True).save(path, "PNG")
    return path


def generate_all_badges(badges: list, size: int = 256) -> dict:
    """
    Save every badge icon. `badges` = list of dicts (from config.BADGES).
    Returns {badge_id: path}.
    """
    out = {}
    for b in badges:
        out[b["id"]] = save_badge_icon(b["id"], b["icon"], b["color"],
                                       size=size)
    return out


# =============================================================
# 3. ZONE PILL  (small rounded chip: "🟢 Strong")
# =============================================================

def zone_pill(zone: str, size: Tuple[int, int] = (140, 40)) -> Image.Image:
    """
    Rounded chip with the zone color and label. Perfect for headers.
    """
    w, h = size
    w, h = max(60, int(w)), max(20, int(h))
    color = ZONE_COLORS.get(zone, "#94A3B8")
    label = ZONE_LABELS.get(zone, "—")

    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    # Pill background (subtle gradient of the zone color)
    radius = h // 2
    pill = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    pd = ImageDraw.Draw(pill)
    pd.rounded_rectangle((0, 0, w, h), radius=radius,
                         fill=color)

    # Slight dark overlay on the right side for depth
    for x in range(w):
        alpha = int(30 * (x / w))
        pd.line([(x, 0), (x, h)], fill=(0, 0, 0, alpha))

    img = Image.alpha_composite(img, pill)

    # Emoji + text
    d = ImageDraw.Draw(img)
    font = _pil_font(int(h * 0.42))
    icon = {"red": "🔴", "yellow": "🟡",
            "green": "🟢", "gold": "🏆"}.get(zone, "•")
    text = f"{icon}  {label}"
    bbox = d.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(((w - tw) / 2 - bbox[0], (h - th) / 2 - bbox[1]),
           text, font=font, fill="white")
    return img


def zone_pill_ctk(zone: str, size: Tuple[int, int] = (140, 40)):
    img = zone_pill(zone, size=size)
    return ctk.CTkImage(light_image=img, dark_image=img,
                        size=(img.width, img.height))


# =============================================================
# 4. CERTIFICATE SEAL  (ornate gold circle with SJ monogram)
# =============================================================

def certificate_seal(size: int = 180,
                     color_inner: str = "#FBBF24",
                     color_outer: str = "#B45309") -> Image.Image:
    """Ornate gold seal with SJ monogram — for the bottom-right of certs."""
    size = max(80, int(size))
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    # Outer glow
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((0, 0, size, size), fill=(color_inner, 90))
    glow = glow.filter(ImageFilter.GaussianBlur(size // 18))
    img = Image.alpha_composite(img, glow)

    # Main disc — radial gradient
    disc = _radial_gradient(size, color_inner, color_outer, center_bias=0.3)
    disc_mask = _circle_mask(size, int(size * 0.05))
    disc_rgba = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    disc_rgba.paste(disc, (0, 0), disc_mask)
    img = Image.alpha_composite(img, disc_rgba)

    # Two concentric rings
    d = ImageDraw.Draw(img)
    d.ellipse((int(size*0.08), int(size*0.08),
               int(size*0.92), int(size*0.92)),
              outline="#FFFFFFAA", width=max(2, size // 60))
    d.ellipse((int(size*0.16), int(size*0.16),
               int(size*0.84), int(size*0.84)),
              outline=color_outer, width=max(2, size // 70))

    # Inner text: SJ
    font = _pil_font(int(size * 0.36))
    text = "SJ"
    bbox = d.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = (size - tw) / 2 - bbox[0]
    ty = (size - th) / 2 - bbox[1] - int(size * 0.02)
    d.text((tx + 1, ty + 1), text, font=font, fill=(0, 0, 0, 100))
    d.text((tx, ty), text, font=font, fill=color_outer)

    # Tiny caption: SHRUTHI JHARI
    small = _pil_font(max(8, int(size * 0.075)))
    cap = "SHRUTHI JHARI"
    bbox2 = d.textbbox((0, 0), cap, font=small)
    tw2, th2 = bbox2[2] - bbox2[0], bbox2[3] - bbox2[1]
    d.text(((size - tw2) / 2 - bbox2[0],
            ty + th + int(size * 0.02) - bbox2[1]),
           cap, font=small, fill=color_outer, align="center")

    # Star decorations around
    for i in range(8):
        ang = math.radians(i * 45)
        r = size * 0.42
        cx = size / 2 + r * math.cos(ang)
        cy = size / 2 + r * math.sin(ang)
        _draw_star(d, cx, cy, size * 0.045, 5, fill=color_outer)

    return img


def _draw_star(draw: ImageDraw.ImageDraw, cx: float, cy: float,
               r: float, points: int = 5, fill="#FFFFFF"):
    pts = []
    for i in range(points * 2):
        ang = -math.pi / 2 + i * (math.pi / points)
        rr = r if i % 2 == 0 else r * 0.42
        pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
    draw.polygon(pts, fill=fill)


def certificate_seal_ctk(size: int = 140):
    img = certificate_seal(size=size)
    return ctk.CTkImage(light_image=img, dark_image=img,
                        size=(img.width, img.height))


# =============================================================
# 5. RIBBON BANNER  ("TOPPER", "IMPROVED", "EXCELLENCE")
# =============================================================

def ribbon_banner(text: str,
                  color: str = GRADIENT_END,
                  size: Tuple[int, int] = (280, 70)) -> Image.Image:
    """A ribbon-style banner image with the given text."""
    w, h = size
    w, h = max(120, int(w)), max(40, int(h))
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Main band
    band_h = int(h * 0.62)
    top = (h - band_h) // 2
    bottom = top + band_h
    r = 10
    d.rounded_rectangle((0, top, w, bottom), radius=r, fill=color)

    # Left/right tails
    tail = int(h * 0.32)
    d.polygon([(0, bottom), (tail, bottom + tail),
               (tail, bottom - tail)], fill=color)
    d.polygon([(w, bottom), (w - tail, bottom + tail),
               (w - tail, bottom - tail)], fill=color)

    # Text
    font = _pil_font(int(band_h * 0.55))
    bbox = d.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(((w - tw) / 2 - bbox[0], (h - th) / 2 - bbox[1] - 2),
           text, font=font, fill="white")

    return img


def ribbon_banner_ctk(text: str, color: str = GRADIENT_END,
                      size: Tuple[int, int] = (280, 70)):
    img = ribbon_banner(text, color=color, size=size)
    return ctk.CTkImage(light_image=img, dark_image=img,
                        size=(img.width, img.height))


# =============================================================
# 6. STAR RATING  (1–5 filled/hollow stars)
# =============================================================

def star_rating(filled: int, total: int = 5,
                size: int = 40, gap: int = 6,
                color_on: str = "#FBBF24",
                color_off: str = "#3D3569") -> Image.Image:
    """Row of filled / empty stars."""
    total = max(1, int(total))
    filled = max(0, min(total, int(filled)))
    size = max(12, int(size))
    w = total * size + (total - 1) * gap
    h = size
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i in range(total):
        cx = i * (size + gap) + size / 2
        cy = h / 2
        _draw_star(d, cx, cy, size / 2,
                   points=5,
                   fill=color_on if i < filled else color_off)
    return img


def star_rating_ctk(filled: int, total: int = 5, size: int = 40):
    img = star_rating(filled, total=total, size=size)
    return ctk.CTkImage(light_image=img, dark_image=img,
                        size=(img.width, img.height))


# =============================================================
# 7. TREND ARROW  (up / down / stable)
# =============================================================

def trend_arrow(kind: str, size: int = 40,
                up: str = STATUS["green"],
                down: str = STATUS["red"],
                flat: str = "#94A3B8") -> Image.Image:
    """kind: 'up' | 'down' | 'flat'."""
    size = max(16, int(size))
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    cx, cy = size / 2, size / 2
    s = size * 0.32

    if kind == "up":
        color = up
        pts = [(cx, cy - s), (cx - s, cy + s * 0.4), (cx + s, cy + s * 0.4)]
        d.polygon(pts, fill=color)
        d.rectangle((cx - s * 0.18, cy + s * 0.4,
                     cx + s * 0.18, cy + s * 1.1), fill=color)
    elif kind == "down":
        color = down
        pts = [(cx, cy + s), (cx - s, cy - s * 0.4), (cx + s, cy - s * 0.4)]
        d.polygon(pts, fill=color)
        d.rectangle((cx - s * 0.18, cy - s * 1.1,
                     cx + s * 0.18, cy - s * 0.4), fill=color)
    else:
        color = flat
        d.rounded_rectangle((cx - s, cy - s * 0.18,
                             cx + s, cy + s * 0.18),
                            radius=int(size * 0.05), fill=color)
    return img


def trend_arrow_ctk(kind: str, size: int = 32):
    img = trend_arrow(kind, size=size)
    return ctk.CTkImage(light_image=img, dark_image=img,
                        size=(img.width, img.height))


# =============================================================
# 8. SPLASH BACKGROUND  (cascade gradient art)
# =============================================================

def splash_background(width: int = 900,
                      height: int = 600,
                      seed: int = 42) -> Image.Image:
    """
    Full-screen gradient with a soft wave overlay — Cascade of Divine Knowledge.
    Deterministic for a given size.
    """
    import random
    rng = random.Random(seed)

    # Base diagonal gradient (brand colors)
    base = _linear_gradient(max(width, height),
                            GRADIENT_START, GRADIENT_END, angle_deg=135)
    base = base.resize((width, height), Image.LANCZOS).convert("RGBA")

    # Soft glow in the upper-left
    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for i in range(5):
        r = int(min(width, height) * (0.35 + i * 0.08))
        a = int(30 - i * 5)
        gd.ellipse((-r * 0.3, -r * 0.3, r, r),
                   fill=(255, 255, 255, a))
    glow = glow.filter(ImageFilter.GaussianBlur(60))
    img = Image.alpha_composite(base, glow)

    # Cascade waves at the bottom
    waves = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    wd = ImageDraw.Draw(waves)
    for k in range(3):
        amp = 40 + k * 25
        phase = rng.uniform(0, math.pi)
        wave_color = (255, 255, 255, 22 - k * 6)
        pts = []
        step = 8
        for x in range(0, width + step, step):
            y = height - 120 - k * 40 + \
                amp * math.sin(x * 0.006 + phase)
            pts.append((x, y))
        pts.append((width, height))
        pts.append((0, height))
        wd.polygon(pts, fill=wave_color)
    waves = waves.filter(ImageFilter.GaussianBlur(2))
    img = Image.alpha_composite(img, waves)

    # Vignette edges
    vignette = Image.new("L", (width, height), 0)
    vd = ImageDraw.Draw(vignette)
    vd.ellipse((-int(width*0.2), -int(height*0.2),
                int(width*1.2), int(height*1.2)), fill=255)
    vignette = vignette.filter(ImageFilter.GaussianBlur(80))
    dark = Image.new("RGBA", (width, height), (0, 0, 0, 100))
    img = Image.composite(img, Image.alpha_composite(img, dark), vignette)

    return img


def splash_background_ctk(width: int = 900, height: int = 600):
    img = splash_background(width, height)
    return ctk.CTkImage(light_image=img, dark_image=img,
                        size=(img.width, img.height))


# =============================================================
# 9. HEADER BAR BACKDROP  (subtle for app header)
# =============================================================

def header_backdrop(width: int = 1200, height: int = 64) -> Image.Image:
    """Thin horizontal gradient for the app header bar."""
    return _linear_gradient(max(width, height), GRADIENT_START,
                            GRADIENT_END, angle_deg=0).resize(
        (width, height), Image.LANCZOS).convert("RGBA")


def header_backdrop_ctk(width: int = 1200, height: int = 64):
    img = header_backdrop(width, height)
    return ctk.CTkImage(light_image=img, dark_image=img,
                        size=(img.width, img.height))


# =============================================================
# 10. PLACEHOLDER  (for empty states / missing images)
# =============================================================

def placeholder_icon(text: str = "—", size: int = 120,
                     color: str = COLORS["text_dim"]) -> Image.Image:
    """A dashed rounded square with a centered label."""
    size = max(40, int(size))
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Dashed border
    step = 8
    for x in range(0, size, step * 2):
        d.line((x, 0, min(x + step, size), 0), fill=color, width=2)
        d.line((x, size - 1, min(x + step, size), size - 1),
               fill=color, width=2)
    for y in range(0, size, step * 2):
        d.line((0, y, 0, min(y + step, size)), fill=color, width=2)
        d.line((size - 1, y, size - 1, min(y + step, size)),
               fill=color, width=2)

    font = _pil_font(int(size * 0.32))
    bbox = d.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(((size - tw) / 2 - bbox[0], (size - th) / 2 - bbox[1]),
           text, font=font, fill=color)
    return img


def placeholder_ctk(text: str = "—", size: int = 120):
    img = placeholder_icon(text, size=size)
    return ctk.CTkImage(light_image=img, dark_image=img,
                        size=(img.width, img.height))


# =============================================================
# 11. SANITY CHECK
# =============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  SHRUTHI JHARI — utils/images.py sanity check")
    print("=" * 60)

    prev = os.path.join(_ROOT, "assets", "images_preview")
    os.makedirs(prev, exist_ok=True)

    def save(img: Image.Image, name: str):
        p = os.path.join(prev, name)
        img.save(p, "PNG")
        print(f"   💾  {name}")

    # ---- Badges ----
    print("\n🏅 Badge icons:")
    from config import BADGES
    for b in BADGES[:4]:
        img = badge_icon(b["icon"], b["color"], size=256, earned=True)
        save(img, f"badge_{b['id']}.png")
    # one locked
    b = BADGES[0]
    save(badge_icon(b["icon"], b["color"], size=256, earned=False),
         f"badge_{b['id']}_locked.png")

    # ---- Zone pills ----
    print("\n🎨 Zone pills:")
    for z in ("red", "yellow", "green", "gold"):
        save(zone_pill(z, size=(180, 52)), f"pill_{z}.png")

    # ---- Certificate seal ----
    print("\n🎖️  Certificate seal:")
    save(certificate_seal(size=220), "seal_gold.png")

    # ---- Ribbon banners ----
    print("\n🎗️  Ribbons:")
    for text, color in [("TOPPER", GRADIENT_END),
                        ("EXCELLENCE", "#8B5CF6"),
                        ("IMPROVED", STATUS["green"])]:
        save(ribbon_banner(text, color=color, size=(340, 80)),
             f"ribbon_{text.lower()}.png")

    # ---- Stars ----
    print("\n⭐ Star ratings:")
    for n in (1, 3, 5):
        save(star_rating(n, total=5, size=48), f"stars_{n}.png")

    # ---- Trend arrows ----
    print("\n📈 Trend arrows:")
    for kind in ("up", "down", "flat"):
        save(trend_arrow(kind, size=64), f"trend_{kind}.png")

    # ---- Splash ----
    print("\n✨ Splash background:")
    save(splash_background(1000, 700), "splash_1000x700.png")
    save(splash_background(600, 400), "splash_600x400.png")

    # ---- Header backdrop ----
    print("\n🧵 Header backdrop:")
    save(header_backdrop(1200, 64), "header_backdrop.png")

    # ---- Placeholder ----
    print("\n🖼️  Placeholders:")
    save(placeholder_icon("No Data", size=160), "placeholder.png")

    print(f"\n📁 Preview folder: {prev}")
    print("\n✅ utils/images.py OK")
    print("=" * 60)