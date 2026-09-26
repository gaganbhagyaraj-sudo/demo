# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  pages/admin/marks_excel.py  ·  Bulk marks import (Excel/CSV)
# =============================================================

from __future__ import annotations

import os
import sys

# --- make project root importable ---
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import io
import csv
import uuid
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


def _safe_float(v, default=None):
    try:
        if v is None:
            return default
        if isinstance(v, float) and v != v:
            return default
        s = str(v).strip()
        if s == "":
            return default
        return float(s)
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


def _subject_keys():
    try:
        return list(SUBJECTS.keys())
    except Exception:
        return ["math", "science", "english"]


def _subject_label(key: str) -> str:
    try:
        info = SUBJECTS.get(key, {})
        if isinstance(info, dict):
            return info.get("label") or info.get("name") or key.title()
        return str(info)
    except Exception:
        return key.title()


DEFAULT_MAX_MARKS = 20


# =============================================================
# EXCEL UPLOAD PAGE
# =============================================================

class AdminMarksExcelPage(BasePage):

    def __init__(self, master, app):
        super().__init__(master, app)

        self.build_header("Excel / CSV Upload",
                          "Bulk-import marks from a spreadsheet",
                          back=False)
        self.build_sidebar(self._build_nav_items())
        self.build_content(scrollable=True)
        self.build_footer()

        # State
        self._ia_number = 3
        self._max_marks = DEFAULT_MAX_MARKS
        self._file_path = None
        self._raw_df = None          # as read from file
        self._preview_df = None      # after mapping
        self._validation = None      # list of dicts per row
        self._ia_btns = {}
        self._import_summary = None

        self.render()

    def _build_nav_items(self):
        items = _admin_nav()
        for it in items:
            if it["key"] == "admin_marks_excel":
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

        # 1. Instructions
        self._render_instructions(content)

        # 2. Upload + settings
        self.section_title("Upload", parent=content)
        self._render_uploader(content)

        # 3. Preview + validation
        if self._preview_df is not None:
            self.section_title("Preview & Validation", parent=content)
            self._render_preview(content)
            self.section_title("Import", parent=content)
            self._render_import_actions(content)

        # 4. Result summary
        if self._import_summary is not None:
            self.section_title("Result", parent=content)
            self._render_result_summary(content)

    # =========================================================
    # INSTRUCTIONS
    # =========================================================

    def _render_instructions(self, parent):
        card = self.card(parent)
        card.pack(fill="x", pady=(0, PAD_MD))

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        ctk.CTkLabel(
            body,
            text="📋  Expected spreadsheet format",
            font=(FONT_FAMILY, 13, "bold"),
            text_color=COLORS["text"],
        ).pack(anchor="w", pady=(0, 8))

        lines = [
            "• Required column:  USN   (or  Name as fallback)",
            f"• Optional columns:  {'  ·  '.join(_subject_keys())}",
            "• One row per student",
            "• Cell values: numbers 0–" + str(self._max_marks) +
            "  (blank = not entered)",
            "• Subject columns may also be named  'IA-1 Math',  'Math_IA1',  etc.",
            "• Accepted formats:  .xlsx, .xls, .csv",
        ]
        for ln in lines:
            ctk.CTkLabel(
                body, text=ln,
                font=(FONT_FAMILY, 10),
                text_color=COLORS["text_muted"],
                justify="left",
            ).pack(anchor="w")

        # Template download
        self.secondary_button(
            body, "⬇  Download template (.xlsx)",
            command=self._download_template,
            width=280, height=36,
        ).pack(anchor="w", pady=(12, 0))

    # =========================================================
    # UPLOADER
    # =========================================================

    def _render_uploader(self, parent):
        card = self.card(parent)
        card.pack(fill="x", pady=(0, PAD_MD))

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        # Row 1: IA picker + Max marks
        top = ctk.CTkFrame(body, fg_color="transparent")
        top.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            top, text="Target IA:",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_muted"]).pack(side="left", padx=(0, 8))

        for n in (1, 2, 3):
            is_active = (self._ia_number == n)
            btn = ctk.CTkButton(
                top, text=f"IA-{n}", width=90, height=34,
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

        ctk.CTkLabel(
            top, text="Max marks:",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_muted"]).pack(
            side="left", padx=(PAD_LG, 6))

        self._max_entry = ctk.CTkEntry(
            top, width=70, height=34,
            font=(FONT_FAMILY, 11, "bold"),
            fg_color=COLORS["surface_alt"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            corner_radius=10,
            justify="center")
        self._max_entry.insert(0, str(self._max_marks))
        self._max_entry.pack(side="left")
        self._max_entry.bind("<FocusOut>", lambda e: self._set_max_marks())
        self._max_entry.bind("<Return>", lambda e: self._set_max_marks())

        # Row 2: File picker
        file_row = ctk.CTkFrame(body, fg_color="transparent")
        file_row.pack(fill="x")

        self.primary_button(
            file_row, "📂  Choose file…",
            command=self._pick_file,
            width=200, height=42,
        ).pack(side="left", padx=(0, PAD_MD))

        self.secondary_button(
            file_row, "🧪  Load sample",
            command=self._load_sample,
            width=160, height=42,
        ).pack(side="left", padx=(0, PAD_MD))

        self.secondary_button(
            file_row, "🗑  Clear",
            command=self._clear_file,
            width=110, height=42,
        ).pack(side="left")

        # File path label
        path_text = self._file_path or "No file selected."
        ctk.CTkLabel(
            body, text=path_text,
            font=(FONT_FAMILY, 10),
            text_color=COLORS["text_muted"] if not self._file_path
                       else COLORS["primary"],
        ).pack(anchor="w", pady=(10, 0))

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
        if self._raw_df is not None:
            self._revalidate()

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
        if self._raw_df is not None:
            self._revalidate()

    # =========================================================
    # FILE PICKING
    # =========================================================

    def _pick_file(self):
        try:
            from tkinter import filedialog
        except Exception as e:
            self.toast(f"File dialog unavailable: {e}", "error")
            return

        path = filedialog.askopenfilename(
            title="Choose spreadsheet",
            filetypes=[
                ("Spreadsheets", "*.xlsx *.xls *.csv"),
                ("Excel", "*.xlsx *.xls"),
                ("CSV", "*.csv"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        self._load_file(path)

    def _load_sample(self):
        """Load a small in-memory sample so the page can be tried offline."""
        try:
            students = self.db.query("""
                SELECT usn, name FROM users
                WHERE role='student' AND status='approved'
                ORDER BY name ASC LIMIT 5
            """)
        except Exception:
            students = pd.DataFrame()

        if students is None or students.empty:
            # No students — synthesize
            students = pd.DataFrame({
                "usn": [f"TEST{i}" for i in range(1, 6)],
                "name": [f"Sample Student {i}" for i in range(1, 6)],
            })

        rows = []
        subj = _subject_keys()[:2]
        for i, (_, r) in enumerate(students.iterrows()):
            row = {"USN": _safe_str(r.get("usn")),
                   "Name": _safe_str(r.get("name"))}
            for s in subj:
                row[s.title()] = (i + 1) * 3
            rows.append(row)
        self._raw_df = pd.DataFrame(rows)
        self._file_path = "(sample data)"
        self._revalidate()
        self._reload()

    def _load_file(self, path: str):
        try:
            if path.lower().endswith(".csv"):
                df = pd.read_csv(path)
            else:
                df = pd.read_excel(path)
        except Exception as e:
            self.toast(f"Could not read file: {e}", "error")
            return

        if df is None or df.empty:
            self.toast("File is empty.", "warning")
            return

        self._file_path = path
        self._raw_df = df
        self.toast(f"Loaded {len(df)} row(s).", "success")
        self._revalidate()
        self._reload()

    def _clear_file(self):
        self._file_path = None
        self._raw_df = None
        self._preview_df = None
        self._validation = None
        self._import_summary = None
        self._reload()

    # =========================================================
    # COLUMN MAPPING
    # =========================================================

    def _detect_columns(self, df: pd.DataFrame):
        """Return a dict mapping target → actual column name.

        Targets: 'usn', 'name', and each subject key.
        """
        cols = list(df.columns)
        lower = {str(c).strip().lower(): c for c in cols}

        mapping = {"usn": None, "name": None, "subjects": {}}

        # USN / Name
        for target, candidates in {
            "usn":  ["usn", "roll", "roll no", "rollno", "register",
                     "reg no", "student id", "id"],
            "name": ["name", "student", "student name", "full name"],
        }.items():
            for c in candidates:
                if c in lower:
                    mapping[target] = lower[c]
                    break

        # Subjects
        for skey in _subject_keys():
            slabel = _subject_label(skey).lower()
            candidates = {
                skey,
                slabel,
                f"ia{self._ia_number} {skey}",
                f"ia-{self._ia_number} {skey}",
                f"ia{self._ia_number} {slabel}",
                f"ia-{self._ia_number} {slabel}",
                f"{skey}_ia{self._ia_number}",
                f"{skey}-ia{self._ia_number}",
                f"{skey} ia{self._ia_number}",
                f"{skey} ia-{self._ia_number}",
            }
            for c in candidates:
                lc = str(c).strip().lower()
                if lc in lower:
                    mapping["subjects"][skey] = lower[lc]
                    break

        return mapping

    # =========================================================
    # VALIDATION
    # =========================================================

    def _revalidate(self):
        """Build preview + validation rows from self._raw_df."""
        df = self._raw_df
        if df is None or df.empty:
            self._preview_df = None
            self._validation = None
            return

        mapping = self._detect_columns(df)

        # Build lookup of students: usn_lower → {id, name, grade, section}
        self._student_lookup = {}
        try:
            all_students = self.db.query("""
                SELECT id, usn, name, grade, section FROM users
                WHERE role='student'
            """)
            for _, r in all_students.iterrows():
                u = _safe_str(r.get("usn")).strip().lower()
                if u:
                    self._student_lookup[u] = r.to_dict()
                # Also index by name (lowercased) as fallback
                nm = _safe_str(r.get("name")).strip().lower()
                if nm:
                    self._student_lookup.setdefault(
                        f"name::{nm}", r.to_dict())
        except Exception:
            pass

        subj_cols = mapping.get("subjects", {})
        if not subj_cols:
            self._preview_df = None
            self._validation = None
            return

        rows = []
        for i, raw in df.iterrows():
            usn = (_safe_str(raw.get(mapping["usn"])).strip()
                   if mapping["usn"] else "")
            name = (_safe_str(raw.get(mapping["name"])).strip()
                    if mapping["name"] else "")

            student = None
            match_by = None
            if usn:
                student = self._student_lookup.get(usn.lower())
                if student:
                    match_by = "USN"
            if not student and name:
                student = self._student_lookup.get(f"name::{name.lower()}")
                if student:
                    match_by = "Name"

            for skey, col in subj_cols.items():
                rawval = raw.get(col)
                val = _safe_float(rawval, default=None)
                status = "ok"
                note = ""

                if student is None:
                    status = "error"
                    note = "Student not found"
                elif val is None:
                    status = "skip"
                    note = "Blank"
                elif val < 0 or val > self._max_marks:
                    status = "error"
                    note = f"Out of range (0–{self._max_marks})"

                rows.append({
                    "row": i + 2,             # +2 = Excel 1-based + header
                    "usn": usn or "(none)",
                    "name": name or (
                        _safe_str(student.get("name")) if student else ""),
                    "matched": student is not None,
                    "match_by": match_by,
                    "student_id": (
                        _safe_str(student.get("id")) if student else None),
                    "subject": skey,
                    "subject_label": _subject_label(skey),
                    "value": val,
                    "status": status,
                    "note": note,
                })

        self._preview_df = df
        self._validation = rows

    # =========================================================
    # PREVIEW
    # =========================================================

    def _render_preview(self, parent):
        rows = self._validation or []
        n_total = len(rows)
        n_ok = sum(1 for r in rows if r["status"] == "ok")
        n_skip = sum(1 for r in rows if r["status"] == "skip")
        n_err = sum(1 for r in rows if r["status"] == "error")

        # Stats
        stat = ctk.CTkFrame(parent, fg_color="transparent")
        stat.pack(fill="x", pady=(0, PAD_MD))

        self.stat_card(
            stat, n_total, "Total rows",
            accent=COLORS["primary"], icon="📄",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            stat, n_ok, "Ready",
            accent=STATUS["green"], icon="✅",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            stat, n_skip, "Skipped",
            accent=COLORS["text_muted"], icon="⏭",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            stat, n_err, "Errors",
            accent=STATUS["red"] if n_err > 0
                   else COLORS["text_muted"],
            icon="❌",
        ).pack(side="left")

        # Table
        card = self.card(parent)
        card.pack(fill="x", pady=(0, PAD_MD))

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        if not rows:
            ctk.CTkLabel(
                body,
                text="No subject columns detected in this file. "
                     "Check the header row.",
                font=FONTS["small"],
                text_color=STATUS["amber"]).pack(pady=20)
            return

        # Header
        header = ctk.CTkFrame(body, fg_color="transparent")
        header.pack(fill="x", pady=(0, 4))

        for label, w in [("Row", 60), ("USN", 140),
                         ("Name", 220), ("Subject", 130),
                         ("Value", 90), ("Status", 220)]:
            ctk.CTkLabel(
                header, text=label, width=w, anchor="w",
                font=(FONT_FAMILY, 10, "bold"),
                text_color=COLORS["text_muted"]).pack(side="left")

        # Limit preview to 200 rows for responsiveness
        preview_cap = 200
        shown = rows[:preview_cap]

        for r in shown:
            self._render_preview_row(body, r)

        if len(rows) > preview_cap:
            ctk.CTkLabel(
                body,
                text=f"… and {len(rows) - preview_cap} more row(s) "
                     f"(hidden for performance).",
                font=(FONT_FAMILY, 10),
                text_color=COLORS["text_muted"],
            ).pack(anchor="w", pady=(6, 0))

    def _render_preview_row(self, parent, r):
        status = r["status"]
        if status == "ok":
            color, icon, label = STATUS["green"], "✅", "Ready"
        elif status == "skip":
            color, icon, label = COLORS["text_muted"], "⏭", "Skipped"
        else:
            color, icon, label = STATUS["red"], "❌", "Error"

        row = ctk.CTkFrame(parent, fg_color=COLORS["surface_alt"],
                           corner_radius=6)
        row.pack(fill="x", pady=1)

        inner = ctk.CTkFrame(row, fg_color="transparent")
        inner.pack(fill="x", padx=8, pady=4)

        ctk.CTkLabel(
            inner, text=str(r["row"]), width=60, anchor="w",
            font=(FONT_FAMILY, 10),
            text_color=COLORS["text_muted"]).pack(side="left")

        ctk.CTkLabel(
            inner, text=r["usn"], width=140, anchor="w",
            font=(FONT_FAMILY, 10),
            text_color=COLORS["text"]).pack(side="left")

        ctk.CTkLabel(
            inner, text=r["name"], width=220, anchor="w",
            font=(FONT_FAMILY, 10),
            text_color=COLORS["text_muted"]).pack(side="left")

        ctk.CTkLabel(
            inner, text=r["subject_label"], width=130, anchor="w",
            font=(FONT_FAMILY, 10),
            text_color=COLORS["text"]).pack(side="left")

        val_txt = "—" if r["value"] is None else f"{r['value']:g}"
        ctk.CTkLabel(
            inner, text=val_txt, width=90, anchor="w",
            font=(FONT_FAMILY, 10, "bold"),
            text_color=COLORS["text"]).pack(side="left")

        # Status chip
        st_box = ctk.CTkFrame(inner, fg_color="transparent", width=220)
        st_box.pack(side="left")
        st_box.pack_propagate(False)

        chip = ctk.CTkFrame(st_box, fg_color=color,
                            corner_radius=CHIP_RADIUS)
        chip.pack(side="left")
        ctk.CTkLabel(
            chip, text=f"  {icon} {label}  ",
            font=(FONT_FAMILY, 9, "bold"),
            text_color="#FFFFFF").pack(padx=2, pady=2)

        if r["note"]:
            ctk.CTkLabel(
                st_box, text=f"  {r['note']}",
                font=(FONT_FAMILY, 9),
                text_color=color).pack(side="left", padx=(6, 0))

    # =========================================================
    # IMPORT ACTIONS
    # =========================================================

    def _render_import_actions(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        rows = self._validation or []
        n_ok = sum(1 for r in rows if r["status"] == "ok")

        # Primary: import valid rows only
        self.primary_button(
            row,
            f"✅  Import {n_ok} valid row(s)",
            command=self._do_import,
            width=260, height=42,
        ).pack(side="left", padx=(0, PAD_MD))

        self.secondary_button(
            row, "🔄  Revalidate",
            command=lambda: (self._revalidate(), self._reload()),
            width=140, height=42,
        ).pack(side="left", padx=(0, PAD_MD))

        self.danger_button(
            row, "🗑  Clear everything",
            command=self._clear_file,
            width=200, height=42,
        ).pack(side="left")

    # =========================================================
    # IMPORT
    # =========================================================

    def _do_import(self):
        rows = self._validation or []
        ok_rows = [r for r in rows if r["status"] == "ok"]

        if not ok_rows:
            self.toast("Nothing to import — no valid rows.", "warning")
            return

        def on_confirm():
            n_ok = 0
            n_err = 0
            errs = []

            for r in ok_rows:
                try:
                    uid = r["student_id"]
                    skey = r["subject"]
                    val = float(r["value"])

                    # Upsert: delete then insert
                    self.db.execute(
                        "DELETE FROM marks WHERE student_id=? "
                        "AND ia_number=? AND subject=?",
                        (uid, self._ia_number, skey))

                    self.db.execute("""
                        INSERT INTO marks
                            (id, student_id, ia_number, subject,
                             marks_obtained, max_marks, entered_at)
                        VALUES (?,?,?,?,?,?,?)
                    """, (
                        f"{uid}-{self._ia_number}-{skey}",
                        uid,
                        self._ia_number,
                        skey,
                        val,
                        self._max_marks,
                        datetime.now().isoformat(),
                    ))
                    n_ok += 1
                except Exception as e:
                    n_err += 1
                    errs.append(
                        f"Row {r['row']} {r['subject_label']}: {e}")

            # Recompute summary if available
            try:
                if hasattr(self.db, "recompute_summary"):
                    self.db.recompute_summary(ia_number=self._ia_number)
                elif hasattr(self.db, "recompute_marks_summary"):
                    self.db.recompute_marks_summary(
                        ia_number=self._ia_number)
            except Exception:
                pass

            # Audit
            try:
                self.db.log_audit(
                    (self.user or {}).get("id", "admin"),
                    "excel_import",
                    target=f"IA-{self._ia_number}",
                    details=f"ok={n_ok} err={n_err}")
            except Exception:
                pass

            self._import_summary = {
                "ok": n_ok,
                "err": n_err,
                "errors": errs[:20],
                "source": os.path.basename(self._file_path or "(sample)"),
                "when": datetime.now().strftime("%d %b %Y · %H:%M"),
            }
            self.toast(f"Imported {n_ok} row(s).", "success")
            self._reload()

        total = len(ok_rows)
        self.confirm(
            "Import marks?",
            f"Import {total} valid row(s) into IA-{self._ia_number}? "
            f"Existing marks for the same (student, subject) will be "
            f"overwritten.",
            on_yes=on_confirm,
            yes_text=f"Import {total}",
        )

    def _render_result_summary(self, parent):
        s = self._import_summary or {}
        card = self.card(parent)
        card.pack(fill="x", pady=(0, PAD_MD))

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        ctk.CTkLabel(
            body,
            text=f"✅  Imported {s.get('ok', 0)} row(s)   ·   "
                 f"❌  {s.get('err', 0)} error(s)",
            font=(FONT_FAMILY, 13, "bold"),
            text_color=STATUS["green"] if s.get("err", 0) == 0
                       else STATUS["amber"],
        ).pack(anchor="w")

        ctk.CTkLabel(
            body,
            text=f"Source: {s.get('source', '—')}   ·   "
                 f"{s.get('when', '')}",
            font=(FONT_FAMILY, 10),
            text_color=COLORS["text_muted"],
        ).pack(anchor="w", pady=(4, 0))

        if s.get("errors"):
            ctk.CTkLabel(
                body, text="Errors:",
                font=(FONT_FAMILY, 10, "bold"),
                text_color=STATUS["red"],
            ).pack(anchor="w", pady=(10, 4))
            for e in s["errors"]:
                ctk.CTkLabel(
                    body, text=f"•  {e}",
                    font=(FONT_FAMILY, 9),
                    text_color=COLORS["text_muted"],
                ).pack(anchor="w")

    # =========================================================
    # TEMPLATE DOWNLOAD
    # =========================================================

    def _download_template(self):
        try:
            from tkinter import filedialog
            path = filedialog.asksaveasfilename(
                title="Save template",
                defaultextension=".xlsx",
                initialfile="marks_template.xlsx",
                filetypes=[("Excel", "*.xlsx")],
            )
            if not path:
                return
            subj = _subject_keys()
            cols = ["USN", "Name"] + [_subject_label(k) for k in subj]

            # Pull a few real students to make the template instantly useful
            try:
                students = self.db.query("""
                    SELECT usn, name FROM users
                    WHERE role='student' AND status='approved'
                    ORDER BY name ASC LIMIT 10
                """)
            except Exception:
                students = pd.DataFrame()

            if students is not None and not students.empty:
                data = []
                for _, r in students.iterrows():
                    row = {
                        "USN": _safe_str(r.get("usn")),
                        "Name": _safe_str(r.get("name")),
                    }
                    for k in subj:
                        row[_subject_label(k)] = None
                    data.append(row)
                df = pd.DataFrame(data, columns=cols)
            else:
                df = pd.DataFrame(columns=cols)
                # One example row
                df.loc[0] = ["USN123", "Sample Student"] + \
                            [None] * len(subj)

            df.to_excel(path, index=False)
            self.toast(f"Template saved: {os.path.basename(path)}",
                       "success")
        except Exception as e:
            self.toast(f"Could not save template: {e}", "error")

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
            print(f"[marks_excel] → show_page('{key}')  args={kw}")

        def go_back(self):
            print("[marks_excel] back")

        def logout(self):
            print("[marks_excel] logout")

    root = ctk.CTk()
    W, H = 1500, 950
    root.geometry(f"{W}x{H}")
    root.configure(fg_color=COLORS["bg"])
    root.title(f"{APP_NAME} — Excel upload")

    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - W) // 2
    y = (sh - H) // 2
    root.geometry(f"{W}x{H}+{x}+{y}")

    app = _FakeApp()
    page = AdminMarksExcelPage(root, app)
    page.pack(fill="both", expand=True)
    root.mainloop()
    print("\n✅ pages/admin/marks_excel.py OK")