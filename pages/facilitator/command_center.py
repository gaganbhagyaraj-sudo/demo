# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  pages/facilitator/command_center.py  ·  Facilitator command center
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
    SUBJECTS, SUBJECT_SHORT,
    FONTS, FONT_FAMILY,
    CARD_RADIUS, BUTTON_RADIUS, CHIP_RADIUS,
    PAD_SM, PAD_MD, PAD_LG, PAD_XL,
)
from pages.base_page import BasePage
from utils.avatars import load_avatar
from utils.charts import zone_donut, subject_bar_chart, heatmap_chart
from models.clustering import cluster_students, segment_summary


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


def _row_get(row, key, default=None):
    try:
        if key in row:
            v = row[key]
            if isinstance(v, float) and v != v:
                return default
            return v
        return default
    except Exception:
        return default


def _facilitator_nav():
    """Static nav config for the facilitator sidebar."""
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
# COMMAND CENTER PAGE
# =============================================================

class FacilitatorCommandCenterPage(BasePage):

    def __init__(self, master, app):
        super().__init__(master, app)

        self.build_header("Command Center",
                          "Your class at a glance", back=False)
        self.build_sidebar(self._build_nav_items())
        self.build_content(scrollable=True)
        self.build_footer()

        self.render()

    # =========================================================
    # NAV  (renamed to avoid collision with BasePage._nav_items)
    # =========================================================

    def _build_nav_items(self):
        items = _facilitator_nav()
        for it in items:
            if it["key"] == "fac_command":
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

        # Load all data once
        self._load_data()

        # 1. KPI row
        self.section_title("Cohort Overview", parent=content)
        self._render_kpis(content)

        # 2. Two column: Alerts left, Zone donut right
        cols = ctk.CTkFrame(content, fg_color="transparent")
        cols.pack(fill="x", pady=(PAD_MD, 0))

        left = ctk.CTkFrame(cols, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=(0, PAD_MD))

        right = ctk.CTkFrame(cols, fg_color="transparent")
        right.pack(side="left", fill="both", expand=False)

        self.section_title("Active Alerts", parent=left)
        self._render_alerts_preview(left)

        self.section_title("Zone Distribution", parent=right)
        self._render_zone_donut(right)

        # 3. Segment breakdown
        self.section_title("Student Segments", parent=content)
        self._render_segments(content)

        # 4. Class subject averages chart
        self.section_title("Subject Averages", parent=content)
        self._render_subject_chart(content)

        # 5. Heatmap preview
        self.section_title("Heatmap Preview", parent=content)
        self._render_heatmap_preview(content)

        # 6. Quick actions
        self.section_title("Quick Actions", parent=content)
        self._render_quick_actions(content)

    # =========================================================
    # DATA LOADING
    # =========================================================

    def _load_data(self):
        # Students
        try:
            self._students = self.db.get_all_students()
        except Exception:
            self._students = pd.DataFrame()

        # Latest IA
        try:
            ia_df = self.db.query(
                "SELECT MAX(ia_number) AS ia FROM marks_summary")
            self._latest_ia = int(ia_df.iloc[0]["ia"] or 3)
        except Exception:
            self._latest_ia = 3

        # Class marks summary
        try:
            self._class_marks = self.db.get_class_marks_summary(
                ia_number=self._latest_ia)
        except Exception:
            self._class_marks = pd.DataFrame()

        # Zone counts
        try:
            self._zone_counts = self.db.class_zone_counts(
                ia_number=self._latest_ia)
        except Exception:
            self._zone_counts = {"red": 0, "yellow": 0,
                                 "green": 0, "gold": 0}

        # Alerts
        try:
            self._alerts = self.db.get_alerts(resolved=False)
        except Exception:
            self._alerts = pd.DataFrame()

        # Subject averages
        try:
            self._subject_avgs = self.db.class_subject_averages(
                ia_number=self._latest_ia)
        except Exception:
            self._subject_avgs = {s: 0 for s in SUBJECTS}

        # Segments
        try:
            self._seg_df = cluster_students(self.db, n_clusters=3)
        except Exception:
            self._seg_df = pd.DataFrame()

    # =========================================================
    # KPIs
    # =========================================================

    def _render_kpis(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        total = len(self._students)
        at_risk = int(self._zone_counts.get("red", 0))

        # Avg percentage
        avg_pct = 0.0
        if self._class_marks is not None and not self._class_marks.empty:
            if "percentage" in self._class_marks.columns:
                avg_pct = _safe_float(self._class_marks["percentage"].mean())

        n_alerts = len(self._alerts)

        top_zone = "green"
        if self._zone_counts:
            try:
                top_zone = max(self._zone_counts, key=self._zone_counts.get)
            except Exception:
                top_zone = "green"
        top_color = ZONE_COLORS.get(top_zone, COLORS["primary"])

        self.stat_card(
            row, total, "Total students",
            accent=COLORS["primary"], icon="👥",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, f"{avg_pct:.1f}%", f"Avg (IA-{self._latest_ia})",
            accent=STATUS["green"] if avg_pct >= 70 else STATUS["amber"],
            icon="📊",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, at_risk, "At risk (🔴)",
            accent=STATUS["red"], icon="⚠️",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, n_alerts, "Active alerts",
            accent=STATUS["amber"] if n_alerts > 0 else COLORS["text_muted"],
            icon="🔔",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, ZONE_LABELS.get(top_zone, top_zone).title(),
            "Most common zone",
            accent=top_color, icon="🎯",
        ).pack(side="left")

    # =========================================================
    # ALERTS PREVIEW
    # =========================================================

    def _render_alerts_preview(self, parent):
        card = self.card(parent)
        card.pack(fill="both", expand=True)

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="both", expand=True,
                  padx=PAD_LG, pady=PAD_LG)

        alerts = self._alerts
        if alerts is None or alerts.empty:
            ctk.CTkLabel(
                body, text="✅  No active alerts — all clear!",
                font=FONTS["body"],
                text_color=STATUS["green"]).pack(pady=20)
            return

        for _, a in alerts.head(5).iterrows():
            severity = _safe_str(a.get("severity", "low")).lower()
            color = {"high": STATUS["red"],
                     "medium": STATUS["amber"],
                     "low": STATUS["info"]}.get(severity,
                                                COLORS["text_muted"])

            row = ctk.CTkFrame(body, fg_color=COLORS["surface_alt"],
                               corner_radius=10)
            row.pack(fill="x", pady=3)

            bar = ctk.CTkFrame(row, fg_color=color,
                               width=4, corner_radius=2)
            bar.pack(side="left", fill="y", padx=(0, 10))

            inner = ctk.CTkFrame(row, fg_color="transparent")
            inner.pack(side="left", fill="x", expand=True,
                       padx=(0, 10), pady=8)

            student = _safe_str(a.get("student_name", "Unknown"))
            atype = _safe_str(a.get("alert_type", "alert")).replace("_", " ").title()

            ctk.CTkLabel(
                inner, text=f"{student}  ·  {atype}",
                font=FONTS["small_bold"],
                text_color=COLORS["text"], anchor="w",
            ).pack(anchor="w")

            ctk.CTkLabel(
                inner, text=_safe_str(a.get("message", ""))[:90],
                font=FONTS["tiny"],
                text_color=COLORS["text_muted"], anchor="w",
            ).pack(anchor="w")

            self.secondary_button(
                row, "View",
                command=lambda: self.navigate("fac_alerts"),
                width=70, height=28,
            ).pack(side="right", padx=10)

        ctk.CTkButton(
            body, text="View all alerts →",
            font=FONTS["tiny"],
            fg_color="transparent", hover=False,
            text_color=COLORS["primary"],
            command=lambda: self.navigate("fac_alerts"),
        ).pack(pady=(10, 0))

    # =========================================================
    # ZONE DONUT
    # =========================================================

    def _render_zone_donut(self, parent):
        card = self.card(parent, width=340)
        card.pack_propagate(False)
        card.pack(fill="both", expand=True)

        try:
            fig = zone_donut(
                self._zone_counts,
                title="",
                animate=False,
                figsize=(3.4, 3.4),
            )
            self.chart_frame(card, fig, height=310).pack(
                fill="both", expand=True, padx=8, pady=8)
        except Exception as e:
            ctk.CTkLabel(
                card, text=f"(chart unavailable: {e})",
                font=FONTS["tiny"],
                text_color=COLORS["text_muted"]).pack(pady=20)

    # =========================================================
    # SEGMENTS
    # =========================================================

    def _render_segments(self, parent):
        df = self._seg_df
        if df is None or df.empty:
            ctk.CTkLabel(
                parent, text="Not enough data for clustering.",
                font=FONTS["body"],
                text_color=COLORS["text_muted"]).pack(pady=10)
            return

        try:
            segs = segment_summary(df)
        except Exception:
            segs = []

        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        for seg in segs:
            card = ctk.CTkFrame(
                row,
                fg_color=COLORS["surface"],
                corner_radius=CARD_RADIUS,
                border_width=2,
                border_color=seg["color"],
                width=340, height=140)
            card.pack(side="left", padx=(0, PAD_MD))
            card.pack_propagate(False)

            body = ctk.CTkFrame(card, fg_color="transparent")
            body.pack(fill="both", expand=True,
                      padx=PAD_LG, pady=PAD_MD)

            head = ctk.CTkFrame(body, fg_color="transparent")
            head.pack(fill="x")

            ctk.CTkLabel(
                head, text=f"{seg['icon']}  {seg['segment']}",
                font=(FONT_FAMILY, 13, "bold"),
                text_color=seg["color"]).pack(side="left")

            ctk.CTkLabel(
                head, text=f"{seg['count']} students",
                font=(FONT_FAMILY, 11, "bold"),
                text_color=COLORS["text"]).pack(side="right")

            stats = ctk.CTkFrame(body, fg_color="transparent")
            stats.pack(fill="x", pady=(10, 0))

            self._mini_stat(stats, "Avg marks",
                            f"{seg['avg_marks']:.1f}", seg["color"])
            self._mini_stat(stats, "Attendance",
                            f"{seg['avg_attendance']:.0f}%", seg["color"])
            self._mini_stat(stats, "Activities",
                            f"{seg['avg_activities']:.1f}", seg["color"])

    def _mini_stat(self, parent, label, value, color):
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.pack(side="left", padx=(0, 16))
        ctk.CTkLabel(
            box, text=value,
            font=(FONT_FAMILY, 14, "bold"),
            text_color=color).pack()
        ctk.CTkLabel(
            box, text=label,
            font=(FONT_FAMILY, 9),
            text_color=COLORS["text_muted"]).pack()

    # =========================================================
    # SUBJECT CHART
    # =========================================================

    def _render_subject_chart(self, parent):
        try:
            fig = subject_bar_chart(
                self._subject_avgs,
                title=f"Subject Averages · IA-{self._latest_ia}",
                animate=False,
            )
            self.chart_frame(parent, fig, height=320).pack(
                fill="x", pady=(0, PAD_MD))
        except Exception as e:
            ctk.CTkLabel(parent, text=f"(chart unavailable: {e})",
                         font=FONTS["tiny"],
                         text_color=COLORS["text_muted"]).pack()

    # =========================================================
    # HEATMAP PREVIEW
    # =========================================================

    def _render_heatmap_preview(self, parent):
        cm = self._class_marks
        if cm is None or cm.empty:
            ctk.CTkLabel(
                parent,
                text="No marks data to preview.",
                font=FONTS["body"],
                text_color=COLORS["text_muted"]).pack(pady=10)
            return

        try:
            needed = ["name", "maths", "phy", "che", "cs"]
            missing = [c for c in needed if c not in cm.columns]
            if missing:
                ctk.CTkLabel(
                    parent,
                    text=f"(heatmap skipped — missing columns: {missing})",
                    font=FONTS["tiny"],
                    text_color=COLORS["text_muted"]).pack()
                return

            matrix = cm[needed].copy()
            matrix.columns = ["Student", "Maths", "Physics",
                              "Chemistry", "Computer Science"]
            matrix = matrix.set_index("Student")
            matrix = matrix.head(12)

            fig = heatmap_chart(
                matrix,
                title=f"Student × Subject (IA-{self._latest_ia})",
                cmap="magma",
                cbar_label="Marks",
                annot=False,
                animate=False,
                figsize=(9, 4.2),
            )
            self.chart_frame(parent, fig, height=340).pack(
                fill="x", pady=(0, PAD_MD))
        except Exception as e:
            ctk.CTkLabel(parent, text=f"(heatmap unavailable: {e})",
                         font=FONTS["tiny"],
                         text_color=COLORS["text_muted"]).pack()

    # =========================================================
    # QUICK ACTIONS
    # =========================================================

    def _render_quick_actions(self, parent):
        grid = ctk.CTkFrame(parent, fg_color="transparent")
        grid.pack(fill="x", pady=(0, PAD_LG))

        actions = [
            ("👥", "Class Roster",   "fac_roster"),
            ("🔔", "Alerts",         "fac_alerts"),
            ("📊", "Marks Analysis", "fac_marks"),
            ("🔥", "Heatmap",        "fac_heatmap"),
            ("🩺", "Remedial",       "fac_remedial"),
            ("📄", "Reports",        "fac_reports"),
        ]

        per_row = 6
        for c in range(per_row):
            grid.grid_columnconfigure(c, weight=1, uniform="qaction")

        for i, (icon, label, key) in enumerate(actions):
            r, col = divmod(i, per_row)
            tile = ctk.CTkFrame(
                grid,
                fg_color=COLORS["surface"],
                corner_radius=CARD_RADIUS,
                border_width=1, border_color=COLORS["border_soft"],
                width=160, height=100)
            tile.grid(row=r, column=col, padx=6, pady=6, sticky="nsew")
            tile.pack_propagate(False)

            def _enter(_, t=tile):
                try:
                    t.configure(fg_color=COLORS["surface_alt"])
                except Exception:
                    pass

            def _leave(_, t=tile):
                try:
                    t.configure(fg_color=COLORS["surface"])
                except Exception:
                    pass

            def _click(_, k=key):
                self.navigate(k)

            tile.bind("<Enter>", _enter)
            tile.bind("<Leave>", _leave)
            tile.bind("<Button-1>", _click)
            try:
                tile.configure(cursor="hand2")
            except Exception:
                pass

            icon_lbl = ctk.CTkLabel(
                tile, text=icon,
                font=(FONT_FAMILY, 24),
                text_color=COLORS["primary"])
            icon_lbl.pack(pady=(16, 6))

            lbl = ctk.CTkLabel(
                tile, text=label,
                font=(FONT_FAMILY, 10, "bold"),
                text_color=COLORS["text"])
            lbl.pack()

            for w in (icon_lbl, lbl):
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
            print(f"[command] → show_page('{key}')  args={kw}")

        def go_back(self):
            print("[command] back")

        def logout(self):
            print("[command] logout")

    root = ctk.CTk()
    W, H = 1400, 900
    root.geometry(f"{W}x{H}")
    root.configure(fg_color=COLORS["bg"])
    root.title(f"{APP_NAME} — facilitator command center")

    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - W) // 2
    y = (sh - H) // 2
    root.geometry(f"{W}x{H}+{x}+{y}")

    app = _FakeApp()
    page = FacilitatorCommandCenterPage(root, app)
    page.pack(fill="both", expand=True)
    root.mainloop()
    print("\n✅ pages/facilitator/command_center.py OK")