# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  pages/admin/class_analytics.py  ·  Class-level analytics
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
    SUBJECTS, SUBJECT_SHORT, SUBJECT_COLORS,
    IA_LIST, IA_COLORS,
    FONTS, FONT_FAMILY,
    CARD_RADIUS, BUTTON_RADIUS, CHIP_RADIUS,
    PAD_SM, PAD_MD, PAD_LG, PAD_XL,
)
from pages.base_page import BasePage
from utils.charts import (
    zone_donut, subject_bar_chart, ia_trend_chart,
    subject_boxplot, ranking_bar_chart,
)
from utils.excel_io import export_class_analytics


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


def _admin_nav():
    return [
        {"key": "admin_dashboard",       "label": "Dashboard",       "icon": "🏠"},
        {"key": "admin_approval",        "label": "Approvals",       "icon": "✅"},
        {"key": "admin_users",           "label": "Users",           "icon": "👥"},
        {"key": "admin_marks_manual",    "label": "Marks Entry",     "icon": "📝"},
        {"key": "admin_marks_excel",     "label": "Excel Upload",    "icon": "📊"},
        {"key": "admin_attendance",      "label": "Attendance",      "icon": "📅"},
        {"key": "admin_analytics",       "label": "Analytics",       "icon": "📈"},
        {"key": "admin_certificates",    "label": "Certificates",    "icon": "📜"},
        {"key": "admin_activities",      "label": "Activities",      "icon": "🎗️"},
        {"key": "admin_audit",           "label": "Audit Log",       "icon": "🔍"},
    ]


def _open_folder(path: str) -> bool:
    try:
        if not os.path.exists(path):
            return False
        if sys.platform.startswith("win"):
            os.startfile(path)   # noqa: S606
        elif sys.platform == "darwin":
            os.system(f'open "{path}"')
        else:
            os.system(f'xdg-open "{path}"')
        return True
    except Exception:
        return False


# =============================================================
# CLASS ANALYTICS PAGE
# =============================================================

class AdminClassAnalyticsPage(BasePage):

    def __init__(self, master, app):
        super().__init__(master, app)

        self.build_header("Class Analytics",
                          "School-wide performance dashboard", back=False)
        self.build_sidebar(self._build_nav_items())
        self.build_content(scrollable=True)
        self.build_footer()

        # State
        self._active_ia = 3
        self._tab_btns = {}

        self.render()

    def _build_nav_items(self):
        items = _admin_nav()
        for it in items:
            if it["key"] == "admin_analytics":
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

        self._load_data()

        # 1. IA tabs
        self._render_ia_tabs(content)

        # 2. KPIs
        self.section_title("Overview", parent=content)
        self._render_kpis(content)

        # 3. Two-column: Subject bars | Zone donut
        cols = ctk.CTkFrame(content, fg_color="transparent")
        cols.pack(fill="x", pady=(PAD_MD, 0))

        left = ctk.CTkFrame(cols, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=(0, PAD_MD))

        right = ctk.CTkFrame(cols, fg_color="transparent")
        right.pack(side="left", fill="both", expand=False)

        self.section_title(f"Subject Averages · IA-{self._active_ia}",
                          parent=left)
        self._render_subject_bars(left)

        self.section_title("Zone Distribution", parent=right)
        self._render_zone_donut(right)

        # 4. IA Trend across subjects
        self.section_title("IA Trend (Class Average)", parent=content)
        self._render_ia_trend(content)

        # 5. Two-column: Ranking | Boxplot
        cols2 = ctk.CTkFrame(content, fg_color="transparent")
        cols2.pack(fill="x", pady=(PAD_MD, 0))

        rank_left = ctk.CTkFrame(cols2, fg_color="transparent")
        rank_left.pack(side="left", fill="both", expand=True, padx=(0, PAD_MD))

        box_right = ctk.CTkFrame(cols2, fg_color="transparent")
        box_right.pack(side="left", fill="both", expand=True)

        self.section_title("Top 5 Performers", parent=rank_left)
        self._render_ranking(rank_left)

        self.section_title("Marks Distribution", parent=box_right)
        self._render_boxplot(box_right)

        # 6. Toppers + attention
        cols3 = ctk.CTkFrame(content, fg_color="transparent")
        cols3.pack(fill="x", pady=(PAD_MD, 0))

        top_left = ctk.CTkFrame(cols3, fg_color="transparent")
        top_left.pack(side="left", fill="both", expand=True, padx=(0, PAD_MD))

        top_right = ctk.CTkFrame(cols3, fg_color="transparent")
        top_right.pack(side="left", fill="both", expand=True)

        self.section_title("Subject Toppers", parent=top_left)
        self._render_subject_toppers(top_left)

        self.section_title("Needs Attention", parent=top_right)
        self._render_attention(top_right)

        # 7. Export
        self._render_export(content)

    # =========================================================
    # LOAD
    # =========================================================

    def _load_data(self):
        # Class marks for active IA
        try:
            self._class_marks = self.db.get_class_marks_summary(
                ia_number=self._active_ia)
        except Exception:
            self._class_marks = pd.DataFrame()

        # All marks (for trend)
        try:
            self._all_marks = self.db.query("""
                SELECT ia_number, maths, phy, che, cs
                FROM marks_summary
            """)
        except Exception:
            self._all_marks = pd.DataFrame()

        # Zone counts
        try:
            self._zone_counts = self.db.class_zone_counts(
                ia_number=self._active_ia)
        except Exception:
            self._zone_counts = {"red": 0, "yellow": 0,
                                 "green": 0, "gold": 0}

        # Subject averages
        try:
            self._subject_avgs = self.db.class_subject_averages(
                ia_number=self._active_ia)
        except Exception:
            self._subject_avgs = {s: 0 for s in SUBJECTS}

        # Subject toppers
        try:
            self._subject_toppers = self.db.get_subject_toppers(
                ia_number=self._active_ia)
        except Exception:
            self._subject_toppers = {}

        # Overall topper
        try:
            self._overall_topper = self.db.get_overall_topper(
                ia_number=self._active_ia)
        except Exception:
            self._overall_topper = None

        # Students count
        try:
            self._students = self.db.get_all_students()
        except Exception:
            self._students = pd.DataFrame()

    # =========================================================
    # IA TABS
    # =========================================================

    def _render_ia_tabs(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        ctk.CTkLabel(
            row, text="Internal Assessment:",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_muted"]).pack(side="left", padx=(0, 10))

        for ia in (1, 2, 3):
            label = f"IA-{ia}"
            btn = ctk.CTkButton(
                row, text=label, width=90, height=38,
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
            row, "🔄 Refresh", command=self._reload,
            width=110, height=38,
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
    # KPIs
    # =========================================================

    def _render_kpis(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        cm = self._class_marks
        n = 0 if cm is None else len(cm)

        avg = best = worst = 0.0
        passing = 0
        if cm is not None and not cm.empty and "percentage" in cm.columns:
            try:
                avg = _safe_float(cm["percentage"].mean())
                best = _safe_float(cm["percentage"].max())
                worst = _safe_float(cm["percentage"].min())
                passing = int((cm["percentage"] >= 40).sum())
            except Exception:
                pass

        pass_pct = (passing / n * 100) if n else 0

        self.stat_card(
            row, n, "Students assessed",
            accent=COLORS["primary"], icon="👥",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, f"{avg:.1f}%", "Class average",
            accent=STATUS["green"] if avg >= 70
                   else (STATUS["amber"] if avg >= 50 else STATUS["red"]),
            icon="📊",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, f"{best:.1f}%", "Highest",
            accent=STATUS["gold"], icon="🏆",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, f"{worst:.1f}%", "Lowest",
            accent=STATUS["red"], icon="⬇️",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, f"{pass_pct:.0f}%", "Pass rate",
            accent=STATUS["green"] if pass_pct >= 80
                   else (STATUS["amber"] if pass_pct >= 50 else STATUS["red"]),
            icon="✅",
        ).pack(side="left")

    # =========================================================
    # SUBJECT BARS
    # =========================================================

    def _render_subject_bars(self, parent):
        try:
            fig = subject_bar_chart(
                self._subject_avgs,
                title="",
                animate=False,
                figsize=(7, 3.6),
            )
            self.chart_frame(parent, fig, height=300).pack(
                fill="x", pady=(0, PAD_MD))
        except Exception as e:
            ctk.CTkLabel(parent, text=f"(chart unavailable: {e})",
                         font=FONTS["tiny"],
                         text_color=COLORS["text_muted"]).pack()

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
            self.chart_frame(card, fig, height=300).pack(
                fill="both", expand=True, padx=8, pady=8)
        except Exception as e:
            ctk.CTkLabel(
                card, text=f"(chart unavailable: {e})",
                font=FONTS["tiny"],
                text_color=COLORS["text_muted"]).pack(pady=20)

    # =========================================================
    # IA TREND
    # =========================================================

    def _render_ia_trend(self, parent):
        try:
            df = self._all_marks
            if df is None or df.empty:
                ctk.CTkLabel(
                    parent, text="No trend data.",
                    font=FONTS["small"],
                    text_color=COLORS["text_muted"]).pack()
                return

            ia_data = {}
            for col, subj in [("maths", "Maths"), ("phy", "Physics"),
                              ("che", "Chemistry"),
                              ("cs", "Computer Science")]:
                vals = []
                for ia in (1, 2, 3):
                    sub = df[df["ia_number"] == ia]
                    vals.append(
                        round(_safe_float(sub[col].mean()), 1)
                        if not sub.empty else 0.0)
                ia_data[subj] = vals

            fig = ia_trend_chart(ia_data,
                                 title="",
                                 animate=False,
                                 figsize=(8, 3.6))
            self.chart_frame(parent, fig, height=300).pack(
                fill="x", pady=(0, PAD_MD))
        except Exception as e:
            ctk.CTkLabel(parent, text=f"(trend unavailable: {e})",
                         font=FONTS["tiny"],
                         text_color=COLORS["text_muted"]).pack()

    # =========================================================
    # RANKING
    # =========================================================

    def _render_ranking(self, parent):
        cm = self._class_marks
        if cm is None or cm.empty:
            ctk.CTkLabel(
                parent, text="No data.",
                font=FONTS["small"],
                text_color=COLORS["text_muted"]).pack()
            return

        top = cm.head(5)
        names = [_safe_str(r.get("name")) or "—"
                 for _, r in top.iterrows()]
        vals = [_safe_float(r.get("percentage")) for _, r in top.iterrows()]

        try:
            fig = ranking_bar_chart(
                names, vals,
                title="",
                value_label="%",
                animate=False,
                figsize=(5, 3.5))
            self.chart_frame(parent, fig, height=300).pack(fill="x")
        except Exception as e:
            ctk.CTkLabel(parent, text=f"(chart unavailable: {e})",
                         font=FONTS["tiny"],
                         text_color=COLORS["text_muted"]).pack()

    # =========================================================
    # BOX PLOT
    # =========================================================

    def _render_boxplot(self, parent):
        cm = self._class_marks
        if cm is None or cm.empty:
            ctk.CTkLabel(
                parent, text="No data.",
                font=FONTS["small"],
                text_color=COLORS["text_muted"]).pack()
            return

        try:
            df = cm[["maths", "phy", "che", "cs"]].copy()
            df.columns = SUBJECTS
            fig = subject_boxplot(df, animate=False, figsize=(5, 3.5))
            self.chart_frame(parent, fig, height=300).pack(fill="x")
        except Exception as e:
            ctk.CTkLabel(parent, text=f"(chart unavailable: {e})",
                         font=FONTS["tiny"],
                         text_color=COLORS["text_muted"]).pack()

    # =========================================================
    # SUBJECT TOPPERS
    # =========================================================

    def _render_subject_toppers(self, parent):
        card = self.card(parent)
        card.pack(fill="x")

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        for subj in SUBJECTS:
            info = self._subject_toppers.get(subj)
            color = SUBJECT_COLORS.get(subj, COLORS["primary"])

            row = ctk.CTkFrame(body, fg_color=COLORS["surface_alt"],
                               corner_radius=8)
            row.pack(fill="x", pady=3)

            # Subject chip
            chip = ctk.CTkFrame(row, fg_color=color,
                                corner_radius=CHIP_RADIUS)
            chip.pack(side="left", padx=(10, 10), pady=8)
            ctk.CTkLabel(
                chip,
                text=f"  {SUBJECT_SHORT.get(subj, subj)}  ",
                font=(FONT_FAMILY, 10, "bold"),
                text_color="#FFFFFF").pack(padx=4, pady=2)

            if not info:
                ctk.CTkLabel(
                    row, text="No data",
                    font=(FONT_FAMILY, 10),
                    text_color=COLORS["text_muted"]).pack(side="left",
                                                          pady=8)
                continue

            name = _safe_str(info.get("name")) or "—"
            usn = _safe_str(info.get("usn")) or "—"
            marks = _safe_float(info.get("marks"))

            ctk.CTkLabel(
                row, text=name, anchor="w",
                font=(FONT_FAMILY, 11, "bold"),
                text_color=COLORS["text"]).pack(side="left", pady=8)

            ctk.CTkLabel(
                row, text=usn, anchor="w",
                font=(FONT_FAMILY, 10),
                text_color=COLORS["text_muted"]).pack(side="left",
                                                      padx=(10, 0), pady=8)

            ctk.CTkLabel(
                row, text=f"{marks:.0f}",
                font=(FONT_FAMILY, 12, "bold"),
                text_color=color).pack(side="right", padx=12, pady=8)

    # =========================================================
    # ATTENTION
    # =========================================================

    def _render_attention(self, parent):
        card = self.card(parent)
        card.pack(fill="x")

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        cm = self._class_marks
        if cm is None or cm.empty:
            ctk.CTkLabel(
                body, text="No data.",
                font=FONTS["small"],
                text_color=COLORS["text_muted"]).pack()
            return

        # Filter failing
        try:
            mask = (
                (cm["maths"] < 40) | (cm["phy"] < 40) |
                (cm["che"] < 40) | (cm["cs"] < 40)
            )
            failing = cm[mask].sort_values("percentage").head(6)
        except Exception:
            failing = pd.DataFrame()

        if failing.empty:
            ctk.CTkLabel(
                body, text="✅  No students below 40 in any subject.",
                font=(FONT_FAMILY, 11),
                text_color=STATUS["green"]).pack(pady=10)
            return

        for _, r in failing.iterrows():
            name = _safe_str(r.get("name")) or "—"
            usn = _safe_str(r.get("usn")) or "—"
            pct = _safe_float(r.get("percentage"))

            row = ctk.CTkFrame(body, fg_color=COLORS["surface_alt"],
                               corner_radius=8)
            row.pack(fill="x", pady=2)

            bar = ctk.CTkFrame(row, fg_color=STATUS["red"],
                               width=4, corner_radius=2)
            bar.pack(side="left", fill="y", padx=(0, 8))

            inner = ctk.CTkFrame(row, fg_color="transparent")
            inner.pack(side="left", fill="x", expand=True,
                       padx=(0, 10), pady=8)

            ctk.CTkLabel(
                inner, text=name,
                font=(FONT_FAMILY, 11, "bold"),
                text_color=COLORS["text"], anchor="w").pack(anchor="w")

            ctk.CTkLabel(
                inner, text=usn,
                font=(FONT_FAMILY, 9),
                text_color=COLORS["text_muted"], anchor="w").pack(anchor="w")

            ctk.CTkLabel(
                row, text=f"{pct:.1f}%",
                font=(FONT_FAMILY, 12, "bold"),
                text_color=STATUS["red"]).pack(side="right", padx=10)

    # =========================================================
    # EXPORT
    # =========================================================

    def _render_export(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(PAD_MD, PAD_LG))

        self.primary_button(
            row, "📥  Export Analytics (.xlsx)",
            command=self._export,
            width=260, height=42,
        ).pack(side="left", padx=(0, PAD_MD))

        self.secondary_button(
            row, "🔄  Refresh",
            command=self._reload,
            width=120, height=42,
        ).pack(side="left")

    def _export(self):
        try:
            path = export_class_analytics(self.db,
                                         ia_number=self._active_ia)
            self.toast(f"Saved: {os.path.basename(path)}", "success")
            self.db.log_audit(
                (self.user or {}).get("id", "admin"),
                "export_class_analytics",
                target=f"IA-{self._active_ia}")
            try:
                _open_folder(os.path.dirname(path))
            except Exception:
                pass
        except Exception as e:
            self.toast(f"Export failed: {e}", "error")


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
                admin = self.db.query(
                    "SELECT * FROM users WHERE role='admin' LIMIT 1")
                if not admin.empty:
                    self._user = admin.iloc[0].to_dict()
                else:
                    self._user = {"id": "admin1", "name": "Administrator",
                                  "role": "admin"}
            except Exception as e:
                print(f"(no DB: {e})")
                self.db = None

        @property
        def current_user(self):
            return self._user

        def show_page(self, key, **kw):
            print(f"[analytics] → show_page('{key}')  args={kw}")

        def go_back(self):
            print("[analytics] back")

        def logout(self):
            print("[analytics] logout")

    root = ctk.CTk()
    W, H = 1400, 900
    root.geometry(f"{W}x{H}")
    root.configure(fg_color=COLORS["bg"])
    root.title(f"{APP_NAME} — class analytics")

    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - W) // 2
    y = (sh - H) // 2
    root.geometry(f"{W}x{H}+{x}+{y}")

    app = _FakeApp()
    page = AdminClassAnalyticsPage(root, app)
    page.pack(fill="both", expand=True)
    root.mainloop()
    print("\n✅ pages/admin/class_analytics.py OK")