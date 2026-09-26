# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  pages/splash.py  ·  First screen (logo + tagline + loader)
# =============================================================

from __future__ import annotations

import os
import sys

# --- make project root importable ---
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import random

import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk

from config import (
    APP_NAME, APP_TAGLINE, APP_VERSION, APP_YEAR,
    COLORS, FONTS, FONT_FAMILY,
    GRADIENT_START, GRADIENT_END,
    LOGO_PATH,
)
from theme import load_logo
from utils.images import splash_background


# =============================================================
# SPLASH PAGE
# =============================================================

class SplashPage(ctk.CTkFrame):
    """
    Splash screen. Not a BasePage subclass — it has no header/footer.
    Auto-advances to 'landing' after SPLASH_HOLD_MS, or on click.
    """

    SPLASH_HOLD_MS = 2800          # total time before auto-advance
    LOAD_STEPS     = 60            # number of loader frames

    def __init__(self, master, app):
        super().__init__(master, fg_color=COLORS["bg"], corner_radius=0)

        self.app = app
        self._logo_image = None        # keep a reference
        self._bg_image = None
        self._loader_job = None
        self._advance_job = None
        self._progress = 0.0

        self._build()

    # =========================================================
    # BUILD
    # =========================================================

    def _build(self):
        # Size from the parent window (or defaults)
        self.update_idletasks()
        win_w = self.winfo_toplevel().winfo_width() or 1280
        win_h = self.winfo_toplevel().winfo_height() or 780

        # --- Cascade gradient background ---
        try:
            bg_pil = splash_background(win_w, win_h)
            self._bg_image = ctk.CTkImage(
                light_image=bg_pil, dark_image=bg_pil,
                size=(win_w, win_h))
            bg_label = ctk.CTkLabel(self, image=self._bg_image, text="")
            bg_label.place(x=0, y=0, relwidth=1, relheight=1)
            bg_label.bind("<Button-1>", lambda e: self._advance())
        except Exception:
            # Fallback: plain background if generation fails
            self.configure(fg_color=COLORS["bg"])
            self.bind("<Button-1>", lambda e: self._advance())

        # --- Center content ---
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.place(relx=0.5, rely=0.5, anchor="center")

        # --- Logo (large, generous margin so nothing clips) ---
        try:
            logo = load_logo(size=180, rounded=False, margin=18)
            self._logo_image = logo
            ctk.CTkLabel(content, image=logo, text="").pack(pady=(0, 22))
        except Exception:
            pass

        # --- App name ---
        ctk.CTkLabel(
            content, text=APP_NAME,
            font=FONTS["display"],
            text_color=COLORS["text"],
        ).pack()

        # --- Tagline ---
        ctk.CTkLabel(
            content, text=APP_TAGLINE,
            font=(FONT_FAMILY, 14, "italic"),
            text_color=COLORS["text_muted"],
        ).pack(pady=(6, 44))

        # --- Loading bar ---
        self._bar_w = 320
        self._bar_h = 6
        self._bar_bg = ctk.CTkFrame(
            content, fg_color=COLORS["surface_alt"],
            width=self._bar_w, height=self._bar_h,
            corner_radius=self._bar_h // 2)
        self._bar_bg.pack()
        self._bar_bg.pack_propagate(False)

        self._bar_fill = ctk.CTkFrame(
            self._bar_bg, fg_color=GRADIENT_END,
            width=1, height=self._bar_h,
            corner_radius=self._bar_h // 2)
        self._bar_fill.place(x=0, y=0)

        # --- Loading text ---
        self._loading_label = ctk.CTkLabel(
            content, text="Loading…",
            font=FONTS["tiny"],
            text_color=COLORS["text_muted"])
        self._loading_label.pack(pady=(12, 0))

        # --- Version footer ---
        ctk.CTkLabel(
            self,
            text=f"v{APP_VERSION}  ·  {APP_YEAR}",
            font=FONTS["micro"],
            text_color=COLORS["text_dim"],
        ).place(relx=0.5, rely=0.97, anchor="center")

        # --- Skip hint ---
        ctk.CTkLabel(
            self,
            text="Click anywhere to continue",
            font=FONTS["micro"],
            text_color=COLORS["text_dim"],
        ).place(relx=0.5, rely=0.93, anchor="center")

        # Start the loader
        self._tick_loader()

        # Schedule auto-advance
        self._advance_job = self.after(
            self.SPLASH_HOLD_MS, self._advance)

    # =========================================================
    # LOADING BAR
    # =========================================================

    def _tick_loader(self):
        self._progress += 1.0 / self.LOAD_STEPS
        t = min(1.0, self._progress)

        fill_w = max(1, int(self._bar_w * t))
        try:
            self._bar_fill.configure(width=fill_w)
            self._bar_fill.place_configure(width=fill_w)
        except Exception:
            pass

        # Loading text per quarter
        if t < 0.25:
            msg = "Waking the cascade…"
        elif t < 0.5:
            msg = "Loading your data…"
        elif t < 0.75:
            msg = "Preparing your journey…"
        elif t < 0.99:
            msg = "Almost there…"
        else:
            msg = "Welcome, seeker."
        try:
            self._loading_label.configure(text=msg)
        except Exception:
            pass

        if t < 1.0:
            interval = int(self.SPLASH_HOLD_MS / self.LOAD_STEPS)
            self._loader_job = self.after(interval, self._tick_loader)

    # =========================================================
    # ADVANCE
    # =========================================================

    def _advance(self):
        # Cancel pending callbacks
        if self._advance_job:
            try:
                self.after_cancel(self._advance_job)
            except Exception:
                pass
            self._advance_job = None
        if self._loader_job:
            try:
                self.after_cancel(self._loader_job)
            except Exception:
                pass
            self._loader_job = None

        # Jump to landing page
        try:
            self.app.show_page("landing")
        except Exception as e:
            print(f"[splash] failed to advance: {e}")


# =============================================================
# SANITY CHECK
# =============================================================

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")

    # Fake app for standalone testing
    class _FakeApp:
        def __init__(self):
            self.current_user = None

        def show_page(self, key, **kw):
            print(f"[splash] → show_page('{key}')  args={kw}")
            try:
                root.destroy()
            except Exception:
                pass

    root = ctk.CTk()
    W, H = 1280, 780
    root.geometry(f"{W}x{H}")
    root.configure(fg_color=COLORS["bg"])
    root.title(f"{APP_NAME} — splash preview")

    # Center
    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - W) // 2
    y = (sh - H) // 2
    root.geometry(f"{W}x{H}+{x}+{y}")

    page = SplashPage(root, _FakeApp())
    page.pack(fill="both", expand=True)

    root.mainloop()
    print("\n✅ pages/splash.py OK")