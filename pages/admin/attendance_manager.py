# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  pages/admin/attendance_manager.py  ·  Attendance management
# =============================================================

from __future__ import annotations

import os
import sys

# --- make project root importable ---
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from datetime import date, datetime, timedelta
from tkinter import filedialog

import customtkinter as ctk
import pandas as pd

from config import (
    APP_NAME, COLORS, STATUS,
    ATTENDANCE_COLORS, ATTENDANCE_STATUS,
    FONTS, FONT_FAMILY,
    CARD_RADIUS, BUTTON_RADIUS, CHIP_RADIUS,
    PAD_SM, PAD_MD, PAD_LG, PAD_XL,
    TEMPLATES_DIR,
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
# ATTENDANCE MANAGER PAGE
# =============================================================

class AdminAttendanceManagerPage(BasePage):

    def __init__(self, master, app):
        super().__init__(master, app)

        self.build_header("Attendance Manager",
                          "Mark daily attendance for all students", back=False)
        self.build_sidebar(self._build_nav_items())
        self.build_content(scrollable=True)
        self.build_footer()

        # State
        self._active_date = date.today().isoformat()
        self._entries = {}      # user_id -> status
        self._row_refs = []     # list of dicts (per student: uid, name, buttons)
        self._table_container = None
        self._date_entry = None
        self._excel_status = None

        self.render()

    def _build_nav_items(self):
        items = _admin_nav()
        for it in items:
            if it["key"] == "admin_attendance":
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
        self._load_existing()

        # 1. Date selector + summary
        self.section_title("1. Select Date", parent=content)
        self._render_date_bar(content)

        # 2. Bulk actions
        self.section_title("2. Bulk Actions", parent=content)
        self._render_bulk_actions(content)

        # 3. Student list
        self.section_title("3. Mark Attendance", parent=content)
        self._render_table(content)

        # 4. Save row
        self._render_save_row(content)

        # 5. Excel upload
        self.section_title("4. Bulk Upload", parent=content)
        self._render_excel_upload(content)

        # 6. Recent records
        self.section_title("Recent Attendance", parent=content)
        self._render_recent(content)

    # =========================================================
    # LOAD
    # =========================================================

    def _load_students(self):
        try:
            self._students = self.db.get_all_students()
        except Exception:
            self._students = pd.DataFrame()

    def _load_existing(self):
        """Load existing attendance for the active date."""
        self._entries = {}
        try:
            rows = self.db.query("""
                SELECT user_id, status FROM attendance
                WHERE att_date=? AND subject='ALL'
            """, (self._active_date,))
            for _, r in rows.iterrows():
                self._entries[_safe_str(r["user_id"])] = _safe_str(r["status"])
        except Exception:
            pass

    # =========================================================
    # DATE BAR
    # =========================================================

    def _render_date_bar(self, parent):
        card = self.card(parent)
        card.pack(fill="x", pady=(0, PAD_MD))

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        row = ctk.CTkFrame(body, fg_color="transparent")
        row.pack(fill="x")

        ctk.CTkLabel(
            row, text="Date (YYYY-MM-DD):",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_muted"]).pack(side="left", padx=(0, 10))

        self._date_entry = ctk.CTkEntry(
            row, width=180, height=38,
            font=FONTS["small"],
            fg_color=COLORS["surface_alt"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            corner_radius=10)
        self._date_entry.insert(0, self._active_date)
        self._date_entry.pack(side="left", padx=(0, PAD_MD))

        self.primary_button(
            row, "Load",
            command=self._apply_date,
            width=100, height=38,
        ).pack(side="left", padx=(0, PAD_MD))

        self.secondary_button(
            row, "Today",
            command=lambda: self._set_date(date.today().isoformat()),
            width=90, height=38,
        ).pack(side="left", padx=(0, PAD_SM))

        self.secondary_button(
            row, "Yesterday",
            command=lambda: self._set_date(
                (date.today() - timedelta(days=1)).isoformat()),
            width=110, height=38,
        ).pack(side="left")

        # Summary chip
        self._summary_label = ctk.CTkLabel(
            body, text="",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_muted"],
            anchor="w")
        self._summary_label.pack(anchor="w", pady=(10, 0))

    def _apply_date(self):
        try:
            new_d = (self._date_entry.get() or "").strip()
            # Validate
            datetime.strptime(new_d, "%Y-%m-%d")
            self._active_date = new_d
            self._load_existing()
            self._reload()
        except Exception:
            self.toast("Invalid date. Use YYYY-MM-DD.", "error")

    def _set_date(self, new_d: str):
        try:
            self._date_entry.delete(0, "end")
            self._date_entry.insert(0, new_d)
        except Exception:
            pass
        self._active_date = new_d
        self._load_existing()
        self._reload()

    # =========================================================
    # BULK ACTIONS
    # =========================================================

    def _render_bulk_actions(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        self.primary_button(
            row, "✅  Mark all Present",
            command=lambda: self._mark_all("P"),
            width=200, height=42,
        ).pack(side="left", padx=(0, PAD_SM))

        self.secondary_button(
            row, "🔵  All Excused",
            command=lambda: self._mark_all("E"),
            width=160, height=42,
        ).pack(side="left", padx=(0, PAD_SM))

        self.secondary_button(
            row, "🧹  Clear all",
            command=lambda: self._mark_all(None),
            width=140, height=42,
        ).pack(side="left")

    def _mark_all(self, status):
        for uid in self._entries.keys():
            pass
        # Build a dict of all student IDs
        if self._students is None or self._students.empty:
            return
        for _, s in self._students.iterrows():
            uid = _safe_str(s.get("id"))
            if status is None:
                self._entries.pop(uid, None)
            else:
                self._entries[uid] = status
        self._reload()

    # =========================================================
    # TABLE
    # =========================================================

    def _render_table(self, parent):
        card = self.card(parent)
        card.pack(fill="x", pady=(0, PAD_MD))

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        self._table_container = ctk.CTkFrame(body, fg_color="transparent")
        self._table_container.pack(fill="x")
        self._row_refs = []

        students = self._students
        if students is None or students.empty:
            ctk.CTkLabel(
                self._table_container,
                text="No students found.",
                font=FONTS["body"],
                text_color=COLORS["text_muted"]).pack(pady=20)
            self._update_summary()
            return

        # Header
        header = ctk.CTkFrame(self._table_container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 4))

        cols = [
            ("#",       40),
            ("Student", 300),
            ("USN",     140),
            ("Status",  240),
        ]
        for label, w in cols:
            ctk.CTkLabel(
                header, text=label, width=w, anchor="w",
                font=(FONT_FAMILY, 10, "bold"),
                text_color=COLORS["text_muted"]).pack(side="left")

        # Rows
        for i, (_, s) in enumerate(students.iterrows(), start=1):
            self._render_row(i, s)

        # Update summary
        self._update_summary()

    def _render_row(self, idx: int, s):
        uid = _safe_str(s.get("id"))
        name = _safe_str(s.get("name")) or "—"
        usn = _safe_str(s.get("usn")) or "—"
        current = self._entries.get(uid)

        row = ctk.CTkFrame(
            self._table_container,
            fg_color=COLORS["surface_alt"] if idx % 2
            else COLORS["surface"],
            corner_radius=6)
        row.pack(fill="x", pady=1)

        inner = ctk.CTkFrame(row, fg_color="transparent")
        inner.pack(fill="x", padx=6, pady=6)

        # Sl
        ctk.CTkLabel(
            inner, text=str(idx), width=40, anchor="w",
            font=(FONT_FAMILY, 10),
            text_color=COLORS["text_muted"]).pack(side="left")

        # Avatar + name
        name_box = ctk.CTkFrame(inner, fg_color="transparent", width=300)
        name_box.pack(side="left")
        name_box.pack_propagate(False)

        try:
            avatar = load_avatar(
                user_id=uid, name=name, size=28, shape="circle")
            ctk.CTkLabel(name_box, image=avatar, text="").pack(
                side="left", padx=(0, 8))
        except Exception:
            pass

        ctk.CTkLabel(
            name_box, text=name,
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text"], anchor="w").pack(side="left")

        # USN
        ctk.CTkLabel(
            inner, text=usn, width=140, anchor="w",
            font=(FONT_FAMILY, 10),
            text_color=COLORS["text_muted"]).pack(side="left")

        # Status buttons
        status_box = ctk.CTkFrame(inner, fg_color="transparent", width=240)
        status_box.pack(side="left")
        status_box.pack_propagate(False)

        btn_refs = {}
        for code, label in [("P", "✓ P"), ("L", "◐ L"),
                            ("A", "✗ A"), ("E", "★ E")]:
            is_active = (current == code)
            color = ATTENDANCE_COLORS.get(code, COLORS["surface_alt"])
            btn = ctk.CTkButton(
                status_box,
                text=label,
                width=52, height=32,
                font=(FONT_FAMILY, 10, "bold"),
                fg_color=color if is_active else COLORS["surface"],
                hover_color=color,
                text_color="#FFFFFF" if is_active else COLORS["text_muted"],
                corner_radius=8,
                command=lambda c=code, u=uid:
                    self._toggle_status(u, c, btn_refs),
            )
            btn.pack(side="left", padx=2)
            btn_refs[code] = btn

        self._row_refs.append({
            "uid": uid, "name": name, "buttons": btn_refs,
        })

    def _toggle_status(self, uid: str, status_code: str, btn_refs: dict):
        # Toggle: if already this status, clear it
        current = self._entries.get(uid)
        if current == status_code:
            self._entries.pop(uid, None)
            new = None
        else:
            self._entries[uid] = status_code
            new = status_code

        # Update button colors
        for code, btn in btn_refs.items():
            is_active = (new == code)
            color = ATTENDANCE_COLORS.get(code, COLORS["surface_alt"])
            try:
                btn.configure(
                    fg_color=color if is_active else COLORS["surface"],
                    text_color="#FFFFFF" if is_active
                    else COLORS["text_muted"],
                )
            except Exception:
                pass

        self._update_summary()

    def _update_summary(self):
        if self._summary_label is None:
            return
        total = len(self._students) if self._students is not None else 0
        counts = {"P": 0, "A": 0, "L": 0, "E": 0}
        for st in self._entries.values():
            if st in counts:
                counts[st] += 1

        marked = sum(counts.values())
        unmarked = total - marked

        parts = [
            f"Date: {self._active_date}",
            f"Total: {total}",
            f"Marked: {marked}",
            f"Unmarked: {unmarked}",
            f"P: {counts['P']}  L: {counts['L']}  "
            f"A: {counts['A']}  E: {counts['E']}",
        ]
        try:
            self._summary_label.configure(
                text="   ·   ".join(parts))
        except Exception:
            pass

    # =========================================================
    # SAVE
    # =========================================================

    def _render_save_row(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        self.primary_button(
            row, "💾  Save Attendance",
            command=self._save_all,
            width=240, height=44,
        ).pack(side="left", padx=(0, PAD_MD))

        self.secondary_button(
            row, "🔄  Reload",
            command=self._reload,
            width=120, height=44,
        ).pack(side="left")

    def _save_all(self):
        if not self._entries:
            self.toast("No attendance marked.", "warning")
            return

        admin_id = (self.user or {}).get("id", "admin")

        def on_confirm():
            n = 0
            for uid, status in self._entries.items():
                try:
                    self.db.mark_attendance(
                        uid, self._active_date, status,
                        subject="ALL", marked_by=admin_id)
                    n += 1
                except Exception as e:
                    print(f"Save error for {uid}: {e}")

            self.toast(
                f"Saved attendance for {n} student(s) on "
                f"{self._active_date}.", "success")
            self.db.log_audit(
                admin_id, "save_attendance",
                target=self._active_date, details=f"rows={n}")
            self._reload()

        self.confirm(
            "Save attendance?",
            f"Save attendance for {len(self._entries)} student(s) on "
            f"{self._active_date}?",
            on_yes=on_confirm,
            yes_text="Save",
        )

    # =========================================================
    # EXCEL UPLOAD
    # =========================================================

    def _render_excel_upload(self, parent):
        card = self.card(parent)
        card.pack(fill="x", pady=(0, PAD_MD))

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        ctk.CTkLabel(
            body,
            text="Bulk import attendance from an Excel file. The file "
                 "must have columns: USN, Name, Date, Status (P/A/L/E).",
            font=(FONT_FAMILY, 10),
            text_color=COLORS["text_muted"],
            anchor="w", wraplength=900, justify="left",
        ).pack(anchor="w", pady=(0, 10))

        row = ctk.CTkFrame(body, fg_color="transparent")
        row.pack(fill="x")

        self.primary_button(
            row, "📂  Upload .xlsx",
            command=self._upload_excel,
            width=180, height=38,
        ).pack(side="left", padx=(0, PAD_SM))

        self.secondary_button(
            row, "📥  Attendance template",
            command=self._download_template,
            width=200, height=38,
        ).pack(side="left", padx=(0, PAD_SM))

        self.secondary_button(
            row, "📁  Open folder",
            command=lambda: _open_folder(TEMPLATES_DIR),
            width=140, height=38,
        ).pack(side="left")

        self._excel_status = ctk.CTkLabel(
            body, text="",
            font=(FONT_FAMILY, 10),
            text_color=COLORS["text_muted"],
            anchor="w", wraplength=900, justify="left")
        self._excel_status.pack(anchor="w", pady=(10, 0))

    def _download_template(self):
        try:
            from utils.excel_io import make_attendance_template
            p = make_attendance_template()
            self.toast(f"Saved: {os.path.basename(p)}", "success")
            _open_folder(TEMPLATES_DIR)
        except Exception as e:
            self.toast(f"Could not create: {e}", "error")

    def _upload_excel(self):
        path = filedialog.askopenfilename(
            title="Choose attendance file",
            filetypes=[("Excel files", "*.xlsx *.xls")])
        if not path:
            return

        try:
            from utils.excel_io import (
                read_attendance_excel, import_attendance_to_db,
            )
            report = read_attendance_excel(path)
            total = report.total_rows
            valid = report.valid_rows
            invalid = report.invalid_rows

            admin_id = (self.user or {}).get("id", "admin")

            def on_confirm():
                try:
                    result = import_attendance_to_db(
                        self.db, path, marked_by=admin_id)
                    self.toast(
                        f"Imported {result.valid_rows} row(s); "
                        f"{len(result.warnings)} warning(s).",
                        "success" if result.valid_rows else "warning")
                    self.db.log_audit(
                        admin_id, "import_attendance_excel",
                        target=os.path.basename(path),
                        details=f"valid={result.valid_rows}")
                    self._reload()
                except Exception as e:
                    self.toast(f"Import failed: {e}", "error")

            # Show status
            try:
                self._excel_status.configure(
                    text=f"📄  {os.path.basename(path)}  —  "
                         f"Total: {total}  |  Valid: {valid}  |  "
                         f"Invalid: {invalid}",
                    text_color=COLORS["text"])
            except Exception:
                pass

            if valid == 0:
                self.toast("No valid rows to import.", "warning")
                return

            self.confirm(
                "Import attendance?",
                f"Import {valid} row(s) from {os.path.basename(path)}?",
                on_yes=on_confirm,
                yes_text=f"Import {valid}",
            )
        except Exception as e:
            self.toast(f"Validation failed: {e}", "error")

    # =========================================================
    # RECENT RECORDS
    # =========================================================

    def _render_recent(self, parent):
        card = self.card(parent)
        card.pack(fill="x", pady=(0, PAD_MD))

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        # Last 10 dates with their aggregate counts
        try:
            rows = self.db.query("""
                SELECT att_date,
                       SUM(CASE WHEN status='P' THEN 1 ELSE 0 END) AS p,
                       SUM(CASE WHEN status='A' THEN 1 ELSE 0 END) AS a,
                       SUM(CASE WHEN status='L' THEN 1 ELSE 0 END) AS l,
                       SUM(CASE WHEN status='E' THEN 1 ELSE 0 END) AS e,
                       COUNT(*) AS total
                FROM attendance
                GROUP BY att_date
                ORDER BY att_date DESC
                LIMIT 10
            """)
        except Exception:
            rows = pd.DataFrame()

        if rows is None or rows.empty:
            ctk.CTkLabel(
                body, text="No attendance recorded yet.",
                font=(FONT_FAMILY, 11),
                text_color=COLORS["text_muted"]).pack(pady=12)
            return

        # Header
        header = ctk.CTkFrame(body, fg_color="transparent")
        header.pack(fill="x", pady=(0, 4))
        for label, w in [("Date", 140), ("Present", 100),
                         ("Late", 80), ("Absent", 100),
                         ("Excused", 100), ("Total", 100),
                         ("Attended %", 120)]:
            ctk.CTkLabel(
                header, text=label, width=w, anchor="w",
                font=(FONT_FAMILY, 10, "bold"),
                text_color=COLORS["text_muted"]).pack(side="left")

        # Rows
        for _, r in rows.iterrows():
            d = _safe_str(r["att_date"])
            p = int(_safe_float(r["p"]))
            a = int(_safe_float(r["a"]))
            l = int(_safe_float(r["l"]))
            e = int(_safe_float(r["e"]))
            total = int(_safe_float(r["total"]))
            attended = p + l + e
            pct = (attended / total * 100) if total else 0

            row = ctk.CTkFrame(body, fg_color=COLORS["surface_alt"],
                               corner_radius=6)
            row.pack(fill="x", pady=1)

            inner = ctk.CTkFrame(row, fg_color="transparent")
            inner.pack(fill="x", padx=8, pady=6)

            ctk.CTkLabel(
                inner, text=d, width=140, anchor="w",
                font=(FONT_FAMILY, 10),
                text_color=COLORS["text"]).pack(side="left")

            ctk.CTkLabel(
                inner, text=str(p), width=100, anchor="w",
                font=(FONT_FAMILY, 10, "bold"),
                text_color=STATUS["green"]).pack(side="left")

            ctk.CTkLabel(
                inner, text=str(l), width=80, anchor="w",
                font=(FONT_FAMILY, 10),
                text_color=STATUS["amber"]).pack(side="left")

            ctk.CTkLabel(
                inner, text=str(a), width=100, anchor="w",
                font=(FONT_FAMILY, 10, "bold"),
                text_color=STATUS["red"]).pack(side="left")

            ctk.CTkLabel(
                inner, text=str(e), width=100, anchor="w",
                font=(FONT_FAMILY, 10),
                text_color=STATUS["info"]).pack(side="left")

            ctk.CTkLabel(
                inner, text=str(total), width=100, anchor="w",
                font=(FONT_FAMILY, 10),
                text_color=COLORS["text_muted"]).pack(side="left")

            att_color = STATUS["green"] if pct >= 85 else \
                        (STATUS["amber"] if pct >= 70 else STATUS["red"])
            ctk.CTkLabel(
                inner, text=f"{pct:.0f}%", width=120, anchor="w",
                font=(FONT_FAMILY, 11, "bold"),
                text_color=att_color).pack(side="left")

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
            print(f"[attendance] → show_page('{key}')  args={kw}")

        def go_back(self):
            print("[attendance] back")

        def logout(self):
            print("[attendance] logout")

    root = ctk.CTk()
    W, H = 1400, 900
    root.geometry(f"{W}x{H}")
    root.configure(fg_color=COLORS["bg"])
    root.title(f"{APP_NAME} — attendance manager")

    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - W) // 2
    y = (sh - H) // 2
    root.geometry(f"{W}x{H}+{x}+{y}")

    app = _FakeApp()
    page = AdminAttendanceManagerPage(root, app)
    page.pack(fill="both", expand=True)
    root.mainloop()
    print("\n✅ pages/admin/attendance_manager.py OK")