# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  pages/student/leaderboard.py  ·  Class leaderboard
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
    IA_LIST, IA_COLORS,
    FONTS, FONT_FAMILY,
    CARD_RADIUS, BUTTON_RADIUS, CHIP_RADIUS,
    PAD_SM, PAD_MD, PAD_LG, PAD_XL,
)
from pages.base_page import BasePage
from utils.avatars import load_avatar


# =============================================================
# HELPERS
# =============================================================

MEDAL_ICONS = {1: "🥇", 2: "🥈", 3: "🥉"}

MEDAL_COLORS = {
    1: "#FBBF24",   # gold
    2: "#C0C0C0",   # silver
    3: "#CD7F32",   # bronze
}


def _safe_str(v) -> str:
    """Convert any value (including NaN) to a clean string."""
    try:
        if v is None:
            return ""
        # pandas NaN check without importing pandas
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
    """Safely read a value from a pandas Series row."""
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
# LEADERBOARD PAGE
# =============================================================

class StudentLeaderboardPage(BasePage):

    def __init__(self, master, app):
        super().__init__(master, app)

        self.build_header(
            "Leaderboard",
            "Where everyone stands this term",
        )
        self.build_content(scrollable=True)
        self.build_footer()

        self._active_ia = 3
        self._tab_btns = {}
        self._list_container = None

        self.render()

    # =========================================================
    # RENDER
    # =========================================================

    def render(self):
        content = self._content
        uid = _safe_str((self.user or {}).get("id"))

        # 1. IA Tabs
        self._render_ia_tabs(content)

        # 2. Top 3 podium
        self.section_title("Top Performers", parent=content)
        self._render_podium(content)

        # 3. Full ranking list
        self.section_title("Full Ranking", parent=content)
        self._list_container = ctk.CTkFrame(content, fg_color="transparent")
        self._list_container.pack(fill="x", pady=(0, PAD_MD))
        self._render_list(uid)

    # =========================================================
    # IA TABS
    # =========================================================

    def _render_ia_tabs(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        ctk.CTkLabel(
            row, text="View:",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_muted"]).pack(side="left", padx=(0, 10))

        for ia in (1, 2, 3):
            label = f"IA-{ia}"
            btn = ctk.CTkButton(
                row, text=label, width=90, height=36,
                font=FONTS["small_bold"],
                fg_color=IA_COLORS.get(label, COLORS["primary"])
                         if ia == self._active_ia
                         else COLORS["surface_alt"],
                hover_color=COLORS["surface_hi"],
                text_color=COLORS["text"],
                corner_radius=BUTTON_RADIUS,
                command=lambda i=ia: self._select_ia(i),
            )
            btn.pack(side="left", padx=(0, PAD_SM))
            self._tab_btns[ia] = btn

        self.secondary_button(
            row, "Refresh",
            command=self._reload,
            width=100, height=36,
        ).pack(side="right")

    def _select_ia(self, ia: int):
        self._active_ia = ia
        for i, btn in self._tab_btns.items():
            try:
                btn.configure(
                    fg_color=IA_COLORS.get(f"IA-{i}", COLORS["primary"])
                             if i == ia
                             else COLORS["surface_alt"])
            except Exception:
                pass
        self._reload()

    def _reload(self):
        for w in self._content.winfo_children():
            w.destroy()
        self.render()

    # =========================================================
    # PODIUM
    # =========================================================

    def _render_podium(self, parent):
        try:
            rows = self.db.get_class_marks_summary(ia_number=self._active_ia)
        except Exception:
            rows = None

        if rows is None or rows.empty:
            ctk.CTkLabel(
                parent,
                text=f"No marks recorded for IA-{self._active_ia}.",
                font=FONTS["body"],
                text_color=COLORS["text_muted"]).pack(pady=16)
            return

        top = rows.head(3)
        podium = ctk.CTkFrame(parent, fg_color="transparent")
        podium.pack(fill="x", pady=(0, PAD_MD))

        for c in range(3):
            podium.grid_columnconfigure(c, weight=1, uniform="podium")

        for i, (_, s) in enumerate(top.iterrows(), start=1):
            self._render_podium_card(podium, s, rank=i, col=i - 1)

    def _render_podium_card(self, parent, s, rank: int, col: int):
        medal = MEDAL_ICONS.get(rank, "•")
        color = MEDAL_COLORS.get(rank, COLORS["primary"])

        card = ctk.CTkFrame(
            parent,
            fg_color=COLORS["surface"],
            corner_radius=CARD_RADIUS,
            border_width=2,
            border_color=color,
            width=360, height=230)
        card.grid(row=0, column=col, padx=8, pady=6, sticky="nsew")
        card.pack_propagate(False)

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="both", expand=True,
                  padx=PAD_LG, pady=PAD_LG)

        ctk.CTkLabel(
            body, text=medal,
            font=(FONT_FAMILY, 34),
        ).pack(pady=(0, 4))

        user_id = _safe_str(_row_get(s, "user_id"))
        name = _safe_str(_row_get(s, "name", "—")) or "—"
        usn = _safe_str(_row_get(s, "usn"))
        pct = _safe_float(_row_get(s, "percentage"))
        grade = _safe_str(_row_get(s, "grade", "—")) or "—"
        zone = _safe_str(_row_get(s, "zone", "yellow")) or "yellow"

        try:
            avatar = load_avatar(
                user_id=user_id,
                name=name,
                size=72,
                shape="circle",
                zone=zone,
                ring_width=5 if zone else 0,
            )
            ctk.CTkLabel(body, image=avatar, text="").pack()
        except Exception:
            pass

        ctk.CTkLabel(
            body, text=name,
            font=(FONT_FAMILY, 14, "bold"),
            text_color=COLORS["text"],
            wraplength=300, justify="center",
        ).pack(pady=(8, 0))

        ctk.CTkLabel(
            body, text=usn,
            font=(FONT_FAMILY, 9),
            text_color=COLORS["text_muted"]).pack()

        ctk.CTkLabel(
            body, text=f"{pct:.2f}%",
            font=(FONT_FAMILY, 22, "bold"),
            text_color=color).pack(pady=(6, 0))

        zone_color = ZONE_COLORS.get(zone, COLORS["primary"])
        zone_label = ZONE_LABELS.get(zone, zone.title())

        meta = ctk.CTkFrame(body, fg_color="transparent")
        meta.pack(pady=(4, 0))

        grade_chip = ctk.CTkFrame(
            meta, fg_color=COLORS["surface_alt"],
            corner_radius=CHIP_RADIUS)
        grade_chip.pack(side="left", padx=(0, 6))
        ctk.CTkLabel(
            grade_chip, text=f"  Grade {grade}  ",
            font=(FONT_FAMILY, 9, "bold"),
            text_color=COLORS["text"]).pack(padx=2, pady=2)

        zone_chip = ctk.CTkFrame(
            meta, fg_color=zone_color,
            corner_radius=CHIP_RADIUS)
        zone_chip.pack(side="left")
        ctk.CTkLabel(
            zone_chip, text=f"  {zone_label}  ",
            font=(FONT_FAMILY, 9, "bold"),
            text_color="#FFFFFF").pack(padx=2, pady=2)

    # =========================================================
    # FULL LIST
    # =========================================================

    def _render_list(self, current_uid):
        for w in self._list_container.winfo_children():
            w.destroy()

        try:
            rows = self.db.get_class_marks_summary(ia_number=self._active_ia)
        except Exception:
            rows = None

        if rows is None or rows.empty:
            ctk.CTkLabel(
                self._list_container,
                text="No data available for this IA.",
                font=FONTS["body"],
                text_color=COLORS["text_muted"]).pack(pady=20)
            return

        # Header row
        header = ctk.CTkFrame(self._list_container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 4))

        headers = [
            ("Rank", 80),
            ("Student", 320),
            ("USN", 180),
            ("%", 100),
            ("Grade", 100),
            ("Zone", 140),
        ]
        for label, w in headers:
            ctk.CTkLabel(
                header, text=label, width=w, anchor="w",
                font=(FONT_FAMILY, 11, "bold"),
                text_color=COLORS["text_muted"]).pack(side="left")

        # Rows — safe scalar comparison, no pandas Series leakage
        current_uid_str = _safe_str(current_uid)
        for rank, (_, s) in enumerate(rows.iterrows(), start=1):
            is_me = (_safe_str(_row_get(s, "user_id")) == current_uid_str)
            self._render_rank_row(s, rank=rank, is_me=bool(is_me))

    def _render_rank_row(self, s, rank: int, is_me: bool):
        is_me = bool(is_me)   # guard against any non-bool truthy value

        row_color = COLORS["surface_hi"] if is_me else COLORS["surface"]
        border_color = COLORS["primary"] if is_me else COLORS["border_soft"]

        row = ctk.CTkFrame(
            self._list_container,
            fg_color=row_color,
            corner_radius=10,
            border_width=1,
            border_color=border_color)
        row.pack(fill="x", pady=2)

        inner = ctk.CTkFrame(row, fg_color="transparent")
        inner.pack(fill="x", padx=10, pady=8)

        # Rank
        medal = MEDAL_ICONS.get(rank, "")
        rank_txt = f"{medal}  {rank}" if medal else f"     {rank}"
        ctk.CTkLabel(
            inner, text=rank_txt, width=80, anchor="w",
            font=(FONT_FAMILY, 12, "bold"),
            text_color=MEDAL_COLORS.get(rank, COLORS["text"]),
        ).pack(side="left")

        # Avatar + name
        student_box = ctk.CTkFrame(inner, fg_color="transparent",
                                   width=320)
        student_box.pack(side="left")
        student_box.pack_propagate(False)

        user_id = _safe_str(_row_get(s, "user_id"))
        name = _safe_str(_row_get(s, "name", "—")) or "—"
        usn = _safe_str(_row_get(s, "usn")) or "—"
        pct = _safe_float(_row_get(s, "percentage"))
        grade = _safe_str(_row_get(s, "grade", "—")) or "—"
        zone = _safe_str(_row_get(s, "zone", "yellow")) or "yellow"

        try:
            avatar = load_avatar(
                user_id=user_id,
                name=name,
                size=32, shape="circle",
            )
            ctk.CTkLabel(student_box, image=avatar, text="").pack(
                side="left", padx=(0, 8))
        except Exception:
            pass

        name_txt = name + ("  (You)" if is_me else "")

        ctk.CTkLabel(
            student_box, text=name_txt,
            font=(FONT_FAMILY, 11, "bold" if is_me else "normal"),
            text_color=COLORS["text"],
            anchor="w",
        ).pack(side="left")

        # USN
        ctk.CTkLabel(
            inner, text=usn, width=180, anchor="w",
            font=(FONT_FAMILY, 10),
            text_color=COLORS["text_muted"],
        ).pack(side="left")

        # %
        pct_color = STATUS["green"] if pct >= 75 else \
                    (STATUS["amber"] if pct >= 50 else STATUS["red"])
        ctk.CTkLabel(
            inner, text=f"{pct:.2f}%", width=100, anchor="w",
            font=(FONT_FAMILY, 12, "bold"),
            text_color=pct_color,
        ).pack(side="left")

        # Grade
        ctk.CTkLabel(
            inner, text=grade, width=100, anchor="w",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text"],
        ).pack(side="left")

        # Zone chip
        zone_color = ZONE_COLORS.get(zone, COLORS["primary"])
        zone_label = ZONE_LABELS.get(zone, zone.title())

        zone_box = ctk.CTkFrame(inner, fg_color="transparent", width=140)
        zone_box.pack(side="left")
        zone_box.pack_propagate(False)

        chip = ctk.CTkFrame(
            zone_box, fg_color=zone_color,
            corner_radius=CHIP_RADIUS)
        chip.pack(side="left")
        ctk.CTkLabel(
            chip, text=f"  {zone_label}  ",
            font=(FONT_FAMILY, 9, "bold"),
            text_color="#FFFFFF").pack(padx=2, pady=2)


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
            print(f"[leaderboard] → show_page('{key}')  args={kw}")

        def go_back(self):
            print("[leaderboard] back")

        def logout(self):
            print("[leaderboard] logout")

    root = ctk.CTk()
    W, H = 1280, 900
    root.geometry(f"{W}x{H}")
    root.configure(fg_color=COLORS["bg"])
    root.title(f"{APP_NAME} — leaderboard preview")

    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - W) // 2
    y = (sh - H) // 2
    root.geometry(f"{W}x{H}+{x}+{y}")

    app = _FakeApp()
    page = StudentLeaderboardPage(root, app)
    page.pack(fill="both", expand=True)
    root.mainloop()
    print("\n✅ pages/student/leaderboard.py OK")