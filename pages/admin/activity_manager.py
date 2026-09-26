# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  pages/admin/activity_manager.py  ·  Activity management
# =============================================================

from __future__ import annotations

import os
import sys

# --- make project root importable ---
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import uuid
from datetime import datetime

import customtkinter as ctk
import pandas as pd

from config import (
    APP_NAME, COLORS, STATUS,
    ACTIVITY_TYPES,
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


ACTIVITY_META = {a["id"]: a for a in ACTIVITY_TYPES}


# =============================================================
# ACTIVITY MANAGER PAGE
# =============================================================

class AdminActivityManagerPage(BasePage):

    def __init__(self, master, app):
        super().__init__(master, app)

        self.build_header("Activity Manager",
                          "Create and manage co-curricular activities",
                          back=False)
        self.build_sidebar(self._build_nav_items())
        self.build_content(scrollable=True)
        self.build_footer()

        # State
        self._show_create = False
        self._list_container = None
        self._form_refs = {}

        self.render()

    def _build_nav_items(self):
        items = _admin_nav()
        for it in items:
            if it["key"] == "admin_activities":
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

        # 2. Actions
        self._render_actions(content)

        # 3. Create form (conditional)
        if self._show_create:
            self.section_title("Create New Activity", parent=content)
            self._render_create_form(content)

        # 4. Activities list
        self.section_title("All Activities", parent=content)
        self._list_container = ctk.CTkFrame(content, fg_color="transparent")
        self._list_container.pack(fill="x", pady=(0, PAD_MD))
        self._render_list()

    # =========================================================
    # LOAD
    # =========================================================

    def _load_data(self):
        # All activities
        try:
            self._activities = self.db.get_activities()
        except Exception:
            self._activities = pd.DataFrame()

        # Score counts per activity
        try:
            self._scores = self.db.query("""
                SELECT activity_id,
                       COUNT(*) AS n,
                       AVG(percentage) AS avg_pct,
                       MAX(percentage) AS max_pct
                FROM activity_scores
                GROUP BY activity_id
            """)
        except Exception:
            self._scores = pd.DataFrame()

        # Students (for manual scoring)
        try:
            self._students = self.db.get_all_students()
        except Exception:
            self._students = pd.DataFrame()

        # Map: activity_id -> stats
        self._score_map = {}
        if self._scores is not None and not self._scores.empty:
            for _, r in self._scores.iterrows():
                self._score_map[_safe_str(r.get("activity_id"))] = {
                    "n":       int(_safe_float(r.get("n"))),
                    "avg_pct": _safe_float(r.get("avg_pct")),
                    "max_pct": _safe_float(r.get("max_pct")),
                }

    # =========================================================
    # STATS
    # =========================================================

    def _render_stats(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        acts = self._activities
        total = 0 if acts is None else len(acts)

        # By type
        by_type = {}
        if acts is not None and not acts.empty:
            for _, r in acts.iterrows():
                t = _safe_str(r.get("type")).lower()
                by_type[t] = by_type.get(t, 0) + 1

        # Total scores logged
        total_scores = 0
        if self._scores is not None and not self._scores.empty:
            total_scores = int(self._scores["n"].sum())

        # Students who logged anything
        unique_students = 0
        try:
            df = self.db.query("""
                SELECT COUNT(DISTINCT user_id) AS n
                FROM activity_scores
            """)
            unique_students = int(df.iloc[0]["n"]) if not df.empty else 0
        except Exception:
            pass

        self.stat_card(
            row, total, "Total activities",
            accent=COLORS["primary"], icon="🎗️",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, total_scores, "Scores logged",
            accent=STATUS["green"], icon="✅",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, unique_students, "Students active",
            accent=STATUS["info"], icon="👥",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, len(by_type), f"Of {len(ACTIVITY_TYPES)} types",
            accent=STATUS["purple"], icon="🎯",
        ).pack(side="left")

    # =========================================================
    # ACTIONS
    # =========================================================

    def _render_actions(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        if not self._show_create:
            self.primary_button(
                row, "➕  Create New Activity",
                command=self._toggle_create,
                width=240, height=42,
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

        # Name
        name_row = ctk.CTkFrame(body, fg_color="transparent")
        name_row.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            name_row, text="Name:",
            width=140, anchor="w",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_muted"]).pack(side="left")

        self._form_refs["name"] = ctk.CTkEntry(
            name_row, width=420, height=38,
            font=FONTS["small"],
            fg_color=COLORS["surface_alt"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            corner_radius=10,
            placeholder_text="e.g. Aptitude Test 2")
        self._form_refs["name"].pack(side="left")

        # Type
        type_row = ctk.CTkFrame(body, fg_color="transparent")
        type_row.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            type_row, text="Type:",
            width=140, anchor="w",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_muted"]).pack(side="left")

        type_values = [f"{a['icon']}  {a['name']}" for a in ACTIVITY_TYPES]
        self._type_lookup = {f"{a['icon']}  {a['name']}": a["id"]
                             for a in ACTIVITY_TYPES}

        self._form_refs["type"] = ctk.CTkOptionMenu(
            type_row, values=type_values, width=420, height=38,
            font=FONTS["small"],
            fg_color=COLORS["surface_alt"],
            button_color=COLORS["primary"],
            button_hover_color=COLORS["primary_hover"],
            text_color=COLORS["text"],
            dropdown_fg_color=COLORS["surface_alt"],
            dropdown_text_color=COLORS["text"],
            corner_radius=10)
        self._form_refs["type"].set(type_values[0])
        self._form_refs["type"].pack(side="left")

        # Subject (optional)
        subj_row = ctk.CTkFrame(body, fg_color="transparent")
        subj_row.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            subj_row, text="Subject (optional):",
            width=140, anchor="w",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_muted"]).pack(side="left")

        self._form_refs["subject"] = ctk.CTkEntry(
            subj_row, width=420, height=38,
            font=FONTS["small"],
            fg_color=COLORS["surface_alt"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            corner_radius=10,
            placeholder_text="e.g. Maths (leave blank for generic)")
        self._form_refs["subject"].pack(side="left")

        # Max score
        ms_row = ctk.CTkFrame(body, fg_color="transparent")
        ms_row.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            ms_row, text="Max score:",
            width=140, anchor="w",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_muted"]).pack(side="left")

        self._form_refs["max_score"] = ctk.CTkEntry(
            ms_row, width=140, height=38,
            font=FONTS["small"],
            fg_color=COLORS["surface_alt"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            corner_radius=10)
        self._form_refs["max_score"].insert(0, "100")
        self._form_refs["max_score"].pack(side="left")

        # Error label
        self._form_refs["error"] = ctk.CTkLabel(
            body, text="",
            font=(FONT_FAMILY, 10),
            text_color=STATUS["red"],
            wraplength=600, justify="left")
        self._form_refs["error"].pack(anchor="w", pady=(0, 10))

        # Submit
        btn_row = ctk.CTkFrame(body, fg_color="transparent")
        btn_row.pack(fill="x")

        self.primary_button(
            btn_row, "✓  Create Activity",
            command=self._submit_create,
            width=200, height=42,
        ).pack(side="left")

    def _submit_create(self):
        name = (self._form_refs["name"].get() or "").strip()
        type_label = self._form_refs["type"].get()
        subject = (self._form_refs["subject"].get() or "").strip() or None
        max_str = (self._form_refs["max_score"].get() or "").strip()

        # Validate
        if not name:
            self._form_refs["error"].configure(
                text="⚠️  Please enter a name.")
            return

        atype = self._type_lookup.get(type_label, "quiz")

        try:
            max_score = float(max_str)
            if max_score <= 0:
                raise ValueError
        except Exception:
            self._form_refs["error"].configure(
                text="⚠️  Max score must be a positive number.")
            return

        # Check duplicate name
        try:
            existing = self.db.query(
                "SELECT 1 FROM activities WHERE name=?", (name,))
            if not existing.empty:
                self._form_refs["error"].configure(
                    text="⚠️  An activity with this name already exists.")
                return
        except Exception:
            pass

        admin_id = (self.user or {}).get("id", "admin")

        try:
            activity_id = str(uuid.uuid4())
            now = datetime.now().isoformat()

            self.db.execute("""
                INSERT INTO activities
                    (id, name, type, subject, max_score, created_at)
                VALUES (?,?,?,?,?,?)
            """, (activity_id, name, atype, subject, max_score, now))

            self.db.log_audit(
                admin_id, "create_activity",
                target=name, details=f"type={atype}")

            self.toast(f"Activity '{name}' created.", "success")
            self._show_create = False
            self._reload()
        except Exception as e:
            self._form_refs["error"].configure(
                text=f"⚠️  Could not create activity: {e}")

    # =========================================================
    # LIST
    # =========================================================

    def _render_list(self):
        for w in self._list_container.winfo_children():
            w.destroy()

        acts = self._activities
        if acts is None or acts.empty:
            ctk.CTkLabel(
                self._list_container,
                text="No activities yet. Create one above to get started.",
                font=FONTS["body"],
                text_color=COLORS["text_muted"]).pack(pady=30)
            return

        for _, a in acts.iterrows():
            self._render_activity_card(a)

    def _render_activity_card(self, a):
        aid = _safe_str(a.get("id"))
        name = _safe_str(a.get("name")) or "—"
        atype = _safe_str(a.get("type")).lower()
        subject = _safe_str(a.get("subject"))
        max_score = _safe_float(a.get("max_score"), 100)

        # Activity meta
        meta = ACTIVITY_META.get(atype, {})
        icon = meta.get("icon", "🎗️")
        color = meta.get("color", COLORS["primary"])
        type_label = meta.get("name", atype.title() or "Activity")

        # Stats from score map
        stats = self._score_map.get(aid, {"n": 0, "avg_pct": 0,
                                          "max_pct": 0})

        card = ctk.CTkFrame(
            self._list_container,
            fg_color=COLORS["surface"],
            corner_radius=CARD_RADIUS,
            border_width=1,
            border_color=color)
        card.pack(fill="x", pady=4)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=PAD_LG, pady=PAD_MD)

        # Icon block
        block = ctk.CTkFrame(
            inner,
            width=52, height=52,
            fg_color=color,
            corner_radius=12)
        block.pack(side="left")
        block.pack_propagate(False)
        ctk.CTkLabel(
            block, text=icon,
            font=(FONT_FAMILY, 24),
            text_color="#FFFFFF").place(
            relx=0.5, rely=0.5, anchor="center")

        # Info
        info = ctk.CTkFrame(inner, fg_color="transparent")
        info.pack(side="left", padx=(PAD_LG, 0),
                  fill="x", expand=True)

        ctk.CTkLabel(
            info, text=name,
            font=(FONT_FAMILY, 14, "bold"),
            text_color=COLORS["text"], anchor="w",
        ).pack(anchor="w")

        meta_bits = [type_label]
        if subject:
            meta_bits.append(subject)
        meta_bits.append(f"Max {int(max_score)}")
        ctk.CTkLabel(
            info, text="  ·  ".join(meta_bits),
            font=(FONT_FAMILY, 10),
            text_color=COLORS["text_muted"], anchor="w",
        ).pack(anchor="w", pady=(2, 0))

        # Stats row
        stats_row = ctk.CTkFrame(info, fg_color="transparent")
        stats_row.pack(anchor="w", pady=(6, 0))

        if stats["n"] > 0:
            ctk.CTkLabel(
                stats_row,
                text=f"👥 {stats['n']}  ·  "
                     f"Avg {stats['avg_pct']:.0f}%  ·  "
                     f"Best {stats['max_pct']:.0f}%",
                font=(FONT_FAMILY, 10, "bold"),
                text_color=STATUS["green"]).pack(anchor="w")
        else:
            ctk.CTkLabel(
                stats_row,
                text="No scores logged yet",
                font=(FONT_FAMILY, 10),
                text_color=COLORS["text_muted"]).pack(anchor="w")

        # Right: actions
        right = ctk.CTkFrame(inner, fg_color="transparent")
        right.pack(side="right")

        self.primary_button(
            right, "📝 Log score",
            command=lambda act=a: self._open_log_score(act),
            width=130, height=34,
        ).pack(pady=(0, 6))

        self.danger_button(
            right, "🗑 Delete",
            command=lambda act=a: self._delete_activity(act),
            width=130, height=34,
        ).pack()

    # =========================================================
    # LOG SCORE
    # =========================================================

    def _open_log_score(self, act):
        aid = _safe_str(act.get("id"))
        name = _safe_str(act.get("name"))
        max_score = _safe_float(act.get("max_score"), 100)

        dialog = _LogScoreDialog(
            self.winfo_toplevel(),
            title=f"Log score — {name}",
            students=self._students,
            max_score=max_score,
            on_submit=lambda uid, score:
                self._log_score(aid, uid, score, max_score),
        )
        dialog.show()

    def _log_score(self, activity_id: str, user_id: str,
                   score: float, max_score: float):
        admin_id = (self.user or {}).get("id", "admin")
        try:
            self.db.log_activity_score(user_id, activity_id,
                                       score, max_score)
            self.db.log_audit(
                admin_id, "log_activity_score",
                target=f"{user_id}:{activity_id}",
                details=f"score={score}/{max_score}")

            # Evaluate badges after logging score
            try:
                from models.badges import BadgeEngine
                BadgeEngine(self.db).evaluate_user(user_id)
            except Exception:
                pass

            self.toast(f"Score logged: {score}/{max_score}.", "success")
            self._reload()
        except Exception as e:
            self.toast(f"Could not log score: {e}", "error")

    # =========================================================
    # DELETE ACTIVITY
    # =========================================================

    def _delete_activity(self, act):
        aid = _safe_str(act.get("id"))
        name = _safe_str(act.get("name"))

        def on_confirm():
            try:
                # Delete related scores first
                self.db.execute(
                    "DELETE FROM activity_scores WHERE activity_id=?",
                    (aid,))
                # Then the activity
                self.db.execute(
                    "DELETE FROM activities WHERE id=?", (aid,))

                self.db.log_audit(
                    (self.user or {}).get("id", "admin"),
                    "delete_activity", target=name)

                self.toast(f"Deleted '{name}'.", "warning")
                self._reload()
            except Exception as e:
                self.toast(f"Could not delete: {e}", "error")

        self.confirm(
            "Delete this activity?",
            f"Permanently delete '{name}' and all its logged scores? "
            f"This cannot be undone.",
            on_yes=on_confirm,
            yes_text="Delete",
        )

    # =========================================================
    # RELOAD
    # =========================================================

    def _reload(self):
        for w in self._content.winfo_children():
            w.destroy()
        self.render()


# =============================================================
# LOG SCORE DIALOG
# =============================================================

class _LogScoreDialog:
    """Modal for logging a single student's score on an activity."""

    def __init__(self, parent, title, students, max_score, on_submit):
        self.parent = parent
        self.title = title
        self.students = students
        self.max_score = max_score
        self.on_submit = on_submit

        self.top = None
        self.student_menu = None
        self.score_entry = None
        self.error_label = None
        self.student_lookup = {}

    def show(self):
        self.top = ctk.CTkToplevel(self.parent)
        self.top.title(self.title)
        self.top.configure(fg_color=COLORS["bg"])
        self.top.resizable(False, False)
        self.top.transient(self.parent)
        try:
            self.top.grab_set()
        except Exception:
            pass

        W, H = 480, 340
        self.top.geometry(f"{W}x{H}")
        try:
            self.parent.update_idletasks()
            px = self.parent.winfo_rootx()
            py = self.parent.winfo_rooty()
            pw = self.parent.winfo_width()
            ph = self.parent.winfo_height()
            x = px + (pw - W) // 2
            y = py + (ph - H) // 2
            self.top.geometry(f"{W}x{H}+{x}+{y}")
        except Exception:
            pass

        # Top bar
        ctk.CTkFrame(self.top, height=6, fg_color=COLORS["primary"],
                     corner_radius=0).pack(fill="x")

        body = ctk.CTkFrame(self.top, fg_color="transparent")
        body.pack(fill="both", expand=True,
                  padx=PAD_XL, pady=PAD_LG)

        ctk.CTkLabel(
            body, text="Log activity score",
            font=(FONT_FAMILY, 16, "bold"),
            text_color=COLORS["text"]).pack(anchor="w", pady=(0, 4))

        ctk.CTkLabel(
            body, text=f"Max: {int(self.max_score)}",
            font=(FONT_FAMILY, 10),
            text_color=COLORS["text_muted"]).pack(anchor="w", pady=(0, 16))

        # Student dropdown
        ctk.CTkLabel(
            body, text="Student",
            font=(FONT_FAMILY, 10, "bold"),
            text_color=COLORS["text_muted"]).pack(anchor="w")

        student_labels = []
        if self.students is not None and not self.students.empty:
            for _, s in self.students.iterrows():
                label = f"{_safe_str(s.get('name'))} ({_safe_str(s.get('usn'))})"
                student_labels.append(label)
                self.student_lookup[label] = _safe_str(s.get("id"))

        if student_labels:
            self.student_menu = ctk.CTkOptionMenu(
                body, values=student_labels, width=400, height=38,
                font=FONTS["small"],
                fg_color=COLORS["surface_alt"],
                button_color=COLORS["primary"],
                button_hover_color=COLORS["primary_hover"],
                text_color=COLORS["text"],
                dropdown_fg_color=COLORS["surface_alt"],
                dropdown_text_color=COLORS["text"],
                corner_radius=10)
            self.student_menu.set(student_labels[0])
            self.student_menu.pack(pady=(4, 12))
        else:
            ctk.CTkLabel(
                body, text="No students available.",
                font=FONTS["small"],
                text_color=STATUS["red"]).pack(pady=(4, 12))

        # Score entry
        ctk.CTkLabel(
            body, text="Score",
            font=(FONT_FAMILY, 10, "bold"),
            text_color=COLORS["text_muted"]).pack(anchor="w")

        self.score_entry = ctk.CTkEntry(
            body, width=400, height=38,
            font=FONTS["small"],
            fg_color=COLORS["surface_alt"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            corner_radius=10,
            placeholder_text=f"0 – {int(self.max_score)}")
        self.score_entry.pack(pady=(4, 12))

        # Error
        self.error_label = ctk.CTkLabel(
            body, text="",
            font=(FONT_FAMILY, 10),
            text_color=STATUS["red"],
            wraplength=400, justify="left")
        self.error_label.pack(anchor="w")

        # Buttons
        btn_row = ctk.CTkFrame(body, fg_color="transparent")
        btn_row.pack(fill="x", pady=(12, 0))

        ctk.CTkButton(
            btn_row, text="Cancel", width=110, height=38,
            font=(FONT_FAMILY, 11, "bold"),
            fg_color=COLORS["surface_alt"],
            hover_color=COLORS["surface_hi"],
            text_color=COLORS["text"],
            corner_radius=BUTTON_RADIUS,
            command=self._close,
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            btn_row, text="Log score", width=110, height=38,
            font=(FONT_FAMILY, 11, "bold"),
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            text_color=COLORS["text"],
            corner_radius=BUTTON_RADIUS,
            command=self._submit,
        ).pack(side="right")

    def _submit(self):
        if self.student_menu is None:
            self.error_label.configure(text="⚠️  No student selected.")
            return

        try:
            student_label = self.student_menu.get()
            uid = self.student_lookup.get(student_label)
        except Exception:
            uid = None

        if not uid:
            self.error_label.configure(text="⚠️  Invalid student.")
            return

        try:
            score = float((self.score_entry.get() or "").strip())
        except Exception:
            self.error_label.configure(text="⚠️  Enter a valid number.")
            return

        if score < 0 or score > self.max_score:
            self.error_label.configure(
                text=f"⚠️  Score must be between 0 and {int(self.max_score)}.")
            return

        ok = self.on_submit(uid, score)
        if ok:
            self._close()

    def _close(self):
        try:
            self.top.grab_release()
        except Exception:
            pass
        try:
            self.top.destroy()
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
            print(f"[activities] → show_page('{key}')  args={kw}")

        def go_back(self):
            print("[activities] back")

        def logout(self):
            print("[activities] logout")

    root = ctk.CTk()
    W, H = 1400, 900
    root.geometry(f"{W}x{H}")
    root.configure(fg_color=COLORS["bg"])
    root.title(f"{APP_NAME} — activity manager")

    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - W) // 2
    y = (sh - H) // 2
    root.geometry(f"{W}x{H}+{x}+{y}")

    app = _FakeApp()
    page = AdminActivityManagerPage(root, app)
    page.pack(fill="both", expand=True)
    root.mainloop()
    print("\n✅ pages/admin/activity_manager.py OK")