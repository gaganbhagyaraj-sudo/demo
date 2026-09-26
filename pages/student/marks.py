# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  pages/student/marks.py  ·  Student marks view
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
    APP_NAME, COLORS, STATUS, ZONE_COLORS,
    SUBJECTS, SUBJECT_SHORT, IA_LIST, IA_COLORS,
    FONTS, FONT_FAMILY,
    CARD_RADIUS, BUTTON_RADIUS, CHIP_RADIUS,
    PAD_SM, PAD_MD, PAD_LG, PAD_XL,
)
from pages.base_page import BasePage
from utils.charts import (
    gauge_chart, ia_trend_chart, radar_chart, subject_bar_chart,
)
from utils.excel_io import export_student_report


# =============================================================
# MARKS PAGE
# =============================================================

class StudentMarksPage(BasePage):

    def __init__(self, master, app, target_user_id: str = None):
        super().__init__(master, app)

        self.target_id = target_user_id or (self.user or {}).get("id")
        self.is_self = (self.target_id == (self.user or {}).get("id"))
        self.target = self.db.get_user(self.target_id) if self.target_id else None

        self.build_header(
            "My Marks" if self.is_self else f"{self.target.get('name', '')} — Marks",
            "Performance across all internal assessments",
            back=not self.is_self,
        )
        self.build_content(scrollable=True)
        self.build_footer()

        # State
        self._active_ia = None
        self._tab_btns = {}

        self.render()

    # =========================================================
    # RENDER
    # =========================================================

    def render(self):
        if not self.target:
            self._render_empty("Student not found.")
            return

        uid = self.target["id"]

        # Load all summaries
        try:
            self._summary = self.db.get_marks_summary(uid)
        except Exception:
            self._summary = None

        if self._summary is None or self._summary.empty:
            self._render_empty("No marks recorded yet.")
            return

        # Default IA = latest
        self._active_ia = int(self._summary.iloc[-1]["ia_number"])

        content = self._content

        # 1. Top stats summary
        self._render_top_stats(content, uid)

        # 2. IA tabs
        self._render_ia_tabs(content)

        # 3. Active IA section (table + gauge + radar)
        self._ia_container = ctk.CTkFrame(content, fg_color="transparent")
        self._ia_container.pack(fill="x", pady=(PAD_MD, 0))
        self._render_active_ia()

        # 4. IA trend line chart
        self.section_title("IA Progression", parent=content)
        self._render_ia_trend(content, uid)

        # 5. Subject comparison bar chart
        self.section_title("Subject Comparison (Latest IA)", parent=content)
        self._render_subject_bars(content, uid)

        # 6. Export
        self._render_export_row(content, uid)

    # =========================================================
    # TOP STATS
    # =========================================================

    def _render_top_stats(self, parent, uid):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        s = self._summary

        # Average %
        avg_pct = s["percentage"].mean()
        avg_grade = s.iloc[-1]["grade"]
        avg_zone = s.iloc[-1]["zone"]

        # Best IA
        best = s.loc[s["percentage"].idxmax()]
        best_pct = best["percentage"]
        best_ia = int(best["ia_number"])

        # Trend
        trend_val = s.iloc[-1]["percentage"] - s.iloc[0]["percentage"]

        # Subject-wise best
        latest = s.iloc[-1]
        best_subj = max(
            [("Maths", latest["maths"]),
             ("Physics", latest["phy"]),
             ("Chemistry", latest["che"]),
             ("Computer Science", latest["cs"])],
            key=lambda x: x[1])

        self.stat_card(
            row, f"{avg_pct:.1f}%", "Average across IAs",
            accent=ZONE_COLORS.get(avg_zone, COLORS["primary"]),
            icon="📊",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, f"IA-{best_ia}", f"Best: {best_pct:.1f}%",
            accent=STATUS["gold"],
            icon="🏆",
        ).pack(side="left", padx=(0, PAD_MD))

        arrow = "📈" if trend_val > 0 else ("📉" if trend_val < 0 else "→")
        trend_color = STATUS["green"] if trend_val > 0 else \
                      (STATUS["red"] if trend_val < 0 else COLORS["text_muted"])
        self.stat_card(
            row, f"{trend_val:+.1f}%",
            f"{arrow} IA-1 → IA-{int(s.iloc[-1]['ia_number'])}",
            accent=trend_color,
            icon="📈",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, best_subj[0].split()[0],
            f"Best subject: {best_subj[1]:.0f}",
            accent=COLORS["primary"],
            icon="🎯",
        ).pack(side="left")

    # =========================================================
    # IA TABS
    # =========================================================

    def _render_ia_tabs(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        for ia in (1, 2, 3):
            exists = any(self._summary["ia_number"] == ia)
            label = f"IA-{ia}"
            if not exists:
                label += "  ·"

            btn = ctk.CTkButton(
                row, text=label, width=120, height=40,
                font=FONTS["small_bold"],
                fg_color=IA_COLORS.get(f"IA-{ia}", COLORS["primary"])
                         if ia == self._active_ia
                         else COLORS["surface_alt"],
                hover_color=COLORS["surface_hi"],
                text_color=COLORS["text"],
                corner_radius=BUTTON_RADIUS,
                state="normal" if exists else "disabled",
                command=lambda i=ia: self._select_ia(i),
            )
            btn.pack(side="left", padx=(0, PAD_SM))
            self._tab_btns[ia] = btn

    def _select_ia(self, ia: int):
        self._active_ia = ia
        # Update button colors
        for i, btn in self._tab_btns.items():
            try:
                btn.configure(
                    fg_color=IA_COLORS.get(f"IA-{i}", COLORS["primary"])
                             if i == ia
                             else COLORS["surface_alt"])
            except Exception:
                pass
        # Re-render the active IA section
        self._render_active_ia()

    # =========================================================
    # ACTIVE IA SECTION
    # =========================================================

    def _render_active_ia(self):
        # Clear
        for w in self._ia_container.winfo_children():
            w.destroy()

        row = self._summary[self._summary["ia_number"] == self._active_ia]
        if row.empty:
            ctk.CTkLabel(
                self._ia_container,
                text=f"IA-{self._active_ia} has not been recorded yet.",
                font=FONTS["body"],
                text_color=COLORS["text_muted"]).pack(pady=20)
            return
        data = row.iloc[0]

        # Two column: table left, gauge right
        cols = ctk.CTkFrame(self._ia_container, fg_color="transparent")
        cols.pack(fill="x")

        left = ctk.CTkFrame(cols, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=(0, PAD_MD))

        right = ctk.CTkFrame(cols, fg_color="transparent")
        right.pack(side="left", fill="both", expand=False)

        # -- Table card --
        card = self.card(left)
        card.pack(fill="x")

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        title_row = ctk.CTkFrame(body, fg_color="transparent")
        title_row.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            title_row, text=f"IA-{self._active_ia} Subject Marks",
            font=(FONT_FAMILY, 15, "bold"),
            text_color=COLORS["text"]).pack(side="left")

        zone = data["zone"]
        zc = ctk.CTkFrame(
            title_row,
            fg_color=ZONE_COLORS.get(zone, COLORS["primary"]),
            corner_radius=CHIP_RADIUS)
        zc.pack(side="right")
        ctk.CTkLabel(
            zc,
            text=f"  {data['grade']}  ·  {data['percentage']:.2f}%  ",
            font=(FONT_FAMILY, 10, "bold"),
            text_color="#FFFFFF",
        ).pack(padx=6, pady=4)

        # Subject rows
        subjects_data = [
            ("Maths",            data["maths"]),
            ("Physics",          data["phy"]),
            ("Chemistry",        data["che"]),
            ("Computer Science", data["cs"]),
        ]
        for subj, mark in subjects_data:
            r = ctk.CTkFrame(body, fg_color=COLORS["surface_alt"],
                             corner_radius=8)
            r.pack(fill="x", pady=3)

            ctk.CTkLabel(
                r, text=subj, width=140, anchor="w",
                font=FONTS["small_bold"],
                text_color=COLORS["text"],
            ).pack(side="left", padx=(12, 0), pady=10)

            # Progress bar
            bar = ctk.CTkProgressBar(
                r, width=220, height=8,
                progress_color=ZONE_COLORS.get(zone, COLORS["primary"]),
                fg_color=COLORS["surface"],
                corner_radius=4)
            bar.pack(side="left", padx=12)
            bar.set(min(1.0, mark / 100.0))

            ctk.CTkLabel(
                r, text=f"{mark:.0f}/100",
                font=(FONT_FAMILY, 11, "bold"),
                text_color=COLORS["text"],
                width=70, anchor="e",
            ).pack(side="right", padx=12)

        # Total
        total_row = ctk.CTkFrame(body, fg_color="transparent")
        total_row.pack(fill="x", pady=(10, 0))

        ctk.CTkLabel(
            total_row, text="Total",
            font=(FONT_FAMILY, 12, "bold"),
            text_color=COLORS["text_muted"]).pack(side="left")
        ctk.CTkLabel(
            total_row, text=f"{int(data['total'])} / 400",
            font=(FONT_FAMILY, 12, "bold"),
            text_color=COLORS["text"]).pack(side="right")

        # -- Gauge card --
        gauge_card = self.card(right, width=300)
        gauge_card.pack_propagate(False)
        gauge_card.pack(fill="both", expand=True)

        try:
            fig = gauge_chart(
                float(data["percentage"]),
                label=f"IA-{self._active_ia} Score",
                color=ZONE_COLORS.get(zone, COLORS["primary"]),
                animate=False,
                figsize=(3.2, 3.2),
            )
            self.chart_frame(gauge_card, fig, height=280).pack(
                fill="both", expand=True, padx=8, pady=8)
        except Exception as e:
            ctk.CTkLabel(
                gauge_card, text=f"(gauge unavailable: {e})",
                font=FONTS["tiny"],
                text_color=COLORS["text_muted"]).pack(pady=20)

    # =========================================================
    # IA TREND
    # =========================================================

    def _render_ia_trend(self, parent, uid):
        try:
            marks = self.db.get_marks(uid)
            ia_data = {}
            for subj in SUBJECTS:
                vals = []
                for ia in (1, 2, 3):
                    sub = marks[
                        (marks["ia_number"] == ia) &
                        (marks["subject"] == subj)]
                    vals.append(float(sub.iloc[0]["marks"])
                                if not sub.empty else 0.0)
                ia_data[subj] = vals

            fig = ia_trend_chart(
                ia_data,
                title="IA Performance Trend",
                animate=False,
            )
            self.chart_frame(parent, fig, height=320).pack(
                fill="x", pady=(0, PAD_MD))
        except Exception as e:
            ctk.CTkLabel(parent, text=f"(trend unavailable: {e})",
                         font=FONTS["tiny"],
                         text_color=COLORS["text_muted"]).pack()

    # =========================================================
    # SUBJECT BARS
    # =========================================================

    def _render_subject_bars(self, parent, uid):
        try:
            latest = self._summary.iloc[-1]
            avgs = {
                "Maths":            float(latest["maths"]),
                "Physics":          float(latest["phy"]),
                "Chemistry":        float(latest["che"]),
                "Computer Science": float(latest["cs"]),
            }
            fig = subject_bar_chart(
                avgs,
                title=f"Subject Breakdown (IA-{int(latest['ia_number'])})",
                animate=False,
            )
            self.chart_frame(parent, fig, height=320).pack(
                fill="x", pady=(0, PAD_MD))
        except Exception as e:
            ctk.CTkLabel(parent, text=f"(chart unavailable: {e})",
                         font=FONTS["tiny"],
                         text_color=COLORS["text_muted"]).pack()

    # =========================================================
    # EXPORT
    # =========================================================

    def _render_export_row(self, parent, uid):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(PAD_MD, PAD_LG))

        self.primary_button(
            row, "Download report (.xlsx)",
            command=lambda: self._export(uid),
            width=240, height=42,
        ).pack(side="left")

        self.secondary_button(
            row, "Refresh",
            command=lambda: self.navigate("stu_marks"),
            width=120, height=42,
        ).pack(side="left", padx=(PAD_MD, 0))

    def _export(self, uid):
        try:
            path = export_student_report(self.db, uid)
            self.toast(f"Report saved: {os.path.basename(path)}",
                       "success")
            # Open folder
            try:
                folder = os.path.dirname(path)
                if sys.platform.startswith("win"):
                    os.startfile(folder)
                elif sys.platform == "darwin":
                    os.system(f'open "{folder}"')
                else:
                    os.system(f'xdg-open "{folder}"')
            except Exception:
                pass
        except Exception as e:
            self.toast(f"Export failed: {e}", "error")

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
                stu = self.db.get_all_students().iloc[0]
                self._user = stu.to_dict()
            except Exception as e:
                print(f"(no DB: {e})")
                self.db = None

        @property
        def current_user(self):
            return self._user

        def show_page(self, key, **kw):
            print(f"[marks] → show_page('{key}')  args={kw}")

        def go_back(self):
            print("[marks] back")

        def logout(self):
            print("[marks] logout")

    root = ctk.CTk()
    W, H = 1280, 900
    root.geometry(f"{W}x{H}")
    root.configure(fg_color=COLORS["bg"])
    root.title(f"{APP_NAME} — marks preview")

    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - W) // 2
    y = (sh - H) // 2
    root.geometry(f"{W}x{H}+{x}+{y}")

    app = _FakeApp()
    page = StudentMarksPage(root, app)
    page.pack(fill="both", expand=True)
    root.mainloop()
    print("\n✅ pages/student/marks.py OK")