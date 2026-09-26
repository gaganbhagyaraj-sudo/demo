# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  pages/facilitator/class_roster.py  ·  Class roster grid
# =============================================================

from __future__ import annotations

import os
import sys

# --- make project root importable ---
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import customtkinter as ctk
import pandas as pd

from config import (
    APP_NAME, COLORS, STATUS, ZONE_COLORS, ZONE_LABELS,
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


def _facilitator_nav():
    return [
        {"key": "fac_command",      "label": "Command Center", "icon": "🎛️"},
        {"key": "fac_roster",       "label": "Class Roster",   "icon": "👥"},
        {"key": "fac_alerts",       "label": "Alerts",         "icon": "🔔"},
        {"key": "fac_marks",        "label": "Marks Analysis", "icon": "📊"},
        {"key": "fac_attendance",   "label": "Attendance",     "icon": "📅"},
        {"key": "fac_heatmap",      "label": "Heatmap",        "icon": "🔥"},
        {"key": "fac_remedial",     "label": "Remedial",       "icon": "🩺"},
        {"key": "fac_interventions","label": "Interventions",  "icon": "🛠️"},
        {"key": "fac_badges",       "label": "Badges",         "icon": "🏅"},
        {"key": "fac_reports",      "label": "Reports",        "icon": "📄"},
    ]


# =============================================================
# CLASS ROSTER PAGE
# =============================================================

class FacilitatorClassRosterPage(BasePage):

    def __init__(self, master, app):
        super().__init__(master, app)

        self.build_header("Class Roster",
                          "All students in one place", back=False)
        self.build_sidebar(self._build_nav_items())
        self.build_content(scrollable=True)
        self.build_footer()

        # State
        self._sort_by = "percentage_desc"
        self._filter_zone = "all"
        self._search_text = ""
        self._cards_container = None
        self._sort_btns = {}
        self._filter_btns = {}
        self._search_entry = None

        self.render()

    def _build_nav_items(self):
        items = _facilitator_nav()
        for it in items:
            if it["key"] == "fac_roster":
                it["active"] = True
                it["command"] = lambda: None
            else:
                it["command"] = (lambda k=it["key"]: self.navigate(k))
        return items

    # =========================================================
    # RENDER
    # =========================================================

    def render(self):
        content = self._content

        # Load students + marks
        self._load_students()

        # 1. Top stats
        self._render_top_stats(content)

        # 2. Controls row: search + sort + filter
        self.section_title("Search & Filter", parent=content)
        self._render_controls(content)

        # 3. Grid container
        self.section_title("Students", parent=content)
        self._cards_container = ctk.CTkFrame(content, fg_color="transparent")
        self._cards_container.pack(fill="x", pady=(0, PAD_MD))

        # 4. Draw the grid
        self._render_grid()

    # =========================================================
    # LOAD DATA
    # =========================================================

    def _load_students(self):
        # All students
        try:
            self._students = self.db.get_all_students()
        except Exception:
            self._students = pd.DataFrame()

        # Latest IA per student
        try:
            ia_df = self.db.query(
                "SELECT MAX(ia_number) AS ia FROM marks_summary")
            self._latest_ia = int(ia_df.iloc[0]["ia"] or 3)
        except Exception:
            self._latest_ia = 3

        # Marks summary (latest IA)
        try:
            self._marks = self.db.get_class_marks_summary(
                ia_number=self._latest_ia)
        except Exception:
            self._marks = pd.DataFrame()

        # Attendance summary
        try:
            att = self.db.get_class_attendance_summary(days=45)
            self._attendance = att
        except Exception:
            self._attendance = pd.DataFrame()

        # Build merged data
        rows = []
        marks_lookup = {}
        if self._marks is not None and not self._marks.empty:
            for _, m in self._marks.iterrows():
                marks_lookup[_safe_str(m.get("user_id"))] = m

        att_lookup = {}
        if self._attendance is not None and not self._attendance.empty:
            for _, a in self._attendance.iterrows():
                uid = _safe_str(a.get("user_id"))
                present = _safe_float(a.get("present"))
                total = _safe_float(a.get("total"))
                pct = (present / total * 100) if total else 0
                att_lookup[uid] = pct

        if self._students is not None and not self._students.empty:
            for _, s in self._students.iterrows():
                uid = _safe_str(s.get("id"))
                m = marks_lookup.get(uid)
                pct = _safe_float(m.get("percentage")) if m is not None else 0.0
                zone = _safe_str(m.get("zone")) if m is not None else ""
                grade = _safe_str(m.get("grade")) if m is not None else ""
                att = att_lookup.get(uid, 0.0)

                rows.append({
                    "id": uid,
                    "usn": _safe_str(s.get("usn")),
                    "name": _safe_str(s.get("name")) or "—",
                    "grade": _safe_str(s.get("grade")),
                    "section": _safe_str(s.get("section")),
                    "percentage": pct,
                    "zone": zone,
                    "grade_letter": grade,
                    "attendance": att,
                })

        self._data = pd.DataFrame(rows)

    # =========================================================
    # TOP STATS
    # =========================================================

    def _render_top_stats(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        total = len(self._data)

        # Zone counts
        zones = self._data["zone"].value_counts().to_dict() \
            if not self._data.empty else {}

        red = zones.get("red", 0)
        yellow = zones.get("yellow", 0)
        green = zones.get("green", 0)
        gold = zones.get("gold", 0)

        self.stat_card(
            row, total, "Total students",
            accent=COLORS["primary"], icon="👥",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, red, "🔴 At Risk",
            accent=STATUS["red"], icon="⚠️",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, yellow, "🟡 Developing",
            accent=STATUS["amber"], icon="⚡",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, green, "🟢 Strong",
            accent=STATUS["green"], icon="✅",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, gold, "🏆 Achievers",
            accent=STATUS["gold"], icon="🏆",
        ).pack(side="left")

    # =========================================================
    # CONTROLS
    # =========================================================

    def _render_controls(self, parent):
        card = self.card(parent)
        card.pack(fill="x", pady=(0, PAD_MD))

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        # Row 1: Search
        search_row = ctk.CTkFrame(body, fg_color="transparent")
        search_row.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            search_row, text="🔍  Search:",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_muted"]).pack(side="left", padx=(0, 8))

        self._search_entry = ctk.CTkEntry(
            search_row, width=340, height=36,
            font=FONTS["small"],
            fg_color=COLORS["surface_alt"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            corner_radius=10,
            placeholder_text="Search by name or USN…")
        self._search_entry.pack(side="left")
        self._search_entry.bind("<KeyRelease>", self._on_search_change)

        self.secondary_button(
            search_row, "Clear",
            command=self._clear_search,
            width=90, height=36,
        ).pack(side="left", padx=(PAD_SM, 0))

        # Row 2: Sort
        sort_row = ctk.CTkFrame(body, fg_color="transparent")
        sort_row.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            sort_row, text="Sort by:",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_muted"]).pack(side="left", padx=(0, 8))

        sorts = [
            ("percentage_desc", "Marks ↓"),
            ("percentage_asc", "Marks ↑"),
            ("attendance_desc", "Attendance ↓"),
            ("name_asc", "Name A-Z"),
            ("usn_asc", "USN"),
        ]
        for key, label in sorts:
            is_active = (self._sort_by == key)
            btn = ctk.CTkButton(
                sort_row, text=label, width=110, height=34,
                font=(FONT_FAMILY, 10),
                fg_color=COLORS["primary"] if is_active
                         else COLORS["surface_alt"],
                hover_color=COLORS["surface_hi"],
                text_color=COLORS["text"],
                corner_radius=BUTTON_RADIUS,
                command=lambda k=key: self._set_sort(k),
            )
            btn.pack(side="left", padx=(0, PAD_SM))
            self._sort_btns[key] = btn

        # Row 3: Filter by zone
        filter_row = ctk.CTkFrame(body, fg_color="transparent")
        filter_row.pack(fill="x")

        ctk.CTkLabel(
            filter_row, text="Zone:",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_muted"]).pack(side="left", padx=(0, 8))

        filters = [
            ("all", "All"),
            ("red", "🔴 At Risk"),
            ("yellow", "🟡 Developing"),
            ("green", "🟢 Strong"),
            ("gold", "🏆 Achievers"),
        ]
        for key, label in filters:
            is_active = (self._filter_zone == key)
            btn = ctk.CTkButton(
                filter_row, text=label, width=120, height=34,
                font=(FONT_FAMILY, 10),
                fg_color=COLORS["primary"] if is_active
                         else COLORS["surface_alt"],
                hover_color=COLORS["surface_hi"],
                text_color=COLORS["text"],
                corner_radius=BUTTON_RADIUS,
                command=lambda k=key: self._set_filter(k),
            )
            btn.pack(side="left", padx=(0, PAD_SM))
            self._filter_btns[key] = btn

    def _on_search_change(self, event=None):
        try:
            self._search_text = (self._search_entry.get() or "").strip().lower()
        except Exception:
            self._search_text = ""
        self._render_grid()

    def _clear_search(self):
        try:
            self._search_entry.delete(0, "end")
        except Exception:
            pass
        self._search_text = ""
        self._render_grid()

    def _set_sort(self, key: str):
        self._sort_by = key
        for k, b in self._sort_btns.items():
            try:
                b.configure(fg_color=COLORS["primary"] if k == key
                            else COLORS["surface_alt"])
            except Exception:
                pass
        self._render_grid()

    def _set_filter(self, key: str):
        self._filter_zone = key
        for k, b in self._filter_btns.items():
            try:
                b.configure(fg_color=COLORS["primary"] if k == key
                            else COLORS["surface_alt"])
            except Exception:
                pass
        self._render_grid()

    # =========================================================
    # GRID
    # =========================================================

    def _render_grid(self):
        for w in self._cards_container.winfo_children():
            w.destroy()

        df = self._data.copy() if self._data is not None else pd.DataFrame()

        if df.empty:
            ctk.CTkLabel(
                self._cards_container,
                text="No students found.",
                font=FONTS["body"],
                text_color=COLORS["text_muted"]).pack(pady=20)
            return

        # Filter
        if self._filter_zone != "all":
            df = df[df["zone"] == self._filter_zone]

        # Search
        if self._search_text:
            q = self._search_text
            mask = df.apply(
                lambda r: q in _safe_str(r.get("name")).lower()
                or q in _safe_str(r.get("usn")).lower(),
                axis=1)
            df = df[mask]

        # Sort
        if self._sort_by == "percentage_desc":
            df = df.sort_values("percentage", ascending=False)
        elif self._sort_by == "percentage_asc":
            df = df.sort_values("percentage", ascending=True)
        elif self._sort_by == "attendance_desc":
            df = df.sort_values("attendance", ascending=False)
        elif self._sort_by == "name_asc":
            df = df.sort_values("name", ascending=True)
        elif self._sort_by == "usn_asc":
            df = df.sort_values("usn", ascending=True)

        if df.empty:
            ctk.CTkLabel(
                self._cards_container,
                text="No students match your filters.",
                font=FONTS["body"],
                text_color=COLORS["text_muted"]).pack(pady=20)
            return

        # Count label
        ctk.CTkLabel(
            self._cards_container,
            text=f"Showing {len(df)} of {len(self._data)} students",
            font=FONTS["tiny"],
            text_color=COLORS["text_muted"],
        ).pack(anchor="w", pady=(0, PAD_SM))

        # Grid
        grid = ctk.CTkFrame(self._cards_container, fg_color="transparent")
        grid.pack(fill="x")

        per_row = 4
        for c in range(per_row):
            grid.grid_columnconfigure(c, weight=1, uniform="stucard")

        for i, (_, s) in enumerate(df.iterrows()):
            r, col = divmod(i, per_row)
            self._render_student_card(grid, s, row=r, col=col)

    # =========================================================
    # STUDENT CARD
    # =========================================================

    def _render_student_card(self, parent, s, row: int, col: int):
        uid = _safe_str(s.get("id"))
        name = _safe_str(s.get("name")) or "—"
        usn = _safe_str(s.get("usn")) or "—"
        pct = _safe_float(s.get("percentage"))
        zone = _safe_str(s.get("zone")) or "yellow"
        att = _safe_float(s.get("attendance"))

        zone_color = ZONE_COLORS.get(zone, COLORS["primary"])
        zone_label = ZONE_LABELS.get(zone, zone.title())

        # Card
        card = ctk.CTkFrame(
            parent,
            fg_color=COLORS["surface"],
            corner_radius=CARD_RADIUS,
            border_width=2,
            border_color=zone_color,
            width=280, height=220)
        card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
        card.pack_propagate(False)

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="both", expand=True,
                  padx=PAD_LG, pady=PAD_MD)

        # Avatar with zone ring
        try:
            avatar = load_avatar(
                user_id=uid,
                name=name,
                size=64,
                shape="circle",
                zone=zone,
                ring_width=5,
            )
            ctk.CTkLabel(body, image=avatar, text="").pack(pady=(0, 6))
        except Exception:
            pass

        # Name
        ctk.CTkLabel(
            body, text=name,
            font=(FONT_FAMILY, 13, "bold"),
            text_color=COLORS["text"],
            wraplength=240, justify="center",
        ).pack()

        # USN
        ctk.CTkLabel(
            body, text=usn,
            font=(FONT_FAMILY, 9),
            text_color=COLORS["text_muted"]).pack(pady=(2, 8))

        # Stats row
        stats = ctk.CTkFrame(body, fg_color="transparent")
        stats.pack(fill="x", pady=(4, 8))

        # Percentage
        pct_box = ctk.CTkFrame(stats, fg_color="transparent")
        pct_box.pack(side="left", expand=True)
        ctk.CTkLabel(
            pct_box, text=f"{pct:.1f}%",
            font=(FONT_FAMILY, 14, "bold"),
            text_color=zone_color).pack()
        ctk.CTkLabel(
            pct_box, text="Marks",
            font=(FONT_FAMILY, 8),
            text_color=COLORS["text_muted"]).pack()

        # Attendance
        att_box = ctk.CTkFrame(stats, fg_color="transparent")
        att_box.pack(side="left", expand=True)
        att_color = STATUS["green"] if att >= 85 else \
                    (STATUS["amber"] if att >= 70 else STATUS["red"])
        ctk.CTkLabel(
            att_box, text=f"{att:.0f}%",
            font=(FONT_FAMILY, 14, "bold"),
            text_color=att_color).pack()
        ctk.CTkLabel(
            att_box, text="Attend.",
            font=(FONT_FAMILY, 8),
            text_color=COLORS["text_muted"]).pack()

        # Zone chip
        chip = ctk.CTkFrame(body, fg_color=zone_color,
                            corner_radius=CHIP_RADIUS)
        chip.pack()
        ctk.CTkLabel(
            chip, text=f"  {zone_label}  ",
            font=(FONT_FAMILY, 9, "bold"),
            text_color="#FFFFFF").pack(padx=4, pady=3)

        # Hover + click
        def _enter(_, c=card, zc=zone_color):
            try:
                c.configure(fg_color=COLORS["surface_alt"],
                            border_width=3)
            except Exception:
                pass

        def _leave(_, c=card):
            try:
                c.configure(fg_color=COLORS["surface"],
                            border_width=2)
            except Exception:
                pass

        def _click(_, u=uid):
            self.navigate("fac_deepdive", user_id=u)

        for w in (card, body):
            w.bind("<Enter>", _enter)
            w.bind("<Leave>", _leave)
            w.bind("<Button-1>", _click)
            try:
                w.configure(cursor="hand2")
            except Exception:
                pass


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
                fac = self.db.query(
                    "SELECT * FROM users WHERE role='facilitator' LIMIT 1")
                if not fac.empty:
                    self._user = fac.iloc[0].to_dict()
                else:
                    self._user = {"id": "fac1", "name": "Facilitator",
                                  "role": "facilitator"}
            except Exception as e:
                print(f"(no DB: {e})")
                self.db = None

        @property
        def current_user(self):
            return self._user

        def show_page(self, key, **kw):
            print(f"[roster] → show_page('{key}')  args={kw}")

        def go_back(self):
            print("[roster] back")

        def logout(self):
            print("[roster] logout")

    root = ctk.CTk()
    W, H = 1400, 900
    root.geometry(f"{W}x{H}")
    root.configure(fg_color=COLORS["bg"])
    root.title(f"{APP_NAME} — class roster")

    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - W) // 2
    y = (sh - H) // 2
    root.geometry(f"{W}x{H}+{x}+{y}")

    app = _FakeApp()
    page = FacilitatorClassRosterPage(root, app)
    page.pack(fill="both", expand=True)
    root.mainloop()
    print("\n✅ pages/facilitator/class_roster.py OK")