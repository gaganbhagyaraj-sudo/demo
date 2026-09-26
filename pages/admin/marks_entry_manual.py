# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  pages/admin/marks_manual.py  ·  Manual marks entry
# =============================================================

from __future__ import annotations

import os
import sys

# --- make project root importable ---
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from datetime import datetime

import customtkinter as ctk
import pandas as pd

from config import (
    APP_NAME, COLORS, STATUS, SUBJECTS,
    FONTS, FONT_FAMILY,
    CARD_RADIUS, BUTTON_RADIUS, CHIP_RADIUS,
    PAD_SM, PAD_MD, PAD_LG, PAD_XL,
    ROLE_ADMIN, ROLE_FACILITATOR, ROLE_STUDENT,
    STATUS_PENDING, STATUS_APPROVED, STATUS_REJECTED,
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


def _safe_int(v, default: int = 0) -> int:
    try:
        if v is None:
            return default
        return int(float(v))
    except Exception:
        return default


def _safe_float(v, default: float = 0.0) -> float:
    try:
        if v is None:
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


# Default max marks per IA — adjust to match your rubric
DEFAULT_MAX_MARKS = 20


# =============================================================
# MANUAL MARKS PAGE
# =============================================================

class AdminMarksManualPage(BasePage):

    def __init__(self, master, app):
        super().__init__(master, app)

        self.build_header("Manual Marks Entry",
                          "Enter IA marks per student, per subject",
                          back=False)
        self.build_sidebar(self._build_nav_items())
        self.build_content(scrollable=True)
        self.build_footer()

        # State
        self._ia_number = 3              # IA-1 / IA-2 / IA-3
        self._subject = None             # current subject key
        self._max_marks = DEFAULT_MAX_MARKS
        self._grade_filter = "all"
        self._section_filter = "all"
        self._search_text = ""
        self._marks_entries = {}         # {student_id: entry_widget}
        self._ia_btns = {}
        self._subject_btns = {}
        self._grade_btns = {}
        self._section_btns = {}
        self._search_entry = None
        self._table_container = None
        self._dirty = set()              # {student_id: True} unsaved

        # Pick a default subject from config
        try:
            self._subject = list(SUBJECTS.keys())[0]
        except Exception:
            self._subject = "math"

        self.render()

    def _build_nav_items(self):
        items = _admin_nav()
        for it in items:
            if it["key"] == "admin_marks_manual":
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

        self._load_students()

        # 1. Top stats
        self._render_stats(content)

        # 2. Selection bar (IA + Subject + Max)
        self.section_title("Assessment", parent=content)
        self._render_selection(content)

        # 3. Filters
        self.section_title("Filters", parent=content)
        self._render_filters(content)

        # 4. Bulk actions
        self._render_bulk_actions(content)

        # 5. Marks table
        self.section_title(
            f"Marks — IA-{self._ia_number} · "
            f"{self._subject_label()}",
            parent=content)
        self._table_container = ctk.CTkFrame(content, fg_color="transparent")
        self._table_container.pack(fill="x", pady=(0, PAD_MD))
        self._render_table()

    # =========================================================
    # LOAD
    # =========================================================

    def _load_students(self):
        try:
            self._students = self.db.query("""
                SELECT * FROM users
                WHERE role='student' AND status='approved'
                ORDER BY grade ASC, section ASC, name ASC
            """)
        except Exception:
            self._students = pd.DataFrame()

        # Load existing marks for the current IA+subject
        self._existing_marks = {}
        try:
            rows = self.db.query("""
                SELECT student_id, marks_obtained
                FROM marks
                WHERE ia_number=? AND subject=?
            """, (self._ia_number, self._subject))
            for _, r in rows.iterrows():
                self._existing_marks[_safe_str(r.get("student_id"))] = \
                    _safe_float(r.get("marks_obtained"), 0.0)
        except Exception:
            pass

    def _subject_label(self) -> str:
        try:
            info = SUBJECTS.get(self._subject, {})
            if isinstance(info, dict):
                return info.get("label") or info.get("name") or \
                       self._subject.title()
            return str(info)
        except Exception:
            return str(self._subject).title()

    # =========================================================
    # STATS
    # =========================================================

    def _render_stats(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        s = self._students
        total = 0 if s is None else len(s)

        n_entered = len(self._existing_marks)
        n_missing = max(0, total - n_entered)

        avg = 0.0
        if self._existing_marks:
            avg = sum(self._existing_marks.values()) / \
                  len(self._existing_marks)

        self.stat_card(
            row, total, "Students",
            accent="#8B5CF6", icon="🎓",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, n_entered, "Entered",
            accent=STATUS["green"], icon="✅",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, n_missing, "Missing",
            accent=STATUS["amber"] if n_missing > 0
                   else COLORS["text_muted"],
            icon="⏳",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, f"{avg:.1f}", "Average",
            accent=COLORS["primary"], icon="📊",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, self._max_marks, "Max marks",
            accent=COLORS["text_muted"], icon="🎯",
        ).pack(side="left")

    # =========================================================
    # SELECTION (IA + subject + max)
    # =========================================================

    def _render_selection(self, parent):
        card = self.card(parent)
        card.pack(fill="x", pady=(0, PAD_MD))

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        # Row 1: IA picker
        ia_row = ctk.CTkFrame(body, fg_color="transparent")
        ia_row.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            ia_row, text="IA:",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_muted"]).pack(side="left", padx=(0, 8))

        for n in (1, 2, 3):
            is_active = (self._ia_number == n)
            btn = ctk.CTkButton(
                ia_row, text=f"IA-{n}", width=100, height=34,
                font=(FONT_FAMILY, 10, "bold"),
                fg_color=COLORS["primary"] if is_active
                         else COLORS["surface_alt"],
                hover_color=COLORS["surface_hi"],
                text_color=COLORS["text"],
                corner_radius=BUTTON_RADIUS,
                command=lambda k=n: self._set_ia(k),
            )
            btn.pack(side="left", padx=(0, PAD_SM))
            self._ia_btns[n] = btn

        # Max marks spinner (right side)
        ctk.CTkLabel(
            ia_row, text="Max:",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_muted"]).pack(side="right", padx=(8, 4))

        self._max_entry = ctk.CTkEntry(
            ia_row, width=70, height=34,
            font=(FONT_FAMILY, 11, "bold"),
            fg_color=COLORS["surface_alt"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            corner_radius=10,
            justify="center")
        self._max_entry.insert(0, str(self._max_marks))
        self._max_entry.pack(side="right")
        self._max_entry.bind("<FocusOut>",
                             lambda e: self._set_max_marks())
        self._max_entry.bind("<Return>",
                             lambda e: self._set_max_marks())

        # Row 2: Subject picker
        sub_row = ctk.CTkFrame(body, fg_color="transparent")
        sub_row.pack(fill="x")

        ctk.CTkLabel(
            sub_row, text="Subject:",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_muted"]).pack(side="left", padx=(0, 8))

        try:
            sub_keys = list(SUBJECTS.keys())
        except Exception:
            sub_keys = ["math", "science", "english"]

        for key in sub_keys:
            label = self._subject_name_for(key)
            is_active = (self._subject == key)
            btn = ctk.CTkButton(
                sub_row, text=label, width=140, height=34,
                font=(FONT_FAMILY, 10),
                fg_color=COLORS["primary"] if is_active
                         else COLORS["surface_alt"],
                hover_color=COLORS["surface_hi"],
                text_color=COLORS["text"],
                corner_radius=BUTTON_RADIUS,
                command=lambda k=key: self._set_subject(k),
            )
            btn.pack(side="left", padx=(0, PAD_SM))
            self._subject_btns[key] = btn

    def _subject_name_for(self, key: str) -> str:
        try:
            info = SUBJECTS.get(key, {})
            if isinstance(info, dict):
                return info.get("label") or info.get("name") or key.title()
            return str(info)
        except Exception:
            return key.title()

    def _set_ia(self, n: int):
        if n == self._ia_number:
            return
        self._ia_number = n
        for k, b in self._ia_btns.items():
            try:
                b.configure(fg_color=COLORS["primary"] if k == n
                            else COLORS["surface_alt"])
            except Exception:
                pass
        self._dirty.clear()
        self._reload()

    def _set_subject(self, key: str):
        if key == self._subject:
            return
        self._subject = key
        for k, b in self._subject_btns.items():
            try:
                b.configure(fg_color=COLORS["primary"] if k == key
                            else COLORS["surface_alt"])
            except Exception:
                pass
        self._dirty.clear()
        self._reload()

    def _set_max_marks(self):
        try:
            v = int(float(self._max_entry.get() or DEFAULT_MAX_MARKS))
            self._max_marks = max(1, min(1000, v))
        except Exception:
            self._max_marks = DEFAULT_MAX_MARKS
        try:
            self._max_entry.delete(0, "end")
            self._max_entry.insert(0, str(self._max_marks))
        except Exception:
            pass
        self._render_table()

    # =========================================================
    # FILTERS
    # =========================================================

    def _render_filters(self, parent):
        card = self.card(parent)
        card.pack(fill="x", pady=(0, PAD_MD))

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        # Search
        s_row = ctk.CTkFrame(body, fg_color="transparent")
        s_row.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            s_row, text="🔍  Search:",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_muted"]).pack(side="left", padx=(0, 8))

        self._search_entry = ctk.CTkEntry(
            s_row, width=340, height=36,
            font=FONTS["small"],
            fg_color=COLORS["surface_alt"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            corner_radius=10,
            placeholder_text="Name, USN, or email…")
        self._search_entry.pack(side="left")
        self._search_entry.bind("<KeyRelease>", self._on_search_change)

        self.secondary_button(
            s_row, "Clear",
            command=self._clear_search,
            width=90, height=36,
        ).pack(side="left", padx=(PAD_SM, 0))

        # Grade filter
        g_row = ctk.CTkFrame(body, fg_color="transparent")
        g_row.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            g_row, text="Grade:",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_muted"]).pack(side="left", padx=(0, 8))

        for key in self._available_grades():
            is_active = (self._grade_filter == key)
            label = "All" if key == "all" else f"Grade {key}"
            btn = ctk.CTkButton(
                g_row, text=label, width=110, height=32,
                font=(FONT_FAMILY, 10),
                fg_color=COLORS["primary"] if is_active
                         else COLORS["surface_alt"],
                hover_color=COLORS["surface_hi"],
                text_color=COLORS["text"],
                corner_radius=BUTTON_RADIUS,
                command=lambda k=key: self._set_grade(k),
            )
            btn.pack(side="left", padx=(0, PAD_SM))
            self._grade_btns[key] = btn

        # Section filter
        st_row = ctk.CTkFrame(body, fg_color="transparent")
        st_row.pack(fill="x")

        ctk.CTkLabel(
            st_row, text="Section:",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_muted"]).pack(side="left", padx=(0, 8))

        for key in self._available_sections():
            is_active = (self._section_filter == key)
            label = "All" if key == "all" else f"Sec {key}"
            btn = ctk.CTkButton(
                st_row, text=label, width=100, height=32,
                font=(FONT_FAMILY, 10),
                fg_color=COLORS["primary"] if is_active
                         else COLORS["surface_alt"],
                hover_color=COLORS["surface_hi"],
                text_color=COLORS["text"],
                corner_radius=BUTTON_RADIUS,
                command=lambda k=key: self._set_section(k),
            )
            btn.pack(side="left", padx=(0, PAD_SM))
            self._section_btns[key] = btn

    def _available_grades(self):
        try:
            s = self._students
            if s is None or s.empty:
                return ["all"]
            vals = sorted({_safe_str(x) for x in s["grade"].tolist()
                           if _safe_str(x)})
            return ["all"] + vals
        except Exception:
            return ["all"]

    def _available_sections(self):
        try:
            s = self._students
            if s is None or s.empty:
                return ["all"]
            vals = sorted({_safe_str(x) for x in s["section"].tolist()
                           if _safe_str(x)})
            return ["all"] + vals
        except Exception:
            return ["all"]

    def _set_grade(self, key: str):
        self._grade_filter = key
        for k, b in self._grade_btns.items():
            try:
                b.configure(fg_color=COLORS["primary"] if k == key
                            else COLORS["surface_alt"])
            except Exception:
                pass
        self._render_table()

    def _set_section(self, key: str):
        self._section_filter = key
        for k, b in self._section_btns.items():
            try:
                b.configure(fg_color=COLORS["primary"] if k == key
                            else COLORS["surface_alt"])
            except Exception:
                pass
        self._render_table()

    def _on_search_change(self, event=None):
        try:
            self._search_text = (self._search_entry.get() or "").strip().lower()
        except Exception:
            self._search_text = ""
        self._render_table()

    def _clear_search(self):
        try:
            self._search_entry.delete(0, "end")
        except Exception:
            pass
        self._search_text = ""
        self._render_table()

    # =========================================================
    # BULK ACTIONS
    # =========================================================

    def _render_bulk_actions(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        self.primary_button(
            row, "💾  Save All Changes",
            command=self._save_all,
            width=220, height=42,
        ).pack(side="left", padx=(0, PAD_MD))

        self.secondary_button(
            row, "🔄  Refresh",
            command=self._reload,
            width=120, height=42,
        ).pack(side="left", padx=(0, PAD_MD))

        self.danger_button(
            row, "🧹  Clear This IA",
            command=self._clear_ia,
            width=180, height=42,
        ).pack(side="left")

        # Dirty indicator
        self._dirty_label = ctk.CTkLabel(
            row, text="",
            font=(FONT_FAMILY, 10, "bold"),
            text_color=STATUS["amber"])
        self._dirty_label.pack(side="right", padx=(PAD_MD, 0))

    # =========================================================
    # TABLE
    # =========================================================

    def _render_table(self):
        for w in self._table_container.winfo_children():
            w.destroy()
        self._marks_entries.clear()

        s = self._students
        if s is None or s.empty:
            ctk.CTkLabel(
                self._table_container,
                text="No students found. Approve some students first.",
                font=FONTS["body"],
                text_color=COLORS["text_muted"]).pack(pady=20)
            return

        df = s.copy()

        if self._grade_filter != "all":
            df = df[df["grade"].astype(str) == self._grade_filter]
        if self._section_filter != "all":
            df = df[df["section"].astype(str) == self._section_filter]

        if self._search_text:
            q = self._search_text
            mask = df.apply(
                lambda r: (q in _safe_str(r.get("name")).lower())
                or (q in _safe_str(r.get("usn")).lower())
                or (q in _safe_str(r.get("email")).lower()),
                axis=1)
            df = df[mask]

        if df.empty:
            ctk.CTkLabel(
                self._table_container,
                text="No students match your filters.",
                font=FONTS["body"],
                text_color=COLORS["text_muted"]).pack(pady=20)
            return

        # Count label
        ctk.CTkLabel(
            self._table_container,
            text=f"Showing {len(df)} of {len(s)} student(s)   ·   "
                 f"Max marks: {self._max_marks}",
            font=(FONT_FAMILY, 10),
            text_color=COLORS["text_muted"],
        ).pack(anchor="w", pady=(0, PAD_SM))

        # Header
        header = ctk.CTkFrame(self._table_container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 4))

        for label, w in [("Student", 300), ("Grade", 90),
                         ("Section", 90), ("USN", 140),
                         ("Marks", 160), ("Status", 120),
                         ("Clear", 80)]:
            ctk.CTkLabel(
                header, text=label, width=w, anchor="w",
                font=(FONT_FAMILY, 10, "bold"),
                text_color=COLORS["text_muted"]).pack(side="left")

        # Rows
        for _, r in df.iterrows():
            self._render_row(r)

        self._update_dirty_label()

    def _render_row(self, u):
        uid = _safe_str(u.get("id"))
        name = _safe_str(u.get("name")) or "—"
        usn = _safe_str(u.get("usn")) or "—"
        grade = _safe_str(u.get("grade")) or "—"
        section = _safe_str(u.get("section")) or "—"

        existing_val = self._existing_marks.get(uid, None)

        row = ctk.CTkFrame(
            self._table_container,
            fg_color=COLORS["surface_alt"],
            corner_radius=8)
        row.pack(fill="x", pady=2)

        inner = ctk.CTkFrame(row, fg_color="transparent")
        inner.pack(fill="x", padx=8, pady=6)

        # Student (avatar + name)
        s_box = ctk.CTkFrame(inner, fg_color="transparent", width=300)
        s_box.pack(side="left")
        s_box.pack_propagate(False)

        try:
            avatar = load_avatar(
                user_id=uid, name=name,
                size=28, shape="circle")
            ctk.CTkLabel(s_box, image=avatar, text="").pack(
                side="left", padx=(0, 8))
        except Exception:
            pass

        ctk.CTkLabel(
            s_box, text=name,
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text"], anchor="w",
        ).pack(side="left")

        # Grade / Section / USN
        ctk.CTkLabel(
            inner, text=grade, width=90, anchor="w",
            font=(FONT_FAMILY, 10),
            text_color=COLORS["text_muted"]).pack(side="left")

        ctk.CTkLabel(
            inner, text=section, width=90, anchor="w",
            font=(FONT_FAMILY, 10),
            text_color=COLORS["text_muted"]).pack(side="left")

        ctk.CTkLabel(
            inner, text=usn, width=140, anchor="w",
            font=(FONT_FAMILY, 10),
            text_color=COLORS["text_muted"]).pack(side="left")

        # Marks entry
        m_box = ctk.CTkFrame(inner, fg_color="transparent", width=160)
        m_box.pack(side="left")
        m_box.pack_propagate(False)

        entry = ctk.CTkEntry(
            m_box, width=90, height=32,
            font=(FONT_FAMILY, 11, "bold"),
            fg_color=COLORS["surface"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            corner_radius=8,
            justify="center",
            placeholder_text="—")
        entry.pack(side="left")

        if existing_val is not None:
            entry.insert(0, f"{existing_val:g}")

        entry.bind("<KeyRelease>",
                   lambda e, i=uid: self._on_mark_change(i))
        entry.bind("<FocusOut>",
                   lambda e, i=uid: self._validate_mark(i))
        entry.bind("<Return>",
                   lambda e, i=uid: self._save_one(i))

        self._marks_entries[uid] = entry

        ctk.CTkLabel(
            m_box, text=f" / {self._max_marks}",
            font=(FONT_FAMILY, 10),
            text_color=COLORS["text_muted"]).pack(side="left", padx=(4, 0))

        # Status chip
        st_box = ctk.CTkFrame(inner, fg_color="transparent", width=120)
        st_box.pack(side="left")
        st_box.pack_propagate(False)

        self._render_status_chip(st_box, uid)

        # Clear button
        clr_box = ctk.CTkFrame(inner, fg_color="transparent", width=80)
        clr_box.pack(side="left")
        clr_box.pack_propagate(False)

        self.secondary_button(
            clr_box, "✖",
            command=lambda i=uid: self._clear_one(i),
            width=50, height=28,
        ).pack(side="left")

    def _render_status_chip(self, parent, uid):
        for w in parent.winfo_children():
            w.destroy()

        val = self._existing_marks.get(uid, None)
        if val is None:
            icon, label, color = "⏳", "Missing", STATUS["amber"]
        else:
            icon, label, color = "✅", "Saved", STATUS["green"]

        chip = ctk.CTkFrame(parent, fg_color=color,
                            corner_radius=CHIP_RADIUS)
        chip.pack(side="left")
        ctk.CTkLabel(
            chip, text=f"  {icon} {label}  ",
            font=(FONT_FAMILY, 9, "bold"),
            text_color="#FFFFFF").pack(padx=2, pady=2)

    # =========================================================
    # INPUT HANDLERS
    # =========================================================

    def _on_mark_change(self, uid: str):
        self._dirty.add(uid)
        self._update_dirty_label()

    def _validate_mark(self, uid: str):
        try:
            e = self._marks_entries.get(uid)
            if e is None:
                return
            txt = (e.get() or "").strip()
            if not txt:
                return
            val = float(txt)
            if val < 0:
                val = 0.0
            if val > self._max_marks:
                val = float(self._max_marks)
            e.delete(0, "end")
            e.insert(0, f"{val:g}")
        except Exception:
            # Non-numeric — clear it
            try:
                e = self._marks_entries.get(uid)
                if e is not None:
                    e.delete(0, "end")
            except Exception:
                pass

    def _update_dirty_label(self):
        try:
            n = len(self._dirty)
            if n == 0:
                self._dirty_label.configure(text="")
            else:
                self._dirty_label.configure(
                    text=f"● {n} unsaved change(s)")
        except Exception:
            pass

    # =========================================================
    # SAVE
    # =========================================================

    def _save_all(self):
        if not self._dirty:
            self.toast("No changes to save.", "info")
            return

        n_ok = 0
        n_err = 0
        for uid in list(self._dirty):
            if self._save_one(uid, silent=True):
                n_ok += 1
            else:
                n_err += 1

        if n_err == 0:
            self.toast(f"Saved {n_ok} mark(s).", "success")
        else:
            self.toast(f"Saved {n_ok}, failed {n_err}.", "warning")

        # Try to recompute summary
        self._recompute_summary()

        self._dirty.clear()
        self._reload()

    def _save_one(self, uid: str, silent: bool = False) -> bool:
        e = self._marks_entries.get(uid)
        if e is None:
            return False

        try:
            txt = (e.get() or "").strip()
        except Exception:
            return False

        # Empty = delete row (mark as not entered)
        if not txt:
            try:
                self.db.execute(
                    "DELETE FROM marks WHERE student_id=? "
                    "AND ia_number=? AND subject=?",
                    (uid, self._ia_number, self._subject))
                self._existing_marks.pop(uid, None)
                self._dirty.discard(uid)
                if not silent:
                    self.toast("Cleared mark.", "info")
                    self._reload()
                return True
            except Exception as ex:
                if not silent:
                    self.toast(f"Clear failed: {ex}", "error")
                return False

        try:
            val = float(txt)
        except Exception:
            if not silent:
                self.toast("Invalid number.", "error")
            return False

        if val < 0 or val > self._max_marks:
            if not silent:
                self.toast(
                    f"Mark must be between 0 and {self._max_marks}.",
                    "error")
            return False

        try:
            # Upsert pattern — delete then insert, so it works with any schema
            self.db.execute(
                "DELETE FROM marks WHERE student_id=? "
                "AND ia_number=? AND subject=?",
                (uid, self._ia_number, self._subject))

            self.db.execute("""
                INSERT INTO marks
                    (id, student_id, ia_number, subject,
                     marks_obtained, max_marks, entered_at)
                VALUES (?,?,?,?,?,?,?)
            """, (
                f"{uid}-{self._ia_number}-{self._subject}",
                uid,
                self._ia_number,
                self._subject,
                val,
                self._max_marks,
                datetime.now().isoformat(),
            ))

            self._existing_marks[uid] = val
            self._dirty.discard(uid)

            self.db.log_audit(
                (self.user or {}).get("id", "admin"),
                "save_mark",
                target=uid,
                details=f"IA-{self._ia_number} {self._subject}={val}")

            if not silent:
                self.toast("Saved ✓", "success")
                self._reload()
            return True
        except Exception as ex:
            if not silent:
                self.toast(f"Save failed: {ex}", "error")
            return False

    def _recompute_summary(self):
        """Try to recompute marks_summary for the affected IA."""
        try:
            if hasattr(self.db, "recompute_summary"):
                self.db.recompute_summary(ia_number=self._ia_number)
            elif hasattr(self.db, "recompute_marks_summary"):
                self.db.recompute_marks_summary(ia_number=self._ia_number)
        except Exception:
            pass

    # =========================================================
    # CLEAR
    # =========================================================

    def _clear_one(self, uid: str):
        e = self._marks_entries.get(uid)
        if e is None:
            return
        try:
            e.delete(0, "end")
        except Exception:
            pass

        # Mark as dirty → user still needs to Save
        self._dirty.add(uid)
        self._update_dirty_label()

        # Refresh status chip
        for child in self._table_container.winfo_children():
            pass  # simple approach — full reload on save

    def _clear_ia(self):
        def on_confirm():
            try:
                self.db.execute(
                    "DELETE FROM marks WHERE ia_number=?",
                    (self._ia_number,))
                self.db.log_audit(
                    (self.user or {}).get("id", "admin"),
                    "clear_ia", target=f"IA-{self._ia_number}")
                self.toast(
                    f"Cleared all marks for IA-{self._ia_number}.",
                    "warning")
                self._dirty.clear()
                self._reload()
            except Exception as e:
                self.toast(f"Clear failed: {e}", "error")

        self.confirm(
            f"Clear all marks for IA-{self._ia_number}?",
            f"This deletes every mark (all subjects) for IA-"
            f"{self._ia_number}. This cannot be undone.",
            on_yes=on_confirm,
            yes_text="Clear all",
        )

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
            print(f"[marks_manual] → show_page('{key}')  args={kw}")

        def go_back(self):
            print("[marks_manual] back")

        def logout(self):
            print("[marks_manual] logout")

    root = ctk.CTk()
    W, H = 1500, 950
    root.geometry(f"{W}x{H}")
    root.configure(fg_color=COLORS["bg"])
    root.title(f"{APP_NAME} — manual marks")

    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - W) // 2
    y = (sh - H) // 2
    root.geometry(f"{W}x{H}+{x}+{y}")

    app = _FakeApp()
    page = AdminMarksManualPage(root, app)
    page.pack(fill="both", expand=True)
    root.mainloop()
    print("\n✅ pages/admin/marks_manual.py OK")