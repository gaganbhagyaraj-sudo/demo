# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  pages/admin/dashboard.py  ·  Admin dashboard
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
    SUBJECTS,
    FONTS, FONT_FAMILY,
    CARD_RADIUS, BUTTON_RADIUS, CHIP_RADIUS,
    PAD_SM, PAD_MD, PAD_LG, PAD_XL,
    DB_PATH,
    ROLE_ADMIN, ROLE_FACILITATOR, ROLE_STUDENT,
    STATUS_PENDING, STATUS_APPROVED, STATUS_REJECTED,
)
from pages.base_page import BasePage
from utils.avatars import load_avatar
from utils.charts import zone_donut


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


def _fmt_time(iso: str) -> str:
    if not iso:
        return "—"
    try:
        d = datetime.fromisoformat(iso)
        now = datetime.now()
        diff = now - d
        if diff.total_seconds() < 60:
            return "just now"
        if diff.total_seconds() < 3600:
            return f"{int(diff.total_seconds() // 60)}m ago"
        if diff.total_seconds() < 86400:
            return f"{int(diff.total_seconds() // 3600)}h ago"
        if diff.days < 7:
            return f"{diff.days}d ago"
        return d.strftime("%d %b %Y")
    except Exception:
        return iso[:16]


# =============================================================
# ADMIN DASHBOARD PAGE
# =============================================================

class AdminDashboardPage(BasePage):

    def __init__(self, master, app):
        super().__init__(master, app)

        self.build_header("Admin Dashboard",
                          "Full control of Shruthi Jhari", back=False)
        self.build_sidebar(self._build_nav_items())
        self.build_content(scrollable=True)
        self.build_footer()

        self.render()

    def _build_nav_items(self):
        items = _admin_nav()
        for it in items:
            if it["key"] == "admin_dashboard":
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

        # 1. KPI row
        self.section_title("System Overview", parent=content)
        self._render_kpis(content)

        # 2. Two-column: pending approvals | zone donut
        cols = ctk.CTkFrame(content, fg_color="transparent")
        cols.pack(fill="x", pady=(PAD_MD, 0))

        left = ctk.CTkFrame(cols, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=(0, PAD_MD))

        right = ctk.CTkFrame(cols, fg_color="transparent")
        right.pack(side="left", fill="both", expand=False)

        self.section_title("Pending Approvals", parent=left)
        self._render_pending_preview(left)

        self.section_title("Zone Distribution", parent=right)
        self._render_zone_donut(right)

        # 3. Two-column: audit log | system health
        cols2 = ctk.CTkFrame(content, fg_color="transparent")
        cols2.pack(fill="x", pady=(PAD_MD, 0))

        audit_left = ctk.CTkFrame(cols2, fg_color="transparent")
        audit_left.pack(side="left", fill="both", expand=True, padx=(0, PAD_MD))

        health_right = ctk.CTkFrame(cols2, fg_color="transparent")
        health_right.pack(side="left", fill="both", expand=True)

        self.section_title("Recent Activity", parent=audit_left)
        self._render_audit_preview(audit_left)

        self.section_title("System Health", parent=health_right)
        self._render_system_health(health_right)

        # 4. Quick actions
        self.section_title("Quick Actions", parent=content)
        self._render_quick_actions(content)

    # =========================================================
    # LOAD
    # =========================================================

    def _load_data(self):
        # Users
        try:
            self._all_users = self.db.query("SELECT * FROM users")
        except Exception:
            self._all_users = pd.DataFrame()

        # Pending users
        try:
            self._pending = self.db.get_pending_users()
        except Exception:
            self._pending = pd.DataFrame()

        # Students
        try:
            self._students = self.db.get_all_students()
        except Exception:
            self._students = pd.DataFrame()

        # Facilitators
        try:
            self._facilitators = self.db.query(
                "SELECT * FROM users WHERE role='facilitator'")
        except Exception:
            self._facilitators = pd.DataFrame()

        # Latest IA
        try:
            ia_df = self.db.query(
                "SELECT MAX(ia_number) AS ia FROM marks_summary")
            self._latest_ia = int(ia_df.iloc[0]["ia"] or 3)
        except Exception:
            self._latest_ia = 3

        # Zone counts
        try:
            self._zone_counts = self.db.class_zone_counts(
                ia_number=self._latest_ia)
        except Exception:
            self._zone_counts = {"red": 0, "yellow": 0,
                                 "green": 0, "gold": 0}

        # Audit log
        try:
            self._audit = self.db.get_audit_log(limit=10)
        except Exception:
            self._audit = pd.DataFrame()

        # Counts
        try:
            self._n_certs = int(self.db.query(
                "SELECT COUNT(*) AS n FROM certificates").iloc[0]["n"])
        except Exception:
            self._n_certs = 0

        try:
            self._n_attempts = int(self.db.query(
                "SELECT COUNT(*) AS n FROM attempts").iloc[0]["n"])
        except Exception:
            self._n_attempts = 0

        try:
            self._n_remedial = int(self.db.query(
                "SELECT COUNT(*) AS n FROM remedial_sessions").iloc[0]["n"])
        except Exception:
            self._n_remedial = 0

    # =========================================================
    # KPIs
    # =========================================================

    def _render_kpis(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        total_users = 0 if self._all_users is None else len(self._all_users)
        n_students = 0 if self._students is None else len(self._students)
        n_facs = 0 if self._facilitators is None else len(self._facilitators)
        n_pending = 0 if self._pending is None else len(self._pending)

        self.stat_card(
            row, total_users, "Total users",
            accent=COLORS["primary"], icon="👥",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, n_students, "Students",
            accent=STATUS["green"], icon="🎓",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, n_facs, "Facilitators",
            accent=STATUS["info"], icon="👨‍🏫",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, n_pending, "Pending approvals",
            accent=STATUS["amber"] if n_pending > 0
                   else COLORS["text_muted"],
            icon="⏳",
        ).pack(side="left")

    # =========================================================
    # PENDING PREVIEW
    # =========================================================

    def _render_pending_preview(self, parent):
        card = self.card(parent)
        card.pack(fill="both", expand=True)

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="both", expand=True,
                  padx=PAD_LG, pady=PAD_LG)

        p = self._pending
        if p is None or p.empty:
            ctk.CTkLabel(
                body, text="✅  No pending approvals — all caught up!",
                font=FONTS["body"],
                text_color=STATUS["green"]).pack(pady=20)
            return

        # Show up to 5
        for _, u in p.head(5).iterrows():
            row = ctk.CTkFrame(body, fg_color=COLORS["surface_alt"],
                               corner_radius=10)
            row.pack(fill="x", pady=3)

            inner = ctk.CTkFrame(row, fg_color="transparent")
            inner.pack(fill="x", padx=10, pady=8)

            # Avatar
            try:
                avatar = load_avatar(
                    user_id=_safe_str(u.get("id")),
                    name=_safe_str(u.get("name")),
                    size=32, shape="circle",
                )
                ctk.CTkLabel(inner, image=avatar, text="").pack(
                    side="left", padx=(0, 10))
            except Exception:
                pass

            # Info
            info = ctk.CTkFrame(inner, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True)

            ctk.CTkLabel(
                info, text=_safe_str(u.get("name")) or "—",
                font=(FONT_FAMILY, 11, "bold"),
                text_color=COLORS["text"], anchor="w",
            ).pack(anchor="w")

            role = _safe_str(u.get("role")).title()
            email = _safe_str(u.get("email"))
            meta = f"{role}  ·  {email}"
            ctk.CTkLabel(
                info, text=meta,
                font=(FONT_FAMILY, 9),
                text_color=COLORS["text_muted"], anchor="w",
            ).pack(anchor="w")

            # Actions
            self.primary_button(
                inner, "→ Review",
                command=lambda: self.navigate("admin_approval"),
                width=100, height=30,
            ).pack(side="right")

        # View all link
        ctk.CTkButton(
            body, text="View all approvals →",
            font=(FONT_FAMILY, 10),
            fg_color="transparent", hover=False,
            text_color=COLORS["primary"],
            command=lambda: self.navigate("admin_approval"),
        ).pack(pady=(10, 0))

    # =========================================================
    # ZONE DONUT
    # =========================================================

    def _render_zone_donut(self, parent):
        card = self.card(parent, width=340)
        card.pack_propagate(False)
        card.pack(fill="both", expand=True)

        try:
            fig = zone_donut(
                self._zone_counts,
                title="",
                animate=False,
                figsize=(3.4, 3.4),
            )
            self.chart_frame(card, fig, height=300).pack(
                fill="both", expand=True, padx=8, pady=8)
        except Exception as e:
            ctk.CTkLabel(
                card, text=f"(chart unavailable: {e})",
                font=FONTS["tiny"],
                text_color=COLORS["text_muted"]).pack(pady=20)

    # =========================================================
    # AUDIT PREVIEW
    # =========================================================

    def _render_audit_preview(self, parent):
        card = self.card(parent)
        card.pack(fill="both", expand=True)

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="both", expand=True,
                  padx=PAD_LG, pady=PAD_LG)

        a = self._audit
        if a is None or a.empty:
            ctk.CTkLabel(
                body, text="No activity yet.",
                font=FONTS["small"],
                text_color=COLORS["text_muted"]).pack(pady=20)
            return

        for _, r in a.head(6).iterrows():
            row = ctk.CTkFrame(body, fg_color="transparent")
            row.pack(fill="x", pady=2)

            # Action dot
            ctk.CTkLabel(
                row, text="●",
                font=(FONT_FAMILY, 10),
                text_color=COLORS["primary"],
            ).pack(side="left", padx=(0, 6))

            actor = _safe_str(r.get("actor_name")) or _safe_str(r.get("actor_id")) or "system"
            action = _safe_str(r.get("action")).replace("_", " ").title()
            target = _safe_str(r.get("target"))

            # Build a compact line
            line = f"{actor} — {action}"
            if target:
                line += f"  ({target[:24]})"

            ctk.CTkLabel(
                row, text=line,
                font=(FONT_FAMILY, 10),
                text_color=COLORS["text"], anchor="w",
            ).pack(side="left", fill="x", expand=True)

            ctk.CTkLabel(
                row, text=_fmt_time(_safe_str(r.get("created_at"))),
                font=(FONT_FAMILY, 9),
                text_color=COLORS["text_muted"],
            ).pack(side="right")

        ctk.CTkButton(
            body, text="View full log →",
            font=(FONT_FAMILY, 10),
            fg_color="transparent", hover=False,
            text_color=COLORS["primary"],
            command=lambda: self.navigate("admin_audit"),
        ).pack(pady=(10, 0))

    # =========================================================
    # SYSTEM HEALTH
    # =========================================================

    def _render_system_health(self, parent):
        card = self.card(parent)
        card.pack(fill="both", expand=True)

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="both", expand=True,
                  padx=PAD_LG, pady=PAD_LG)

        # DB size
        db_size = 0
        try:
            if os.path.exists(DB_PATH):
                db_size = os.path.getsize(DB_PATH)
        except Exception:
            pass

        def _fmt_size(b):
            if b < 1024:
                return f"{b} B"
            if b < 1024 * 1024:
                return f"{b/1024:.1f} KB"
            return f"{b/(1024*1024):.1f} MB"

        # Table counts
        tables = [
            ("users",      len(self._all_users) if self._all_users is not None else 0),
            ("students",   len(self._students) if self._students is not None else 0),
            ("attempts",   self._n_attempts),
            ("certificates", self._n_certs),
            ("remedial",   self._n_remedial),
        ]

        rows = [
            ("Database size",   _fmt_size(db_size),   COLORS["primary"]),
            ("Database path",   os.path.basename(DB_PATH), COLORS["text_muted"]),
            ("Latest IA",       f"IA-{self._latest_ia}",   COLORS["primary"]),
        ]

        for k, v, color in rows:
            r = ctk.CTkFrame(body, fg_color="transparent")
            r.pack(fill="x", pady=2)
            ctk.CTkLabel(
                r, text=k, width=140, anchor="w",
                font=(FONT_FAMILY, 10),
                text_color=COLORS["text_muted"]).pack(side="left")
            ctk.CTkLabel(
                r, text=v, anchor="w",
                font=(FONT_FAMILY, 10, "bold"),
                text_color=color).pack(side="left")

        ctk.CTkLabel(
            body, text="Tables:",
            font=(FONT_FAMILY, 10, "bold"),
            text_color=COLORS["text_muted"],
        ).pack(anchor="w", pady=(10, 4))

        for name, count in tables:
            r = ctk.CTkFrame(body, fg_color=COLORS["surface_alt"],
                             corner_radius=6)
            r.pack(fill="x", pady=2)

            ctk.CTkLabel(
                r, text=name, anchor="w",
                font=(FONT_FAMILY, 10),
                text_color=COLORS["text"]).pack(
                side="left", padx=10, pady=5)

            ctk.CTkLabel(
                r, text=str(count), anchor="e",
                font=(FONT_FAMILY, 10, "bold"),
                text_color=COLORS["primary"]).pack(
                side="right", padx=10, pady=5)

    # =========================================================
    # QUICK ACTIONS
    # =========================================================

    def _render_quick_actions(self, parent):
        grid = ctk.CTkFrame(parent, fg_color="transparent")
        grid.pack(fill="x", pady=(0, PAD_LG))

        actions = [
            ("✅", "Review Approvals", "admin_approval"),
            ("👥", "Manage Users",     "admin_users"),
            ("📝", "Manual Marks",     "admin_marks_manual"),
            ("📊", "Excel Upload",     "admin_marks_excel"),
            ("📅", "Attendance",       "admin_attendance"),
            ("📈", "Analytics",        "admin_analytics"),
            ("📜", "Certificates",     "admin_certificates"),
            ("🎗️", "Activities",      "admin_activities"),
        ]

        per_row = 4
        for c in range(per_row):
            grid.grid_columnconfigure(c, weight=1, uniform="qadmin")

        for i, (icon, label, key) in enumerate(actions):
            r, col = divmod(i, per_row)

            tile = ctk.CTkFrame(
                grid,
                fg_color=COLORS["surface"],
                corner_radius=CARD_RADIUS,
                border_width=1, border_color=COLORS["border_soft"],
                width=280, height=110)
            tile.grid(row=r, column=col, padx=6, pady=6, sticky="nsew")
            tile.pack_propagate(False)

            def _enter(_, t=tile):
                try:
                    t.configure(fg_color=COLORS["surface_alt"])
                except Exception:
                    pass

            def _leave(_, t=tile):
                try:
                    t.configure(fg_color=COLORS["surface"])
                except Exception:
                    pass

            def _click(_, k=key):
                self.navigate(k)

            tile.bind("<Enter>", _enter)
            tile.bind("<Leave>", _leave)
            tile.bind("<Button-1>", _click)
            try:
                tile.configure(cursor="hand2")
            except Exception:
                pass

            icon_lbl = ctk.CTkLabel(
                tile, text=icon,
                font=(FONT_FAMILY, 26),
                text_color=COLORS["primary"])
            icon_lbl.pack(pady=(20, 6))

            lbl = ctk.CTkLabel(
                tile, text=label,
                font=(FONT_FAMILY, 11, "bold"),
                text_color=COLORS["text"])
            lbl.pack()

            for w in (icon_lbl, lbl):
                w.bind("<Button-1>", _click)
                try:
                    w.configure(cursor="hand2")
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
            print(f"[admin] → show_page('{key}')  args={kw}")

        def go_back(self):
            print("[admin] back")

        def logout(self):
            print("[admin] logout")

    root = ctk.CTk()
    W, H = 1400, 900
    root.geometry(f"{W}x{H}")
    root.configure(fg_color=COLORS["bg"])
    root.title(f"{APP_NAME} — admin dashboard")

    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - W) // 2
    y = (sh - H) // 2
    root.geometry(f"{W}x{H}+{x}+{y}")

    app = _FakeApp()
    page = AdminDashboardPage(root, app)
    page.pack(fill="both", expand=True)
    root.mainloop()
    print("\n✅ pages/admin/dashboard.py OK")