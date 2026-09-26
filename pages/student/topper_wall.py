# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  pages/student/topper_wall.py  ·  Public topper showcase
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
    APP_NAME, COLORS, STATUS, ZONE_COLORS, ZONE_LABELS,
    SUBJECTS, SUBJECT_COLORS, SUBJECT_SHORT,
    IA_LIST,
    FONTS, FONT_FAMILY,
    CARD_RADIUS, BUTTON_RADIUS, CHIP_RADIUS,
    PAD_SM, PAD_MD, PAD_LG, PAD_XL,
)
from pages.base_page import BasePage
from utils.avatars import load_avatar


# =============================================================
# HELPERS
# =============================================================

def _safe_str(v) -> str:
    try:
        if v is None:
            return ""
        if isinstance(v, float) and v != v:
            return ""
        return str(v)
    except Exception:
        return ""


def _safe_float(v, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        if isinstance(v, float) and v != v:
            return default
        return float(v)
    except Exception:
        return default


def _row_get(row, key: str, default=None):
    try:
        if key in row:
            v = row[key]
            if isinstance(v, float) and v != v:
                return default
            return v
        return default
    except Exception:
        return default


# =============================================================
# TOPPER WALL PAGE
# =============================================================

class StudentTopperWallPage(BasePage):

    def __init__(self, master, app):
        super().__init__(master, app)

        self.build_header(
            "Topper Wall",
            "Celebrating this term's top performers",
        )
        self.build_content(scrollable=True)
        self.build_footer()

        self._active_ia = 3
        self._tab_btns = {}

        self.render()

    # =========================================================
    # RENDER
    # =========================================================

    def render(self):
        content = self._content

        # IA tabs
        self._render_ia_tabs(content)

        # 1. Overall topper (big hero card)
        self.section_title("Overall Topper", parent=content)
        self._render_overall_topper(content)

        # 2. Subject toppers (4 cards in a grid)
        self.section_title("Subject Toppers", parent=content)
        self._render_subject_toppers(content)

        # 3. Class statistics
        self.section_title("Class Statistics", parent=content)
        self._render_class_stats(content)

    # =========================================================
    # IA TABS
    # =========================================================

    def _render_ia_tabs(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        ctk.CTkLabel(
            row, text="Showing toppers for:",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_muted"]).pack(side="left", padx=(0, 10))

        for ia in (1, 2, 3):
            label = f"IA-{ia}"
            btn = ctk.CTkButton(
                row, text=label, width=90, height=36,
                font=FONTS["small_bold"],
                fg_color=COLORS["primary"] if ia == self._active_ia
                         else COLORS["surface_alt"],
                hover_color=COLORS["surface_hi"],
                text_color=COLORS["text"],
                corner_radius=BUTTON_RADIUS,
                command=lambda i=ia: self._select_ia(i),
            )
            btn.pack(side="left", padx=(0, PAD_SM))
            self._tab_btns[ia] = btn

        self.secondary_button(
            row, "Refresh", command=self._reload,
            width=100, height=36,
        ).pack(side="right")

    def _select_ia(self, ia: int):
        self._active_ia = ia
        for i, btn in self._tab_btns.items():
            try:
                btn.configure(
                    fg_color=COLORS["primary"] if i == ia
                             else COLORS["surface_alt"])
            except Exception:
                pass
        self._reload()

    def _reload(self):
        for w in self._content.winfo_children():
            w.destroy()
        self.render()

    # =========================================================
    # OVERALL TOPPER
    # =========================================================

    def _render_overall_topper(self, parent):
        try:
            topper = self.db.get_overall_topper(ia_number=self._active_ia)
        except Exception:
            topper = None

        if not topper:
            ctk.CTkLabel(
                parent,
                text=f"No marks recorded for IA-{self._active_ia}.",
                font=FONTS["body"],
                text_color=COLORS["text_muted"]).pack(pady=20)
            return

        name = _safe_str(topper.get("name", "—")) or "—"
        usn = _safe_str(topper.get("usn")) or "—"
        uid = _safe_str(topper.get("user_id"))
        pct = _safe_float(topper.get("percentage"))
        grade = _safe_str(topper.get("grade", "—")) or "—"
        total = _safe_float(topper.get("total"))

        # Hero card
        card = ctk.CTkFrame(
            parent,
            fg_color=COLORS["surface"],
            corner_radius=CARD_RADIUS,
            border_width=2,
            border_color=STATUS["gold"])
        card.pack(fill="x", pady=(0, PAD_MD))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=PAD_XL, pady=PAD_XL)

        # Left: big avatar
        try:
            avatar = load_avatar(
                user_id=uid,
                name=name,
                size=140,
                shape="circle",
                zone="gold",
                ring_width=8,
            )
            ctk.CTkLabel(inner, image=avatar, text="").pack(side="left")
        except Exception:
            pass

        # Middle: info
        mid = ctk.CTkFrame(inner, fg_color="transparent")
        mid.pack(side="left", padx=(PAD_XL, 0), fill="both", expand=True)

        ctk.CTkLabel(
            mid, text="🥇  Overall Topper",
            font=(FONT_FAMILY, 12, "bold"),
            text_color=STATUS["gold"]).pack(anchor="w")

        ctk.CTkLabel(
            mid, text=name,
            font=(FONT_FAMILY, 28, "bold"),
            text_color=COLORS["text"]).pack(anchor="w", pady=(4, 2))

        ctk.CTkLabel(
            mid, text=usn,
            font=FONTS["small"],
            text_color=COLORS["text_muted"]).pack(anchor="w")

        # Big % row
        stats_row = ctk.CTkFrame(mid, fg_color="transparent")
        stats_row.pack(anchor="w", pady=(14, 0))

        pct_box = ctk.CTkFrame(
            stats_row, fg_color=STATUS["gold"],
            corner_radius=CHIP_RADIUS)
        pct_box.pack(side="left", padx=(0, 10))
        ctk.CTkLabel(
            pct_box, text=f"  {pct:.2f}%  ",
            font=(FONT_FAMILY, 14, "bold"),
            text_color="#FFFFFF").pack(padx=6, pady=5)

        grade_box = ctk.CTkFrame(
            stats_row, fg_color=COLORS["surface_alt"],
            corner_radius=CHIP_RADIUS)
        grade_box.pack(side="left", padx=(0, 10))
        ctk.CTkLabel(
            grade_box, text=f"  Grade {grade}  ",
            font=(FONT_FAMILY, 12, "bold"),
            text_color=COLORS["text"]).pack(padx=6, pady=5)

        total_box = ctk.CTkFrame(
            stats_row, fg_color=COLORS["surface_alt"],
            corner_radius=CHIP_RADIUS)
        total_box.pack(side="left")
        ctk.CTkLabel(
            total_box, text=f"  Total {int(total)}/400  ",
            font=(FONT_FAMILY, 12, "bold"),
            text_color=COLORS["text"]).pack(padx=6, pady=5)

    # =========================================================
    # SUBJECT TOPPERS
    # =========================================================

    def _render_subject_toppers(self, parent):
        try:
            toppers = self.db.get_subject_toppers(ia_number=self._active_ia)
        except Exception:
            toppers = {}

        grid = ctk.CTkFrame(parent, fg_color="transparent")
        grid.pack(fill="x", pady=(0, PAD_MD))

        per_row = 4
        for c in range(per_row):
            grid.grid_columnconfigure(c, weight=1, uniform="subtopper")

        for i, subj in enumerate(SUBJECTS):
            info = toppers.get(subj)
            r, col = divmod(i, per_row)
            self._render_subject_card(grid, subj, info, row=r, col=col)

    def _render_subject_card(self, parent, subject: str, info, row: int, col: int):
        color = SUBJECT_COLORS.get(subject, COLORS["primary"])

        card = ctk.CTkFrame(
            parent,
            fg_color=COLORS["surface"],
            corner_radius=CARD_RADIUS,
            border_width=2,
            border_color=color,
            width=280, height=280)
        card.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")
        card.pack_propagate(False)

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="both", expand=True,
                  padx=PAD_LG, pady=PAD_LG)

        # Subject chip top
        chip = ctk.CTkFrame(body, fg_color=color,
                            corner_radius=CHIP_RADIUS)
        chip.pack()
        ctk.CTkLabel(
            chip,
            text=f"  {SUBJECT_SHORT.get(subject, subject)}  ",
            font=(FONT_FAMILY, 10, "bold"),
            text_color="#FFFFFF").pack(padx=6, pady=3)

        if not info:
            ctk.CTkLabel(
                body, text="No data",
                font=FONTS["small"],
                text_color=COLORS["text_muted"]).pack(pady=40)
            return

        name = _safe_str(info.get("name", "—")) or "—"
        usn = _safe_str(info.get("usn")) or "—"
        uid = _safe_str(info.get("user_id"))
        marks = _safe_float(info.get("marks"))

        try:
            avatar = load_avatar(
                user_id=uid,
                name=name,
                size=76,
                shape="circle",
            )
            ctk.CTkLabel(body, image=avatar, text="").pack(pady=(12, 6))
        except Exception:
            pass

        ctk.CTkLabel(
            body, text=name,
            font=(FONT_FAMILY, 13, "bold"),
            text_color=COLORS["text"],
            wraplength=240, justify="center").pack()

        ctk.CTkLabel(
            body, text=usn,
            font=(FONT_FAMILY, 9),
            text_color=COLORS["text_muted"]).pack(pady=(2, 8))

        # Big marks
        ctk.CTkLabel(
            body, text=f"{marks:.0f}",
            font=(FONT_FAMILY, 26, "bold"),
            text_color=color).pack()

        ctk.CTkLabel(
            body, text="marks",
            font=(FONT_FAMILY, 9),
            text_color=COLORS["text_muted"]).pack()

    # =========================================================
    # CLASS STATS
    # =========================================================

    def _render_class_stats(self, parent):
        try:
            avgs = self.db.class_subject_averages(
                ia_number=self._active_ia)
            zones = self.db.class_zone_counts(ia_number=self._active_ia)
        except Exception:
            avgs, zones = {}, {}

        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        # Avg per subject
        for subj in SUBJECTS:
            v = _safe_float(avgs.get(subj, 0))
            self.stat_card(
                row, f"{v:.1f}", f"{SUBJECT_SHORT.get(subj, subj)} avg",
                accent=SUBJECT_COLORS.get(subj, COLORS["primary"]),
                icon="📊",
            ).pack(side="left", padx=(0, PAD_MD))

        # Zone counts
        zone_row = ctk.CTkFrame(parent, fg_color="transparent")
        zone_row.pack(fill="x", pady=(PAD_MD, 0))

        for zone in ("red", "yellow", "green", "gold"):
            count = int(zones.get(zone, 0))
            color = ZONE_COLORS.get(zone, COLORS["primary"])
            label = ZONE_LABELS.get(zone, zone.title())
            icon = {"red": "🔴", "yellow": "🟡",
                    "green": "🟢", "gold": "🏆"}.get(zone, "•")

            card = ctk.CTkFrame(
                zone_row,
                fg_color=COLORS["surface"],
                corner_radius=CARD_RADIUS,
                border_width=1,
                border_color=color,
                width=180, height=90)
            card.pack(side="left", padx=(0, PAD_MD))
            card.pack_propagate(False)

            body = ctk.CTkFrame(card, fg_color="transparent")
            body.pack(expand=True)

            ctk.CTkLabel(
                body, text=f"{icon}  {count}",
                font=(FONT_FAMILY, 22, "bold"),
                text_color=color).pack()
            ctk.CTkLabel(
                body, text=label,
                font=(FONT_FAMILY, 10),
                text_color=COLORS["text_muted"]).pack()

        # Total students
        total_students = sum(int(zones.get(z, 0))
                             for z in ("red", "yellow", "green", "gold"))
        total_card = ctk.CTkFrame(
            zone_row,
            fg_color=COLORS["surface"],
            corner_radius=CARD_RADIUS,
            border_width=1,
            border_color=COLORS["border_soft"],
            width=180, height=90)
        total_card.pack(side="left")
        total_card.pack_propagate(False)

        tbody = ctk.CTkFrame(total_card, fg_color="transparent")
        tbody.pack(expand=True)
        ctk.CTkLabel(
            tbody, text=f"👥  {total_students}",
            font=(FONT_FAMILY, 22, "bold"),
            text_color=COLORS["text"]).pack()
        ctk.CTkLabel(
            tbody, text="Total students",
            font=(FONT_FAMILY, 10),
            text_color=COLORS["text_muted"]).pack()


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
                stu = self.db.get_all_students().iloc[0]
                self._user = stu.to_dict()
            except Exception as e:
                print(f"(no DB: {e})")
                self.db = None

        @property
        def current_user(self):
            return self._user

        def show_page(self, key, **kw):
            print(f"[topper_wall] → show_page('{key}')  args={kw}")

        def go_back(self):
            print("[topper_wall] back")

        def logout(self):
            print("[topper_wall] logout")

    root = ctk.CTk()
    W, H = 1280, 900
    root.geometry(f"{W}x{H}")
    root.configure(fg_color=COLORS["bg"])
    root.title(f"{APP_NAME} — topper wall preview")

    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - W) // 2
    y = (sh - H) // 2
    root.geometry(f"{W}x{H}+{x}+{y}")

    app = _FakeApp()
    page = StudentTopperWallPage(root, app)
    page.pack(fill="both", expand=True)
    root.mainloop()
    print("\n✅ pages/student/topper_wall.py OK")