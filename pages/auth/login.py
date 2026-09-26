# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  pages/auth/login.py  ·  Login page
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
    APP_NAME, APP_TAGLINE,
    COLORS, STATUS, ROLES,
    FONTS, FONT_FAMILY,
    GRADIENT_START, GRADIENT_END,
    CARD_RADIUS, BUTTON_RADIUS,
    PAD_SM, PAD_MD, PAD_LG, PAD_XL,
    ROLE_ADMIN, ROLE_FACILITATOR, ROLE_STUDENT,
    STATUS_APPROVED, STATUS_PENDING, STATUS_REJECTED,
    DEMO_ADMIN, DEMO_FACILITATOR, DEMO_STUDENT,
)
from theme import load_logo, make_ctk_image, make_gradient_image
from utils.images import splash_background


# =============================================================
# LOGIN PAGE
# =============================================================

class LoginPage(ctk.CTkFrame):

    def __init__(self, master, app):
        super().__init__(master, fg_color=COLORS["bg"], corner_radius=0)

        self.app = app
        self.db = app.db
        self._bg_image = None

        # Entry widget references
        self._email_entry = None
        self._password_entry = None
        self._error_label = None
        self._show_password = False
        self._login_btn = None

        self._build()

    # =========================================================
    # BUILD
    # =========================================================

    def _build(self):
        self.update_idletasks()
        win_w = self.winfo_toplevel().winfo_width() or 1280
        win_h = self.winfo_toplevel().winfo_height() or 780

        # --- Gradient background ---
        try:
            bg_pil = splash_background(win_w, win_h)
            self._bg_image = ctk.CTkImage(
                light_image=bg_pil, dark_image=bg_pil,
                size=(win_w, win_h))
            ctk.CTkLabel(self, image=self._bg_image, text="").place(
                x=0, y=0, relwidth=1, relheight=1)
        except Exception:
            self.configure(fg_color=COLORS["bg"])

        # --- Back-to-landing button (top-left) ---
        ctk.CTkButton(
            self, text="← Back", width=90, height=34,
            font=FONTS["small_bold"],
            fg_color="transparent",
            hover_color=COLORS["surface_hi"],
            text_color=COLORS["text"],
            border_width=1, border_color=COLORS["border"],
            corner_radius=BUTTON_RADIUS,
            command=lambda: self.app.show_page("landing"),
        ).place(x=PAD_XL, y=PAD_LG)

        # --- Centered card (width/height in CONSTRUCTOR) ---
        card = ctk.CTkFrame(
            self,
            width=440, height=580,
            fg_color=COLORS["surface"],
            corner_radius=20,
            border_width=1, border_color=COLORS["border"])
        card.pack_propagate(False)
        card.place(relx=0.5, rely=0.5, anchor="center")

        # --- Gradient top bar of the card ---
        topbar = ctk.CTkFrame(card, fg_color=COLORS["surface"],
                              height=6, corner_radius=0)
        topbar.pack(fill="x", side="top")
        grad = make_ctk_image(make_gradient_image(440, 6, radius=0))
        ctk.CTkLabel(topbar, image=grad, text="", height=6).pack(fill="x")

        # --- Body of the card ---
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="both", expand=True,
                  padx=PAD_XL, pady=(PAD_LG, PAD_LG))

        # Logo
        try:
            logo = load_logo(size=78, rounded=False, margin=10)
            ctk.CTkLabel(body, image=logo, text="").pack(pady=(0, 8))
        except Exception:
            pass

        # Title
        ctk.CTkLabel(
            body, text="Welcome back",
            font=(FONT_FAMILY, 22, "bold"),
            text_color=COLORS["text"],
        ).pack()

        ctk.CTkLabel(
            body, text=APP_TAGLINE,
            font=(FONT_FAMILY, 11, "italic"),
            text_color=COLORS["text_muted"],
        ).pack(pady=(2, 22))

        # --- Email field ---
        ctk.CTkLabel(body, text="Email",
                     font=FONTS["small_bold"],
                     text_color=COLORS["text_muted"],
                     anchor="w").pack(anchor="w", pady=(0, 4))

        self._email_entry = ctk.CTkEntry(
            body, width=340, height=42,
            font=FONTS["body"],
            fg_color=COLORS["surface_alt"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            corner_radius=10,
            placeholder_text="you@sj.com")
        self._email_entry.pack(pady=(0, 14))

        # --- Password field ---
        ctk.CTkLabel(body, text="Password",
                     font=FONTS["small_bold"],
                     text_color=COLORS["text_muted"],
                     anchor="w").pack(anchor="w", pady=(0, 4))

        pwd_row = ctk.CTkFrame(body, fg_color="transparent")
        pwd_row.pack()

        self._password_entry = ctk.CTkEntry(
            pwd_row, width=290, height=42,
            font=FONTS["body"],
            fg_color=COLORS["surface_alt"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            corner_radius=10,
            placeholder_text="••••••",
            show="•")
        self._password_entry.pack(side="left")

        self._toggle_btn = ctk.CTkButton(
            pwd_row, text="👁", width=44, height=42,
            font=(FONT_FAMILY, 14),
            fg_color=COLORS["surface_alt"],
            hover_color=COLORS["surface_hi"],
            text_color=COLORS["text_muted"],
            corner_radius=10,
            command=self._toggle_password)
        self._toggle_btn.pack(side="left", padx=(6, 0))

        # --- Error label (hidden by default) ---
        self._error_label = ctk.CTkLabel(
            body, text="",
            font=FONTS["small"],
            text_color=STATUS["red"],
            wraplength=340, justify="left")
        self._error_label.pack(pady=(14, 0))

        # --- Sign-in button ---
        self._login_btn = ctk.CTkButton(
            body, text="Sign In", width=340, height=46,
            font=FONTS["body_bold"],
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            text_color=COLORS["text"],
            corner_radius=BUTTON_RADIUS,
            command=self._attempt_login)
        self._login_btn.pack(pady=(14, 8))

        # Enter key shortcuts
        self._email_entry.bind("<Return>", lambda e: self._attempt_login())
        self._password_entry.bind("<Return>", lambda e: self._attempt_login())

        # --- Register prompt ---
        prompt = ctk.CTkFrame(body, fg_color="transparent")
        prompt.pack(pady=(4, 0))
        ctk.CTkLabel(prompt, text="New here?",
                     font=FONTS["small"],
                     text_color=COLORS["text_muted"]).pack(side="left")
        ctk.CTkButton(prompt, text="Create an account",
                      font=FONTS["small_bold"],
                      fg_color="transparent",
                      hover=False,
                      text_color=COLORS["primary"],
                      command=lambda: self.app.show_page("register")
                      ).pack(side="left", padx=(6, 0))

        # --- Demo credentials footer ---
        demo = ctk.CTkFrame(card, fg_color=COLORS["bg"],
                            height=80, corner_radius=0)
        demo.pack(fill="x", side="bottom")
        demo.pack_propagate(False)

        ctk.CTkLabel(
            demo, text="DEMO ACCOUNTS",
            font=(FONT_FAMILY, 9, "bold"),
            text_color=COLORS["text_dim"],
        ).pack(pady=(10, 4))

        creds = ctk.CTkFrame(demo, fg_color="transparent")
        creds.pack()

        for label, email in [
            ("👑 Admin",       DEMO_ADMIN["email"]),
            ("👨‍🏫 Facilitator", DEMO_FACILITATOR["email"]),
            ("🎓 Student",      DEMO_STUDENT["email"]),
        ]:
            btn = ctk.CTkButton(
                creds, text=label, width=120, height=26,
                font=(FONT_FAMILY, 9),
                fg_color=COLORS["surface_alt"],
                hover_color=COLORS["surface_hi"],
                text_color=COLORS["text_muted"],
                corner_radius=6,
                command=lambda e=email: self._fill_demo(e))
            btn.pack(side="left", padx=3)

        ctk.CTkLabel(
            demo, text="Click a role to auto-fill · password: demo",
            font=(FONT_FAMILY, 8),
            text_color=COLORS["text_dim"],
        ).pack(pady=(4, 6))

        # Focus email on start
        self.after(80, self._email_entry.focus_set)

    # =========================================================
    # HELPERS
    # =========================================================

    def _toggle_password(self):
        self._show_password = not self._show_password
        try:
            self._password_entry.configure(
                show="" if self._show_password else "•")
            self._toggle_btn.configure(
                text="🙈" if self._show_password else "👁")
        except Exception:
            pass

    def _fill_demo(self, email: str):
        try:
            self._email_entry.delete(0, "end")
            self._email_entry.insert(0, email)
            self._password_entry.delete(0, "end")
            self._password_entry.insert(0, "demo")
            self._clear_error()
        except Exception:
            pass

    def _show_error(self, msg: str):
        try:
            self._error_label.configure(text=f"⚠️  {msg}")
        except Exception:
            pass

    def _clear_error(self):
        try:
            self._error_label.configure(text="")
        except Exception:
            pass

    def _set_loading(self, loading: bool):
        try:
            if loading:
                self._login_btn.configure(text="Signing in…",
                                          state="disabled")
            else:
                self._login_btn.configure(text="Sign In",
                                          state="normal")
        except Exception:
            pass

    # =========================================================
    # LOGIN LOGIC
    # =========================================================

    def _attempt_login(self):
        self._clear_error()

        email = (self._email_entry.get() or "").strip()
        password = self._password_entry.get() or ""

        if not email:
            self._show_error("Please enter your email.")
            return
        if not password:
            self._show_error("Please enter your password.")
            return

        self._set_loading(True)
        # Small defer so the button shows the loading state
        self.after(120, lambda: self._do_login(email, password))

    def _do_login(self, email: str, password: str):
        try:
            user = self.db.get_user_by_email(email)
        except Exception as e:
            self._set_loading(False)
            self._show_error(f"Database error: {e}")
            return

        if not user:
            self._set_loading(False)
            self._show_error("No account found with this email.")
            return

        # Password check (demo passwords are all 'demo')
        if (user.get("password") or "") != password:
            self._set_loading(False)
            self._show_error("Incorrect password. Try 'demo'.")
            return

        # Status check
        status = user.get("status", STATUS_APPROVED)
        if status == STATUS_PENDING:
            self._set_loading(False)
            self._show_error(
                "Your account is pending admin approval. "
                "You'll be notified once approved.")
            return
        if status == STATUS_REJECTED:
            self._set_loading(False)
            self._show_error(
                "Your registration was rejected. Contact the administrator.")
            return

        # Success
        self._set_loading(False)
        try:
            self.app.set_user(user)
        except Exception as e:
            self._show_error(f"Login failed: {e}")


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
            print(f"[login] → show_page('{key}')  args={kw}")

        def set_user(self, user):
            print(f"[login] ✅ authenticated: "
                  f"{user['name']}  ({user['role']})")
            # Print what the router would do next
            role = user.get("role", "")
            dest = {"admin": "admin_dashboard",
                    "facilitator": "fac_command",
                    "student": "stu_dashboard"}.get(role, "landing")
            print(f"[login] → would route to: {dest}")

    root = ctk.CTk()
    W, H = 1280, 780
    root.geometry(f"{W}x{H}")
    root.configure(fg_color=COLORS["bg"])
    root.title(f"{APP_NAME} — login preview")

    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - W) // 2
    y = (sh - H) // 2
    root.geometry(f"{W}x{H}+{x}+{y}")

    app = _FakeApp()
    page = LoginPage(root, app)
    page.pack(fill="both", expand=True)
    root.mainloop()
    print("\n✅ pages/auth/login.py OK")