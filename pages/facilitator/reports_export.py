# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  pages/facilitator/reports_export.py  ·  Reports & export
# =============================================================

from __future__ import annotations

import os
import sys

# --- make project root importable ---
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import zipfile
from datetime import datetime

import customtkinter as ctk
import pandas as pd

from config import (
    APP_NAME, COLORS, STATUS, DATA_DIR, CERT_DIR, TEMPLATES_DIR,
    FONTS, FONT_FAMILY,
    CARD_RADIUS, BUTTON_RADIUS, CHIP_RADIUS,
    PAD_SM, PAD_MD, PAD_LG, PAD_XL,
)
from pages.base_page import BasePage
from utils.excel_io import (
    export_class_marks, export_class_analytics, export_student_report,
)
from utils.certificates import generate_class_certificates


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
# REPORTS & EXPORT PAGE
# =============================================================

class FacilitatorReportsExportPage(BasePage):

    def __init__(self, master, app):
        super().__init__(master, app)

        self.build_header("Reports & Export",
                          "Download data, reports, and certificates",
                          back=False)
        self.build_sidebar(self._build_nav_items())
        self.build_content(scrollable=True)
        self.build_footer()

        # State
        self._log = []      # list of {when, label, path}
        self._log_container = None

        self.render()

    def _build_nav_items(self):
        items = _facilitator_nav()
        for it in items:
            if it["key"] == "fac_reports":
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

        # 1. Preview stats
        self._render_preview_stats(content)

        # 2. Class-level exports
        self.section_title("Class Reports", parent=content)
        self._render_class_exports(content)

        # 3. Student-level exports
        self.section_title("Student Reports", parent=content)
        self._render_student_exports(content)

        # 4. Certificates
        self.section_title("Certificates", parent=content)
        self._render_certificate_exports(content)

        # 5. Folder shortcuts
        self.section_title("Folders", parent=content)
        self._render_folder_shortcuts(content)

        # 6. Activity log
        self.section_title("Recent Exports", parent=content)
        self._log_container = ctk.CTkFrame(content, fg_color="transparent")
        self._log_container.pack(fill="x", pady=(0, PAD_MD))
        self._render_log()

    # =========================================================
    # LOAD
    # =========================================================

    def _load_data(self):
        # Latest IA
        try:
            ia_df = self.db.query(
                "SELECT MAX(ia_number) AS ia FROM marks_summary")
            self._latest_ia = int(ia_df.iloc[0]["ia"] or 3)
        except Exception:
            self._latest_ia = 3

        # Students
        try:
            self._students = self.db.get_all_students()
        except Exception:
            self._students = pd.DataFrame()

        # Class marks summary
        try:
            self._class_marks = self.db.get_class_marks_summary(
                ia_number=self._latest_ia)
        except Exception:
            self._class_marks = pd.DataFrame()

        # Zone counts
        try:
            self._zone_counts = self.db.class_zone_counts(
                ia_number=self._latest_ia)
        except Exception:
            self._zone_counts = {"red": 0, "yellow": 0,
                                 "green": 0, "gold": 0}

        # Certificates count
        try:
            certs = self.db.query("SELECT COUNT(*) AS n FROM certificates")
            self._cert_count = int(certs.iloc[0]["n"]) if not certs.empty else 0
        except Exception:
            self._cert_count = 0

    # =========================================================
    # PREVIEW STATS
    # =========================================================

    def _render_preview_stats(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        n_students = 0 if self._students is None else len(self._students)
        n_marks = 0 if self._class_marks is None else len(self._class_marks)

        # At risk count
        red = int(self._zone_counts.get("red", 0))

        # Class average
        avg_pct = 0.0
        if self._class_marks is not None and not self._class_marks.empty:
            if "percentage" in self._class_marks.columns:
                avg_pct = _safe_float(self._class_marks["percentage"].mean())

        self.stat_card(
            row, f"IA-{self._latest_ia}", "Latest IA",
            accent=COLORS["primary"], icon="📊",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, n_students, "Students",
            accent=COLORS["primary"], icon="👥",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, n_marks, "Mark records",
            accent=COLORS["primary"], icon="📝",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, f"{avg_pct:.1f}%", "Class avg",
            accent=STATUS["green"] if avg_pct >= 70
                   else (STATUS["amber"] if avg_pct >= 50 else STATUS["red"]),
            icon="🎯",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, red, "At-risk",
            accent=STATUS["red"], icon="⚠️",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, self._cert_count, "Certificates issued",
            accent=STATUS["gold"], icon="📜",
        ).pack(side="left")

    # =========================================================
    # CLASS EXPORTS
    # =========================================================

    def _render_class_exports(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        # Marks xlsx
        card = self._export_card(
            row,
            icon="📊",
            title="Class Marks",
            desc=f"All student marks for IA-{self._latest_ia} with summary sheet",
            color=COLORS["primary"],
        )
        self.primary_button(
            card, "Export .xlsx",
            command=self._export_class_marks,
            width=150, height=36,
        ).pack(anchor="w", pady=(8, 0))

        # Analytics xlsx
        card = self._export_card(
            row,
            icon="📈",
            title="Class Analytics",
            desc="Marks + zone counts + subject averages in one workbook",
            color="#8B5CF6",
        )
        self.primary_button(
            card, "Export .xlsx",
            command=self._export_class_analytics,
            width=150, height=36,
        ).pack(anchor="w", pady=(8, 0))

    # =========================================================
    # STUDENT EXPORTS
    # =========================================================

    def _render_student_exports(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        # Single student
        card = self._export_card(
            row,
            icon="👤",
            title="Single Student Report",
            desc="Pick a student → get marks + attendance + activities + badges",
            color="#10B981",
        )

        # Student dropdown
        student_names = []
        student_lookup = {}
        if self._students is not None and not self._students.empty:
            for _, s in self._students.iterrows():
                label = f"{_safe_str(s.get('name'))} ({_safe_str(s.get('usn'))})"
                student_names.append(label)
                student_lookup[label] = _safe_str(s.get("id"))

        self._student_lookup = student_lookup

        if student_names:
            menu = ctk.CTkOptionMenu(
                card, values=student_names, width=280, height=34,
                font=FONTS["small"],
                fg_color=COLORS["surface_alt"],
                button_color=COLORS["primary"],
                button_hover_color=COLORS["primary_hover"],
                text_color=COLORS["text"],
                dropdown_fg_color=COLORS["surface_alt"],
                dropdown_text_color=COLORS["text"],
                corner_radius=10)
            menu.set(student_names[0])
            menu.pack(anchor="w", pady=(6, 8))
            self._student_menu = menu

        self.primary_button(
            card, "Export .xlsx",
            command=self._export_single_student,
            width=150, height=36,
        ).pack(anchor="w")

        # Batch all students
        card = self._export_card(
            row,
            icon="📦",
            title="Batch: All Student Reports",
            desc=f"Generate all {len(student_names)} reports and zip them",
            color="#F59E0B",
        )
        self.primary_button(
            card, "Export all (.zip)",
            command=self._export_all_students,
            width=180, height=36,
        ).pack(anchor="w", pady=(8, 0))

    # =========================================================
    # CERTIFICATES
    # =========================================================

    def _render_certificate_exports(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        # Batch generate
        card = self._export_card(
            row,
            icon="📜",
            title="Generate All Certificates",
            desc="Award + generate certificates for every eligible student",
            color="#FBBF24",
        )
        self.primary_button(
            card, "Generate",
            command=self._generate_certificates,
            width=150, height=36,
        ).pack(anchor="w", pady=(8, 0))

        # Open certificates folder
        card = self._export_card(
            row,
            icon="🗂️",
            title="Open Certificates Folder",
            desc=f"Browse all issued PDFs ({self._cert_count} so far)",
            color="#60A5FA",
        )
        self.secondary_button(
            card, "Open folder",
            command=lambda: self._open_folder(CERT_DIR, "Certificates"),
            width=150, height=36,
        ).pack(anchor="w", pady=(8, 0))

    # =========================================================
    # FOLDER SHORTCUTS
    # =========================================================

    def _render_folder_shortcuts(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        shortcuts = [
            ("📁", "Data folder",       DATA_DIR,      "All exports land here"),
            ("📜", "Certificates",      CERT_DIR,      "Generated PDFs"),
            ("📋", "Templates",         TEMPLATES_DIR, "Blank xlsx templates"),
        ]

        for icon, title, path, desc in shortcuts:
            card = self._export_card(
                row, icon=icon, title=title, desc=desc,
                color=COLORS["text_muted"],
            )
            self.secondary_button(
                card, "Open",
                command=lambda p=path, t=title: self._open_folder(p, t),
                width=100, height=34,
            ).pack(anchor="w", pady=(8, 0))

    # =========================================================
    # EXPORT CARD BUILDER
    # =========================================================

    def _export_card(self, parent, icon, title, desc, color,
                     width=340, height=170):
        card = ctk.CTkFrame(
            parent,
            fg_color=COLORS["surface"],
            corner_radius=CARD_RADIUS,
            border_width=1,
            border_color=color,
            width=width, height=height)
        card.pack(side="left", padx=(0, PAD_MD), pady=4)
        card.pack_propagate(False)

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="both", expand=True,
                  padx=PAD_LG, pady=PAD_MD)

        head = ctk.CTkFrame(body, fg_color="transparent")
        head.pack(anchor="w", fill="x")

        ctk.CTkLabel(
            head, text=icon,
            font=(FONT_FAMILY, 22),
            text_color=color).pack(side="left", padx=(0, 8))

        ctk.CTkLabel(
            head, text=title,
            font=(FONT_FAMILY, 13, "bold"),
            text_color=COLORS["text"]).pack(side="left")

        ctk.CTkLabel(
            body, text=desc,
            font=(FONT_FAMILY, 10),
            text_color=COLORS["text_muted"],
            wraplength=width - 40, justify="left",
        ).pack(anchor="w", pady=(6, 0))

        return body

    # =========================================================
    # EXPORT HANDLERS
    # =========================================================

    def _export_class_marks(self):
        try:
            path = export_class_marks(self.db,
                                     ia_number=self._latest_ia)
            self._add_log("Class Marks (IA-" + str(self._latest_ia) + ")",
                          path)
            self.toast(f"Saved: {os.path.basename(path)}", "success")
            self._open_folder(DATA_DIR, "Data")
        except Exception as e:
            self.toast(f"Export failed: {e}", "error")

    def _export_class_analytics(self):
        try:
            path = export_class_analytics(self.db,
                                         ia_number=self._latest_ia)
            self._add_log("Class Analytics (IA-" +
                          str(self._latest_ia) + ")", path)
            self.toast(f"Saved: {os.path.basename(path)}", "success")
            self._open_folder(DATA_DIR, "Data")
        except Exception as e:
            self.toast(f"Export failed: {e}", "error")

    def _export_single_student(self):
        try:
            label = self._student_menu.get()
            uid = self._student_lookup.get(label)
            if not uid:
                self.toast("Please select a student.", "warning")
                return
            path = export_student_report(self.db, uid)
            self._add_log(f"Student: {label}", path)
            self.toast(f"Saved: {os.path.basename(path)}", "success")
            self._open_folder(DATA_DIR, "Data")
        except Exception as e:
            self.toast(f"Export failed: {e}", "error")

    def _export_all_students(self):
        if self._students is None or self._students.empty:
            self.toast("No students to export.", "warning")
            return

        # Confirm batch
        def on_confirm():
            try:
                paths = []
                for _, s in self._students.iterrows():
                    uid = _safe_str(s.get("id"))
                    if not uid:
                        continue
                    try:
                        p = export_student_report(self.db, uid)
                        paths.append(p)
                    except Exception:
                        continue

                if not paths:
                    self.toast("No reports generated.", "warning")
                    return

                # Zip them
                zip_name = f"all_reports_{datetime.now().strftime('%Y%m%d_%H%M')}.zip"
                zip_path = os.path.join(DATA_DIR, zip_name)
                with zipfile.ZipFile(zip_path, "w",
                                    zipfile.ZIP_DEFLATED) as zf:
                    for p in paths:
                        zf.write(p, arcname=os.path.basename(p))

                self._add_log(f"Batch: {len(paths)} reports", zip_path)
                self.toast(
                    f"Batch saved: {zip_name} ({len(paths)} reports)",
                    "success")
                self._open_folder(DATA_DIR, "Data")
            except Exception as e:
                self.toast(f"Batch export failed: {e}", "error")

        self.confirm(
            "Export all student reports?",
            f"This will generate {len(self._students)} reports and zip them. "
            f"It may take a few seconds.",
            on_yes=on_confirm,
            yes_text="Export all",
        )

    def _generate_certificates(self):
        def on_confirm():
            try:
                results = generate_class_certificates(
                    self.db, ia_number=self._latest_ia)
                total = sum(len(v) for v in results.values())
                if total > 0:
                    self.toast(
                        f"Generated {total} certificate(s).", "success")
                else:
                    self.toast("No certificates to generate.", "info")
                # Reload to refresh cert count
                self._reload()
            except Exception as e:
                self.toast(f"Generation failed: {e}", "error")

        self.confirm(
            "Generate all eligible certificates?",
            "This will issue certificates for gold-zone students, subject "
            "toppers, perfect attendance, most improved, all-rounders, and "
            "activity champions.",
            on_yes=on_confirm,
            yes_text="Generate",
        )

    # =========================================================
    # FOLDER OPEN
    # =========================================================

    def _open_folder(self, path, label):
        # Ensure it exists
        try:
            os.makedirs(path, exist_ok=True)
        except Exception:
            pass
        if not _open_folder(path):
            self.toast(f"Could not open {label}", "error")

    # =========================================================
    # LOG
    # =========================================================

    def _add_log(self, label: str, path: str):
        self._log.insert(0, {
            "when": datetime.now().strftime("%H:%M:%S"),
            "label": label,
            "path": path,
        })
        self._log = self._log[:10]      # keep last 10
        self._render_log()

    def _render_log(self):
        if self._log_container is None:
            return
        for w in self._log_container.winfo_children():
            w.destroy()

        if not self._log:
            ctk.CTkLabel(
                self._log_container,
                text="No exports yet this session.",
                font=FONTS["small"],
                text_color=COLORS["text_muted"]).pack(pady=12)
            return

        card = self.card(self._log_container)
        card.pack(fill="x")

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        for entry in self._log:
            row = ctk.CTkFrame(body, fg_color=COLORS["surface_alt"],
                               corner_radius=8)
            row.pack(fill="x", pady=2)

            ctk.CTkLabel(
                row, text=entry["when"],
                width=80, anchor="w",
                font=(FONT_FAMILY, 10),
                text_color=COLORS["text_muted"],
            ).pack(side="left", padx=(8, 0), pady=6)

            ctk.CTkLabel(
                row, text=entry["label"],
                font=(FONT_FAMILY, 10, "bold"),
                text_color=COLORS["text"], anchor="w",
            ).pack(side="left", padx=(0, 10))

            ctk.CTkLabel(
                row, text=os.path.basename(entry["path"]),
                font=(FONT_FAMILY, 9),
                text_color=COLORS["text_muted"], anchor="w",
            ).pack(side="left")

            self.secondary_button(
                row, "Open",
                command=lambda p=entry["path"]:
                    self._open_export(p),
                width=70, height=28,
            ).pack(side="right", padx=8)

    def _open_export(self, path: str):
        try:
            if not os.path.exists(path):
                self.toast("File not found", "error")
                return
            if sys.platform.startswith("win"):
                os.startfile(path)  # noqa: S606
            elif sys.platform == "darwin":
                os.system(f'open "{path}"')
            else:
                os.system(f'xdg-open "{path}"')
        except Exception as e:
            self.toast(f"Cannot open: {e}", "error")

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
            print(f"[reports] → show_page('{key}')  args={kw}")

        def go_back(self):
            print("[reports] back")

        def logout(self):
            print("[reports] logout")

    root = ctk.CTk()
    W, H = 1400, 900
    root.geometry(f"{W}x{H}")
    root.configure(fg_color=COLORS["bg"])
    root.title(f"{APP_NAME} — reports & export")

    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - W) // 2
    y = (sh - H) // 2
    root.geometry(f"{W}x{H}+{x}+{y}")

    app = _FakeApp()
    page = FacilitatorReportsExportPage(root, app)
    page.pack(fill="both", expand=True)
    root.mainloop()
    print("\n✅ pages/facilitator/reports_export.py OK")