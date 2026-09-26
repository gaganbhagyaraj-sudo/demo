# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  pages/landing.py  ·  Public landing page + topper carousel
# =============================================================

from __future__ import annotations

import os
import sys

# --- make project root importable ---
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from typing import List, Dict, Optional

import tkinter as tk
import customtkinter as ctk

from config import (
    APP_NAME, APP_TAGLINE, APP_YEAR, APP_VERSION,
    COLORS, STATUS, ZONE_COLORS, SUBJECTS,
    FONTS, FONT_FAMILY,
    GRADIENT_START, GRADIENT_END,
    CARD_RADIUS, BUTTON_RADIUS, CHIP_RADIUS,
    PAD_SM, PAD_MD, PAD_LG, PAD_XL,
)
from theme import load_logo, make_ctk_image, make_gradient_image
from utils.avatars import load_avatar
from utils.images import splash_background


# =============================================================
# LANDING PAGE
# =============================================================

class LandingPage(ctk.CTkFrame):
    """
    Public landing page shown before login.
    Auto-sliding topper carousel + Sign In / Register buttons.
    """

    SLIDE_INTERVAL_MS = 3000

    def __init__(self, master, app):
        super().__init__(master, fg_color=COLORS["bg"], corner_radius=0)

        self.app = app
        self.db = app.db
        self._slides: List[Dict] = []
        self._slide_index = 0
        self._slide_job = None
        self._bg_image = None
        self._current_slide_widget: Optional[ctk.CTkFrame] = None
        self._dot_widgets: List[ctk.CTkFrame] = []

        self._build()

    # =========================================================
    # BUILD
    # =========================================================

    def _build(self):
        self.update_idletasks()
        win_w = self.winfo_toplevel().winfo_width() or 1280
        win_h = self.winfo_toplevel().winfo_height() or 780
        self._win_w = win_w
        self._win_h = win_h

        # --- Cascade gradient background ---
        try:
            bg_pil = splash_background(win_w, win_h)
            self._bg_image = ctk.CTkImage(
                light_image=bg_pil, dark_image=bg_pil,
                size=(win_w, win_h))
            ctk.CTkLabel(self, image=self._bg_image, text="").place(
                x=0, y=0, relwidth=1, relheight=1)
        except Exception:
            self.configure(fg_color=COLORS["bg"])

        # --- Top-left branding ---
        brand = ctk.CTkFrame(self, fg_color="transparent")
        brand.place(x=PAD_XL, y=PAD_LG)

        try:
            logo = load_logo(size=64, rounded=False, margin=8)
            ctk.CTkLabel(brand, image=logo, text="").pack(side="left")
        except Exception:
            pass

        brand_text = ctk.CTkFrame(brand, fg_color="transparent")
        brand_text.pack(side="left", padx=(12, 0))

        ctk.CTkLabel(brand_text, text=APP_NAME,
                     font=FONTS["h3"], text_color=COLORS["text"],
                     anchor="w").pack(anchor="w")
        ctk.CTkLabel(brand_text, text=APP_TAGLINE,
                     font=FONTS["micro"],
                     text_color=COLORS["text_muted"],
                     anchor="w").pack(anchor="w")

        # --- Top-right quick actions ---
        top_right = ctk.CTkFrame(self, fg_color="transparent")
        top_right.place(relx=1.0, x=-PAD_XL, y=PAD_LG, anchor="ne")

        ctk.CTkButton(
            top_right, text="Sign In", width=100, height=36,
            font=FONTS["small_bold"],
            fg_color="transparent", hover_color=COLORS["surface_hi"],
            text_color=COLORS["text"],
            border_width=1, border_color=COLORS["border"],
            corner_radius=BUTTON_RADIUS,
            command=lambda: self.app.show_page("login"),
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            top_right, text="Register", width=100, height=36,
            font=FONTS["small_bold"],
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            text_color=COLORS["text"],
            corner_radius=BUTTON_RADIUS,
            command=lambda: self.app.show_page("register"),
        ).pack(side="right")

        # --- Hero title ---
        hero = ctk.CTkFrame(self, fg_color="transparent")
        hero.place(relx=0.5, y=110, anchor="n")

        ctk.CTkLabel(
            hero, text="Celebrating Our Stars",
            font=(FONT_FAMILY, 26, "bold"),
            text_color=COLORS["text"],
        ).pack()

        ctk.CTkLabel(
            hero, text="Meet the achievers of this term",
            font=(FONT_FAMILY, 12, "italic"),
            text_color=COLORS["text_muted"],
        ).pack(pady=(4, 0))

        # --- Carousel container (width/height in CONSTRUCTOR) ---
        self._carousel_frame = ctk.CTkFrame(
            self,
            width=560, height=340,
            fg_color=COLORS["surface"],
            corner_radius=24,
            border_width=1, border_color=COLORS["border"])
        self._carousel_frame.pack_propagate(False)
        self._carousel_frame.place(
            relx=0.5, rely=0.52, anchor="center")

        # Gradient accent bar on top
        bar = ctk.CTkFrame(self._carousel_frame,
                           fg_color=COLORS["surface"],
                           height=6, corner_radius=0)
        bar.pack(fill="x", side="top")
        grad_img = make_ctk_image(make_gradient_image(560, 6, radius=0))
        ctk.CTkLabel(bar, image=grad_img, text="", height=6).pack(fill="x")

        # Carousel stage (where slides render)
        self._stage = ctk.CTkFrame(self._carousel_frame,
                                   fg_color="transparent")
        self._stage.pack(fill="both", expand=True)

        # --- Nav buttons + dots ---
        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.place(relx=0.5, y=650, anchor="n")

        ctk.CTkButton(
            nav, text="‹", width=36, height=36,
            font=(FONT_FAMILY, 18, "bold"),
            fg_color=COLORS["surface_alt"],
            hover_color=COLORS["primary"],
            text_color=COLORS["text"],
            corner_radius=18,
            command=self._prev_slide,
        ).pack(side="left")

        self._dots_frame = ctk.CTkFrame(nav, fg_color="transparent")
        self._dots_frame.pack(side="left", padx=16)

        ctk.CTkButton(
            nav, text="›", width=36, height=36,
            font=(FONT_FAMILY, 18, "bold"),
            fg_color=COLORS["surface_alt"],
            hover_color=COLORS["primary"],
            text_color=COLORS["text"],
            corner_radius=18,
            command=self._next_slide,
        ).pack(side="left")

        # --- Bottom CTA row ---
        cta = ctk.CTkFrame(self, fg_color="transparent")
        cta.place(relx=0.5, y=710, anchor="n")

        ctk.CTkButton(
            cta, text="  Sign In  ", width=180, height=44,
            font=FONTS["body_bold"],
            fg_color=COLORS["surface_alt"],
            hover_color=COLORS["primary"],
            text_color=COLORS["text"],
            corner_radius=BUTTON_RADIUS,
            command=lambda: self.app.show_page("login"),
        ).pack(side="left", padx=(0, PAD_MD))

        ctk.CTkButton(
            cta, text="  Register  ", width=180, height=44,
            font=FONTS["body_bold"],
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            text_color=COLORS["text"],
            corner_radius=BUTTON_RADIUS,
            command=lambda: self.app.show_page("register"),
        ).pack(side="left")

        # --- Version footer ---
        ctk.CTkLabel(
            self,
            text=f"{APP_NAME}  ·  v{APP_VERSION}  ·  {APP_YEAR}",
            font=FONTS["micro"],
            text_color=COLORS["text_dim"],
        ).place(relx=0.5, rely=0.98, anchor="center")

        # --- Load data + start carousel ---
        self._load_slides()
        self._build_dots()
        self._render_slide(0)
        self._schedule_next_slide()

    # =========================================================
    # DATA
    # =========================================================

    def _load_slides(self):
        self._slides = []

        # Overall topper
        try:
            overall = self.db.get_overall_topper(ia_number=3)
            if overall:
                self._slides.append({
                    "kind": "overall",
                    "title": "🥇 Overall Topper",
                    "accent": STATUS["gold"],
                    "user_id": overall["user_id"],
                    "name": overall["name"],
                    "usn": overall["usn"] or "",
                    "value_line": f"{overall['percentage']:.2f}%",
                    "value_sub": f"Grade {overall['grade']}  ·  "
                                 f"Total {int(overall['total'])}",
                })
        except Exception:
            pass

        # Subject toppers
        subject_icons = {
            "Maths":            ("🥇 Maths Topper",            "#8B5CF6"),
            "Physics":          ("🥇 Physics Topper",          "#EC4899"),
            "Chemistry":        ("🥇 Chemistry Topper",        "#10B981"),
            "Computer Science": ("🥇 Computer Science Topper", "#F59E0B"),
        }
        try:
            toppers = self.db.get_subject_toppers(ia_number=3)
            for subj, info in toppers.items():
                if not info:
                    continue
                title, accent = subject_icons.get(
                    subj, (f"🥇 {subj} Topper", COLORS["primary"]))
                self._slides.append({
                    "kind": "subject",
                    "subject": subj,
                    "title": title,
                    "accent": accent,
                    "user_id": info["user_id"],
                    "name": info["name"],
                    "usn": info["usn"] or "",
                    "value_line": f"{info['marks']:.0f}",
                    "value_sub": f"marks in {subj}",
                })
        except Exception:
            pass

        if not self._slides:
            self._slides = [{
                "kind": "empty",
                "title": "Coming soon",
                "accent": COLORS["primary"],
                "user_id": "",
                "name": "Toppers will appear here",
                "usn": "",
                "value_line": "—",
                "value_sub": "once marks are uploaded",
            }]

    # =========================================================
    # RENDER
    # =========================================================

    def _render_slide(self, index: int):
        if not self._slides:
            return
        index = index % len(self._slides)
        self._slide_index = index
        slide = self._slides[index]

        if self._current_slide_widget is not None:
            try:
                self._current_slide_widget.destroy()
            except Exception:
                pass

        wrap = ctk.CTkFrame(self._stage, fg_color="transparent")
        wrap.pack(fill="both", expand=True,
                  padx=PAD_XL, pady=(PAD_LG, PAD_MD))
        self._current_slide_widget = wrap

        # Title
        ctk.CTkLabel(
            wrap, text=slide["title"],
            font=(FONT_FAMILY, 14, "bold"),
            text_color=slide["accent"],
        ).pack(anchor="center", pady=(6, 16))

        # Avatar
        try:
            avatar = load_avatar(
                user_id=slide.get("user_id", "") or "_empty_",
                name=slide["name"],
                size=110,
                shape="circle",
                zone="gold" if slide["kind"] == "overall" else None,
                ring_width=6 if slide["kind"] == "overall" else 0,
            )
            ctk.CTkLabel(wrap, image=avatar, text="").pack()
        except Exception:
            circ = ctk.CTkFrame(wrap, fg_color=slide["accent"],
                                width=110, height=110,
                                corner_radius=55)
            circ.pack()
            circ.pack_propagate(False)

        # Name
        ctk.CTkLabel(
            wrap, text=slide["name"],
            font=(FONT_FAMILY, 20, "bold"),
            text_color=COLORS["text"],
        ).pack(pady=(14, 2))

        # USN
        if slide.get("usn"):
            ctk.CTkLabel(
                wrap, text=slide["usn"],
                font=FONTS["tiny"],
                text_color=COLORS["text_muted"],
            ).pack()

        # Big value
        ctk.CTkLabel(
            wrap, text=slide["value_line"],
            font=(FONT_FAMILY, 30, "bold"),
            text_color=slide["accent"],
        ).pack(pady=(14, 0))

        # Sub value
        ctk.CTkLabel(
            wrap, text=slide["value_sub"],
            font=FONTS["small"],
            text_color=COLORS["text_muted"],
        ).pack(pady=(2, 0))

        self._update_dots()

    # =========================================================
    # DOTS
    # =========================================================

    def _build_dots(self):
        for w in self._dots_frame.winfo_children():
            w.destroy()

        self._dot_widgets = []
        for i in range(len(self._slides)):
            d = ctk.CTkFrame(
                self._dots_frame,
                width=20 if i == 0 else 8,
                height=8,
                fg_color=GRADIENT_END if i == 0 else COLORS["text_dim"],
                corner_radius=4)
            d.pack(side="left", padx=3)
            d.pack_propagate(False)
            self._dot_widgets.append(d)

    def _update_dots(self):
        for i, d in enumerate(self._dot_widgets):
            try:
                if i == self._slide_index:
                    d.configure(fg_color=GRADIENT_END, width=20)
                else:
                    d.configure(fg_color=COLORS["text_dim"], width=8)
            except Exception:
                pass

    # =========================================================
    # CAROUSEL CONTROL
    # =========================================================

    def _next_slide(self):
        self._render_slide(self._slide_index + 1)
        self._reschedule_next_slide()

    def _prev_slide(self):
        self._render_slide(self._slide_index - 1)
        self._reschedule_next_slide()

    def _schedule_next_slide(self):
        self._slide_job = self.after(
            self.SLIDE_INTERVAL_MS, self._auto_advance)

    def _reschedule_next_slide(self):
        if self._slide_job:
            try:
                self.after_cancel(self._slide_job)
            except Exception:
                pass
        self._schedule_next_slide()

    def _auto_advance(self):
        self._render_slide(self._slide_index + 1)
        self._schedule_next_slide()

    # =========================================================
    # LIFECYCLE
    # =========================================================

    def on_show(self, **kwargs):
        self._load_slides()
        self._build_dots()
        self._render_slide(0)
        self._reschedule_next_slide()

    def on_hide(self):
        if self._slide_job:
            try:
                self.after_cancel(self._slide_job)
            except Exception:
                pass
            self._slide_job = None

    def destroy(self):
        self.on_hide()
        super().destroy()


# =============================================================
# SANITY CHECK
# =============================================================

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")

    class _FakeApp:
        def __init__(self):
            self.current_user = None
            try:
                from database import get_db
                self.db = get_db()
            except Exception:
                self.db = None

        def show_page(self, key, **kw):
            print(f"[landing] → show_page('{key}')  args={kw}")

    root = ctk.CTk()
    W, H = 1280, 780
    root.geometry(f"{W}x{H}")
    root.configure(fg_color=COLORS["bg"])
    root.title(f"{APP_NAME} — landing preview")

    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - W) // 2
    y = (sh - H) // 2
    root.geometry(f"{W}x{H}+{x}+{y}")

    app = _FakeApp()
    page = LandingPage(root, app)
    page.pack(fill="both", expand=True)
    root.mainloop()
    print("\n✅ pages/landing.py OK")