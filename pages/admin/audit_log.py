# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  pages/admin/audit_log.py  ·  System audit log
# =============================================================

from __future__ import annotations

import os
import sys

# --- make project root importable ---
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import csv
from datetime import datetime, timedelta

import customtkinter as ctk
import pandas as pd

from config import (
    APP_NAME, COLORS, STATUS,
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


# Action categories → icons + colors
ACTION_CATEGORIES = {
    "login":                    ("🔓", "Login",          "#60A5FA"),
    "logout":                   ("🔒", "Logout",         "#60A5FA"),
    "register":                 ("📝", "Register",       "#8B5CF6"),
    "approve_user":             ("✅", "Approve user",   "#10B981"),
    "reject_user":              ("❌", "Reject user",    "#EF4444"),
    "create_user":              ("➕", "Create user",    "#10B981"),
    "update_user":              ("✏️", "Update user",   "#F59E0B"),
    "delete_user":              ("🗑", "Delete user",    "#EF4444"),
    "reset_password":           ("🔑", "Reset password", "#F59E0B"),
    "save_marks_manual":        ("📝", "Save marks",     "#8B5CF6"),
    "import_marks_excel":       ("📊", "Import marks",   "#8B5CF6"),
    "save_attendance":          ("📅", "Save attendance","#10B981"),
    "import_attendance_excel":  ("📅", "Import attd.",   "#10B981"),
    "generate_certificate":     ("📜", "Certificate",    "#FBBF24"),
    "bulk_certificate_generation": ("📜", "Bulk certs",  "#FBBF24"),
    "create_activity":          ("🎗️", "Create activity","#EC4899"),
    "delete_activity":          ("🗑", "Delete activity","#EF4444"),
    "log_activity_score":       ("🎯", "Log score",      "#EC4899"),
    "award_badge":              ("🏅", "Award badge",    "#FBBF24"),
    "revoke_badge":             ("🏅", "Revoke badge",   "#EF4444"),
    "export_class_analytics":   ("📈", "Export analytics","#60A5FA"),
}


def _action_meta(action: str):
    a = _safe_str(action).lower()
    return ACTION_CATEGORIES.get(a, ("⚙️", a.replace("_", " ").title()
                                     or "Action", COLORS["text_muted"]))


def _fmt_time(iso: str) -> str:
    if not iso:
        return "—"
    try:
        d = datetime.fromisoformat(iso)
        return d.strftime("%d %b %Y · %H:%M:%S")
    except Exception:
        return iso[:19]


# =============================================================
# AUDIT LOG PAGE
# =============================================================

class AdminAuditLogPage(BasePage):

    def __init__(self, master, app):
        super().__init__(master, app)

        self.build_header("Audit Log",
                          "Complete system activity history", back=False)
        self.build_sidebar(self._build_nav_items())
        self.build_content(scrollable=True)
        self.build_footer()

        # State
        self._search_text = ""
        self._action_filter = "all"
        self._range_filter = "7d"   # 1d | 7d | 30d | all
        self._list_container = None
        self._action_btns = {}
        self._range_btns = {}
        self._search_entry = None

        self.render()

    def _build_nav_items(self):
        items = _admin_nav()
        for it in items:
            if it["key"] == "admin_audit":
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

        # 2. Controls
        self.section_title("Filters", parent=content)
        self._render_controls(content)

        # 3. List
        self.section_title("Activity", parent=content)
        self._list_container = ctk.CTkFrame(content, fg_color="transparent")
        self._list_container.pack(fill="x", pady=(0, PAD_MD))
        self._render_list()

    # =========================================================
    # LOAD
    # =========================================================

    def _load_data(self):
        try:
            self._entries = self.db.get_audit_log(limit=1000)
        except Exception:
            self._entries = pd.DataFrame()

    # =========================================================
    # STATS
    # =========================================================

    def _render_stats(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        e = self._entries
        total = 0 if e is None else len(e)

        # Today
        today = 0
        week = 0
        if e is not None and not e.empty:
            now = datetime.now()
            start_today = now.replace(hour=0, minute=0, second=0,
                                      microsecond=0)
            start_week = now - timedelta(days=7)
            for _, r in e.iterrows():
                try:
                    d = datetime.fromisoformat(_safe_str(r.get("created_at")))
                    if d >= start_today:
                        today += 1
                    if d >= start_week:
                        week += 1
                except Exception:
                    pass

        # Unique actors
        actors = 0
        if e is not None and not e.empty and "actor_id" in e.columns:
            actors = e["actor_id"].nunique()

        # Unique actions
        actions = 0
        if e is not None and not e.empty and "action" in e.columns:
            actions = e["action"].nunique()

        self.stat_card(
            row, total, "Total entries",
            accent=COLORS["primary"], icon="📜",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, today, "Today",
            accent=STATUS["info"], icon="📅",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, week, "Last 7 days",
            accent=STATUS["green"], icon="🗓️",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, actors, "Unique actors",
            accent=STATUS["purple"], icon="👥",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, actions, "Action types",
            accent=STATUS["gold"], icon="🎯",
        ).pack(side="left")

    # =========================================================
    # CONTROLS
    # =========================================================

    def _render_controls(self, parent):
        card = self.card(parent)
        card.pack(fill="x", pady=(0, PAD_MD))

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        # Row 1: Search
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
            placeholder_text="Action, target, or actor…")
        self._search_entry.pack(side="left")
        self._search_entry.bind("<KeyRelease>", self._on_search_change)

        self.secondary_button(
            s_row, "Clear",
            command=self._clear_search,
            width=90, height=36,
        ).pack(side="left", padx=(PAD_SM, 0))

        # Export button (right)
        self.secondary_button(
            s_row, "📥  Export CSV",
            command=self._export_csv,
            width=140, height=36,
        ).pack(side="right")

        # Row 2: Time range
        r_row = ctk.CTkFrame(body, fg_color="transparent")
        r_row.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            r_row, text="Range:",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_muted"]).pack(side="left", padx=(0, 8))

        for key, label in [("1d", "Today"),
                           ("7d", "Last 7 days"),
                           ("30d", "Last 30 days"),
                           ("all", "All time")]:
            is_active = (self._range_filter == key)
            btn = ctk.CTkButton(
                r_row, text=label, width=130, height=32,
                font=(FONT_FAMILY, 10),
                fg_color=COLORS["primary"] if is_active
                         else COLORS["surface_alt"],
                hover_color=COLORS["surface_hi"],
                text_color=COLORS["text"],
                corner_radius=BUTTON_RADIUS,
                command=lambda k=key: self._set_range(k),
            )
            btn.pack(side="left", padx=(0, PAD_SM))
            self._range_btns[key] = btn

        # Row 3: Action type filter
        a_row = ctk.CTkFrame(body, fg_color="transparent")
        a_row.pack(fill="x")

        ctk.CTkLabel(
            a_row, text="Action:",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_muted"]).pack(side="left", padx=(0, 8))

        # Common actions
        common_actions = [
            ("all", "All"),
            ("approve_user", "✅ Approve"),
            ("reject_user", "❌ Reject"),
            ("save_marks_manual", "📝 Marks"),
            ("save_attendance", "📅 Attd."),
            ("generate_certificate", "📜 Cert."),
            ("award_badge", "🏅 Badge"),
            ("delete_user", "🗑 Delete"),
        ]
        for key, label in common_actions:
            is_active = (self._action_filter == key)
            btn = ctk.CTkButton(
                a_row, text=label, width=110, height=32,
                font=(FONT_FAMILY, 9),
                fg_color=COLORS["primary"] if is_active
                         else COLORS["surface_alt"],
                hover_color=COLORS["surface_hi"],
                text_color=COLORS["text"],
                corner_radius=BUTTON_RADIUS,
                command=lambda k=key: self._set_action_filter(k),
            )
            btn.pack(side="left", padx=(0, 4), pady=2)
            self._action_btns[key] = btn

    def _set_range(self, key: str):
        self._range_filter = key
        for k, b in self._range_btns.items():
            try:
                b.configure(fg_color=COLORS["primary"] if k == key
                            else COLORS["surface_alt"])
            except Exception:
                pass
        self._render_list()

    def _set_action_filter(self, key: str):
        self._action_filter = key
        for k, b in self._action_btns.items():
            try:
                b.configure(fg_color=COLORS["primary"] if k == key
                            else COLORS["surface_alt"])
            except Exception:
                pass
        self._render_list()

    def _on_search_change(self, event=None):
        try:
            self._search_text = (self._search_entry.get() or "").strip().lower()
        except Exception:
            self._search_text = ""
        self._render_list()

    def _clear_search(self):
        try:
            self._search_entry.delete(0, "end")
        except Exception:
            pass
        self._search_text = ""
        self._render_list()

    # =========================================================
    # LIST
    # =========================================================

    def _render_list(self):
        for w in self._list_container.winfo_children():
            w.destroy()

        e = self._entries
        if e is None or e.empty:
            ctk.CTkLabel(
                self._list_container,
                text="No audit entries yet.",
                font=FONTS["body"],
                text_color=COLORS["text_muted"]).pack(pady=30)
            return

        df = e.copy()

        # Range filter
        if self._range_filter != "all":
            now = datetime.now()
            if self._range_filter == "1d":
                cutoff = now.replace(hour=0, minute=0, second=0,
                                     microsecond=0)
            elif self._range_filter == "7d":
                cutoff = now - timedelta(days=7)
            elif self._range_filter == "30d":
                cutoff = now - timedelta(days=30)
            else:
                cutoff = None

            if cutoff is not None:
                df = df[df["created_at"].apply(
                    lambda x: self._is_after(x, cutoff))]

        # Action filter
        if self._action_filter != "all":
            df = df[df["action"].astype(str) == self._action_filter]

        # Search
        if self._search_text:
            q = self._search_text
            df = df[df.apply(
                lambda r: (q in _safe_str(r.get("action")).lower())
                or (q in _safe_str(r.get("target")).lower())
                or (q in _safe_str(r.get("actor_name")).lower())
                or (q in _safe_str(r.get("actor_id")).lower())
                or (q in _safe_str(r.get("details")).lower()),
                axis=1)]

        if df.empty:
            ctk.CTkLabel(
                self._list_container,
                text="No entries match your filters.",
                font=FONTS["body"],
                text_color=COLORS["text_muted"]).pack(pady=20)
            return

        # Count
        ctk.CTkLabel(
            self._list_container,
            text=f"Showing {min(len(df), 100)} of {len(df)} entries",
            font=(FONT_FAMILY, 10),
            text_color=COLORS["text_muted"],
        ).pack(anchor="w", pady=(0, PAD_SM))

        for _, r in df.head(100).iterrows():
            self._render_entry(r)

        if len(df) > 100:
            ctk.CTkLabel(
                self._list_container,
                text=f"... {len(df) - 100} more — use filters or export",
                font=(FONT_FAMILY, 10),
                text_color=COLORS["text_muted"]).pack(pady=6)

    def _is_after(self, iso: str, cutoff: datetime) -> bool:
        try:
            d = datetime.fromisoformat(_safe_str(iso))
            return d >= cutoff
        except Exception:
            return True

    def _render_entry(self, r):
        action = _safe_str(r.get("action"))
        icon, label, color = _action_meta(action)

        actor = _safe_str(r.get("actor_name")) or \
                _safe_str(r.get("actor_id")) or "system"
        target = _safe_str(r.get("target"))
        details = _safe_str(r.get("details"))
        when = _fmt_time(_safe_str(r.get("created_at")))

        row = ctk.CTkFrame(
            self._list_container,
            fg_color=COLORS["surface"],
            corner_radius=CARD_RADIUS,
            border_width=1,
            border_color=COLORS["border_soft"])
        row.pack(fill="x", pady=3)

        # Left color bar (thin)
        bar = ctk.CTkFrame(row, fg_color=color, width=4, corner_radius=0)
        bar.pack(side="left", fill="y")

        inner = ctk.CTkFrame(row, fg_color="transparent")
        inner.pack(side="left", fill="x", expand=True,
                   padx=PAD_LG, pady=PAD_MD)

        # Head line
        head = ctk.CTkFrame(inner, fg_color="transparent")
        head.pack(fill="x")

        # Action chip
        chip = ctk.CTkFrame(head, fg_color=color,
                            corner_radius=CHIP_RADIUS)
        chip.pack(side="left")
        ctk.CTkLabel(
            chip,
            text=f"  {icon}  {label}  ",
            font=(FONT_FAMILY, 10, "bold"),
            text_color="#FFFFFF").pack(padx=4, pady=3)

        # Actor
        ctk.CTkLabel(
            head, text=f"by {actor}",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text"]).pack(side="left", padx=(10, 0))

        # When
        ctk.CTkLabel(
            head, text=when,
            font=(FONT_FAMILY, 10),
            text_color=COLORS["text_muted"]).pack(side="right")

        # Target + details line
        meta_parts = []
        if target:
            meta_parts.append(f"→ {target[:60]}")
        if details:
            meta_parts.append(details[:80])

        if meta_parts:
            ctk.CTkLabel(
                inner, text="  ·  ".join(meta_parts),
                font=(FONT_FAMILY, 10),
                text_color=COLORS["text_muted"], anchor="w",
                wraplength=1000, justify="left",
            ).pack(anchor="w", pady=(6, 0))

    # =========================================================
    # EXPORT
    # =========================================================

    def _export_csv(self):
        try:
            e = self._entries
            if e is None or e.empty:
                self.toast("Nothing to export.", "warning")
                return

            path = os.path.join(
                os.path.expanduser("~"),
                f"audit_log_{datetime.now().strftime('%Y%m%d_%H%M')}.csv")

            # Save as CSV
            e.to_csv(path, index=False)

            self.toast(f"Saved: {os.path.basename(path)}", "success")
            self.db.log_audit(
                (self.user or {}).get("id", "admin"),
                "export_audit_log", target=os.path.basename(path))

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
            print(f"[audit] → show_page('{key}')  args={kw}")

        def go_back(self):
            print("[audit] back")

        def logout(self):
            print("[audit] logout")

    root = ctk.CTk()
    W, H = 1400, 900
    root.geometry(f"{W}x{H}")
    root.configure(fg_color=COLORS["bg"])
    root.title(f"{APP_NAME} — audit log")

    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - W) // 2
    y = (sh - H) // 2
    root.geometry(f"{W}x{H}+{x}+{y}")

    app = _FakeApp()
    page = AdminAuditLogPage(root, app)
    page.pack(fill="both", expand=True)
    root.mainloop()
    print("\n✅ pages/admin/audit_log.py OK")