# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  pages/student/attendance.py  ·  Student attendance view
# =============================================================

from __future__ import annotations

import os
import sys

# --- make project root importable ---
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import calendar
from datetime import date, datetime, timedelta

import customtkinter as ctk
import pandas as pd

from config import (
    APP_NAME, COLORS, STATUS, ATTENDANCE_STATUS, ATTENDANCE_COLORS,
    FONTS, FONT_FAMILY,
    CARD_RADIUS, BUTTON_RADIUS, CHIP_RADIUS,
    PAD_SM, PAD_MD, PAD_LG, PAD_XL,
)
from pages.base_page import BasePage
from utils.charts import attendance_trend_chart


# =============================================================
# HELPERS
# =============================================================

STATUS_ICON = {
    "P": "✓",
    "A": "✗",
    "L": "◐",
    "E": "★",
}

STATUS_LABEL = {
    "P": "Present",
    "A": "Absent",
    "L": "Late",
    "E": "Excused",
}


def _color_for_status(status: str) -> str:
    return ATTENDANCE_COLORS.get(status, COLORS["text_dim"])


# =============================================================
# ATTENDANCE PAGE
# =============================================================

class StudentAttendancePage(BasePage):

    LOOKBACK_DAYS = 60

    def __init__(self, master, app, target_user_id: str = None):
        super().__init__(master, app)

        self.target_id = target_user_id or (self.user or {}).get("id")
        self.is_self = (self.target_id == (self.user or {}).get("id"))
        self.target = self.db.get_user(self.target_id) if self.target_id else None

        self.build_header(
            "My Attendance" if self.is_self else f"{self.target.get('name', '')} — Attendance",
            f"Last {self.LOOKBACK_DAYS} days",
            back=not self.is_self,
        )
        self.build_content(scrollable=True)
        self.build_footer()

        # Filters
        self._month_filter = None

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

        try:
            self._att = self.db.get_attendance(uid, days=self.LOOKBACK_DAYS)
        except Exception:
            self._att = pd.DataFrame()

        if self._att is None or self._att.empty:
            self._render_empty("No attendance records yet.")
            return

        # Normalize
        self._att["att_date"] = pd.to_datetime(self._att["att_date"]).dt.date
        self._att = self._att.sort_values("att_date", ascending=False)

        # 1. Top stats
        self._render_top_stats(content)

        # 2. Calendar heatmap
        self.section_title("Calendar", parent=content)
        self._render_calendar(content)

        # 3. Trend chart
        self.section_title("Trend", parent=content)
        self._render_trend(content)

        # 4. Streaks
        self.section_title("Streaks & Records", parent=content)
        self._render_streaks(content)

        # 5. Records table
        self.section_title("Recent Records", parent=content)
        self._render_records(content)

        # 6. Export
        self._render_export(content, uid)

    # =========================================================
    # TOP STATS
    # =========================================================

    def _render_top_stats(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        a = self._att
        total = len(a)
        present = (a["status"].isin(["P", "L", "E"])).sum()
        absent = (a["status"] == "A").sum()
        late = (a["status"] == "L").sum()
        pct = (present / total) * 100 if total else 0

        pct_color = STATUS["green"] if pct >= 90 else \
                    (STATUS["amber"] if pct >= 75 else STATUS["red"])

        self.stat_card(
            row, f"{pct:.1f}%", "Overall",
            accent=pct_color,
            icon="📅",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, f"{present}/{total}", "Days present",
            accent=STATUS["green"],
            icon="✓",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, int(absent), "Days absent",
            accent=STATUS["red"],
            icon="✗",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, int(late), "Late arrivals",
            accent=STATUS["amber"],
            icon="◐",
        ).pack(side="left")

    # =========================================================
    # CALENDAR HEATMAP
    # =========================================================

    def _render_calendar(self, parent):
        card = self.card(parent)
        card.pack(fill="x", pady=(0, PAD_MD))

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        # Build lookup: date → status
        lookup = {row["att_date"]: row["status"]
                  for _, row in self._att.iterrows()}

        # Show last 8 weeks of weeks (Mon..Sun), columns = weeks
        today = date.today()
        start = today - timedelta(days=self.LOOKBACK_DAYS - 1)
        # Align start to Monday
        start = start - timedelta(days=start.weekday())
        end = today

        # Header row: day labels
        header = ctk.CTkFrame(body, fg_color="transparent")
        header.pack(fill="x")
        ctk.CTkLabel(header, text="", width=30).pack(side="left")
        for i, d in enumerate(["M", "T", "W", "T", "F", "S", "S"]):
            ctk.CTkLabel(header, text=d, width=26,
                         font=(FONT_FAMILY, 9, "bold"),
                         text_color=COLORS["text_muted"]).pack(
                side="left", padx=1)

        grid_row = ctk.CTkFrame(body, fg_color="transparent")
        grid_row.pack(fill="x", pady=(4, 0))

        # Weeks as columns
        cursor = start
        while cursor <= end:
            # Column = one week
            col = ctk.CTkFrame(grid_row, fg_color="transparent")
            col.pack(side="left", padx=1)

            for i in range(7):
                d = cursor + timedelta(days=i)
                status = lookup.get(d, None)

                # Determine color
                if status:
                    color = _color_for_status(status)
                else:
                    color = COLORS["surface_alt"]

                cell = ctk.CTkFrame(col, width=26, height=26,
                                    fg_color=color, corner_radius=4)
                cell.pack(pady=1)
                cell.pack_propagate(False)

                # Tooltip-ish: tiny label
                if status:
                    ctk.CTkLabel(
                        cell, text=STATUS_ICON.get(status, ""),
                        font=(FONT_FAMILY, 11, "bold"),
                        text_color="#FFFFFF",
                    ).place(relx=0.5, rely=0.5, anchor="center")

                # Hover
                def _on_enter(_, c=cell, dd=d, ss=status):
                    try:
                        c.configure(border_width=1,
                                    border_color=COLORS["text"])
                        if ss:
                            self._calendar_hint.configure(
                                text=f"{dd.strftime('%d %b %Y')}  ·  "
                                     f"{STATUS_LABEL.get(ss, ss)}")
                        else:
                            self._calendar_hint.configure(
                                text=f"{dd.strftime('%d %b %Y')}  ·  no record")
                    except Exception:
                        pass

                def _on_leave(_, c=cell):
                    try:
                        c.configure(border_width=0)
                    except Exception:
                        pass

                cell.bind("<Enter>", _on_enter)
                cell.bind("<Leave>", _on_leave)

            cursor += timedelta(days=7)

        # Hint line
        self._calendar_hint = ctk.CTkLabel(
            body, text="Hover a day to see details",
            font=FONTS["tiny"],
            text_color=COLORS["text_muted"])
        self._calendar_hint.pack(anchor="w", pady=(10, 0))

        # Legend
        legend = ctk.CTkFrame(body, fg_color="transparent")
        legend.pack(anchor="w", pady=(8, 0))

        for code in ("P", "L", "A", "E"):
            chip = ctk.CTkFrame(
                legend,
                fg_color=ATTENDANCE_COLORS[code],
                width=14, height=14, corner_radius=3)
            chip.pack(side="left", padx=(0, 6))
            chip.pack_propagate(False)
            ctk.CTkLabel(
                legend, text=STATUS_LABEL[code],
                font=(FONT_FAMILY, 9),
                text_color=COLORS["text_muted"]).pack(side="left",
                                                      padx=(0, 14))

    # =========================================================
    # TREND
    # =========================================================

    def _render_trend(self, parent):
        try:
            # Build weekly buckets: past N weeks, present%
            a = self._att.copy()
            a["week"] = pd.to_datetime(a["att_date"]).apply(
                lambda d: d - timedelta(days=d.weekday()))

            rows = []
            for wk, grp in a.groupby("week"):
                present = grp["status"].isin(["P", "L", "E"]).sum()
                total = len(grp)
                pct = (present / total * 100) if total else 0
                rows.append({
                    "att_date": wk.strftime("%d %b"),
                    "present_pct": round(pct, 1),
                })
            trend = pd.DataFrame(rows).sort_values("att_date")

            fig = attendance_trend_chart(
                trend, title="Weekly attendance %", animate=False,
                figsize=(8, 3.4))
            self.chart_frame(parent, fig, height=280).pack(
                fill="x", pady=(0, PAD_MD))
        except Exception as e:
            ctk.CTkLabel(parent, text=f"(trend unavailable: {e})",
                         font=FONTS["tiny"],
                         text_color=COLORS["text_muted"]).pack()

    # =========================================================
    # STREAKS
    # =========================================================

    def _render_streaks(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        # Build set of dates with 'present-like' status
        present_dates = set(
            d for d, s in zip(self._att["att_date"], self._att["status"])
            if s in ("P", "L", "E"))

        # Current streak (count back from today, skip weekends)
        cur = 0
        d = date.today()
        for _ in range(self.LOOKBACK_DAYS):
            if d in present_dates:
                cur += 1
            elif d.weekday() < 5 and d not in present_dates and \
                    (d in set(self._att["att_date"])):
                # marked absent on weekday
                break
            d -= timedelta(days=1)

        # Best streak
        best = 0
        run = 0
        for d in sorted(present_dates):
            if d - timedelta(days=1) in present_dates or run == 0:
                run += 1
            else:
                run = 1
            best = max(best, run)

        # Missed days in window
        missed = int((self._att["status"] == "A").sum())

        self.stat_card(
            row, cur, "Current streak",
            accent=STATUS["green"],
            icon="🔥",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, best, "Best streak",
            accent=STATUS["gold"],
            icon="🏆",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, missed, "Days missed",
            accent=STATUS["red"],
            icon="✗",
        ).pack(side="left")

    # =========================================================
    # RECORDS
    # =========================================================

    def _render_records(self, parent):
        card = self.card(parent)
        card.pack(fill="x", pady=(0, PAD_MD))

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        # Header row
        header = ctk.CTkFrame(body, fg_color="transparent")
        header.pack(fill="x", pady=(0, 6))
        for txt, w in [("Date", 180), ("Day", 120),
                       ("Status", 140), ("Marked", 200)]:
            ctk.CTkLabel(
                header, text=txt, width=w, anchor="w",
                font=(FONT_FAMILY, 11, "bold"),
                text_color=COLORS["text_muted"]).pack(side="left")

        # Rows (last 15)
        for _, r in self._att.head(15).iterrows():
            row = ctk.CTkFrame(body, fg_color=COLORS["surface_alt"],
                               corner_radius=8)
            row.pack(fill="x", pady=2)

            d = r["att_date"]
            status = r["status"]
            color = _color_for_status(status)

            ctk.CTkLabel(
                row, text=d.strftime("%d %b %Y"),
                width=180, anchor="w",
                font=FONTS["small"],
                text_color=COLORS["text"],
            ).pack(side="left", padx=(10, 0), pady=8)

            ctk.CTkLabel(
                row, text=d.strftime("%A"),
                width=120, anchor="w",
                font=FONTS["small"],
                text_color=COLORS["text_muted"],
            ).pack(side="left")

            # Status chip
            chip = ctk.CTkFrame(row, fg_color=color,
                                corner_radius=CHIP_RADIUS)
            chip.pack(side="left", padx=(0, 10))
            ctk.CTkLabel(
                chip,
                text=f"{STATUS_ICON.get(status, '•')}  "
                     f"{STATUS_LABEL.get(status, status)}",
                font=(FONT_FAMILY, 10, "bold"),
                text_color="#FFFFFF",
            ).pack(padx=8, pady=3)

            # Marked by / time (if present)
            marked = r.get("marked_at") or ""
            if marked:
                try:
                    marked_txt = marked[:16].replace("T", " ")
                except Exception:
                    marked_txt = str(marked)
            else:
                marked_txt = "—"
            ctk.CTkLabel(
                row, text=marked_txt,
                width=200, anchor="w",
                font=FONTS["tiny"],
                text_color=COLORS["text_muted"],
            ).pack(side="left")

    # =========================================================
    # EXPORT
    # =========================================================

    def _render_export(self, parent, uid):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(PAD_MD, PAD_LG))

        self.primary_button(
            row, "Export attendance (.csv)",
            command=lambda: self._export_csv(uid),
            width=260, height=42,
        ).pack(side="left")

    def _export_csv(self, uid):
        try:
            path = os.path.join(
                os.path.expanduser("~"),
                f"attendance_{self.target.get('usn', uid)}.csv")
            self._att.to_csv(path, index=False)
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
            print(f"[attendance] → show_page('{key}')  args={kw}")

        def go_back(self):
            print("[attendance] back")

        def logout(self):
            print("[attendance] logout")

    root = ctk.CTk()
    W, H = 1280, 900
    root.geometry(f"{W}x{H}")
    root.configure(fg_color=COLORS["bg"])
    root.title(f"{APP_NAME} — attendance preview")

    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - W) // 2
    y = (sh - H) // 2
    root.geometry(f"{W}x{H}+{x}+{y}")

    app = _FakeApp()
    page = StudentAttendancePage(root, app)
    page.pack(fill="both", expand=True)
    root.mainloop()
    print("\n✅ pages/student/attendance.py OK")