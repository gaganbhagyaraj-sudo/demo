# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  pages/auth/register.py  ·  Registration page
# =============================================================

from __future__ import annotations

import os
import sys

# --- make project root importable ---
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import re
import uuid
from datetime import datetime

import customtkinter as ctk

from config import (
    APP_NAME, APP_TAGLINE,
    COLORS, STATUS, FONTS, FONT_FAMILY,
    GRADIENT_START, GRADIENT_END,
    CARD_RADIUS, BUTTON_RADIUS, CHIP_RADIUS,
    PAD_SM, PAD_MD, PAD_LG, PAD_XL,
    ROLE_STUDENT, ROLE_FACILITATOR,
    STATUS_PENDING,
)
from theme import load_logo, make_ctk_image, make_gradient_image
from utils.images import splash_background


# =============================================================
# CONSTANTS
# =============================================================

GRADES   = [f"Grade {i}" for i in range(6, 13)]
SECTIONS = ["A", "B", "C", "D"]

EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$")
USN_RE   = re.compile(r"^[A-Z0-9]{6,15}$", re.IGNORECASE)


# =============================================================
# REGISTER PAGE
# =============================================================

class RegisterPage(ctk.CTkFrame):

    def __init__(self, master, app):
        super().__init__(master, fg_color=COLORS["bg"], corner_radius=0)

        self.app = app
        self.db = app.db
        self._bg_image = None

        # Role
        self._role = ROLE_STUDENT

        # Widget references
        self._name_entry = None
        self._email_entry = None
        self._password_entry = None
        self._confirm_entry = None
        self._usn_entry = None
        self._grade_menu = None
        self._section_menu = None
        self._error_label = None
        self._submit_btn = None
        self._role_btns = {}
        self._student_only_fields = []
        self._interests_selected = set()
        self._interest_chips = {}

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

        # --- Back button ---
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

        # --- Scrollable outer (in case content is tall) ---
        scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0)
        scroll.pack(fill="both", expand=True,
                    padx=PAD_XL, pady=(90, PAD_LG))

        # --- Center the card ---
        holder = ctk.CTkFrame(scroll, fg_color="transparent")
        holder.pack(anchor="center", pady=(0, 20))

        card = ctk.CTkFrame(
            holder,
            width=520, height=760,
            fg_color=COLORS["surface"],
            corner_radius=20,
            border_width=1, border_color=COLORS["border"])
        card.pack_propagate(False)
        card.pack()

        # Gradient top bar
        topbar = ctk.CTkFrame(card, fg_color=COLORS["surface"],
                              height=6, corner_radius=0)
        topbar.pack(fill="x", side="top")
        grad = make_ctk_image(make_gradient_image(520, 6, radius=0))
        ctk.CTkLabel(topbar, image=grad, text="", height=6).pack(fill="x")

        # Body
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="both", expand=True,
                  padx=PAD_XL, pady=(PAD_LG, PAD_LG))

        # Logo + title
        try:
            logo = load_logo(size=64, rounded=False, margin=8)
            ctk.CTkLabel(body, image=logo, text="").pack(pady=(0, 6))
        except Exception:
            pass

        ctk.CTkLabel(body, text="Create your account",
                     font=(FONT_FAMILY, 20, "bold"),
                     text_color=COLORS["text"]).pack()
        ctk.CTkLabel(body, text="Join the cascade of learning",
                     font=(FONT_FAMILY, 11, "italic"),
                     text_color=COLORS["text_muted"]).pack(pady=(2, 16))

        # --- Role selector ---
        ctk.CTkLabel(body, text="I am a…",
                     font=FONTS["small_bold"],
                     text_color=COLORS["text_muted"],
                     anchor="w").pack(anchor="w", pady=(0, 4))

        role_row = ctk.CTkFrame(body, fg_color="transparent")
        role_row.pack(fill="x", pady=(0, 12))

        for role_key, label in [(ROLE_STUDENT, "🎓  Student"),
                                (ROLE_FACILITATOR, "👨‍🏫  Facilitator")]:
            btn = ctk.CTkButton(
                role_row, text=label, width=210, height=40,
                font=FONTS["small_bold"],
                fg_color=COLORS["primary"] if role_key == self._role
                         else COLORS["surface_alt"],
                hover_color=COLORS["surface_hi"],
                text_color=COLORS["text"],
                corner_radius=BUTTON_RADIUS,
                command=lambda r=role_key: self._set_role(r))
            btn.pack(side="left", padx=(0, 8), expand=True, fill="x")
            self._role_btns[role_key] = btn

        # --- Full name ---
        ctk.CTkLabel(body, text="Full name",
                     font=FONTS["small_bold"],
                     text_color=COLORS["text_muted"],
                     anchor="w").pack(anchor="w", pady=(0, 4))
        self._name_entry = ctk.CTkEntry(
            body, width=420, height=40,
            font=FONTS["body"],
            fg_color=COLORS["surface_alt"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            corner_radius=10,
            placeholder_text="e.g. Rahul Sharma")
        self._name_entry.pack(pady=(0, 12))

        # --- Email ---
        ctk.CTkLabel(body, text="Email",
                     font=FONTS["small_bold"],
                     text_color=COLORS["text_muted"],
                     anchor="w").pack(anchor="w", pady=(0, 4))
        self._email_entry = ctk.CTkEntry(
            body, width=420, height=40,
            font=FONTS["body"],
            fg_color=COLORS["surface_alt"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            corner_radius=10,
            placeholder_text="you@example.com")
        self._email_entry.pack(pady=(0, 12))

        # --- USN (students only) ---
        usn_lbl = ctk.CTkLabel(body, text="USN",
                               font=FONTS["small_bold"],
                               text_color=COLORS["text_muted"],
                               anchor="w")
        usn_lbl.pack(anchor="w", pady=(0, 4))
        self._usn_entry = ctk.CTkEntry(
            body, width=420, height=40,
            font=FONTS["body"],
            fg_color=COLORS["surface_alt"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            corner_radius=10,
            placeholder_text="e.g. 1RV21CS016")
        self._usn_entry.pack(pady=(0, 12))
        self._student_only_fields.append((usn_lbl, self._usn_entry))

        # --- Grade + Section (students only) ---
        gs_row = ctk.CTkFrame(body, fg_color="transparent")
        gs_row.pack(fill="x", pady=(0, 12))
        self._student_only_fields.append(gs_row)

        ctk.CTkLabel(gs_row, text="Grade",
                     font=FONTS["small_bold"],
                     text_color=COLORS["text_muted"],
                     anchor="w").grid(row=0, column=0, sticky="w",
                                      padx=(0, 8))
        ctk.CTkLabel(gs_row, text="Section",
                     font=FONTS["small_bold"],
                     text_color=COLORS["text_muted"],
                     anchor="w").grid(row=0, column=1, sticky="w")

        self._grade_menu = ctk.CTkOptionMenu(
            gs_row, values=GRADES, width=200, height=40,
            font=FONTS["small"],
            fg_color=COLORS["surface_alt"],
            button_color=COLORS["primary"],
            button_hover_color=COLORS["primary_hover"],
            text_color=COLORS["text"],
            dropdown_fg_color=COLORS["surface_alt"],
            dropdown_text_color=COLORS["text"],
            corner_radius=10)
        self._grade_menu.set(GRADES[1])
        self._grade_menu.grid(row=1, column=0, sticky="w", padx=(0, 8))

        self._section_menu = ctk.CTkOptionMenu(
            gs_row, values=SECTIONS, width=200, height=40,
            font=FONTS["small"],
            fg_color=COLORS["surface_alt"],
            button_color=COLORS["primary"],
            button_hover_color=COLORS["primary_hover"],
            text_color=COLORS["text"],
            dropdown_fg_color=COLORS["surface_alt"],
            dropdown_text_color=COLORS["text"],
            corner_radius=10)
        self._section_menu.set("A")
        self._section_menu.grid(row=1, column=1, sticky="w")

        # --- Interests (students only) ---
        interest_lbl = ctk.CTkLabel(body, text="Your interests",
                                    font=FONTS["small_bold"],
                                    text_color=COLORS["text_muted"],
                                    anchor="w")
        interest_lbl.pack(anchor="w", pady=(6, 4))
        self._student_only_fields.append(interest_lbl)

        interests_box = ctk.CTkFrame(body, fg_color="transparent")
        interests_box.pack(fill="x", pady=(0, 12))
        self._student_only_fields.append(interests_box)

        try:
            rows = self.db.query("SELECT name FROM interests ORDER BY name")
            all_interests = rows["name"].tolist()
        except Exception:
            all_interests = ["Cricket", "Cooking", "Gaming", "Space",
                             "Music", "Football", "Movies"]

        # 2-column grid of chips
        for i, name in enumerate(all_interests):
            chip = ctk.CTkButton(
                interests_box, text=name, width=90, height=30,
                font=(FONT_FAMILY, 10),
                fg_color=COLORS["surface_alt"],
                hover_color=COLORS["surface_hi"],
                text_color=COLORS["text_muted"],
                corner_radius=CHIP_RADIUS,
                command=lambda n=name: self._toggle_interest(n))
            chip.grid(row=i // 3, column=i % 3, padx=4, pady=4, sticky="w")
            self._interest_chips[name] = chip

        # --- Password ---
        ctk.CTkLabel(body, text="Password",
                     font=FONTS["small_bold"],
                     text_color=COLORS["text_muted"],
                     anchor="w").pack(anchor="w", pady=(0, 4))
        self._password_entry = ctk.CTkEntry(
            body, width=420, height=40,
            font=FONTS["body"],
            fg_color=COLORS["surface_alt"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            corner_radius=10,
            placeholder_text="At least 4 characters",
            show="•")
        self._password_entry.pack(pady=(0, 12))

        # --- Confirm password ---
        ctk.CTkLabel(body, text="Confirm password",
                     font=FONTS["small_bold"],
                     text_color=COLORS["text_muted"],
                     anchor="w").pack(anchor="w", pady=(0, 4))
        self._confirm_entry = ctk.CTkEntry(
            body, width=420, height=40,
            font=FONTS["body"],
            fg_color=COLORS["surface_alt"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            corner_radius=10,
            placeholder_text="Re-enter password",
            show="•")
        self._confirm_entry.pack(pady=(0, 8))

        # --- Error label ---
        self._error_label = ctk.CTkLabel(
            body, text="",
            font=FONTS["small"],
            text_color=STATUS["red"],
            wraplength=420, justify="left")
        self._error_label.pack(pady=(6, 0))

        # --- Submit ---
        self._submit_btn = ctk.CTkButton(
            body, text="Create account", width=420, height=46,
            font=FONTS["body_bold"],
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            text_color=COLORS["text"],
            corner_radius=BUTTON_RADIUS,
            command=self._attempt_register)
        self._submit_btn.pack(pady=(12, 8))

        # --- Sign in link ---
        prompt = ctk.CTkFrame(body, fg_color="transparent")
        prompt.pack()
        ctk.CTkLabel(prompt, text="Already have an account?",
                     font=FONTS["small"],
                     text_color=COLORS["text_muted"]).pack(side="left")
        ctk.CTkButton(prompt, text="Sign in",
                      font=FONTS["small_bold"],
                      fg_color="transparent", hover=False,
                      text_color=COLORS["primary"],
                      command=lambda: self.app.show_page("login")
                      ).pack(side="left", padx=(6, 0))

        # Hint footer
        ctk.CTkLabel(
            body,
            text="Your account will be reviewed by the administrator "
                 "before you can sign in.",
            font=(FONT_FAMILY, 9),
            text_color=COLORS["text_dim"],
            wraplength=420, justify="center").pack(pady=(14, 0))

        # Focus
        self.after(80, self._name_entry.focus_set)

    # =========================================================
    # ROLE
    # =========================================================

    def _set_role(self, role: str):
        self._role = role
        for key, btn in self._role_btns.items():
            try:
                btn.configure(
                    fg_color=COLORS["primary"] if key == role
                             else COLORS["surface_alt"])
            except Exception:
                pass

        # Show/hide student-only fields
        show = (role == ROLE_STUDENT)
        for w in self._student_only_fields:
            try:
                if isinstance(w, tuple):
                    for ww in w:
                        if show:
                            ww.pack()
                        else:
                            ww.pack_forget()
                else:
                    if show:
                        w.pack(fill="x", pady=(0, 12))
                    else:
                        w.pack_forget()
            except Exception:
                pass

        self._clear_error()

    # =========================================================
    # INTERESTS
    # =========================================================

    def _toggle_interest(self, name: str):
        chip = self._interest_chips.get(name)
        if not chip:
            return
        if name in self._interests_selected:
            self._interests_selected.discard(name)
            try:
                chip.configure(fg_color=COLORS["surface_alt"],
                               text_color=COLORS["text_muted"])
            except Exception:
                pass
        else:
            self._interests_selected.add(name)
            try:
                chip.configure(fg_color=COLORS["primary"],
                               text_color=COLORS["text"])
            except Exception:
                pass

    # =========================================================
    # VALIDATION + SUBMIT
    # =========================================================

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

    def _attempt_register(self):
        self._clear_error()

        name = (self._name_entry.get() or "").strip()
        email = (self._email_entry.get() or "").strip().lower()
        password = self._password_entry.get() or ""
        confirm = self._confirm_entry.get() or ""

        # Common checks
        if not name or len(name) < 2:
            self._show_error("Please enter a valid full name.")
            return
        if not EMAIL_RE.match(email):
            self._show_error("Please enter a valid email address.")
            return
        if len(password) < 4:
            self._show_error("Password must be at least 4 characters.")
            return
        if password != confirm:
            self._show_error("Passwords do not match.")
            return

        # Role-specific
        usn = None
        grade = None
        section = None
        if self._role == ROLE_STUDENT:
            usn = (self._usn_entry.get() or "").strip().upper()
            if not USN_RE.match(usn):
                self._show_error(
                    "USN must be 6–15 letters/numbers (e.g., 1RV21CS016).")
                return
            grade = self._grade_menu.get()
            section = self._section_menu.get()

        # Uniqueness checks
        try:
            if self.db.get_user_by_email(email):
                self._show_error("An account with this email already exists.")
                return
            if usn and self.db.get_user_by_usn(usn):
                self._show_error("An account with this USN already exists.")
                return
        except Exception as e:
            self._show_error(f"Database error: {e}")
            return

        # Submit
        self._set_loading(True)
        self.after(120, lambda: self._do_register(
            name, email, password, usn, grade, section))

    def _do_register(self, name, email, password, usn, grade, section):
        try:
            user_id = str(uuid.uuid4())
            now = datetime.now().isoformat()

            self.db.execute("""
                INSERT INTO users
                    (id, usn, name, email, password, role, grade, section,
                     avatar_path, status, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (user_id, usn, name, email, password,
                  self._role, grade, section, None,
                  STATUS_PENDING, now))

            # Save interests (students only)
            if self._role == ROLE_STUDENT and self._interests_selected:
                for interest_name in self._interests_selected:
                    row = self.db.query(
                        "SELECT id FROM interests WHERE name=?",
                        (interest_name,))
                    if not row.empty:
                        iid = int(row.iloc[0]["id"])
                        self.db.execute(
                            """INSERT OR IGNORE INTO user_interests
                               (user_id, interest_id, weight)
                               VALUES (?,?,?)""",
                            (user_id, iid, 1.0))

            # Audit log
            try:
                self.db.log_audit(user_id, "register",
                                  target=email,
                                  details=f"role={self._role}")
            except Exception:
                pass

            # Success — go to pending page
            self._set_loading(False)
            try:
                self.app.show_page("pending",
                                   email=email, name=name,
                                   role=self._role)
            except TypeError:
                # Fake app doesn't accept kwargs — ignore
                self.app.show_page("pending")

        except Exception as e:
            self._set_loading(False)
            self._show_error(f"Registration failed: {e}")

    def _set_loading(self, loading: bool):
        try:
            self._submit_btn.configure(
                text="Creating account…" if loading else "Create account",
                state="disabled" if loading else "normal")
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
            print(f"[register] → show_page('{key}')  args={kw}")

    root = ctk.CTk()
    W, H = 1280, 900
    root.geometry(f"{W}x{H}")
    root.configure(fg_color=COLORS["bg"])
    root.title(f"{APP_NAME} — register preview")

    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - W) // 2
    y = (sh - H) // 2
    root.geometry(f"{W}x{H}+{x}+{y}")

    app = _FakeApp()
    page = RegisterPage(root, app)
    page.pack(fill="both", expand=True)
    root.mainloop()
    print("\n✅ pages/auth/register.py OK")