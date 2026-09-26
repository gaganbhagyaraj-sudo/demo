# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  pages/facilitator/heatmap.py  ·  Class-wide heatmap
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
    IA_LIST, IA_COLORS,
    FONTS, FONT_FAMILY,
    CARD_RADIUS, BUTTON_RADIUS, CHIP_RADIUS,
    PAD_SM, PAD_MD, PAD_LG, PAD_XL,
)
from pages.base_page import BasePage
from utils.charts import heatmap_chart
from models.bkt import BKTTracker


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
# HEATMAP PAGE
# =============================================================

class FacilitatorHeatmapPage(BasePage):

    def __init__(self, master, app):
        super().__init__(master, app)

        self.build_header("Heatmap",
                          "Patterns across students and subjects", back=False)
        self.build_sidebar(self._build_nav_items())
        self.build_content(scrollable=True)
        self.build_footer()

        # State
        self._active_ia = 3
        self._active_tab = "marks"   # "marks" | "mastery"
        self._ia_btns = {}
        self._tab_btns = {}

        self.render()

    def _build_nav_items(self):
        items = _facilitator_nav()
        for it in items:
            if it["key"] == "fac_heatmap":
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

        # 1. View tabs (Marks / Mastery)
        self._render_view_tabs(content)

        # 2. IA selector (only shows if marks tab active)
        if self._active_tab == "marks":
            self._render_ia_tabs(content)

        # 3. Legend / explanation
        self._render_legend(content)

        # 4. Main heatmap
        self.section_title(
            "Students × Subjects" if self._active_tab == "marks"
            else "Students × Concepts",
            parent=content,
        )
        self._render_heatmap(content)

        # 5. Insights below
        self.section_title("Insights", parent=content)
        self._render_insights(content)

    # =========================================================
    # VIEW TABS
    # =========================================================

    def _render_view_tabs(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        ctk.CTkLabel(
            row, text="View:",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_muted"]).pack(side="left", padx=(0, 10))

        for key, label in [("marks", "📊  Marks"),
                           ("mastery", "🎯  Mastery")]:
            is_active = (self._active_tab == key)
            btn = ctk.CTkButton(
                row, text=label, width=140, height=38,
                font=FONTS["small_bold"],
                fg_color=COLORS["primary"] if is_active
                         else COLORS["surface_alt"],
                hover_color=COLORS["surface_hi"],
                text_color=COLORS["text"],
                corner_radius=BUTTON_RADIUS,
                command=lambda k=key: self._set_view(k),
            )
            btn.pack(side="left", padx=(0, PAD_SM))
            self._tab_btns[key] = btn

        self.secondary_button(
            row, "Refresh", command=self._reload,
            width=100, height=38,
        ).pack(side="right")

    def _set_view(self, key: str):
        self._active_tab = key
        for k, b in self._tab_btns.items():
            try:
                b.configure(fg_color=COLORS["primary"] if k == key
                            else COLORS["surface_alt"])
            except Exception:
                pass
        self._reload()

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
            self._ia_btns[ia] = btn

    def _select_ia(self, ia: int):
        self._active_ia = ia
        for i, btn in self._ia_btns.items():
            try:
                btn.configure(
                    fg_color=IA_COLORS.get(f"IA-{i}", COLORS["primary"])
                             if i == ia
                             else COLORS["surface_alt"])
            except Exception:
                pass
        self._reload()

    # =========================================================
    # LEGEND
    # =========================================================

    def _render_legend(self, parent):
        card = self.card(parent)
        card.pack(fill="x", pady=(0, PAD_MD))

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD_LG, pady=PAD_MD)

        if self._active_tab == "marks":
            ctk.CTkLabel(
                body, text="Marks scale:",
                font=(FONT_FAMILY, 10, "bold"),
                text_color=COLORS["text_muted"]).pack(side="left", padx=(0, 12))

            for pct, label, color in [
                (95, "90–100", "#FBBF24"),
                (85, "80–89", "#10B981"),
                (75, "70–79", "#34D399"),
                (65, "60–69", "#60A5FA"),
                (55, "50–59", "#818CF8"),
                (45, "40–49", "#F59E0B"),
                (25, "< 40", "#EF4444"),
            ]:
                chip = ctk.CTkFrame(body, fg_color=color,
                                    width=14, height=14, corner_radius=3)
                chip.pack(side="left", padx=(0, 4))
                chip.pack_propagate(False)
                ctk.CTkLabel(
                    body, text=label,
                    font=(FONT_FAMILY, 9),
                    text_color=COLORS["text_muted"],
                ).pack(side="left", padx=(0, 12))

        else:
            ctk.CTkLabel(
                body, text="Mastery scale:",
                font=(FONT_FAMILY, 10, "bold"),
                text_color=COLORS["text_muted"]).pack(side="left", padx=(0, 12))

            for label, color in [
                ("Mastered (≥75%)", "#10B981"),
                ("Developing (40–74%)", "#F59E0B"),
                ("Weak (<40%)", "#EF4444"),
            ]:
                chip = ctk.CTkFrame(body, fg_color=color,
                                    width=14, height=14, corner_radius=3)
                chip.pack(side="left", padx=(0, 4))
                chip.pack_propagate(False)
                ctk.CTkLabel(
                    body, text=label,
                    font=(FONT_FAMILY, 9),
                    text_color=COLORS["text_muted"],
                ).pack(side="left", padx=(0, 12))

    # =========================================================
    # MAIN HEATMAP
    # =========================================================

    def _render_heatmap(self, parent):
        card = self.card(parent)
        card.pack(fill="x", pady=(0, PAD_MD))

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        try:
            if self._active_tab == "marks":
                self._render_marks_heatmap(body)
            else:
                self._render_mastery_heatmap(body)
        except Exception as e:
            ctk.CTkLabel(
                body, text=f"(heatmap unavailable: {e})",
                font=FONTS["small"],
                text_color=STATUS["red"]).pack()

    def _render_marks_heatmap(self, body):
        try:
            df = self.db.get_class_marks_summary(ia_number=self._active_ia)
        except Exception:
            df = None

        if df is None or df.empty:
            ctk.CTkLabel(
                body, text=f"No marks data for IA-{self._active_ia}.",
                font=FONTS["body"],
                text_color=COLORS["text_muted"]).pack(pady=20)
            return

        needed = ["name", "maths", "phy", "che", "cs"]
        missing = [c for c in needed if c not in df.columns]
        if missing:
            ctk.CTkLabel(
                body,
                text=f"(missing columns: {missing})",
                font=FONTS["tiny"],
                text_color=COLORS["text_muted"]).pack()
            return

        matrix = df[needed].copy()
        matrix.columns = ["Student", "Maths", "Physics",
                          "Chemistry", "Computer Science"]
        matrix = matrix.set_index("Student")
        # Sort by total marks (desc)
        matrix["_avg"] = matrix.mean(axis=1)
        matrix = matrix.sort_values("_avg", ascending=False)
        matrix = matrix.drop(columns=["_avg"])

        fig = heatmap_chart(
            matrix,
            title=f"Student × Subject (IA-{self._active_ia})",
            cmap="magma",
            cbar_label="Marks (0–100)",
            annot=True,
            animate=False,
            figsize=(10, max(4, len(matrix) * 0.35)),
        )
        self.chart_frame(body, fig, height=420).pack(
            fill="x", pady=(0, PAD_MD))

    def _render_mastery_heatmap(self, body):
        # Get all students
        try:
            students = self.db.get_all_students()
        except Exception:
            students = None

        if students is None or students.empty:
            ctk.CTkLabel(
                body, text="No students found.",
                font=FONTS["body"],
                text_color=COLORS["text_muted"]).pack(pady=20)
            return

        # Get all concepts
        try:
            concepts = self.db.query(
                "SELECT id, name, difficulty FROM concepts "
                "ORDER BY difficulty, name")
        except Exception:
            concepts = None

        if concepts is None or concepts.empty:
            ctk.CTkLabel(
                body, text="No concepts found.",
                font=FONTS["body"],
                text_color=COLORS["text_muted"]).pack(pady=20)
            return

        tracker = BKTTracker(self.db)

        # Build matrix: students × concepts (mastery × 100)
        concept_names = concepts["name"].tolist()
        concept_ids = concepts["id"].tolist()
        rows = {}
        for _, s in students.iterrows():
            uid = _safe_str(s.get("id"))
            name = _safe_str(s.get("name")) or "—"
            try:
                summary = tracker.summary(uid)
            except Exception:
                summary = pd.DataFrame()
            mastery_map = {}
            if summary is not None and not summary.empty:
                for _, r in summary.iterrows():
                    mastery_map[_safe_str(r["concept_id"])] = \
                        _safe_float(r["p_mastery"]) * 100
            row_vals = [mastery_map.get(cid, 0.0) for cid in concept_ids]
            rows[name] = row_vals

        matrix = pd.DataFrame.from_dict(rows, orient="index",
                                       columns=concept_names)
        if matrix.empty:
            ctk.CTkLabel(
                body, text="No mastery data yet.",
                font=FONTS["body"],
                text_color=COLORS["text_muted"]).pack(pady=20)
            return

        # Sort by average mastery desc
        matrix["_avg"] = matrix.mean(axis=1)
        matrix = matrix.sort_values("_avg", ascending=False)
        matrix = matrix.drop(columns=["_avg"])

        fig = heatmap_chart(
            matrix,
            title="Student × Concept Mastery (%)",
            cmap="RdYlGn",
            cbar_label="Mastery %",
            annot=False,
            animate=False,
            figsize=(11, max(4, len(matrix) * 0.35)),
        )
        self.chart_frame(body, fig, height=440).pack(
            fill="x", pady=(0, PAD_MD))

    # =========================================================
    # INSIGHTS
    # =========================================================

    def _render_insights(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        if self._active_tab == "marks":
            self._render_marks_insights(row)
        else:
            self._render_mastery_insights(row)

    def _render_marks_insights(self, parent):
        try:
            df = self.db.get_class_marks_summary(ia_number=self._active_ia)
        except Exception:
            df = None

        if df is None or df.empty:
            return

        # Hardest subject (lowest avg)
        try:
            avgs = {
                "Maths":     _safe_float(df["maths"].mean()),
                "Physics":   _safe_float(df["phy"].mean()),
                "Chemistry": _safe_float(df["che"].mean()),
                "Computer Science": _safe_float(df["cs"].mean()),
            }
            hardest = min(avgs, key=avgs.get)
            easiest = max(avgs, key=avgs.get)
            hardest_avg = avgs[hardest]
            easiest_avg = avgs[easiest]

            self._insight_card(
                parent, "⚠️  Hardest subject",
                f"{hardest}  ·  avg {hardest_avg:.1f}",
                STATUS["red"],
            ).pack(side="left", padx=(0, PAD_MD))

            self._insight_card(
                parent, "✅  Strongest subject",
                f"{easiest}  ·  avg {easiest_avg:.1f}",
                STATUS["green"],
            ).pack(side="left", padx=(0, PAD_MD))
        except Exception:
            pass

        # At-risk students
        try:
            red_count = int((df["zone"] == "red").sum()) \
                if "zone" in df.columns else 0
            gold_count = int((df["zone"] == "gold").sum()) \
                if "zone" in df.columns else 0

            self._insight_card(
                parent, "🚨  At-risk students",
                f"{red_count} students in red zone",
                STATUS["red"] if red_count > 0 else STATUS["green"],
            ).pack(side="left", padx=(0, PAD_MD))

            self._insight_card(
                parent, "🏆  Achievers",
                f"{gold_count} in gold zone",
                STATUS["gold"],
            ).pack(side="left")
        except Exception:
            pass

    def _render_mastery_insights(self, parent):
        # Aggregate mastery across all students
        try:
            tracker = BKTTracker(self.db)
            students = self.db.get_all_students()
            if students.empty:
                return

            avg_m = []
            for _, s in students.iterrows():
                try:
                    o = tracker.overall_mastery(_safe_str(s.get("id")))
                    avg_m.append(_safe_float(o.get("avg_mastery")))
                except Exception:
                    pass

            if not avg_m:
                return

            class_avg = sum(avg_m) / len(avg_m) * 100
            above = sum(1 for m in avg_m if m * 100 >= 75)
            below = sum(1 for m in avg_m if m * 100 < 40)

            self._insight_card(
                parent, "🎯  Class mastery",
                f"avg {class_avg:.1f}%",
                STATUS["green"] if class_avg >= 75
                else (STATUS["amber"] if class_avg >= 40 else STATUS["red"]),
            ).pack(side="left", padx=(0, PAD_MD))

            self._insight_card(
                parent, "✅  Strong in mastery",
                f"{above} students ≥ 75%",
                STATUS["green"],
            ).pack(side="left", padx=(0, PAD_MD))

            self._insight_card(
                parent, "⚠️  Needs help",
                f"{below} students < 40%",
                STATUS["red"],
            ).pack(side="left")

        except Exception:
            pass

    def _insight_card(self, parent, title, value, color):
        card = ctk.CTkFrame(
            parent,
            fg_color=COLORS["surface"],
            corner_radius=CARD_RADIUS,
            border_width=1,
            border_color=color,
            width=280, height=84)
        card.pack_propagate(False)

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="both", expand=True,
                  padx=PAD_MD, pady=PAD_MD)

        ctk.CTkLabel(
            body, text=title,
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_muted"], anchor="w",
        ).pack(anchor="w")

        ctk.CTkLabel(
            body, text=value,
            font=(FONT_FAMILY, 13, "bold"),
            text_color=color, anchor="w",
        ).pack(anchor="w", pady=(6, 0))

        return card

    # =========================================================
    # RELOAD
    # =========================================================

    def _reload(self):
        for w in self._content.winfo_children():
            w.destroy()
        self.render()


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
            print(f"[heatmap] → show_page('{key}')  args={kw}")

        def go_back(self):
            print("[heatmap] back")

        def logout(self):
            print("[heatmap] logout")

    root = ctk.CTk()
    W, H = 1400, 900
    root.geometry(f"{W}x{H}")
    root.configure(fg_color=COLORS["bg"])
    root.title(f"{APP_NAME} — heatmap")

    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - W) // 2
    y = (sh - H) // 2
    root.geometry(f"{W}x{H}+{x}+{y}")

    app = _FakeApp()
    page = FacilitatorHeatmapPage(root, app)
    page.pack(fill="both", expand=True)
    root.mainloop()
    print("\n✅ pages/facilitator/heatmap.py OK")