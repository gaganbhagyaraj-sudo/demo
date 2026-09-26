# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  pages/auth/pending.py  ·  Pending approval screen
# =============================================================

from __future__ import annotations

import os
import sys

# --- make project root importable ---
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import customtkinter as ctk

from config import (
    APP_NAME, APP_TAGLINE, APP_VERSION, APP_YEAR,
    COLORS, STATUS, FONTS, FONT_FAMILY,
    GRADIENT_START, GRADIENT_END,
    CARD_RADIUS, BUTTON_RADIUS,
    PAD_SM, PAD_MD, PAD_LG, PAD_XL,
    ROLE_ADMIN, ROLE_FACILITATOR, ROLE_STUDENT,
    STATUS_PENDING, STATUS_APPROVED, STATUS_REJECTED,
)
from theme import load_logo, make_ctk_image, make_gradient_image
from utils.images import splash_background
from utils.avatars import load_avatar


# =============================================================
# PENDING PAGE
# =============================================================

class PendingPage(ctk.CTkFrame):
    """Waiting screen shown while a new registration awaits admin approval."""

    POLL_INTERVAL_MS = 5000     # check DB every 5s

    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color=COLORS["bg"], corner_radius=0)

        self.app = app
        self.db = app.db
        self._bg_image = None
        self._poll_job = None

        # Registration context (passed via show_page kwargs)
        self._reg_email = kwargs.get("email", "")
        self._reg_name  = kwargs.get("name", "")
        self._reg_role  = kwargs.get("role", ROLE_STUDENT)

        # If the DB has a user with this email, grab their full record
        self._user = None
        if self._reg_email:
            try:
                self._user = self.db.get_user_by_email(self._reg_email)
            except Exception:
                self._user = None

        self._build()

    # =========================================================
    # BUILD
    # =========================================================

    def _build(self):
        self.update_idletasks()
        win_w = self.winfo_toplevel().winfo_width() or 1280
        win_h = self.winfo_toplevel().winfo_height() or 780

        # --- Background ---
        try:
            bg_pil = splash_background(win_w, win_h)
            self._bg_image = ctk.CTkImage(
                light_image=bg_pil, dark_image=bg_pil,
                size=(win_w, win_h))
            ctk.CTkLabel(self, image=self._bg_image, text="").place(
                x=0, y=0, relwidth=1, relheight=1)
        except Exception:
            self.configure(fg_color=COLORS["bg"])

        # --- Center card ---
        card = ctk.CTkFrame(
            self,
            width=520, height=560,
            fg_color=COLORS["surface"],
            corner_radius=20,
            border_width=1, border_color=COLORS["border"])
        card.pack_propagate(False)
        card.place(relx=0.5, rely=0.5, anchor="center")

        # Gradient accent bar
        topbar = ctk.CTkFrame(card, fg_color=COLORS["surface"],
                              height=6, corner_radius=0)
        topbar.pack(fill="x", side="top")
        grad = make_ctk_image(make_gradient_image(520, 6, radius=0))
        ctk.CTkLabel(topbar, image=grad, text="", height=6).pack(fill="x")

        # Body
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="both", expand=True,
                  padx=PAD_XL, pady=(PAD_LG, PAD_LG))

        # --- Big hourglass icon ---
        icon_box = ctk.CTkFrame(
            body, width=110, height=110,
            fg_color=COLORS["surface_alt"],
            corner_radius=55)
        icon_box.pack(pady=(6, 14))
        icon_box.pack_propagate(False)

        ctk.CTkLabel(
            icon_box, text="⏳",
            font=(FONT_FAMILY, 44),
            text_color=STATUS["amber"],
        ).place(relx=0.5, rely=0.5, anchor="center")

        # --- Title ---
        ctk.CTkLabel(
            body, text="Awaiting approval",
            font=(FONT_FAMILY, 22, "bold"),
            text_color=COLORS["text"],
        ).pack()

        ctk.CTkLabel(
            body, text="Your account is being reviewed by the administrator.",
            font=FONTS["small"],
            text_color=COLORS["text_muted"],
            wraplength=420, justify="center",
        ).pack(pady=(6, 20))

        # --- Divider ---
        ctk.CTkFrame(body, height=1, fg_color=COLORS["border_soft"]).pack(
            fill="x", pady=(0, 16))

        # --- User info rows ---
        info = ctk.CTkFrame(body, fg_color="transparent")
        info.pack(fill="x")

        # Avatar + name
        avatar_row = ctk.CTkFrame(info, fg_color="transparent")
        avatar_row.pack(fill="x", pady=(0, 12))

        try:
            avatar = load_avatar(
                user_id=(self._user or {}).get("id", "_pending_"),
                name=self._reg_name or "New User",
                size=52, shape="circle")
            ctk.CTkLabel(avatar_row, image=avatar, text="").pack(
                side="left", padx=(0, 12))
        except Exception:
            pass

        name_box = ctk.CTkFrame(avatar_row, fg_color="transparent")
        name_box.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            name_box, text=self._reg_name or "New User",
            font=FONTS["h4"],
            text_color=COLORS["text"], anchor="w").pack(anchor="w")
        ctk.CTkLabel(
            name_box, text=self._reg_email or "",
            font=FONTS["tiny"],
            text_color=COLORS["text_muted"], anchor="w").pack(anchor="w")

        # Role chip
        role_label = {
            ROLE_STUDENT: "🎓 Student",
            ROLE_FACILITATOR: "👨‍🏫 Facilitator",
            ROLE_ADMIN: "👑 Administrator",
        }.get(self._reg_role, self._reg_role.title())

        chip = ctk.CTkFrame(
            info, fg_color=COLORS["surface_alt"],
            corner_radius=12)
        chip.pack(anchor="w", pady=(0, 14))
        ctk.CTkLabel(
            chip, text=role_label,
            font=FONTS["small_bold"],
            text_color=COLORS["text"]).pack(padx=12, pady=5)

        # --- What happens next ---
        ctk.CTkLabel(
            body, text="What happens next?",
            font=FONTS["small_bold"],
            text_color=COLORS["text_muted"],
            anchor="w").pack(anchor="w", pady=(6, 6))

        steps = [
            "📬  The admin will review your details",
            "✅  Once approved, this page will unlock automatically",
            "🎓  You'll be taken straight to your dashboard",
        ]
        for s in steps:
            ctk.CTkLabel(
                body, text=s,
                font=FONTS["small"],
                text_color=COLORS["text"],
                anchor="w").pack(anchor="w", pady=2)

        # --- Live status line ---
        self._status_label = ctk.CTkLabel(
            body, text="● Checking status…",
            font=FONTS["tiny"],
            text_color=COLORS["text_muted"])
        self._status_label.pack(pady=(16, 0))

        # --- Buttons ---
        btn_row = ctk.CTkFrame(body, fg_color="transparent")
        btn_row.pack(side="bottom", pady=(16, 0))

        ctk.CTkButton(
            btn_row, text="Back to home", width=180, height=40,
            font=FONTS["small_bold"],
            fg_color=COLORS["surface_alt"],
            hover_color=COLORS["surface_hi"],
            text_color=COLORS["text"],
            corner_radius=BUTTON_RADIUS,
            command=lambda: self.app.show_page("landing"),
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_row, text="Check now", width=160, height=40,
            font=FONTS["small_bold"],
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            text_color=COLORS["text"],
            corner_radius=BUTTON_RADIUS,
            command=self._check_status,
        ).pack(side="left")

        # Footer version
        ctk.CTkLabel(
            self,
            text=f"{APP_NAME}  ·  v{APP_VERSION}  ·  {APP_YEAR}",
            font=FONTS["micro"],
            text_color=COLORS["text_dim"],
        ).place(relx=0.5, rely=0.97, anchor="center")

        # --- Start polling ---
        self._schedule_poll()

    # =========================================================
    # POLLING
    # =========================================================

    def _schedule_poll(self):
        self._poll_job = self.after(
            self.POLL_INTERVAL_MS, self._poll_status)

    def _cancel_poll(self):
        if self._poll_job:
            try:
                self.after_cancel(self._poll_job)
            except Exception:
                pass
            self._poll_job = None

    def _poll_status(self):
        self._check_status(silent=True)
        self._schedule_poll()

    def _check_status(self, silent: bool = False):
        # No email → just show a message
        if not self._reg_email:
            if not silent:
                self._set_status("● Could not verify — please sign in again.",
                                 STATUS["amber"])
            return

        # Re-fetch user from DB
        try:
            user = self.db.get_user_by_email(self._reg_email)
        except Exception as e:
            if not silent:
                self._set_status(f"● Database error: {e}",
                                 STATUS["red"])
            return

        if not user:
            self._set_status("● Account not found.",
                             STATUS["red"])
            return

        status = user.get("status", STATUS_PENDING)

        if status == STATUS_APPROVED:
            self._set_status("● Approved! Redirecting…",
                             STATUS["green"])
            self._cancel_poll()
            self.after(700, lambda: self._on_approved(user))
            return

        if status == STATUS_REJECTED:
            self._set_status("● Registration rejected.",
                             STATUS["red"])
            self._cancel_poll()
            self.after(700, self._on_rejected)
            return

        # Still pending
        self._set_status("● Waiting for admin approval…",
                         STATUS["amber"])

    def _set_status(self, text: str, color: str):
        try:
            self._status_label.configure(text=text, text_color=color)
        except Exception:
            pass

    def _on_approved(self, user: dict):
        """Admin approved — route to role-based dashboard."""
        try:
            self.app.set_user(user)
        except Exception:
            # Fallback if app has no set_user
            self.app.show_page("login")

    def _on_rejected(self):
        """Admin rejected — send back to register."""
        try:
            self.app.show_page("register")
        except Exception:
            pass

    # =========================================================
    # LIFECYCLE
    # =========================================================

    def on_show(self, **kwargs):
        # Refresh context if kwargs came in
        if kwargs.get("email"):
            self._reg_email = kwargs["email"]
        if kwargs.get("name"):
            self._reg_name = kwargs["name"]
        if kwargs.get("role"):
            self._reg_role = kwargs["role"]

        # Re-fetch and re-check immediately
        self._check_status()
        self._cancel_poll()
        self._schedule_poll()

    def on_hide(self):
        self._cancel_poll()

    def destroy(self):
        self._cancel_poll()
        try:
            super().destroy()
        except Exception:
            pass


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
            except Exception as e:
                print(f"(no DB: {e})")
                self.db = None

        def show_page(self, key, **kw):
            print(f"[pending] → show_page('{key}')  args={kw}")

        def set_user(self, user):
            print(f"[pending] ✅ approved & signed in: "
                  f"{user['name']}  ({user['role']})")

    root = ctk.CTk()
    W, H = 1280, 780
    root.geometry(f"{W}x{H}")
    root.configure(fg_color=COLORS["bg"])
    root.title(f"{APP_NAME} — pending preview")

    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - W) // 2
    y = (sh - H) // 2
    root.geometry(f"{W}x{H}+{x}+{y}")

    app = _FakeApp()

    # Demo: use an already-approved user to see the redirect path fire quickly.
    # Change to a random nonexistent email to test the "not found" path.
    page = PendingPage(
        root, app,
        email="rahul.sharma@sj.com",
        name="Rahul Sharma",
        role="student",
    )
    page.pack(fill="both", expand=True)
    root.mainloop()
    print("\n✅ pages/auth/pending.py OK")