# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  theme.py  ·  Gradient + Styling Engine  (v3.1 — fixed place())
# =============================================================

import os
import math

import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageTk

from config import (
    GRADIENT_START, GRADIENT_END, GRADIENT_ANGLE,
    GRADIENT_SOFT, GRADIENT_DEEP, GRADIENT_GLOW,
    COLORS, STATUS, FONTS, FONT_FAMILY,
    LOGO_PATH, CARD_RADIUS, BUTTON_RADIUS, CHIP_RADIUS,
)

# =============================================================
# 1. COLOR MATH
# =============================================================

def hex_to_rgb(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return "#{:02X}{:02X}{:02X}".format(
        int(max(0, min(255, rgb[0]))),
        int(max(0, min(255, rgb[1]))),
        int(max(0, min(255, rgb[2]))),
    )


def lerp_color(c1: str, c2: str, t: float) -> str:
    t = max(0.0, min(1.0, t))
    a, b = hex_to_rgb(c1), hex_to_rgb(c2)
    return rgb_to_hex((
        a[0] + (b[0] - a[0]) * t,
        a[1] + (b[1] - a[1]) * t,
        a[2] + (b[2] - a[2]) * t,
    ))


# =============================================================
# 2. GRADIENT IMAGE GENERATION
# =============================================================

_gradient_cache = {}


def make_gradient_image(width: int, height: int,
                        start: str = GRADIENT_START,
                        end: str = GRADIENT_END,
                        angle: int = GRADIENT_ANGLE,
                        radius: int = 0) -> Image.Image:
    width = max(1, int(width))
    height = max(1, int(height))
    key = (width, height, start, end, angle, radius)

    if key in _gradient_cache:
        return _gradient_cache[key]

    base = Image.new("RGB", (width, height), start)
    top = Image.new("RGB", (width, height), end)
    mask = Image.new("L", (width, height))
    pixels = mask.load()

    rad = math.radians(angle)
    dx, dy = math.cos(rad), math.sin(rad)
    denom = abs(dx) * width + abs(dy) * height
    if denom == 0:
        denom = 1

    for y in range(height):
        row = y * dy
        for x in range(width):
            v = (x * dx + row) / denom
            if v < 0.0:
                v = 0.0
            elif v > 1.0:
                v = 1.0
            pixels[x, y] = int(v * 255)

    img = Image.composite(top, base, mask)

    if radius > 0:
        img = img.convert("RGBA")
        rounded_mask = Image.new("L", (width, height), 0)
        d = ImageDraw.Draw(rounded_mask)
        r = min(radius, width // 2, height // 2)
        d.rounded_rectangle((0, 0, width - 1, height - 1), radius=r, fill=255)
        img.putalpha(rounded_mask)

    _gradient_cache[key] = img
    return img


def make_ctk_image(image: Image.Image, size=None):
    if size:
        image = image.resize(size, Image.LANCZOS)
    return ctk.CTkImage(light_image=image, dark_image=image,
                        size=(image.width, image.height))


def make_gradient_bg(width: int, height: int, radius: int = 0) -> ctk.CTkImage:
    img = make_gradient_image(width, height, radius=radius)
    return make_ctk_image(img)


# =============================================================
# 3. SHADOWS / GLOW / ROUNDED RECTS
# =============================================================

def rounded_rect_image(width, height, radius=14, color="#000000",
                       border=0, border_color="#FFFFFF") -> Image.Image:
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, width - 1, height - 1),
                        radius=radius, fill=color,
                        outline=border_color if border else None,
                        width=border)
    return img


def soft_shadow(width, height, radius=20, blur=14, opacity=90) -> Image.Image:
    pad = blur * 2
    w, h = width + pad * 2, height + pad * 2
    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(shadow)
    d.rounded_rectangle((pad, pad, pad + width, pad + height),
                        radius=radius, fill=(0, 0, 0, opacity))
    return shadow.filter(ImageFilter.GaussianBlur(blur))


def glow_ring(size, color=GRADIENT_END, thickness=3, blur=10) -> Image.Image:
    pad = blur * 2
    s = size + pad * 2
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((pad, pad, pad + size, pad + size),
              outline=color, width=thickness)
    return img.filter(ImageFilter.GaussianBlur(blur))


# =============================================================
# 4. PIL FONTS
# =============================================================

_PIL_FONT_CANDIDATES = [
    "arial.ttf", "Arial.ttf",
    "segoeuib.ttf", "SegoeUI-Bold.ttf",
    "DejaVuSans-Bold.ttf", "DejaVuSans.ttf",
    "calibrib.ttf", "Calibri-Bold.ttf",
]

_pil_font_cache = {}


def get_pil_font(size: int):
    size = max(6, int(size))
    if size in _pil_font_cache:
        return _pil_font_cache[size]
    for name in _PIL_FONT_CANDIDATES:
        try:
            f = ImageFont.truetype(name, size)
            _pil_font_cache[size] = f
            return f
        except Exception:
            continue
    f = ImageFont.load_default()
    _pil_font_cache[size] = f
    return f


def draw_centered_text(draw: ImageDraw.ImageDraw, text: str,
                       box_size: int, fill="white", font_size=None):
    font = get_pil_font(font_size or int(box_size * 0.45))
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (box_size - tw) / 2 - bbox[0]
    y = (box_size - th) / 2 - bbox[1]
    draw.text((x, y), text, fill=fill, font=font)


# =============================================================
# 5. LOGO LOADER
# =============================================================

_logo_cache = {}


def _fallback_logo(size: int) -> Image.Image:
    grad = make_gradient_image(size, size, radius=size // 2)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    img.paste(grad, (0, 0), grad)
    d = ImageDraw.Draw(img)
    draw_centered_text(d, "SJ", size, fill="white",
                       font_size=int(size * 0.45))
    return img


def load_logo(size=140, rounded=False, margin=12):
    """
    Load SJ.png, resize to `size`, pad with transparent margin so nothing
    gets clipped. Returns a CTkImage.
    """
    key = (size, rounded, margin)
    if key in _logo_cache:
        return _logo_cache[key]

    canvas_size = size + margin * 2
    canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))

    img = None
    if os.path.exists(LOGO_PATH):
        try:
            img = Image.open(LOGO_PATH).convert("RGBA")
            img = img.resize((size, size), Image.LANCZOS)
            if rounded:
                mask = Image.new("L", (size, size), 0)
                ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
                img.putalpha(mask)
        except Exception:
            img = None

    if img is None:
        img = _fallback_logo(size)

    canvas.paste(img, (margin, margin), img)

    ctk_img = make_ctk_image(canvas)
    _logo_cache[key] = ctk_img
    return ctk_img


# =============================================================
# 6. GRADIENT BUTTON
# =============================================================

class GradientButton(ctk.CTkFrame):

    def __init__(self, master, text="", command=None,
                 width=220, height=48,
                 start=GRADIENT_START, end=GRADIENT_END,
                 radius=BUTTON_RADIUS,
                 font=None, text_color=None,
                 parent_bg=COLORS["bg"], **kw):

        for k in ("width", "height", "text", "image", "font"):
            kw.pop(k, None)

        super().__init__(master, fg_color=parent_bg,
                         corner_radius=radius, **kw)

        self.gw = int(width)
        self.gh = int(height)
        self.command = command
        self._start = start
        self._end = end
        self._radius = radius
        self._bg_color = parent_bg

        self._inner = tk.Frame(self, width=self.gw, height=self.gh,
                               bg=self._bg_color,
                               highlightthickness=0, bd=0)
        self._inner.pack_propagate(False)
        self._inner.pack(fill="both", expand=True)

        grad = make_gradient_image(self.gw, self.gh,
                                   start, end, radius=radius)
        self._bg_img = ImageTk.PhotoImage(grad)

        self._bg_label = tk.Label(self._inner, image=self._bg_img,
                                  bd=0, highlightthickness=0)
        self._bg_label.place(x=0, y=0, relwidth=1, relheight=1)

        self._label = tk.Label(self._inner, text=text,
                               font=font or FONTS["body_bold"],
                               fg=text_color or COLORS["text"],
                               bg=self._bg_color, bd=0)
        self._label.place(relx=0.5, rely=0.5, anchor="center")

        for w in (self, self._inner, self._bg_label, self._label):
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)
            w.bind("<Button-1>", self._on_click)

    def _on_enter(self, _):
        grad = make_gradient_image(self.gw, self.gh,
                                   GRADIENT_SOFT[0], GRADIENT_SOFT[1],
                                   radius=self._radius)
        self._bg_img = ImageTk.PhotoImage(grad)
        self._bg_label.configure(image=self._bg_img)
        try:
            self._inner.configure(cursor="hand2")
        except Exception:
            pass

    def _on_leave(self, _):
        grad = make_gradient_image(self.gw, self.gh,
                                   self._start, self._end,
                                   radius=self._radius)
        self._bg_img = ImageTk.PhotoImage(grad)
        self._bg_label.configure(image=self._bg_img)

    def _on_click(self, _):
        if self.command:
            self.command()

    def set_text(self, text):
        self._label.configure(text=text)


# =============================================================
# 7. GRADIENT CARD
# =============================================================

class GradientCard(ctk.CTkFrame):

    def __init__(self, master, width=300, height=180,
                 header_text="", radius=CARD_RADIUS,
                 parent_bg=COLORS["surface"], **kw):

        for k in ("width", "height", "text", "image", "font"):
            kw.pop(k, None)

        super().__init__(master, fg_color=COLORS["surface"],
                         corner_radius=radius, **kw)

        self.gw = int(width)
        self.gh = int(height)
        self._header_h = 40
        self._radius = radius
        self._bg_color = parent_bg

        self._inner = tk.Frame(self, width=self.gw, height=self.gh,
                               bg=COLORS["surface"],
                               highlightthickness=0, bd=0)
        self._inner.pack_propagate(False)
        self._inner.pack(fill="both", expand=True)

        grad = make_gradient_image(self.gw - 4, self._header_h,
                                   radius=radius)
        self._header_img = ImageTk.PhotoImage(grad)
        tk.Label(self._inner, image=self._header_img, bd=0,
                 highlightthickness=0).place(x=2, y=2)

        tk.Label(self._inner, text=header_text,
                 font=FONTS["h4"],
                 fg=COLORS["text"], bg=COLORS["surface"], bd=0
                 ).place(x=16, y=12)

        self.body = tk.Frame(self._inner, bg=COLORS["surface"],
                             bd=0, highlightthickness=0)
        self.body.place(x=12, y=self._header_h + 8,
                        relwidth=1, relheight=1)


# =============================================================
# 8. BADGE CARD
# =============================================================

class BadgeCard(ctk.CTkFrame):

    def __init__(self, master, icon="🏅", name="Badge", desc="",
                 color=STATUS["gold"], size=96, earned=True,
                 parent_bg=COLORS["surface"], **kw):

        for k in ("width", "height", "image", "text"):
            kw.pop(k, None)

        super().__init__(master, fg_color=parent_bg, **kw)

        self.badge_size = int(size)
        self.icon = icon
        self.name = name
        self.desc = desc
        self.color = color
        self.earned = earned
        self._bg_color = parent_bg

        self.canvas = tk.Canvas(self, width=self.badge_size,
                                height=self.badge_size,
                                bg=parent_bg, highlightthickness=0, bd=0)
        self.canvas.pack()

        self._render(earned)

        tk.Label(self, text=name,
                 font=FONTS["tiny"],
                 fg=COLORS["text"] if earned else COLORS["text_dim"],
                 bg=parent_bg, bd=0).pack(pady=(6, 0))

    def _render(self, earned):
        self.canvas.delete("all")
        s = self.badge_size
        pad = 14

        if earned:
            glow = glow_ring(s - pad * 2, color=self.color,
                             thickness=3, blur=8)
            self._glow_img = ImageTk.PhotoImage(glow)
            self.canvas.create_image(s // 2, s // 2, image=self._glow_img)
            self.canvas.create_oval(pad, pad, s - pad, s - pad,
                                    fill=COLORS["surface_hi"],
                                    outline=self.color, width=3)
        else:
            self.canvas.create_oval(pad, pad, s - pad, s - pad,
                                    fill=COLORS["surface_alt"],
                                    outline=COLORS["border"], width=2)

        self.canvas.create_text(
            s // 2, s // 2, text=self.icon,
            font=(FONT_FAMILY, int(s * 0.4)),
            fill=COLORS["text"] if earned else COLORS["text_dim"],
        )


# =============================================================
# 9. TOAST
# =============================================================

class Toast:

    def __init__(self, root, message="", kind="info", duration=3000):
        self.root = root
        palette = {
            "success": STATUS["green"],
            "error":   STATUS["red"],
            "info":    STATUS["info"],
            "warning": STATUS["amber"],
        }
        accent = palette.get(kind, STATUS["info"])

        self.frame = ctk.CTkFrame(root, fg_color=COLORS["surface"],
                                  corner_radius=10, border_width=2,
                                  border_color=accent)
        self.frame.place(relx=1.0, rely=0.0, anchor="ne", x=-20, y=20)

        bar = ctk.CTkFrame(self.frame, fg_color=accent,
                           width=6, corner_radius=10)
        bar.pack(side="left", fill="y", padx=(0, 10))

        ctk.CTkLabel(self.frame, text=message, font=FONTS["body"],
                     text_color=COLORS["text"]).pack(padx=14, pady=12)

        root.after(duration, self._dismiss)

    def _dismiss(self):
        try:
            self.frame.destroy()
        except Exception:
            pass


# =============================================================
# 10. STYLED PRIMITIVES
# =============================================================

def make_title(parent, text, size="h1", bg=None):
    return ctk.CTkLabel(parent, text=text, font=FONTS[size],
                        text_color=COLORS["text"],
                        fg_color=bg or "transparent")


def make_subtitle(parent, text, bg=None):
    return ctk.CTkLabel(parent, text=text, font=FONTS["body"],
                        text_color=COLORS["text_muted"],
                        fg_color=bg or "transparent")


def make_divider(parent, color=None):
    return ctk.CTkFrame(parent, height=1,
                        fg_color=color or COLORS["border_soft"])


def make_chip(parent, text, color=None):
    chip = ctk.CTkFrame(parent, fg_color=color or COLORS["surface_alt"],
                        corner_radius=CHIP_RADIUS)
    ctk.CTkLabel(chip, text=text, font=FONTS["tiny"],
                 text_color=COLORS["text"]).pack(padx=10, pady=4)
    return chip


# =============================================================
# 11. DEMO — static, clean, centered
# =============================================================

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")

    WIN_W, WIN_H = 1080, 720

    root = ctk.CTk()
    root.geometry(f"{WIN_W}x{WIN_H}")
    root.minsize(900, 620)
    root.configure(fg_color=COLORS["bg"])
    root.title("Shruthi Jhari — theme preview")

    # Center window
    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - WIN_W) // 2
    y = (sh - WIN_H) // 2
    root.geometry(f"{WIN_W}x{WIN_H}+{x}+{y}")

    # Gradient background
    bg = make_gradient_bg(WIN_W, WIN_H)
    bg_label = ctk.CTkLabel(root, image=bg, text="")
    bg_label.place(x=0, y=0, relwidth=1, relheight=1)

    # ---- FIX: pass width/height to constructor, not to place() ----
    PANEL_W, PANEL_H = 560, 580

    panel = ctk.CTkFrame(root,
                         width=PANEL_W,
                         height=PANEL_H,
                         fg_color=COLORS["surface"],
                         corner_radius=24,
                         border_width=1,
                         border_color=COLORS["border"])
    panel.pack_propagate(False)
    panel.place(relx=0.5, rely=0.5, anchor="center")

    # Logo
    logo = load_logo(size=150, rounded=False, margin=14)
    logo_label = ctk.CTkLabel(panel, image=logo, text="")
    logo_label.pack(pady=(28, 10))

    # Title + tagline
    ctk.CTkLabel(panel, text="Shruthi Jhari",
                 font=FONTS["display"],
                 text_color=COLORS["text"]).pack(pady=(0, 4))

    ctk.CTkLabel(panel, text="Cascade of divine knowledge",
                 font=FONTS["body"],
                 text_color=COLORS["text_muted"]).pack(pady=(0, 24))

    # Divider
    make_divider(panel).pack(fill="x", padx=40, pady=(0, 20))

    # Button
    GradientButton(
        panel,
        text="Enter Shruthi Jhari",
        command=lambda: Toast(root, "Welcome, seeker!", "success"),
        parent_bg=COLORS["surface"],
        width=240, height=50,
    ).pack(pady=(0, 28))

    # Badges
    badge_row = ctk.CTkFrame(panel, fg_color="transparent")
    badge_row.pack(pady=(0, 24))

    BadgeCard(badge_row, icon="🌟", name="Perfect",
              color=STATUS["gold"],
              parent_bg=COLORS["surface"]).pack(side="left", padx=10)
    BadgeCard(badge_row, icon="🧠", name="Aptitude",
              color=STATUS["purple"],
              parent_bg=COLORS["surface"]).pack(side="left", padx=10)
    BadgeCard(badge_row, icon="🔥", name="Streak",
              color=STATUS["red"], earned=False,
              parent_bg=COLORS["surface"]).pack(side="left", padx=10)

    # Footer
    ctk.CTkLabel(panel, text="© Team Shruthi Jhari · 2025",
                 font=FONTS["micro"],
                 text_color=COLORS["text_dim"]).pack(side="bottom",
                                                     pady=(0, 16))

    root.mainloop()
