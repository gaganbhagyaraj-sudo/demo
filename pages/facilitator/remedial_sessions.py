# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  pages/facilitator/remedial_sessions.py  ·  Remedial sessions manager
# =============================================================

from __future__ import annotations

import os
import sys

# --- make project root importable ---
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from datetime import datetime, timedelta

import customtkinter as ctk
import pandas as pd

from config import (
    APP_NAME, COLORS, STATUS, ZONE_COLORS, ZONE_LABELS,
    SUBJECTS, SUBJECT_COLORS, SUBJECT_SHORT,
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


def _fmt_date(iso: str) -> str:
    if not iso:
        return "—"
    try:
        d = datetime.fromisoformat(iso)
        return d.strftime("%d %b %Y, %I:%M %p")
    except Exception:
        return iso[:16]


# =============================================================
# REMEDIAL SESSIONS PAGE
# =============================================================

class FacilitatorRemedialSessionsPage(BasePage):

    def __init__(self, master, app):
        super().__init__(master, app)

        self.build_header("Remedial Sessions",
                          "Targeted support for students who need it",
                          back=False)
        self.build_sidebar(self._build_nav_items())
        self.build_content(scrollable=True)
        self.build_footer()

        # State
        self._sessions_container = None
        self._show_create = False
        self._form_refs = {}

        self.render()

    def _build_nav_items(self):
        items = _facilitator_nav()
        for it in items:
            if it["key"] == "fac_remedial":
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

        # 1. Stats
        self._render_stats(content)

        # 2. Actions row
        self._render_actions(content)

        # 3. Create form (conditional)
        if self._show_create:
            self.section_title("Create New Session", parent=content)
            self._render_create_form(content)

        # 4. Suggested students
        self.section_title("Suggested Students (At Risk)", parent=content)
        self._render_suggestions(content)

        # 5. Sessions list
        self.section_title("Your Sessions", parent=content)
        self._sessions_container = ctk.CTkFrame(content, fg_color="transparent")
        self._sessions_container.pack(fill="x", pady=(0, PAD_MD))
        self._render_sessions_list()

    # =========================================================
    # LOAD
    # =========================================================

    def _load_data(self):
        fac_id = (self.user or {}).get("id", "fac1")

        # Sessions
        try:
            self._sessions = self.db.get_remedial_sessions(
                facilitator_id=fac_id)
        except Exception:
            self._sessions = pd.DataFrame()

        # All students (for assignment)
        try:
            self._students = self.db.get_all_students()
        except Exception:
            self._students = pd.DataFrame()

        # Red-zone students
        try:
            class_marks = self.db.get_class_marks_summary(ia_number=3)
            if class_marks is None or class_marks.empty:
                self._red_students = pd.DataFrame()
            else:
                red = class_marks[class_marks["zone"] == "red"] \
                    if "zone" in class_marks.columns else pd.DataFrame()
                self._red_students = red
        except Exception:
            self._red_students = pd.DataFrame()

        # Enrollment counts per session
        self._enrollments = {}
        if self._sessions is not None and not self._sessions.empty:
            for _, s in self._sessions.iterrows():
                sid = _safe_str(s.get("id"))
                try:
                    enr = self.db.query("""
                        SELECT re.*, u.name AS student_name, u.usn AS usn
                        FROM remedial_enrollments re
                        LEFT JOIN users u ON u.id = re.user_id
                        WHERE re.session_id=?
                    """, (sid,))
                    self._enrollments[sid] = enr
                except Exception:
                    self._enrollments[sid] = pd.DataFrame()

    # =========================================================
    # STATS
    # =========================================================

    def _render_stats(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        s = self._sessions
        total = 0 if s is None else len(s)
        upcoming = 0
        completed = 0
        total_students = 0

        if s is not None and not s.empty:
            now = datetime.now()
            for _, ses in s.iterrows():
                try:
                    sched = datetime.fromisoformat(
                        _safe_str(ses.get("scheduled_at")))
                    if sched >= now:
                        upcoming += 1
                    else:
                        completed += 1
                except Exception:
                    pass

        # Enrolled students
        for enr in self._enrollments.values():
            if enr is not None and not enr.empty:
                total_students += len(enr)

        self.stat_card(
            row, total, "Total sessions",
            accent=COLORS["primary"], icon="🩺",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, upcoming, "Upcoming",
            accent=STATUS["info"], icon="🕒",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, completed, "Past",
            accent=COLORS["text_muted"], icon="✅",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, total_students, "Students enrolled",
            accent=STATUS["green"], icon="👥",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, len(self._red_students), "🔴 At-risk students",
            accent=STATUS["red"], icon="⚠️",
        ).pack(side="left")

    # =========================================================
    # ACTIONS
    # =========================================================

    def _render_actions(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        if not self._show_create:
            self.primary_button(
                row, "➕  Create New Session",
                command=self._toggle_create,
                width=220, height=42,
            ).pack(side="left")
        else:
            self.secondary_button(
                row, "✕  Cancel",
                command=self._toggle_create,
                width=140, height=42,
            ).pack(side="left")

        self.secondary_button(
            row, "🔄  Refresh",
            command=self._reload,
            width=120, height=42,
        ).pack(side="left", padx=(PAD_MD, 0))

    def _toggle_create(self):
        self._show_create = not self._show_create
        self._reload()

    # =========================================================
    # CREATE FORM
    # =========================================================

    def _render_create_form(self, parent):
        card = self.card(parent)
        card.pack(fill="x", pady=(0, PAD_MD))

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        # Row 1: Subject
        subj_row = ctk.CTkFrame(body, fg_color="transparent")
        subj_row.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            subj_row, text="Subject:",
            width=120, anchor="w",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_muted"]).pack(side="left")

        self._form_refs["subject"] = ctk.CTkOptionMenu(
            subj_row, values=SUBJECTS, width=260, height=38,
            font=FONTS["small"],
            fg_color=COLORS["surface_alt"],
            button_color=COLORS["primary"],
            button_hover_color=COLORS["primary_hover"],
            text_color=COLORS["text"],
            dropdown_fg_color=COLORS["surface_alt"],
            dropdown_text_color=COLORS["text"],
            corner_radius=10)
        self._form_refs["subject"].set(SUBJECTS[0])
        self._form_refs["subject"].pack(side="left")

        # Row 2: Topic
        topic_row = ctk.CTkFrame(body, fg_color="transparent")
        topic_row.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            topic_row, text="Topic:",
            width=120, anchor="w",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_muted"]).pack(side="left")

        self._form_refs["topic"] = ctk.CTkEntry(
            topic_row, width=480, height=38,
            font=FONTS["small"],
            fg_color=COLORS["surface_alt"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            corner_radius=10,
            placeholder_text="e.g. Fractions — common denominators")
        self._form_refs["topic"].pack(side="left")

        # Row 3: Date + Time + Duration
        dt_row = ctk.CTkFrame(body, fg_color="transparent")
        dt_row.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            dt_row, text="Date:",
            width=120, anchor="w",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_muted"]).pack(side="left")

        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        self._form_refs["date"] = ctk.CTkEntry(
            dt_row, width=150, height=38,
            font=FONTS["small"],
            fg_color=COLORS["surface_alt"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            corner_radius=10)
        self._form_refs["date"].insert(0, tomorrow)
        self._form_refs["date"].pack(side="left", padx=(0, 16))

        ctk.CTkLabel(
            dt_row, text="Time (HH:MM):",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_muted"]).pack(side="left", padx=(0, 6))

        self._form_refs["time"] = ctk.CTkEntry(
            dt_row, width=110, height=38,
            font=FONTS["small"],
            fg_color=COLORS["surface_alt"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            corner_radius=10)
        self._form_refs["time"].insert(0, "15:00")
        self._form_refs["time"].pack(side="left", padx=(0, 16))

        ctk.CTkLabel(
            dt_row, text="Duration (min):",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_muted"]).pack(side="left", padx=(0, 6))

        self._form_refs["duration"] = ctk.CTkEntry(
            dt_row, width=80, height=38,
            font=FONTS["small"],
            fg_color=COLORS["surface_alt"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            corner_radius=10)
        self._form_refs["duration"].insert(0, "45")
        self._form_refs["duration"].pack(side="left")

        # Row 4: Notes
        notes_row = ctk.CTkFrame(body, fg_color="transparent")
        notes_row.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            notes_row, text="Notes:",
            width=120, anchor="nw",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_muted"]).pack(side="left")

        self._form_refs["notes"] = ctk.CTkTextbox(
            notes_row, width=480, height=70,
            font=FONTS["small"],
            fg_color=COLORS["surface_alt"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            corner_radius=10)
        self._form_refs["notes"].pack(side="left")

        # Row 5: Error
        self._form_refs["error"] = ctk.CTkLabel(
            body, text="",
            font=FONTS["small"],
            text_color=STATUS["red"],
            wraplength=600, justify="left")
        self._form_refs["error"].pack(anchor="w", pady=(0, 10))

        # Row 6: Submit
        btn_row = ctk.CTkFrame(body, fg_color="transparent")
        btn_row.pack(fill="x")

        self.primary_button(
            btn_row, "✓  Create Session",
            command=self._submit_create,
            width=180, height=42,
        ).pack(side="left")

    def _submit_create(self):
        subject = self._form_refs["subject"].get()
        topic = (self._form_refs["topic"].get() or "").strip()
        date_str = (self._form_refs["date"].get() or "").strip()
        time_str = (self._form_refs["time"].get() or "").strip()
        dur_str = (self._form_refs["duration"].get() or "").strip()
        notes = self._form_refs["notes"].get("1.0", "end").strip()

        # Validate
        if not topic:
            self._form_refs["error"].configure(
                text="⚠️  Please enter a topic.")
            return
        try:
            scheduled_dt = datetime.strptime(
                f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        except Exception:
            self._form_refs["error"].configure(
                text="⚠️  Date must be YYYY-MM-DD and time HH:MM.")
            return
        try:
            duration = int(dur_str)
            if duration <= 0:
                raise ValueError
        except Exception:
            self._form_refs["error"].configure(
                text="⚠️  Duration must be a positive integer.")
            return

        fac_id = (self.user or {}).get("id", "fac1")

        try:
            session_id = self.db.create_remedial(
                subject=subject,
                topic=topic,
                facilitator_id=fac_id,
                scheduled_at=scheduled_dt.isoformat(),
                duration_min=duration,
                notes=notes or None,
            )
            self.toast("Session created ✓", "success")
            self._show_create = False
            self._reload()
        except Exception as e:
            self._form_refs["error"].configure(
                text=f"⚠️  Could not create session: {e}")

    # =========================================================
    # SUGGESTIONS
    # =========================================================

    def _render_suggestions(self, parent):
        card = self.card(parent)
        card.pack(fill="x", pady=(0, PAD_MD))

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        red = self._red_students
        if red is None or red.empty:
            ctk.CTkLabel(
                body, text="✅  No at-risk students — great!",
                font=FONTS["body"],
                text_color=STATUS["green"]).pack(pady=10)
            return

        ctk.CTkLabel(
            body,
            text="These students are in the Red zone. Enroll them in a "
                 "session below.",
            font=FONTS["small"],
            text_color=COLORS["text_muted"],
        ).pack(anchor="w", pady=(0, 10))

        row = ctk.CTkFrame(body, fg_color="transparent")
        row.pack(fill="x")

        for _, s in red.head(8).iterrows():
            uid = _safe_str(s.get("user_id"))
            name = _safe_str(s.get("name")) or "—"
            pct = _safe_float(s.get("percentage"))
            chip = ctk.CTkFrame(
                row,
                fg_color=STATUS["red"],
                corner_radius=CHIP_RADIUS)
            chip.pack(side="left", padx=(0, 8), pady=2)
            ctk.CTkLabel(
                chip,
                text=f"  {name}  ({pct:.0f}%)  ",
                font=(FONT_FAMILY, 10, "bold"),
                text_color="#FFFFFF").pack(padx=4, pady=3)

    # =========================================================
    # SESSIONS LIST
    # =========================================================

    def _render_sessions_list(self):
        for w in self._sessions_container.winfo_children():
            w.destroy()

        s = self._sessions
        if s is None or s.empty:
            ctk.CTkLabel(
                self._sessions_container,
                text="No sessions yet. Create one above to get started.",
                font=FONTS["body"],
                text_color=COLORS["text_muted"]).pack(pady=20)
            return

        # Sort: upcoming first (ascending), then past (descending)
        try:
            s = s.copy()
            s["_dt"] = s["scheduled_at"].apply(
                lambda x: datetime.fromisoformat(_safe_str(x))
                if _safe_str(x) else datetime.min)
            now = datetime.now()
            upcoming = s[s["_dt"] >= now].sort_values("_dt")
            past = s[s["_dt"] < now].sort_values("_dt", ascending=False)
            ordered = pd.concat([upcoming, past])
        except Exception:
            ordered = s

        for _, ses in ordered.iterrows():
            self._render_session_card(ses)

    def _render_session_card(self, ses):
        sid = _safe_str(ses.get("id"))
        subject = _safe_str(ses.get("subject")) or "—"
        topic = _safe_str(ses.get("topic")) or "—"
        scheduled = _safe_str(ses.get("scheduled_at"))
        duration = int(_safe_float(ses.get("duration_min")))
        notes = _safe_str(ses.get("notes"))
        status = _safe_str(ses.get("status")) or "scheduled"

        subj_color = SUBJECT_COLORS.get(subject, COLORS["primary"])

        # Determine if upcoming/past
        is_upcoming = False
        try:
            dt = datetime.fromisoformat(scheduled)
            is_upcoming = dt >= datetime.now()
        except Exception:
            pass

        # Status color
        status_color = STATUS["info"] if is_upcoming \
            else COLORS["text_muted"]
        status_label = "Upcoming" if is_upcoming else "Past"

        card = ctk.CTkFrame(
            self._sessions_container,
            fg_color=COLORS["surface"],
            corner_radius=CARD_RADIUS,
            border_width=1,
            border_color=subj_color)
        card.pack(fill="x", pady=4)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=PAD_LG, pady=PAD_MD)

        # Head: subject block + title
        head = ctk.CTkFrame(inner, fg_color="transparent")
        head.pack(fill="x")

        # Subject chip left
        block = ctk.CTkFrame(
            head,
            width=52, height=52,
            fg_color=subj_color,
            corner_radius=12)
        block.pack(side="left")
        block.pack_propagate(False)
        subj_short = SUBJECT_SHORT.get(subject, subject[:2].upper())
        ctk.CTkLabel(
            block, text=subj_short,
            font=(FONT_FAMILY, 14, "bold"),
            text_color="#FFFFFF").place(relx=0.5, rely=0.5, anchor="center")

        # Title
        title_box = ctk.CTkFrame(head, fg_color="transparent")
        title_box.pack(side="left", padx=(PAD_LG, 0),
                       fill="x", expand=True)

        ctk.CTkLabel(
            title_box, text=topic,
            font=(FONT_FAMILY, 14, "bold"),
            text_color=COLORS["text"], anchor="w",
            wraplength=700, justify="left",
        ).pack(anchor="w")

        meta_line = f"{subject}  ·  {duration} min  ·  {_fmt_date(scheduled)}"
        ctk.CTkLabel(
            title_box, text=meta_line,
            font=(FONT_FAMILY, 10),
            text_color=COLORS["text_muted"], anchor="w",
        ).pack(anchor="w", pady=(2, 0))

        # Right: status chip
        chip = ctk.CTkFrame(head, fg_color=status_color,
                            corner_radius=CHIP_RADIUS)
        chip.pack(side="right")
        ctk.CTkLabel(
            chip, text=f"  {status_label}  ",
            font=(FONT_FAMILY, 10, "bold"),
            text_color="#FFFFFF").pack(padx=6, pady=3)

        # Notes
        if notes:
            ctk.CTkLabel(
                inner, text=f"📝  {notes}",
                font=(FONT_FAMILY, 10),
                text_color=COLORS["text_muted"], anchor="w",
                wraplength=900, justify="left",
            ).pack(anchor="w", pady=(8, 0))

        # Enrollments
        enr = self._enrollments.get(sid, pd.DataFrame())
        ctk.CTkLabel(
            inner, text=f"👥  Enrolled: {len(enr)} students",
            font=(FONT_FAMILY, 10, "bold"),
            text_color=COLORS["text_muted"], anchor="w",
        ).pack(anchor="w", pady=(8, 6))

        # Show first 6 enrolled
        if not enr.empty:
            chip_row = ctk.CTkFrame(inner, fg_color="transparent")
            chip_row.pack(fill="x", pady=(0, 6))

            for _, e in enr.head(6).iterrows():
                sname = _safe_str(e.get("student_name")) or "—"
                attended = bool(e.get("attended"))

                chip_color = STATUS["green"] if attended \
                    else COLORS["surface_alt"]

                c = ctk.CTkFrame(
                    chip_row, fg_color=chip_color,
                    corner_radius=CHIP_RADIUS)
                c.pack(side="left", padx=(0, 6), pady=2)
                ctk.CTkLabel(
                    c,
                    text=f"  {sname}  ",
                    font=(FONT_FAMILY, 10),
                    text_color=COLORS["text"] if attended else COLORS["text"],
                ).pack(padx=4, pady=3)

        # Actions row
        actions = ctk.CTkFrame(inner, fg_color="transparent")
        actions.pack(fill="x", pady=(10, 0))

        self.secondary_button(
            actions, "👥 Assign students",
            command=lambda s_id=sid, s_subj=subject: self._assign_students(
                s_id, s_subj),
            width=170, height=32,
        ).pack(side="left", padx=(0, 8))

        if is_upcoming:
            self.primary_button(
                actions, "✓  Mark complete",
                command=lambda s_id=sid: self._mark_session_complete(s_id),
                width=170, height=32,
            ).pack(side="left")
        else:
            ctk.CTkLabel(
                actions, text=f"Status: {status.title()}",
                font=(FONT_FAMILY, 10, "bold"),
                text_color=COLORS["text_muted"],
            ).pack(side="left")

    # =========================================================
    # ACTIONS
    # =========================================================

    def _assign_students(self, session_id: str, subject: str):
        """Quick-assign red-zone students to a session."""
        red = self._red_students
        if red is None or red.empty:
            self.toast("No at-risk students to assign.", "info")
            return

        def on_confirm():
            assigned = 0
            for _, r in red.iterrows():
                uid = _safe_str(r.get("user_id"))
                if not uid:
                    continue
                try:
                    # Check if already enrolled
                    existing = self.db.query("""
                        SELECT 1 FROM remedial_enrollments
                        WHERE session_id=? AND user_id=?
                    """, (session_id, uid))
                    if not existing.empty:
                        continue
                    self.db.enroll_remedial(session_id, uid)
                    assigned += 1
                except Exception:
                    pass

            if assigned > 0:
                self.toast(f"Enrolled {assigned} student(s).", "success")
            else:
                self.toast("All at-risk students already enrolled.", "info")
            self._reload()

        self.confirm(
            f"Enroll at-risk students?",
            f"This will add {len(red)} student(s) in the red zone to this "
            f"{subject} session.",
            on_yes=on_confirm,
            yes_text="Enroll all",
        )

    def _mark_session_complete(self, session_id: str):
        try:
            self.db.execute(
                "UPDATE remedial_sessions SET status='completed' WHERE id=?",
                (session_id,))
            self.toast("Session marked complete.", "success")
            self._reload()
        except Exception as e:
            self.toast(f"Could not update: {e}", "error")

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
            print(f"[remedial] → show_page('{key}')  args={kw}")

        def go_back(self):
            print("[remedial] back")

        def logout(self):
            print("[remedial] logout")

    root = ctk.CTk()
    W, H = 1400, 900
    root.geometry(f"{W}x{H}")
    root.configure(fg_color=COLORS["bg"])
    root.title(f"{APP_NAME} — remedial sessions")

    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - W) // 2
    y = (sh - H) // 2
    root.geometry(f"{W}x{H}+{x}+{y}")

    app = _FakeApp()
    page = FacilitatorRemedialSessionsPage(root, app)
    page.pack(fill="both", expand=True)
    root.mainloop()
    print("\n✅ pages/facilitator/remedial_sessions.py OK")