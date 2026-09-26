# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  pages/admin/certificate_generator.py  ·  Certificate generation
# =============================================================

from __future__ import annotations

import os
import sys

# --- make project root importable ---
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import subprocess
from datetime import datetime

import customtkinter as ctk
import pandas as pd

from config import (
    APP_NAME, COLORS, STATUS, ZONE_COLORS, ZONE_LABELS,
    FONTS, FONT_FAMILY,
    CARD_RADIUS, BUTTON_RADIUS, CHIP_RADIUS,
    PAD_SM, PAD_MD, PAD_LG, PAD_XL,
    CERT_DIR, CERTIFICATES,
)
from pages.base_page import BasePage
from utils.avatars import load_avatar
from utils.certificates import (
    generate_class_certificates,
    certificate_academic_excellence,
    certificate_subject_topper,
    certificate_perfect_attendance,
    certificate_most_improved,
    certificate_all_rounder,
    certificate_activity_champion,
)


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


CERT_ICONS = {
    "academic_excellence": "🏆",
    "subject_topper":      "🎯",
    "perfect_attendance":  "🌟",
    "most_improved":       "📈",
    "all_rounder":         "💎",
    "activity_champion":   "🎗️",
}

CERT_COLORS = {
    "academic_excellence": "#FBBF24",
    "subject_topper":      "#8B5CF6",
    "perfect_attendance":  "#60A5FA",
    "most_improved":       "#10B981",
    "all_rounder":         "#EC4899",
    "activity_champion":   "#F59E0B",
}


def _open_file(path: str) -> bool:
    try:
        if not os.path.exists(path):
            return False
        if sys.platform.startswith("win"):
            os.startfile(path)   # noqa: S606
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
        return True
    except Exception:
        return False


def _open_folder(path: str) -> bool:
    try:
        if not os.path.exists(path):
            return False
        if sys.platform.startswith("win"):
            os.startfile(path)   # noqa: S606
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
        return True
    except Exception:
        return False


def _fmt_date(iso: str) -> str:
    if not iso:
        return "—"
    try:
        d = datetime.fromisoformat(iso)
        return d.strftime("%d %b %Y")
    except Exception:
        return iso[:10]


# =============================================================
# CERTIFICATE GENERATOR PAGE
# =============================================================

class AdminCertificateGeneratorPage(BasePage):

    def __init__(self, master, app):
        super().__init__(master, app)

        self.build_header("Certificate Generator",
                          "Issue and browse achievement certificates",
                          back=False)
        self.build_sidebar(self._build_nav_items())
        self.build_content(scrollable=True)
        self.build_footer()

        # State
        self._list_container = None
        self._type_filter = "all"
        self._filter_btns = {}

        self.render()

    def _build_nav_items(self):
        items = _admin_nav()
        for it in items:
            if it["key"] == "admin_certificates":
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
        self.section_title("Overview", parent=content)
        self._render_stats(content)

        # 2. Bulk generate
        self.section_title("1. Auto-generate", parent=content)
        self._render_bulk(content)

        # 3. Manual generate
        self.section_title("2. Generate individually", parent=content)
        self._render_manual(content)

        # 4. Folder shortcut
        self.section_title("3. Browse folder", parent=content)
        self._render_folder_row(content)

        # 5. Filter + list
        self.section_title("Issued Certificates", parent=content)
        self._render_filter_row(content)
        self._list_container = ctk.CTkFrame(content, fg_color="transparent")
        self._list_container.pack(fill="x", pady=(0, PAD_MD))
        self._render_list()

    # =========================================================
    # LOAD
    # =========================================================

    def _load_data(self):
        # Certificates
        try:
            self._certs = self.db.query("""
                SELECT c.*, u.name AS student_name, u.usn
                FROM certificates c
                LEFT JOIN users u ON u.id = c.user_id
                ORDER BY c.issued_at DESC
            """)
        except Exception:
            self._certs = pd.DataFrame()

        # Students
        try:
            self._students = self.db.get_all_students()
        except Exception:
            self._students = pd.DataFrame()

    # =========================================================
    # STATS
    # =========================================================

    def _render_stats(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        c = self._certs
        total = 0 if c is None else len(c)

        # By type
        by_type = {}
        this_month = 0
        now = datetime.now()
        if c is not None and not c.empty:
            for _, r in c.iterrows():
                t = _safe_str(r.get("cert_type"))
                by_type[t] = by_type.get(t, 0) + 1
                try:
                    d = datetime.fromisoformat(_safe_str(r.get("issued_at")))
                    if d.year == now.year and d.month == now.month:
                        this_month += 1
                except Exception:
                    pass

        # Students with certs
        with_certs = 0
        if c is not None and not c.empty:
            with_certs = c["user_id"].nunique()

        n_students = 0 if self._students is None else len(self._students)
        coverage = (with_certs / n_students * 100) if n_students else 0

        self.stat_card(
            row, total, "Total certificates",
            accent=STATUS["gold"], icon="📜",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, this_month, "This month",
            accent=COLORS["primary"], icon="🗓️",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, len(by_type), f"Of {len(CERTIFICATES)} types",
            accent=COLORS["primary"], icon="🎯",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, f"{with_certs}/{n_students}",
            f"Students covered ({coverage:.0f}%)",
            accent=STATUS["green"], icon="👥",
        ).pack(side="left")

    # =========================================================
    # BULK GENERATE
    # =========================================================

    def _render_bulk(self, parent):
        card = self.card(parent)
        card.pack(fill="x", pady=(0, PAD_MD))

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        ctk.CTkLabel(
            body,
            text="Automatically issue certificates for every student who "
                 "qualifies this term.",
            font=(FONT_FAMILY, 11),
            text_color=COLORS["text_muted"],
            anchor="w", wraplength=900, justify="left",
        ).pack(anchor="w", pady=(0, 10))

        # What gets generated
        rules = [
            ("🏆", "Academic Excellence", "Gold zone (≥90% overall)"),
            ("🎯", "Subject Topper",      "Highest marks in any subject"),
            ("🌟", "Perfect Attendance",  "100% attendance"),
            ("📈", "Most Improved",        "Biggest IA-1 → IA-3 gain"),
            ("💎", "All-Rounder",          "≥90 in every subject"),
            ("🎗️", "Activity Champion",  "Most co-curricular activities"),
        ]
        grid = ctk.CTkFrame(body, fg_color="transparent")
        grid.pack(fill="x", pady=(0, 12))

        for i, (icon, title, desc) in enumerate(rules):
            chip = ctk.CTkFrame(grid, fg_color=COLORS["surface_alt"],
                                corner_radius=8)
            chip.pack(side="left", padx=(0, 8), pady=2)

            ctk.CTkLabel(
                chip, text=f"  {icon}  {title}  ",
                font=(FONT_FAMILY, 10, "bold"),
                text_color=COLORS["text"]).pack(padx=4, pady=4)

        row = ctk.CTkFrame(body, fg_color="transparent")
        row.pack(fill="x")

        self.primary_button(
            row, "⚡  Generate All Now",
            command=self._run_bulk,
            width=240, height=44,
        ).pack(side="left")

    def _run_bulk(self):
        def on_confirm():
            try:
                results = generate_class_certificates(self.db, ia_number=3)
                total = sum(len(v) for v in results.values())
                if total == 0:
                    self.toast("No certificates generated — no eligible "
                               "students yet.", "info")
                else:
                    summary = ", ".join(
                        f"{k.replace('_',' ')}: {len(v)}"
                        for k, v in results.items() if v)
                    self.toast(
                        f"✅  Generated {total} certificate(s). {summary}",
                        "success")
                self.db.log_audit(
                    (self.user or {}).get("id", "admin"),
                    "bulk_certificate_generation",
                    details=f"total={total}")
                self._reload()
            except Exception as e:
                self.toast(f"Generation failed: {e}", "error")

        self.confirm(
            "Generate all eligible certificates?",
            "This will issue certificates for every qualifying student "
            "based on the latest IA. Existing certificates are not "
            "duplicated.",
            on_yes=on_confirm,
            yes_text="Generate all",
        )

    # =========================================================
    # MANUAL GENERATE
    # =========================================================

    def _render_manual(self, parent):
        card = self.card(parent)
        card.pack(fill="x", pady=(0, PAD_MD))

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        # Student dropdown
        s_row = ctk.CTkFrame(body, fg_color="transparent")
        s_row.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            s_row, text="Student:",
            width=140, anchor="w",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_muted"]).pack(side="left")

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
                s_row, values=student_names, width=380, height=38,
                font=FONTS["small"],
                fg_color=COLORS["surface_alt"],
                button_color=COLORS["primary"],
                button_hover_color=COLORS["primary_hover"],
                text_color=COLORS["text"],
                dropdown_fg_color=COLORS["surface_alt"],
                dropdown_text_color=COLORS["text"],
                corner_radius=10)
            menu.set(student_names[0])
            menu.pack(side="left")
            self._student_menu = menu
        else:
            ctk.CTkLabel(
                s_row, text="No students available.",
                font=FONTS["small"],
                text_color=STATUS["red"]).pack(side="left")

        # Certificate type dropdown
        t_row = ctk.CTkFrame(body, fg_color="transparent")
        t_row.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            t_row, text="Certificate:",
            width=140, anchor="w",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_muted"]).pack(side="left")

        cert_labels = []
        cert_lookup = {}
        for c in CERTIFICATES:
            icon = CERT_ICONS.get(c["id"], "📜")
            label = f"{icon}  {c['name']}"
            cert_labels.append(label)
            cert_lookup[label] = c["id"]

        menu2 = ctk.CTkOptionMenu(
            t_row, values=cert_labels, width=380, height=38,
            font=FONTS["small"],
            fg_color=COLORS["surface_alt"],
            button_color=COLORS["primary"],
            button_hover_color=COLORS["primary_hover"],
            text_color=COLORS["text"],
            dropdown_fg_color=COLORS["surface_alt"],
            dropdown_text_color=COLORS["text"],
            corner_radius=10)
        menu2.set(cert_labels[0])
        menu2.pack(side="left")
        self._cert_menu = menu2
        self._cert_lookup = cert_lookup

        # Subject dropdown (only relevant for subject_topper)
        sj_row = ctk.CTkFrame(body, fg_color="transparent")
        sj_row.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            sj_row, text="Subject (optional):",
            width=140, anchor="w",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_muted"]).pack(side="left")

        self._subject_menu = ctk.CTkOptionMenu(
            sj_row,
            values=["(auto)", "Maths", "Physics", "Chemistry",
                    "Computer Science"],
            width=380, height=38,
            font=FONTS["small"],
            fg_color=COLORS["surface_alt"],
            button_color=COLORS["primary"],
            button_hover_color=COLORS["primary_hover"],
            text_color=COLORS["text"],
            dropdown_fg_color=COLORS["surface_alt"],
            dropdown_text_color=COLORS["text"],
            corner_radius=10)
        self._subject_menu.set("(auto)")
        self._subject_menu.pack(side="left")

        # Generate button
        row = ctk.CTkFrame(body, fg_color="transparent")
        row.pack(fill="x")

        self.primary_button(
            row, "📜  Generate Certificate",
            command=self._generate_manual,
            width=240, height=44,
        ).pack(side="left")

    def _generate_manual(self):
        try:
            label = self._student_menu.get()
            cert_label = self._cert_menu.get()
            subject = self._subject_menu.get()
        except Exception:
            self.toast("Please select a student and certificate.", "warning")
            return

        uid = self._student_lookup.get(label)
        ctype = self._cert_lookup.get(cert_label)
        if not uid or not ctype:
            self.toast("Invalid selection.", "error")
            return

        student = self.db.get_user(uid)
        if not student:
            self.toast("Student not found.", "error")
            return

        name = _safe_str(student.get("name"))
        usn = _safe_str(student.get("usn")) or uid

        # Try to gather data
        try:
            ms = self.db.get_marks_summary(uid)
            latest = ms.iloc[-1] if not ms.empty else None
        except Exception:
            latest = None

        admin_id = (self.user or {}).get("id", "admin")

        def do_generate():
            try:
                path = None
                title = CERT_ICONS.get(ctype, "📜") + " " + cert_label

                if ctype == "academic_excellence":
                    if latest is None:
                        self.toast("No marks to base this on.", "warning")
                        return
                    path = certificate_academic_excellence(
                        uid, name, usn,
                        _safe_float(latest.get("percentage")),
                        _safe_str(latest.get("grade")),
                        _safe_str(latest.get("zone")))

                elif ctype == "subject_topper":
                    marks = self._pick_subject_marks(uid, subject, latest)
                    if not marks:
                        self.toast(
                            "No marks found for this student.", "warning")
                        return
                    subj, value = marks
                    path = certificate_subject_topper(
                        uid, name, usn, subj, value)

                elif ctype == "perfect_attendance":
                    pct = self.db.attendance_percent(uid, days=30)
                    path = certificate_perfect_attendance(uid, name, usn, pct)

                elif ctype == "most_improved":
                    hist = self.db.get_color_history(uid)
                    if hist is None or len(hist) < 2:
                        self.toast("Not enough history.", "warning")
                        return
                    path = certificate_most_improved(
                        uid, name, usn,
                        _safe_float(hist.iloc[0].get("percentage")),
                        _safe_float(hist.iloc[-1].get("percentage")))

                elif ctype == "all_rounder":
                    if latest is None:
                        self.toast("No marks to base this on.", "warning")
                        return
                    subj_marks = {
                        "Maths":            _safe_float(latest.get("maths")),
                        "Physics":          _safe_float(latest.get("phy")),
                        "Chemistry":        _safe_float(latest.get("che")),
                        "Computer Science": _safe_float(latest.get("cs")),
                    }
                    path = certificate_all_rounder(
                        uid, name, usn, subj_marks)

                elif ctype == "activity_champion":
                    acts = self.db.get_user_activities(uid)
                    path = certificate_activity_champion(
                        uid, name, usn, len(acts))

                if not path:
                    self.toast("Could not generate certificate.", "error")
                    return

                # Log to DB
                self.db.issue_certificate(
                    uid, ctype, title, file_path=path,
                    issued_by=admin_id)

                self.db.log_audit(
                    admin_id, "generate_certificate",
                    target=f"{uid}:{ctype}", details=path)

                self.toast(f"Generated ✓ {os.path.basename(path)}",
                           "success")

                # Open the PDF
                _open_file(path)

                # Reload
                self._reload()

            except Exception as e:
                self.toast(f"Generation failed: {e}", "error")

        self.confirm(
            "Generate this certificate?",
            f"Generate {cert_label} for {name}?",
            on_yes=do_generate,
            yes_text="Generate",
        )

    def _pick_subject_marks(self, uid, subject_choice, latest):
        """Return (subject, marks) for a given student and subject choice."""
        subjects = ["Maths", "Physics", "Chemistry", "Computer Science"]
        if latest is None:
            return None
        mapping = {
            "Maths": "maths",
            "Physics": "phy",
            "Chemistry": "che",
            "Computer Science": "cs",
        }
        if subject_choice == "(auto)":
            # Pick the student's best subject
            best_subj = None
            best_v = -1
            for s in subjects:
                v = _safe_float(latest.get(mapping[s]))
                if v > best_v:
                    best_v = v
                    best_subj = s
            return (best_subj, best_v) if best_subj else None
        else:
            v = _safe_float(latest.get(mapping.get(subject_choice, "maths")))
            return (subject_choice, v)

    # =========================================================
    # FOLDER SHORTCUT
    # =========================================================

    def _render_folder_row(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        self.secondary_button(
            row, "📁  Open certificates folder",
            command=lambda: _open_folder(CERT_DIR),
            width=260, height=42,
        ).pack(side="left")

        # Count files
        n_files = 0
        try:
            if os.path.exists(CERT_DIR):
                n_files = len([f for f in os.listdir(CERT_DIR)
                               if f.endswith(".pdf")])
        except Exception:
            pass

        ctk.CTkLabel(
            row, text=f"📄  {n_files} PDF file(s) in folder",
            font=(FONT_FAMILY, 10),
            text_color=COLORS["text_muted"]).pack(side="left",
                                                  padx=(PAD_MD, 0))

    # =========================================================
    # FILTER
    # =========================================================

    def _render_filter_row(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        ctk.CTkLabel(
            row, text="Type:",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_muted"]).pack(side="left", padx=(0, 8))

        filters = [("all", "All")]
        for c in CERTIFICATES:
            icon = CERT_ICONS.get(c["id"], "📜")
            filters.append((c["id"], f"{icon} {c['name']}"))

        for key, label in filters:
            is_active = (self._type_filter == key)
            btn = ctk.CTkButton(
                row, text=label, width=170, height=34,
                font=(FONT_FAMILY, 10),
                fg_color=COLORS["primary"] if is_active
                         else COLORS["surface_alt"],
                hover_color=COLORS["surface_hi"],
                text_color=COLORS["text"],
                corner_radius=BUTTON_RADIUS,
                command=lambda k=key: self._set_filter(k),
            )
            btn.pack(side="left", padx=(0, PAD_SM), pady=2)
            self._filter_btns[key] = btn

    def _set_filter(self, key: str):
        self._type_filter = key
        for k, b in self._filter_btns.items():
            try:
                b.configure(fg_color=COLORS["primary"] if k == key
                            else COLORS["surface_alt"])
            except Exception:
                pass
        self._render_list()

    # =========================================================
    # LIST
    # =========================================================

    def _render_list(self):
        for w in self._list_container.winfo_children():
            w.destroy()

        c = self._certs
        if c is None or c.empty:
            ctk.CTkLabel(
                self._list_container,
                text="No certificates issued yet.",
                font=FONTS["body"],
                text_color=COLORS["text_muted"]).pack(pady=30)
            return

        df = c.copy()

        # Filter
        if self._type_filter != "all":
            df = df[df["cert_type"] == self._type_filter]

        if df.empty:
            ctk.CTkLabel(
                self._list_container,
                text="No certificates match this filter.",
                font=FONTS["body"],
                text_color=COLORS["text_muted"]).pack(pady=20)
            return

        # Sort newest first
        try:
            df = df.sort_values("issued_at", ascending=False)
        except Exception:
            pass

        # Count
        ctk.CTkLabel(
            self._list_container,
            text=f"Showing {len(df)} certificate(s)",
            font=(FONT_FAMILY, 10),
            text_color=COLORS["text_muted"],
        ).pack(anchor="w", pady=(0, PAD_SM))

        for _, r in df.head(40).iterrows():
            self._render_cert_row(r)

        if len(df) > 40:
            ctk.CTkLabel(
                self._list_container,
                text=f"... and {len(df) - 40} more",
                font=(FONT_FAMILY, 10),
                text_color=COLORS["text_muted"]).pack(pady=6)

    def _render_cert_row(self, r):
        ctype = _safe_str(r.get("cert_type"))
        icon = CERT_ICONS.get(ctype, "📜")
        color = CERT_COLORS.get(ctype, COLORS["primary"])

        uid = _safe_str(r.get("user_id"))
        name = _safe_str(r.get("student_name")) or "—"
        usn = _safe_str(r.get("usn"))
        title = _safe_str(r.get("title")) or "Certificate"
        path = _safe_str(r.get("file_path"))
        issued = _safe_str(r.get("issued_at"))
        has_file = bool(path and os.path.exists(path))

        row = ctk.CTkFrame(
            self._list_container,
            fg_color=COLORS["surface"],
            corner_radius=CARD_RADIUS,
            border_width=1,
            border_color=color)
        row.pack(fill="x", pady=4)

        inner = ctk.CTkFrame(row, fg_color="transparent")
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
            info, text=title,
            font=(FONT_FAMILY, 13, "bold"),
            text_color=COLORS["text"], anchor="w",
        ).pack(anchor="w")

        sub = f"{name}"
        if usn:
            sub += f"  ·  {usn}"
        ctk.CTkLabel(
            info, text=sub,
            font=(FONT_FAMILY, 10),
            text_color=COLORS["text_muted"], anchor="w",
        ).pack(anchor="w", pady=(2, 0))

        ctk.CTkLabel(
            info, text=f"Issued {_fmt_date(issued)}",
            font=(FONT_FAMILY, 9),
            text_color=COLORS["text_muted"], anchor="w",
        ).pack(anchor="w", pady=(2, 0))

        # Right: actions
        right = ctk.CTkFrame(inner, fg_color="transparent")
        right.pack(side="right")

        if has_file:
            self.primary_button(
                right, "Open PDF",
                command=lambda p=path: _open_file(p),
                width=110, height=34,
            ).pack(side="left", padx=(0, 6))

            self.secondary_button(
                right, "Folder",
                command=lambda: _open_folder(CERT_DIR),
                width=90, height=34,
            ).pack(side="left")
        else:
            ctk.CTkLabel(
                right,
                text="⚠️ File missing",
                font=(FONT_FAMILY, 10),
                text_color=STATUS["amber"]).pack()

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
            print(f"[certs] → show_page('{key}')  args={kw}")

        def go_back(self):
            print("[certs] back")

        def logout(self):
            print("[certs] logout")

    root = ctk.CTk()
    W, H = 1400, 900
    root.geometry(f"{W}x{H}")
    root.configure(fg_color=COLORS["bg"])
    root.title(f"{APP_NAME} — certificate generator")

    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - W) // 2
    y = (sh - H) // 2
    root.geometry(f"{W}x{H}+{x}+{y}")

    app = _FakeApp()
    page = AdminCertificateGeneratorPage(root, app)
    page.pack(fill="both", expand=True)
    root.mainloop()
    print("\n✅ pages/admin/certificate_generator.py OK")