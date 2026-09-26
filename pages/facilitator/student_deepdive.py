# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  pages/facilitator/student_deepdive.py  ·  Student deep-dive
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
    APP_NAME, COLORS, STATUS, ZONE_COLORS, ZONE_LABELS,
    SUBJECTS, SUBJECT_SHORT, IA_LIST,
    ATTENDANCE_STATUS, ATTENDANCE_COLORS,
    FONTS, FONT_FAMILY,
    CARD_RADIUS, BUTTON_RADIUS, CHIP_RADIUS,
    PAD_SM, PAD_MD, PAD_LG, PAD_XL,
)
from pages.base_page import BasePage
from utils.avatars import load_avatar
from utils.charts import gauge_chart, ia_trend_chart, radar_chart
from models.bkt import BKTTracker
from models.badges import BadgeEngine


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
# STUDENT DEEP-DIVE
# =============================================================

class FacilitatorStudentDeepdivePage(BasePage):

    def __init__(self, master, app, user_id: str = None):
        super().__init__(master, app)

        self.target_id = user_id
        self.target = self.db.get_user(self.target_id) if self.target_id else None

        name = self.target.get("name", "Student") if self.target else "Student"
        self.build_header(name, "Full academic record", back=True)
        self.build_sidebar(self._build_nav_items())
        self.build_content(scrollable=True)
        self.build_footer()

        self._tracker = BKTTracker(self.db)
        self._badges = BadgeEngine(self.db)

        self.render()

    def _build_nav_items(self):
        items = _facilitator_nav()
        for it in items:
            if it["key"] == "fac_roster":
                it["active"] = True
            it["command"] = (lambda k=it["key"]: self.navigate(k))
        return items

    # =========================================================
    # RENDER
    # =========================================================

    def render(self):
        if not self.target:
            self._render_empty("Student not found.")
            return

        uid = self.target["id"]
        content = self._content

        # Load data
        self._load_data(uid)

        # 1. Hero card (avatar + name + zone + quick actions)
        self._render_hero(content)

        # 2. KPI row
        self._render_kpis(content)

        # 3. Two-column: Marks table | Gauge + Trend
        cols = ctk.CTkFrame(content, fg_color="transparent")
        cols.pack(fill="x", pady=(0, PAD_MD))

        left = ctk.CTkFrame(cols, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=(0, PAD_MD))

        right = ctk.CTkFrame(cols, fg_color="transparent")
        right.pack(side="left", fill="both", expand=False)

        self.section_title("Marks Summary", parent=left)
        self._render_marks_table(left)

        self.section_title("Current IA Score", parent=right)
        self._render_gauge(right)

        # 4. Trend chart
        self.section_title("IA Trend", parent=content)
        self._render_ia_trend(content)

        # 5. Mastery mini + attendance mini
        cols2 = ctk.CTkFrame(content, fg_color="transparent")
        cols2.pack(fill="x", pady=(0, PAD_MD))

        m_left = ctk.CTkFrame(cols2, fg_color="transparent")
        m_left.pack(side="left", fill="both", expand=True, padx=(0, PAD_MD))

        m_right = ctk.CTkFrame(cols2, fg_color="transparent")
        m_right.pack(side="left", fill="both", expand=True)

        self.section_title("Mastery Snapshot", parent=m_left)
        self._render_mastery_snapshot(m_left)

        self.section_title("Attendance Snapshot", parent=m_right)
        self._render_attendance_snapshot(m_right)

        # 6. Badges
        self.section_title("Badges Earned", parent=content)
        self._render_badges(content)

        # 7. Recent interventions
        self.section_title("Interventions History", parent=content)
        self._render_interventions(content)

        # 8. Recent attempts log
        self.section_title("Recent Attempts", parent=content)
        self._render_attempts(content)

    # =========================================================
    # DATA
    # =========================================================

    def _load_data(self, uid):
        # Marks summary
        try:
            self._marks_summary = self.db.get_marks_summary(uid)
        except Exception:
            self._marks_summary = pd.DataFrame()

        # Full marks
        try:
            self._all_marks = self.db.get_marks(uid)
        except Exception:
            self._all_marks = pd.DataFrame()

        # Attendance
        try:
            self._attendance = self.db.get_attendance(uid, days=60)
        except Exception:
            self._attendance = pd.DataFrame()

        # Badges
        try:
            self._user_badges = self.db.get_user_badges(uid)
        except Exception:
            self._user_badges = pd.DataFrame()

        # Interventions for this student
        try:
            self._interventions = self.db.get_interventions(
                student_id=uid)
        except Exception:
            self._interventions = pd.DataFrame()

        # Recent attempts
        try:
            self._attempts = self.db.query("""
                SELECT a.*, c.name AS concept_name
                FROM attempts a
                LEFT JOIN concepts c ON c.id = a.concept_id
                WHERE a.user_id=?
                ORDER BY a.created_at DESC
                LIMIT 15
            """, (uid,))
        except Exception:
            self._attempts = pd.DataFrame()

        # Mastery overall
        try:
            self._overall_mastery = self._tracker.overall_mastery(uid)
        except Exception:
            self._overall_mastery = {"avg_mastery": 0, "mastered": 0,
                                     "developing": 0, "weak": 0,
                                     "total_concepts": 0}

        # Latest IA
        try:
            ia_df = self.db.query(
                "SELECT MAX(ia_number) AS ia FROM marks_summary WHERE user_id=?",
                (uid,))
            self._latest_ia = int(ia_df.iloc[0]["ia"] or 3)
        except Exception:
            self._latest_ia = 3

    # =========================================================
    # HERO
    # =========================================================

    def _render_hero(self, parent):
        user = self.target
        uid = user["id"]

        card = self.card(parent)
        card.pack(fill="x", pady=(0, PAD_MD))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        # Get zone
        zone = self._current_zone()
        zone_color = ZONE_COLORS.get(zone, COLORS["primary"])
        zone_label = ZONE_LABELS.get(zone, zone.title())

        # Avatar
        try:
            avatar = load_avatar(
                user_id=uid,
                name=user.get("name", ""),
                size=110,
                shape="circle",
                zone=zone,
                ring_width=6 if zone else 0,
            )
            ctk.CTkLabel(inner, image=avatar, text="").pack(side="left")
        except Exception:
            pass

        # Info
        info = ctk.CTkFrame(inner, fg_color="transparent")
        info.pack(side="left", padx=(PAD_LG, 0),
                  fill="both", expand=True)

        ctk.CTkLabel(
            info, text=user.get("name", "—"),
            font=(FONT_FAMILY, 22, "bold"),
            text_color=COLORS["text"], anchor="w",
        ).pack(anchor="w")

        meta_parts = []
        if user.get("usn"):
            meta_parts.append(f"USN: {user['usn']}")
        if user.get("grade"):
            meta_parts.append(user["grade"])
        if user.get("section"):
            meta_parts.append(f"Sec {user['section']}")

        ctk.CTkLabel(
            info, text="   ·   ".join(meta_parts) or "Student",
            font=FONTS["small"],
            text_color=COLORS["text_muted"], anchor="w",
        ).pack(anchor="w", pady=(2, 8))

        # Zone chip
        chip = ctk.CTkFrame(info, fg_color=zone_color,
                            corner_radius=CHIP_RADIUS)
        chip.pack(anchor="w")
        ctk.CTkLabel(
            chip,
            text=f"  {zone_label}  ",
            font=(FONT_FAMILY, 10, "bold"),
            text_color="#FFFFFF",
        ).pack(padx=6, pady=4)

        # Right: quick actions
        actions = ctk.CTkFrame(inner, fg_color="transparent")
        actions.pack(side="right")

        self.primary_button(
            actions, "📩  Message",
            command=lambda: self._send_message(),
            width=140, height=38,
        ).pack(pady=(0, 6))

        self.secondary_button(
            actions, "🩺  Assign Remedial",
            command=lambda: self._assign_remedial(),
            width=180, height=34,
        ).pack(pady=(0, 6))

        self.secondary_button(
            actions, "📅  Schedule 1:1",
            command=lambda: self._schedule_meeting(),
            width=180, height=34,
        ).pack(pady=(0, 6))

        self.secondary_button(
            actions, "📄  Full report",
            command=lambda: self.navigate("fac_reports",
                                          user_id=uid),
            width=180, height=34,
        ).pack()

    # =========================================================
    # KPIs
    # =========================================================

    def _render_kpis(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        # Latest %
        latest_pct = 0.0
        grade = "—"
        if self._marks_summary is not None and not self._marks_summary.empty:
            latest = self._marks_summary.iloc[-1]
            latest_pct = _safe_float(latest.get("percentage"))
            grade = _safe_str(latest.get("grade")) or "—"

        # Attendance
        att_pct = self._attendance_percent()

        # Badges
        n_badges = 0 if self._user_badges is None else len(self._user_badges)

        # Mastery
        m = self._overall_mastery
        avg_m = _safe_float(m.get("avg_mastery")) * 100

        self.stat_card(
            row, f"{latest_pct:.1f}%",
            f"Latest IA ({grade})",
            accent=ZONE_COLORS.get(self._current_zone(), COLORS["primary"]),
            icon="📊",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, f"{att_pct:.0f}%", "Attendance (60d)",
            accent=STATUS["green"] if att_pct >= 85
                   else (STATUS["amber"] if att_pct >= 70 else STATUS["red"]),
            icon="📅",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, n_badges, "Badges",
            accent=STATUS["gold"], icon="🏅",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, f"{avg_m:.0f}%", "Avg mastery",
            accent=STATUS["green"] if avg_m >= 75
                   else (STATUS["amber"] if avg_m >= 40 else STATUS["red"]),
            icon="🎯",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, m.get("weak", 0), "Weak concepts",
            accent=STATUS["red"], icon="⚠️",
        ).pack(side="left")

    # =========================================================
    # MARKS TABLE
    # =========================================================

    def _render_marks_table(self, parent):
        card = self.card(parent)
        card.pack(fill="x")

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        ms = self._marks_summary
        if ms is None or ms.empty:
            ctk.CTkLabel(
                body, text="No marks recorded yet.",
                font=FONTS["small"],
                text_color=COLORS["text_muted"]).pack()
            return

        headers = ["IA", "Maths", "Phy", "Che", "CS", "Total", "%", "Grade"]
        grid = ctk.CTkFrame(body, fg_color="transparent")
        grid.pack(fill="x")

        for i, h in enumerate(headers):
            ctk.CTkLabel(
                grid, text=h,
                font=(FONT_FAMILY, 10, "bold"),
                text_color=COLORS["text_muted"],
            ).grid(row=0, column=i, padx=6, pady=6, sticky="w")

        for r, (_, row) in enumerate(ms.iterrows(), start=1):
            data = [
                f"IA-{int(row.get('ia_number', 0))}",
                f"{_safe_float(row.get('maths')):.0f}",
                f"{_safe_float(row.get('phy')):.0f}",
                f"{_safe_float(row.get('che')):.0f}",
                f"{_safe_float(row.get('cs')):.0f}",
                f"{int(_safe_float(row.get('total')))}",
                f"{_safe_float(row.get('percentage')):.1f}%",
                _safe_str(row.get("grade")) or "—",
            ]
            zone = _safe_str(row.get("zone"))
            grade_color = ZONE_COLORS.get(zone, COLORS["text"])
            for i, val in enumerate(data):
                color = grade_color if i == 7 else COLORS["text"]
                ctk.CTkLabel(
                    grid, text=val,
                    font=(FONT_FAMILY, 10),
                    text_color=color,
                ).grid(row=r, column=i, padx=6, pady=4, sticky="w")

    # =========================================================
    # GAUGE
    # =========================================================

    def _render_gauge(self, parent):
        card = self.card(parent, width=340)
        card.pack_propagate(False)
        card.pack(fill="both", expand=True)

        try:
            latest_pct = 0.0
            zone = self._current_zone() or "yellow"
            if self._marks_summary is not None and not self._marks_summary.empty:
                latest_pct = _safe_float(
                    self._marks_summary.iloc[-1].get("percentage"))

            fig = gauge_chart(
                latest_pct,
                label=f"IA-{self._latest_ia}",
                color=ZONE_COLORS.get(zone, COLORS["primary"]),
                animate=False,
                figsize=(3.2, 3.2),
            )
            self.chart_frame(card, fig, height=290).pack(
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
            marks = self._all_marks
            if marks is None or marks.empty:
                ctk.CTkLabel(
                    parent, text="No trend data yet.",
                    font=FONTS["small"],
                    text_color=COLORS["text_muted"]).pack()
                return

            ia_data = {}
            for subj in SUBJECTS:
                vals = []
                for ia in (1, 2, 3):
                    sub = marks[(marks["ia_number"] == ia)
                                & (marks["subject"] == subj)]
                    vals.append(_safe_float(sub.iloc[0]["marks"])
                                if not sub.empty else 0.0)
                ia_data[subj] = vals

            fig = ia_trend_chart(ia_data,
                                 title="IA Performance Trend",
                                 animate=False)
            self.chart_frame(parent, fig, height=300).pack(
                fill="x", pady=(0, PAD_MD))
        except Exception as e:
            ctk.CTkLabel(parent, text=f"(trend unavailable: {e})",
                         font=FONTS["tiny"],
                         text_color=COLORS["text_muted"]).pack()

    # =========================================================
    # MASTERY SNAPSHOT
    # =========================================================

    def _render_mastery_snapshot(self, parent):
        card = self.card(parent)
        card.pack(fill="x")

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        m = self._overall_mastery
        row = ctk.CTkFrame(body, fg_color="transparent")
        row.pack(fill="x")

        stats = [
            ("Mastered", m.get("mastered", 0), STATUS["green"]),
            ("Developing", m.get("developing", 0), STATUS["amber"]),
            ("Weak", m.get("weak", 0), STATUS["red"]),
        ]

        for label, value, color in stats:
            box = ctk.CTkFrame(row, fg_color="transparent")
            box.pack(side="left", expand=True)
            ctk.CTkLabel(
                box, text=str(value),
                font=(FONT_FAMILY, 20, "bold"),
                text_color=color).pack()
            ctk.CTkLabel(
                box, text=label,
                font=(FONT_FAMILY, 9),
                text_color=COLORS["text_muted"]).pack()

        # Weak concepts list
        try:
            weak = self._tracker.weak_concepts(self.target["id"], threshold=0.4)
            if weak is not None and not weak.empty:
                ctk.CTkLabel(
                    body, text="Weak concepts:",
                    font=(FONT_FAMILY, 10, "bold"),
                    text_color=COLORS["text_muted"]).pack(
                    anchor="w", pady=(14, 6))
                for _, w in weak.head(4).iterrows():
                    row = ctk.CTkFrame(body, fg_color=COLORS["surface_alt"],
                                       corner_radius=6)
                    row.pack(fill="x", pady=2)
                    ctk.CTkLabel(
                        row, text=_safe_str(w.get("name")) or "—",
                        font=(FONT_FAMILY, 10),
                        text_color=COLORS["text"], anchor="w",
                    ).pack(side="left", padx=8, pady=4)
                    ctk.CTkLabel(
                        row,
                        text=f"{_safe_float(w.get('p_mastery'))*100:.0f}%",
                        font=(FONT_FAMILY, 10, "bold"),
                        text_color=STATUS["red"],
                    ).pack(side="right", padx=8)
        except Exception:
            pass

    # =========================================================
    # ATTENDANCE SNAPSHOT
    # =========================================================

    def _render_attendance_snapshot(self, parent):
        card = self.card(parent)
        card.pack(fill="x")

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        att = self._attendance
        if att is None or att.empty:
            ctk.CTkLabel(
                body, text="No attendance data.",
                font=FONTS["small"],
                text_color=COLORS["text_muted"]).pack()
            return

        # Counts
        counts = att["status"].value_counts().to_dict()
        present = counts.get("P", 0) + counts.get("L", 0) + counts.get("E", 0)
        absent = counts.get("A", 0)
        late = counts.get("L", 0)
        total = len(att)
        pct = (present / total * 100) if total else 0

        row = ctk.CTkFrame(body, fg_color="transparent")
        row.pack(fill="x")

        stats = [
            (f"{pct:.0f}%", "Present %",
             STATUS["green"] if pct >= 85
             else (STATUS["amber"] if pct >= 70 else STATUS["red"])),
            (str(present), "Days present", STATUS["green"]),
            (str(absent), "Days absent", STATUS["red"]),
            (str(late), "Late", STATUS["amber"]),
        ]

        for value, label, color in stats:
            box = ctk.CTkFrame(row, fg_color="transparent")
            box.pack(side="left", expand=True)
            ctk.CTkLabel(
                box, text=value,
                font=(FONT_FAMILY, 18, "bold"),
                text_color=color).pack()
            ctk.CTkLabel(
                box, text=label,
                font=(FONT_FAMILY, 9),
                text_color=COLORS["text_muted"]).pack()

        # Last 5 records
        try:
            recent = att.sort_values("att_date", ascending=False).head(5)
            ctk.CTkLabel(
                body, text="Last 5 days:",
                font=(FONT_FAMILY, 10, "bold"),
                text_color=COLORS["text_muted"]).pack(
                anchor="w", pady=(14, 6))
            for _, a in recent.iterrows():
                status = _safe_str(a.get("status")) or "—"
                color = ATTENDANCE_COLORS.get(status, COLORS["text_muted"])
                rec = ctk.CTkFrame(body, fg_color=COLORS["surface_alt"],
                                   corner_radius=6)
                rec.pack(fill="x", pady=2)
                ctk.CTkLabel(
                    rec, text=_safe_str(a.get("att_date"))[:10],
                    font=(FONT_FAMILY, 10),
                    text_color=COLORS["text"], anchor="w",
                ).pack(side="left", padx=8, pady=4)
                ctk.CTkLabel(
                    rec, text=f"  {status}  ",
                    font=(FONT_FAMILY, 10, "bold"),
                    text_color="#FFFFFF",
                    fg_color=color,
                ).pack(side="right", padx=6, pady=3)
        except Exception:
            pass

    # =========================================================
    # BADGES
    # =========================================================

    def _render_badges(self, parent):
        card = self.card(parent)
        card.pack(fill="x", pady=(0, PAD_MD))

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        badges = self._user_badges
        if badges is None or badges.empty:
            ctk.CTkLabel(
                body, text="No badges earned yet.",
                font=FONTS["small"],
                text_color=COLORS["text_muted"]).pack()
            return

        row = ctk.CTkFrame(body, fg_color="transparent")
        row.pack(fill="x")

        for _, b in badges.iterrows():
            chip = ctk.CTkFrame(
                row,
                fg_color=COLORS["surface_alt"],
                corner_radius=CHIP_RADIUS)
            chip.pack(side="left", padx=(0, PAD_SM), pady=2)

            color = _safe_str(b.get("color")) or STATUS["gold"]
            ctk.CTkLabel(
                chip,
                text=f"  {_safe_str(b.get('icon')) or '🏅'}  {_safe_str(b.get('name')) or '—'}  ",
                font=(FONT_FAMILY, 10, "bold"),
                text_color=color,
            ).pack(padx=4, pady=4)

    # =========================================================
    # INTERVENTIONS
    # =========================================================

    def _render_interventions(self, parent):
        card = self.card(parent)
        card.pack(fill="x", pady=(0, PAD_MD))

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        iv = self._interventions
        if iv is None or iv.empty:
            ctk.CTkLabel(
                body, text="No interventions logged for this student yet.",
                font=FONTS["small"],
                text_color=COLORS["text_muted"]).pack()
            return

        for _, r in iv.head(8).iterrows():
            row = ctk.CTkFrame(body, fg_color=COLORS["surface_alt"],
                               corner_radius=8)
            row.pack(fill="x", pady=3)

            inner = ctk.CTkFrame(row, fg_color="transparent")
            inner.pack(fill="x", padx=10, pady=8)

            ctk.CTkLabel(
                inner, text=_safe_str(r.get("itype", "action")).title(),
                font=(FONT_FAMILY, 11, "bold"),
                text_color=COLORS["text"], anchor="w",
            ).pack(anchor="w")

            ctk.CTkLabel(
                inner, text=_safe_str(r.get("created_at"))[:16],
                font=(FONT_FAMILY, 9),
                text_color=COLORS["text_muted"], anchor="w",
            ).pack(anchor="w")

    # =========================================================
    # ATTEMPTS
    # =========================================================

    def _render_attempts(self, parent):
        card = self.card(parent)
        card.pack(fill="x", pady=(0, PAD_MD))

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        att = self._attempts
        if att is None or att.empty:
            ctk.CTkLabel(
                body, text="No attempts recorded.",
                font=FONTS["small"],
                text_color=COLORS["text_muted"]).pack()
            return

        # Header
        header = ctk.CTkFrame(body, fg_color="transparent")
        header.pack(fill="x", pady=(0, 6))
        for txt, w in [("When", 160), ("Concept", 220),
                       ("Result", 120), ("Hints", 80)]:
            ctk.CTkLabel(
                header, text=txt, width=w, anchor="w",
                font=(FONT_FAMILY, 10, "bold"),
                text_color=COLORS["text_muted"]).pack(side="left")

        for _, a in att.iterrows():
            row = ctk.CTkFrame(body, fg_color=COLORS["surface_alt"],
                               corner_radius=6)
            row.pack(fill="x", pady=2)

            ctk.CTkLabel(
                row, text=_safe_str(a.get("created_at"))[:16],
                width=160, anchor="w",
                font=(FONT_FAMILY, 10),
                text_color=COLORS["text"],
            ).pack(side="left", padx=(8, 0), pady=4)

            ctk.CTkLabel(
                row, text=_safe_str(a.get("concept_name")) or "—",
                width=220, anchor="w",
                font=(FONT_FAMILY, 10),
                text_color=COLORS["text_muted"],
            ).pack(side="left")

            correct = bool(a.get("correct"))
            result_color = STATUS["green"] if correct else STATUS["red"]
            ctk.CTkLabel(
                row, text="✓ Correct" if correct else "✗ Wrong",
                width=120, anchor="w",
                font=(FONT_FAMILY, 10, "bold"),
                text_color=result_color,
            ).pack(side="left")

            ctk.CTkLabel(
                row, text=str(int(_safe_float(a.get("hints_used")))),
                width=80, anchor="w",
                font=(FONT_FAMILY, 10),
                text_color=COLORS["text_muted"],
            ).pack(side="left")

    # =========================================================
    # ACTIONS
    # =========================================================

    def _send_message(self):
        self.toast(
            f"Message composer for {self.target.get('name', '')} coming soon.",
            "info")

    def _assign_remedial(self):
        try:
            self.navigate("fac_remedial", user_id=self.target["id"])
        except Exception:
            self.toast("Navigate to Remedial to assign a session.", "info")

    def _schedule_meeting(self):
        self.toast("Schedule a 1:1 session — coming soon.", "info")

    # =========================================================
    # HELPERS
    # =========================================================

    def _current_zone(self):
        try:
            if self._marks_summary is not None and not self._marks_summary.empty:
                return _safe_str(self._marks_summary.iloc[-1].get("zone")) \
                    or "yellow"
        except Exception:
            pass
        return "yellow"

    def _attendance_percent(self):
        att = self._attendance
        if att is None or att.empty:
            return 0.0
        try:
            present = (att["status"].isin(["P", "L", "E"])).sum()
            return (present / len(att)) * 100
        except Exception:
            return 0.0

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
            print(f"[deepdive] → show_page('{key}')  args={kw}")

        def go_back(self):
            print("[deepdive] back")

        def logout(self):
            print("[deepdive] logout")

    root = ctk.CTk()
    W, H = 1400, 900
    root.geometry(f"{W}x{H}")
    root.configure(fg_color=COLORS["bg"])
    root.title(f"{APP_NAME} — student deep-dive")

    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - W) // 2
    y = (sh - H) // 2
    root.geometry(f"{W}x{H}+{x}+{y}")

    app = _FakeApp()

    # Pick a student
    stu_id = None
    if app.db:
        try:
            stu_id = app.db.get_all_students().iloc[0]["id"]
        except Exception:
            pass

    page = FacilitatorStudentDeepdivePage(root, app, user_id=stu_id)
    page.pack(fill="both", expand=True)
    root.mainloop()
    print("\n✅ pages/facilitator/student_deepdive.py OK")