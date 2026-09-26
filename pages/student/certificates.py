# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  pages/student/certificates.py  ·  Student certificates
# =============================================================

from __future__ import annotations

import os
import sys

# --- make project root importable ---
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import subprocess
from datetime import datetime

import customtkinter as ctk

from config import (
    APP_NAME, COLORS, STATUS,
    FONTS, FONT_FAMILY,
    CARD_RADIUS, BUTTON_RADIUS, CHIP_RADIUS,
    PAD_SM, PAD_MD, PAD_LG, PAD_XL,
    CERTIFICATES, CERT_BY_ID,
)
from pages.base_page import BasePage


# =============================================================
# HELPERS
# =============================================================

CERT_ICONS = {
    "academic_excellence": "🏆",
    "subject_topper":      "🎯",
    "perfect_attendance":  "🌟",
    "most_improved":       "📈",
    "all_rounder":         "💎",
    "activity_champion":   "🎗️",
}

CERT_COLORS = {
    "academic_excellence": "#FBBF24",
    "subject_topper":      "#8B5CF6",
    "perfect_attendance":  "#60A5FA",
    "most_improved":       "#10B981",
    "all_rounder":         "#EC4899",
    "activity_champion":   "#F59E0B",
}


def _open_file(path: str) -> bool:
    try:
        if not os.path.exists(path):
            return False
        if sys.platform.startswith("win"):
            os.startfile(path)   # noqa: S606
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
        return True
    except Exception:
        return False


def _reveal_in_folder(path: str) -> bool:
    try:
        folder = os.path.dirname(path)
        if not os.path.exists(folder):
            return False
        if sys.platform.startswith("win"):
            os.startfile(folder)   # noqa: S606
        elif sys.platform == "darwin":
            subprocess.Popen(["open", folder])
        else:
            subprocess.Popen(["xdg-open", folder])
        return True
    except Exception:
        return False


# =============================================================
# CERTIFICATES PAGE
# =============================================================

class StudentCertificatesPage(BasePage):

    def __init__(self, master, app, target_user_id: str = None):
        super().__init__(master, app)

        self.target_id = target_user_id or (self.user or {}).get("id")
        self.is_self = (self.target_id == (self.user or {}).get("id"))
        self.target = self.db.get_user(self.target_id) if self.target_id else None

        self.build_header(
            "My Certificates" if self.is_self
            else f"{self.target.get('name', '')} — Certificates",
            "Recognitions of your achievements",
            back=not self.is_self,
        )
        self.build_content(scrollable=True)
        self.build_footer()

        self.render()

    # =========================================================
    # RENDER
    # =========================================================

    def render(self):
        if not self.target:
            self._render_empty("Student not found.")
            return

        uid = self.target["id"]
        content = self._content

        # Load
        try:
            self._certs = self.db.get_user_certificates(uid)
        except Exception:
            self._certs = None

        # 1. Summary stats
        self._render_summary(content)

        # 2. Available certificates section (which can be generated)
        self.section_title("Your Certificates", parent=content)
        self._render_cert_list(content, uid)

        # 3. Legend: what each certificate means
        self.section_title("Certificate Types", parent=content)
        self._render_catalog(content)

    # =========================================================
    # SUMMARY
    # =========================================================

    def _render_summary(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        total = 0 if self._certs is None else len(self._certs)

        # By type count
        by_type = {}
        if self._certs is not None and not self._certs.empty:
            for _, r in self._certs.iterrows():
                by_type[r["cert_type"]] = by_type.get(r["cert_type"], 0) + 1

        # This month
        this_month = 0
        if self._certs is not None and not self._certs.empty:
            now = datetime.now()
            for _, r in self._certs.iterrows():
                try:
                    d = datetime.fromisoformat(r["issued_at"])
                    if d.year == now.year and d.month == now.month:
                        this_month += 1
                except Exception:
                    pass

        self.stat_card(
            row, total, "Total certificates",
            accent=STATUS["gold"], icon="📜",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, this_month, "This month",
            accent=COLORS["primary"], icon="🗓️",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, len(by_type), f"Of {len(CERTIFICATES)} types",
            accent=COLORS["primary"], icon="🎯",
        ).pack(side="left")

    # =========================================================
    # CERT LIST
    # =========================================================

    def _render_cert_list(self, parent, uid):
        certs = self._certs
        if certs is None or certs.empty:
            card = self.card(parent)
            card.pack(fill="x", pady=(0, PAD_MD))

            body = ctk.CTkFrame(card, fg_color="transparent")
            body.pack(fill="x", padx=PAD_LG, pady=PAD_XL)

            ctk.CTkLabel(
                body, text="🎓",
                font=(FONT_FAMILY, 42),
                text_color=COLORS["text_muted"]).pack()

            ctk.CTkLabel(
                body, text="No certificates yet",
                font=(FONT_FAMILY, 15, "bold"),
                text_color=COLORS["text"]).pack(pady=(8, 4))

            ctk.CTkLabel(
                body,
                text="Keep working hard! Certificates are awarded for\n"
                     "academic excellence, perfect attendance, and more.",
                font=FONTS["small"],
                text_color=COLORS["text_muted"],
                justify="center").pack()

            # Generate available certificates button
            self.primary_button(
                body, "Check what I can earn now",
                command=lambda: self._check_generate(uid),
                width=240, height=42,
            ).pack(pady=(16, 0))
            return

        # Ensure newest first
        try:
            certs = certs.sort_values("issued_at", ascending=False)
        except Exception:
            pass

        for _, cert in certs.iterrows():
            self._render_cert_row(parent, cert)

    def _render_cert_row(self, parent, cert):
        ctype = cert["cert_type"]
        icon = CERT_ICONS.get(ctype, "📜")
        color = CERT_COLORS.get(ctype, COLORS["primary"])

        card = self.card(parent)
        card.pack(fill="x", pady=4)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=PAD_LG, pady=PAD_MD)

        # Left: icon block
        block = ctk.CTkFrame(
            inner,
            width=64, height=64,
            fg_color=color,
            corner_radius=14)
        block.pack(side="left")
        block.pack_propagate(False)

        ctk.CTkLabel(
            block, text=icon,
            font=(FONT_FAMILY, 28),
            text_color="#FFFFFF",
        ).place(relx=0.5, rely=0.5, anchor="center")

        # Middle: title + date
        mid = ctk.CTkFrame(inner, fg_color="transparent")
        mid.pack(side="left", fill="x", expand=True, padx=(PAD_LG, 0))

        ctk.CTkLabel(
            mid, text=cert["title"],
            font=(FONT_FAMILY, 15, "bold"),
            text_color=COLORS["text"], anchor="w",
        ).pack(anchor="w")

        meta = CERT_BY_ID.get(ctype, {}).get("desc", "")
        if meta:
            ctk.CTkLabel(
                mid, text=meta,
                font=(FONT_FAMILY, 10),
                text_color=COLORS["text_muted"], anchor="w",
            ).pack(anchor="w", pady=(2, 0))

        issued = (cert.get("issued_at") or "")[:10]
        ctk.CTkLabel(
            mid, text=f"Issued {issued}",
            font=(FONT_FAMILY, 10),
            text_color=COLORS["text_muted"], anchor="w",
        ).pack(anchor="w", pady=(2, 0))

        # Right: actions
        right = ctk.CTkFrame(inner, fg_color="transparent")
        right.pack(side="right")

        file_path = cert.get("file_path")
        has_file = bool(file_path and os.path.exists(file_path))

        if has_file:
            self.primary_button(
                right, "Open PDF",
                command=lambda p=file_path: self._open(p),
                width=110, height=36,
            ).pack(side="left", padx=(0, PAD_SM))

            self.secondary_button(
                right, "Show folder",
                command=lambda p=file_path: self._reveal(p),
                width=120, height=36,
            ).pack(side="left")
        else:
            self.secondary_button(
                right, "Regenerate",
                command=lambda c=cert: self._regenerate(c),
                width=120, height=36,
            ).pack(side="left")

    # =========================================================
    # CATALOG
    # =========================================================

    def _render_catalog(self, parent):
        card = self.card(parent)
        card.pack(fill="x", pady=(0, PAD_MD))

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        grid = ctk.CTkFrame(body, fg_color="transparent")
        grid.pack(fill="x")

        for c in range(3):
            grid.grid_columnconfigure(c, weight=1, uniform="catalog")

        for i, cert_def in enumerate(CERTIFICATES):
            r, col = divmod(i, 3)

            item = ctk.CTkFrame(
                grid,
                fg_color=COLORS["surface_alt"],
                corner_radius=CARD_RADIUS,
                width=380, height=88)
            item.grid(row=r, column=col, padx=6, pady=6, sticky="nsew")
            item.pack_propagate(False)

            inner = ctk.CTkFrame(item, fg_color="transparent")
            inner.pack(fill="both", expand=True,
                       padx=PAD_MD, pady=PAD_MD)

            icon = CERT_ICONS.get(cert_def["id"], "📜")
            color = CERT_COLORS.get(cert_def["id"], COLORS["primary"])

            ctk.CTkLabel(
                inner, text=icon,
                font=(FONT_FAMILY, 24),
                text_color=color).pack(side="left", padx=(0, 10))

            text_box = ctk.CTkFrame(inner, fg_color="transparent")
            text_box.pack(side="left", fill="both", expand=True)

            ctk.CTkLabel(
                text_box, text=cert_def["name"],
                font=(FONT_FAMILY, 12, "bold"),
                text_color=COLORS["text"], anchor="w",
            ).pack(anchor="w")

            ctk.CTkLabel(
                text_box, text=cert_def["desc"],
                font=(FONT_FAMILY, 9),
                text_color=COLORS["text_muted"], anchor="w",
                wraplength=260, justify="left",
            ).pack(anchor="w", pady=(2, 0))

    # =========================================================
    # ACTIONS
    # =========================================================

    def _open(self, path: str):
        if not _open_file(path):
            self.toast("Could not open PDF", "error")
        else:
            self.toast("Opening certificate…", "info")

    def _reveal(self, path: str):
        if not _reveal_in_folder(path):
            self.toast("Could not open folder", "error")

    def _regenerate(self, cert):
        """Try to regenerate the certificate from utils.certificates."""
        uid = self.target["id"]
        ctype = cert["cert_type"]
        try:
            from utils.certificates import (
                certificate_academic_excellence,
                certificate_subject_topper,
                certificate_perfect_attendance,
                certificate_most_improved,
                certificate_all_rounder,
                certificate_activity_champion,
            )
        except Exception as e:
            self.toast(f"Regenerate failed: {e}", "error")
            return

        name = self.target.get("name", "")
        usn = self.target.get("usn") or uid

        try:
            # Get latest summary for context
            ms = self.db.get_marks_summary(uid)
            latest = ms.iloc[-1] if not ms.empty else None

            new_path = None
            if ctype == "academic_excellence" and latest is not None:
                new_path = certificate_academic_excellence(
                    uid, name, usn,
                    float(latest["percentage"]), latest["grade"], latest["zone"])
            elif ctype == "subject_topper":
                toppers = self.db.get_subject_toppers(ia_number=3)
                for subj, info in toppers.items():
                    if info and info["user_id"] == uid:
                        new_path = certificate_subject_topper(
                            uid, name, usn, subj, float(info["marks"]))
                        break
            elif ctype == "perfect_attendance":
                pct = self.db.attendance_percent(uid, days=30)
                new_path = certificate_perfect_attendance(uid, name, usn, pct)
            elif ctype == "most_improved":
                hist = self.db.get_color_history(uid)
                if len(hist) >= 2:
                    new_path = certificate_most_improved(
                        uid, name, usn,
                        float(hist.iloc[0]["percentage"]),
                        float(hist.iloc[-1]["percentage"]))
            elif ctype == "all_rounder" and latest is not None:
                new_path = certificate_all_rounder(
                    uid, name, usn,
                    {"Maths": float(latest["maths"]),
                     "Physics": float(latest["phy"]),
                     "Chemistry": float(latest["che"]),
                     "Computer Science": float(latest["cs"])})
            elif ctype == "activity_champion":
                acts = self.db.get_user_activities(uid)
                new_path = certificate_activity_champion(
                    uid, name, usn, len(acts))

            if new_path:
                # Update the DB row
                self.db.execute(
                    "UPDATE certificates SET file_path=? WHERE id=?",
                    (new_path, cert["id"]))
                self.toast("Certificate regenerated", "success")
                self.navigate("stu_certificates")
            else:
                self.toast("Cannot regenerate — criteria not met", "warning")
        except Exception as e:
            self.toast(f"Regenerate failed: {e}", "error")

    def _check_generate(self, uid):
        """Try generating any certificate the student qualifies for now."""
        try:
            from utils.certificates import generate_class_certificates
            results = generate_class_certificates(self.db, ia_number=3)
            # Filter this student's certs
            mine = 0
            for ctype, paths in results.items():
                for p in paths:
                    if f"_{uid}_" in p or p.startswith(os.path.join(
                            os.path.dirname(p), f"{uid}_")):
                        mine += 1
            if mine:
                self.toast(f"Generated {mine} certificate(s)!", "success")
                self.navigate("stu_certificates")
            else:
                self.toast("You don't meet the criteria yet — keep going!", "info")
        except Exception as e:
            self.toast(f"Could not check: {e}", "error")

    # =========================================================
    # HELPERS
    # =========================================================

    def _render_empty(self, msg):
        ctk.CTkLabel(
            self._content, text=msg,
            font=FONTS["h3"],
            text_color=COLORS["text_muted"]).pack(pady=60)


# =============================================================
# SANITY CHECK
# =============================================================

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")

    class _FakeApp:
        def __init__(self):
            self._user = None
            try:
                from database import get_db
                self.db = get_db()
                # pick a student who likely has certs
                for _, s in self.db.get_all_students().iterrows():
                    certs = self.db.get_user_certificates(s["id"])
                    if not certs.empty:
                        self._user = s.to_dict()
                        break
                if self._user is None:
                    self._user = self.db.get_all_students().iloc[0].to_dict()
            except Exception as e:
                print(f"(no DB: {e})")
                self.db = None

        @property
        def current_user(self):
            return self._user

        def show_page(self, key, **kw):
            print(f"[certs] → show_page('{key}')  args={kw}")

        def go_back(self):
            print("[certs] back")

        def logout(self):
            print("[certs] logout")

    root = ctk.CTk()
    W, H = 1280, 900
    root.geometry(f"{W}x{H}")
    root.configure(fg_color=COLORS["bg"])
    root.title(f"{APP_NAME} — certificates preview")

    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - W) // 2
    y = (sh - H) // 2
    root.geometry(f"{W}x{H}+{x}+{y}")

    app = _FakeApp()
    page = StudentCertificatesPage(root, app)
    page.pack(fill="both", expand=True)
    root.mainloop()
    print("\n✅ pages/student/certificates.py OK")