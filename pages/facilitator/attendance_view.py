# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  pages/facilitator/attendance_view.py  ·  Class attendance view
# =============================================================

from __future__ import annotations

import os
import sys

# --- make project root importable ---
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from datetime import date, datetime, timedelta

import customtkinter as ctk
import pandas as pd

from config import (
    APP_NAME, COLORS, STATUS, ATTENDANCE_COLORS, ATTENDANCE_STATUS,
    FONTS, FONT_FAMILY,
    CARD_RADIUS, BUTTON_RADIUS, CHIP_RADIUS,
    PAD_SM, PAD_MD, PAD_LG, PAD_XL,
)
from pages.base_page import BasePage
from utils.avatars import load_avatar
from utils.charts import attendance_trend_chart


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


def _att_color(pct: float) -> str:
    if pct >= 85:
        return STATUS["green"]
    if pct >= 70:
        return STATUS["amber"]
    return STATUS["red"]


# =============================================================
# ATTENDANCE VIEW PAGE
# =============================================================

class FacilitatorAttendanceViewPage(BasePage):

    LOOKBACK_DAYS = 30

    def __init__(self, master, app):
        super().__init__(master, app)

        self.build_header("Attendance Overview",
                          "Class-wide attendance analysis", back=False)
        self.build_sidebar(self._build_nav_items())
        self.build_content(scrollable=True)
        self.build_footer()

        # State
        self._days = self.LOOKBACK_DAYS

        self.render()

    def _build_nav_items(self):
        items = _facilitator_nav()
        for it in items:
            if it["key"] == "fac_attendance":
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

        # 1. Top stats
        self._render_stats(content)

        # 2. Daily trend chart
        self.section_title(f"Daily Attendance ({self._days} days)",
                          parent=content)
        self._render_trend(content)

        # 3. Top + Low attenders side by side
        cols = ctk.CTkFrame(content, fg_color="transparent")
        cols.pack(fill="x", pady=(0, PAD_MD))

        left = ctk.CTkFrame(cols, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=(0, PAD_MD))

        right = ctk.CTkFrame(cols, fg_color="transparent")
        right.pack(side="left", fill="both", expand=True)

        self.section_title("🌟 Best Attenders", parent=left)
        self._render_top_attenders(left)

        self.section_title("⚠️ Needs Attention", parent=right)
        self._render_low_attenders(right)

        # 4. Full table
        self.section_title("All Students", parent=content)
        self._render_table(content)

        # 5. Export
        self._render_export(content)

    # =========================================================
    # LOAD
    # =========================================================

    def _load_data(self):
        # Class summary
        try:
            self._class_summary = self.db.get_class_attendance_summary(
                days=self._days)
        except Exception:
            self._class_summary = pd.DataFrame()

        # All raw attendance
        since = (date.today() - timedelta(days=self._days)).isoformat()
        try:
            self._attendance = self.db.query("""
                SELECT a.*, u.name, u.usn
                FROM attendance a
                JOIN users u ON u.id = a.user_id
                WHERE a.att_date >= ?
                ORDER BY a.att_date DESC
            """, (since,))
        except Exception:
            self._attendance = pd.DataFrame()

        # All students (for missing data)
        try:
            self._students = self.db.get_all_students()
        except Exception:
            self._students = pd.DataFrame()

        # Build combined per-student summary
        rows = []
        if self._students is not None and not self._students.empty:
            # lookup: user_id → (present, total)
            lookup = {}
            if self._class_summary is not None and not self._class_summary.empty:
                for _, r in self._class_summary.iterrows():
                    uid = _safe_str(r.get("user_id"))
                    lookup[uid] = (
                        int(_safe_float(r.get("present"))),
                        int(_safe_float(r.get("total"))),
                    )

            for _, s in self._students.iterrows():
                uid = _safe_str(s.get("id"))
                present, total = lookup.get(uid, (0, 0))
                pct = (present / total * 100) if total else 0
                rows.append({
                    "id": uid,
                    "name": _safe_str(s.get("name")) or "—",
                    "usn": _safe_str(s.get("usn")) or "—",
                    "present": present,
                    "total": total,
                    "absent": total - present,
                    "pct": pct,
                })

        self._per_student = pd.DataFrame(rows)

    # =========================================================
    # STATS
    # =========================================================

    def _render_stats(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        df = self._per_student
        n = 0 if df is None else len(df)

        class_pct = 0.0
        total_present = 0
        total_days = 0
        excellent = 0   # ≥ 90%
        at_risk = 0     # < 70%

        if df is not None and not df.empty:
            try:
                total_present = int(df["present"].sum())
                total_days = int(df["total"].sum())
                class_pct = (total_present / total_days * 100) \
                    if total_days else 0
                excellent = int((df["pct"] >= 90).sum())
                at_risk = int((df["pct"] < 70).sum())
            except Exception:
                pass

        self.stat_card(
            row, f"{class_pct:.1f}%", f"Class avg ({self._days}d)",
            accent=_att_color(class_pct), icon="📅",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, n, "Students",
            accent=COLORS["primary"], icon="👥",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, excellent, "🌟 ≥ 90%",
            accent=STATUS["green"], icon="✅",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, at_risk, "⚠️ < 70%",
            accent=STATUS["red"], icon="🚨",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, f"{total_present}/{total_days}",
            "Marks → Present/Total",
            accent=COLORS["primary"], icon="📊",
        ).pack(side="left")

    # =========================================================
    # TREND CHART
    # =========================================================

    def _render_trend(self, parent):
        att = self._attendance
        if att is None or att.empty:
            ctk.CTkLabel(
                parent, text="No attendance records for this window.",
                font=FONTS["small"],
                text_color=COLORS["text_muted"]).pack(pady=20)
            return

        try:
            df = att.copy()
            df["att_date"] = pd.to_datetime(df["att_date"]).dt.date

            # Daily present%
            rows = []
            for d, grp in df.groupby("att_date"):
                present = grp["status"].isin(["P", "L", "E"]).sum()
                total = len(grp)
                pct = (present / total * 100) if total else 0
                rows.append({
                    "att_date": d.strftime("%d %b"),
                    "present_pct": round(pct, 1),
                })
            trend = pd.DataFrame(rows).sort_values("att_date")

            fig = attendance_trend_chart(
                trend,
                title="Daily attendance %",
                animate=False,
                figsize=(8, 3.4),
            )
            self.chart_frame(parent, fig, height=280).pack(
                fill="x", pady=(0, PAD_MD))
        except Exception as e:
            ctk.CTkLabel(parent, text=f"(trend unavailable: {e})",
                         font=FONTS["tiny"],
                         text_color=COLORS["text_muted"]).pack()

    # =========================================================
    # TOP ATTENDERS
    # =========================================================

    def _render_top_attenders(self, parent):
        card = self.card(parent)
        card.pack(fill="x")

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        df = self._per_student
        if df is None or df.empty:
            ctk.CTkLabel(
                body, text="No data.",
                font=FONTS["small"],
                text_color=COLORS["text_muted"]).pack()
            return

        top = df.sort_values("pct", ascending=False).head(5)

        for i, (_, s) in enumerate(top.iterrows(), start=1):
            row = ctk.CTkFrame(body, fg_color=COLORS["surface_alt"],
                               corner_radius=8)
            row.pack(fill="x", pady=2)

            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"#{i}")
            ctk.CTkLabel(
                row, text=medal, width=40, anchor="w",
                font=(FONT_FAMILY, 12, "bold"),
                text_color=STATUS["gold"],
            ).pack(side="left", padx=(10, 0), pady=6)

            ctk.CTkLabel(
                row, text=_safe_str(s.get("name")),
                width=170, anchor="w",
                font=(FONT_FAMILY, 11, "bold"),
                text_color=COLORS["text"],
            ).pack(side="left")

            ctk.CTkLabel(
                row, text=f"{int(_safe_float(s.get('present')))}/{int(_safe_float(s.get('total')))}",
                font=(FONT_FAMILY, 10),
                text_color=COLORS["text_muted"],
            ).pack(side="left", padx=(0, 10))

            pct = _safe_float(s.get("pct"))
            ctk.CTkLabel(
                row, text=f"{pct:.0f}%",
                font=(FONT_FAMILY, 12, "bold"),
                text_color=STATUS["green"],
            ).pack(side="right", padx=10)

    # =========================================================
    # LOW ATTENDERS
    # =========================================================

    def _render_low_attenders(self, parent):
        card = self.card(parent)
        card.pack(fill="x")

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        df = self._per_student
        if df is None or df.empty:
            ctk.CTkLabel(
                body, text="No data.",
                font=FONTS["small"],
                text_color=COLORS["text_muted"]).pack()
            return

        low = df[df["pct"] < 75].sort_values("pct").head(5)

        if low.empty:
            ctk.CTkLabel(
                body,
                text="✅  All students above 75% attendance!",
                font=FONTS["body"],
                text_color=STATUS["green"]).pack(pady=10)
            return

        for _, s in low.iterrows():
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
                inner, text=_safe_str(s.get("name")),
                font=(FONT_FAMILY, 11, "bold"),
                text_color=COLORS["text"], anchor="w",
            ).pack(anchor="w")

            ctk.CTkLabel(
                inner,
                text=f"{int(_safe_float(s.get('absent')))} days absent of "
                     f"{int(_safe_float(s.get('total')))}",
                font=(FONT_FAMILY, 9),
                text_color=STATUS["red"], anchor="w",
            ).pack(anchor="w")

            pct = _safe_float(s.get("pct"))
            ctk.CTkLabel(
                row, text=f"{pct:.0f}%",
                font=(FONT_FAMILY, 12, "bold"),
                text_color=STATUS["red"],
            ).pack(side="right", padx=10)

    # =========================================================
    # TABLE
    # =========================================================

    def _render_table(self, parent):
        card = self.card(parent)
        card.pack(fill="x", pady=(0, PAD_MD))

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        df = self._per_student
        if df is None or df.empty:
            ctk.CTkLabel(
                body, text="No data.",
                font=FONTS["small"],
                text_color=COLORS["text_muted"]).pack()
            return

        # Header
        header = ctk.CTkFrame(body, fg_color="transparent")
        header.pack(fill="x", pady=(0, 6))

        headers = [
            ("Student", 260),
            ("USN", 140),
            ("Present", 100),
            ("Absent", 100),
            ("Total", 100),
            ("%", 100),
            ("Status", 140),
        ]
        for label, w in headers:
            ctk.CTkLabel(
                header, text=label, width=w, anchor="w",
                font=(FONT_FAMILY, 10, "bold"),
                text_color=COLORS["text_muted"]).pack(side="left")

        # Rows (sort by pct desc)
        for _, s in df.sort_values("pct", ascending=False).iterrows():
            row = ctk.CTkFrame(body, fg_color=COLORS["surface_alt"],
                               corner_radius=6)
            row.pack(fill="x", pady=2)

            # Student
            student_box = ctk.CTkFrame(row, fg_color="transparent",
                                       width=260)
            student_box.pack(side="left", padx=(8, 0), pady=6)
            student_box.pack_propagate(False)

            try:
                avatar = load_avatar(
                    user_id=_safe_str(s.get("id")),
                    name=_safe_str(s.get("name")),
                    size=28, shape="circle",
                )
                ctk.CTkLabel(student_box, image=avatar, text="").pack(
                    side="left", padx=(0, 8))
            except Exception:
                pass

            ctk.CTkLabel(
                student_box, text=_safe_str(s.get("name")),
                font=(FONT_FAMILY, 11),
                text_color=COLORS["text"], anchor="w",
            ).pack(side="left")

            ctk.CTkLabel(
                row, text=_safe_str(s.get("usn")), width=140, anchor="w",
                font=(FONT_FAMILY, 10),
                text_color=COLORS["text_muted"],
            ).pack(side="left")

            ctk.CTkLabel(
                row, text=str(int(_safe_float(s.get("present")))),
                width=100, anchor="w",
                font=(FONT_FAMILY, 10),
                text_color=STATUS["green"],
            ).pack(side="left")

            ctk.CTkLabel(
                row, text=str(int(_safe_float(s.get("absent")))),
                width=100, anchor="w",
                font=(FONT_FAMILY, 10),
                text_color=STATUS["red"],
            ).pack(side="left")

            ctk.CTkLabel(
                row, text=str(int(_safe_float(s.get("total")))),
                width=100, anchor="w",
                font=(FONT_FAMILY, 10),
                text_color=COLORS["text_muted"],
            ).pack(side="left")

            pct = _safe_float(s.get("pct"))
            ctk.CTkLabel(
                row, text=f"{pct:.1f}%", width=100, anchor="w",
                font=(FONT_FAMILY, 11, "bold"),
                text_color=_att_color(pct),
            ).pack(side="left")

            # Status chip
            label = "Excellent" if pct >= 90 else \
                    ("Good" if pct >= 85 else
                     ("OK" if pct >= 70 else "At Risk"))
            color = _att_color(pct)

            chip_box = ctk.CTkFrame(row, fg_color="transparent", width=140)
            chip_box.pack(side="left")
            chip_box.pack_propagate(False)

            chip = ctk.CTkFrame(chip_box, fg_color=color,
                                corner_radius=CHIP_RADIUS)
            chip.pack(side="left")
            ctk.CTkLabel(
                chip, text=f"  {label}  ",
                font=(FONT_FAMILY, 9, "bold"),
                text_color="#FFFFFF").pack(padx=4, pady=2)

    # =========================================================
    # EXPORT
    # =========================================================

    def _render_export(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(PAD_MD, PAD_LG))

        self.primary_button(
            row, "📥  Export attendance (.csv)",
            command=self._export,
            width=280, height=42,
        ).pack(side="left")

        self.secondary_button(
            row, "🔄  Refresh",
            command=self._reload,
            width=120, height=42,
        ).pack(side="left", padx=(PAD_MD, 0))

    def _reload(self):
        for w in self._content.winfo_children():
            w.destroy()
        self.render()

    def _export(self):
        try:
            df = self._per_student
            if df is None or df.empty:
                self.toast("No data to export", "warning")
                return
            path = os.path.join(
                os.path.expanduser("~"),
                f"class_attendance_{date.today().isoformat()}.csv")
            df.to_csv(path, index=False)
            self.toast(f"Saved: {os.path.basename(path)}", "success")
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
            print(f"[attendance] → show_page('{key}')  args={kw}")

        def go_back(self):
            print("[attendance] back")

        def logout(self):
            print("[attendance] logout")

    root = ctk.CTk()
    W, H = 1400, 900
    root.geometry(f"{W}x{H}")
    root.configure(fg_color=COLORS["bg"])
    root.title(f"{APP_NAME} — attendance view")

    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - W) // 2
    y = (sh - H) // 2
    root.geometry(f"{W}x{H}+{x}+{y}")

    app = _FakeApp()
    page = FacilitatorAttendanceViewPage(root, app)
    page.pack(fill="both", expand=True)
    root.mainloop()
    print("\n✅ pages/facilitator/attendance_view.py OK")