# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  pages/admin/user_management.py  ·  User management
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
    FONTS, FONT_FAMILY,
    CARD_RADIUS, BUTTON_RADIUS, CHIP_RADIUS,
    PAD_SM, PAD_MD, PAD_LG, PAD_XL,
    ROLE_ADMIN, ROLE_FACILITATOR, ROLE_STUDENT,
    STATUS_PENDING, STATUS_APPROVED, STATUS_REJECTED,
)
from pages.base_page import BasePage
from utils.avatars import load_avatar, clear_cache


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


def _role_meta(role: str):
    role = _safe_str(role).lower()
    return {
        ROLE_STUDENT:     ("🎓", "Student",     "#8B5CF6"),
        ROLE_FACILITATOR: ("👨‍🏫", "Facilitator", "#EC4899"),
        ROLE_ADMIN:       ("👑", "Admin",       "#FBBF24"),
    }.get(role, ("•", role.title() or "User", COLORS["primary"]))


def _status_meta(status: str):
    status = _safe_str(status).lower()
    return {
        STATUS_APPROVED: ("✅", "Approved", STATUS["green"]),
        STATUS_PENDING:  ("⏳", "Pending",  STATUS["amber"]),
        STATUS_REJECTED: ("❌", "Rejected", STATUS["red"]),
    }.get(status, ("•", status.title() or "—", COLORS["text_muted"]))


def _fmt_date(iso: str) -> str:
    if not iso:
        return "—"
    try:
        d = datetime.fromisoformat(iso)
        return d.strftime("%d %b %Y")
    except Exception:
        return iso[:10]


# =============================================================
# USER MANAGEMENT PAGE
# =============================================================

class AdminUserManagementPage(BasePage):

    def __init__(self, master, app):
        super().__init__(master, app)

        self.build_header("User Management",
                          "Manage all accounts in Shruthi Jhari", back=False)
        self.build_sidebar(self._build_nav_items())
        self.build_content(scrollable=True)
        self.build_footer()

        # State
        self._role_filter = "all"
        self._status_filter = "all"
        self._search_text = ""
        self._filter_btns = {}
        self._status_btns = {}
        self._search_entry = None
        self._table_container = None

        self.render()

    def _build_nav_items(self):
        items = _admin_nav()
        for it in items:
            if it["key"] == "admin_users":
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

        self._load_users()

        # 1. Stats
        self._render_stats(content)

        # 2. Actions row (add user + refresh)
        self._render_actions(content)

        # 3. Controls (search + filters)
        self.section_title("Filters", parent=content)
        self._render_controls(content)

        # 4. Table
        self.section_title("All Users", parent=content)
        self._table_container = ctk.CTkFrame(content, fg_color="transparent")
        self._table_container.pack(fill="x", pady=(0, PAD_MD))
        self._render_table()

    # =========================================================
    # LOAD
    # =========================================================

    def _load_users(self):
        try:
            self._users = self.db.query("""
                SELECT * FROM users
                ORDER BY
                    CASE role
                        WHEN 'admin' THEN 0
                        WHEN 'facilitator' THEN 1
                        ELSE 2
                    END,
                    name ASC
            """)
        except Exception:
            self._users = pd.DataFrame()

    # =========================================================
    # STATS
    # =========================================================

    def _render_stats(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        u = self._users
        total = 0 if u is None else len(u)

        by_role = {"admin": 0, "facilitator": 0, "student": 0}
        by_status = {"approved": 0, "pending": 0, "rejected": 0}

        if u is not None and not u.empty:
            for _, r in u.iterrows():
                rl = _safe_str(r.get("role")).lower()
                st = _safe_str(r.get("status")).lower()
                if rl in by_role:
                    by_role[rl] += 1
                if st in by_status:
                    by_status[st] += 1

        self.stat_card(
            row, total, "Total users",
            accent=COLORS["primary"], icon="👥",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, by_role["admin"], "Admins",
            accent="#FBBF24", icon="👑",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, by_role["facilitator"], "Facilitators",
            accent="#EC4899", icon="👨‍🏫",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, by_role["student"], "Students",
            accent="#8B5CF6", icon="🎓",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, by_status["approved"], "Approved",
            accent=STATUS["green"], icon="✅",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, by_status["pending"], "Pending",
            accent=STATUS["amber"], icon="⏳",
        ).pack(side="left")

    # =========================================================
    # ACTIONS
    # =========================================================

    def _render_actions(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        self.primary_button(
            row, "➕  Add New User",
            command=self._show_add_dialog,
            width=200, height=42,
        ).pack(side="left", padx=(0, PAD_MD))

        self.secondary_button(
            row, "🔄  Refresh",
            command=self._reload,
            width=120, height=42,
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
            placeholder_text="Name, email, or USN…")
        self._search_entry.pack(side="left")
        self._search_entry.bind("<KeyRelease>", self._on_search_change)

        self.secondary_button(
            s_row, "Clear",
            command=self._clear_search,
            width=90, height=36,
        ).pack(side="left", padx=(PAD_SM, 0))

        # Row 2: Role filter
        role_row = ctk.CTkFrame(body, fg_color="transparent")
        role_row.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            role_row, text="Role:",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_muted"]).pack(side="left", padx=(0, 8))

        for key, label in [("all", "All"),
                           ("admin", "👑 Admin"),
                           ("facilitator", "👨‍🏫 Fac"),
                           ("student", "🎓 Student")]:
            is_active = (self._role_filter == key)
            btn = ctk.CTkButton(
                role_row, text=label, width=120, height=32,
                font=(FONT_FAMILY, 10),
                fg_color=COLORS["primary"] if is_active
                         else COLORS["surface_alt"],
                hover_color=COLORS["surface_hi"],
                text_color=COLORS["text"],
                corner_radius=BUTTON_RADIUS,
                command=lambda k=key: self._set_role_filter(k),
            )
            btn.pack(side="left", padx=(0, PAD_SM))
            self._filter_btns[key] = btn

        # Row 3: Status filter
        st_row = ctk.CTkFrame(body, fg_color="transparent")
        st_row.pack(fill="x")

        ctk.CTkLabel(
            st_row, text="Status:",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_muted"]).pack(side="left", padx=(0, 8))

        for key, label in [("all", "All"),
                           ("approved", "✅ Approved"),
                           ("pending", "⏳ Pending"),
                           ("rejected", "❌ Rejected")]:
            is_active = (self._status_filter == key)
            btn = ctk.CTkButton(
                st_row, text=label, width=120, height=32,
                font=(FONT_FAMILY, 10),
                fg_color=COLORS["primary"] if is_active
                         else COLORS["surface_alt"],
                hover_color=COLORS["surface_hi"],
                text_color=COLORS["text"],
                corner_radius=BUTTON_RADIUS,
                command=lambda k=key: self._set_status_filter(k),
            )
            btn.pack(side="left", padx=(0, PAD_SM))
            self._status_btns[key] = btn

    def _set_role_filter(self, key: str):
        self._role_filter = key
        for k, b in self._filter_btns.items():
            try:
                b.configure(fg_color=COLORS["primary"] if k == key
                            else COLORS["surface_alt"])
            except Exception:
                pass
        self._render_table()

    def _set_status_filter(self, key: str):
        self._status_filter = key
        for k, b in self._status_btns.items():
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
    # TABLE
    # =========================================================

    def _render_table(self):
        for w in self._table_container.winfo_children():
            w.destroy()

        u = self._users
        if u is None or u.empty:
            ctk.CTkLabel(
                self._table_container,
                text="No users found.",
                font=FONTS["body"],
                text_color=COLORS["text_muted"]).pack(pady=20)
            return

        df = u.copy()

        # Filter by role
        if self._role_filter != "all":
            df = df[df["role"].astype(str).str.lower() == self._role_filter]

        # Filter by status
        if self._status_filter != "all":
            df = df[df["status"].astype(str).str.lower()
                    == self._status_filter]

        # Search
        if self._search_text:
            q = self._search_text
            mask = df.apply(
                lambda r: (q in _safe_str(r.get("name")).lower())
                or (q in _safe_str(r.get("email")).lower())
                or (q in _safe_str(r.get("usn")).lower()),
                axis=1)
            df = df[mask]

        if df.empty:
            ctk.CTkLabel(
                self._table_container,
                text="No users match your filters.",
                font=FONTS["body"],
                text_color=COLORS["text_muted"]).pack(pady=20)
            return

        # Count label
        ctk.CTkLabel(
            self._table_container,
            text=f"Showing {len(df)} of {len(u)} users",
            font=(FONT_FAMILY, 10),
            text_color=COLORS["text_muted"],
        ).pack(anchor="w", pady=(0, PAD_SM))

        # Header
        header = ctk.CTkFrame(self._table_container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 4))

        for label, w in [("User", 260), ("Email", 220),
                         ("USN", 140), ("Role", 130),
                         ("Status", 120), ("Joined", 120),
                         ("Actions", 260)]:
            ctk.CTkLabel(
                header, text=label, width=w, anchor="w",
                font=(FONT_FAMILY, 10, "bold"),
                text_color=COLORS["text_muted"]).pack(side="left")

        # Rows
        for _, r in df.iterrows():
            self._render_row(r)

    def _render_row(self, u):
        uid = _safe_str(u.get("id"))
        name = _safe_str(u.get("name")) or "—"
        email = _safe_str(u.get("email")) or "—"
        usn = _safe_str(u.get("usn")) or "—"
        role = _safe_str(u.get("role"))
        status = _safe_str(u.get("status"))
        created = _safe_str(u.get("created_at"))

        _, _, role_color = _role_meta(role)
        _, _, status_color = _status_meta(status)

        row = ctk.CTkFrame(
            self._table_container,
            fg_color=COLORS["surface_alt"],
            corner_radius=8)
        row.pack(fill="x", pady=2)

        inner = ctk.CTkFrame(row, fg_color="transparent")
        inner.pack(fill="x", padx=8, pady=6)

        # User (avatar + name)
        user_box = ctk.CTkFrame(inner, fg_color="transparent", width=260)
        user_box.pack(side="left")
        user_box.pack_propagate(False)

        try:
            avatar = load_avatar(
                user_id=uid, name=name,
                size=32, shape="circle")
            ctk.CTkLabel(user_box, image=avatar, text="").pack(
                side="left", padx=(0, 8))
        except Exception:
            pass

        ctk.CTkLabel(
            user_box, text=name,
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text"], anchor="w",
        ).pack(side="left")

        # Email
        ctk.CTkLabel(
            inner, text=email, width=220, anchor="w",
            font=(FONT_FAMILY, 10),
            text_color=COLORS["text_muted"],
        ).pack(side="left")

        # USN
        ctk.CTkLabel(
            inner, text=usn, width=140, anchor="w",
            font=(FONT_FAMILY, 10),
            text_color=COLORS["text_muted"],
        ).pack(side="left")

        # Role chip
        role_box = ctk.CTkFrame(inner, fg_color="transparent", width=130)
        role_box.pack(side="left")
        role_box.pack_propagate(False)

        chip = ctk.CTkFrame(role_box, fg_color=role_color,
                            corner_radius=CHIP_RADIUS)
        chip.pack(side="left")
        icon, rlabel, _ = _role_meta(role)
        ctk.CTkLabel(
            chip, text=f"  {icon} {rlabel}  ",
            font=(FONT_FAMILY, 9, "bold"),
            text_color="#FFFFFF").pack(padx=2, pady=2)

        # Status chip
        st_box = ctk.CTkFrame(inner, fg_color="transparent", width=120)
        st_box.pack(side="left")
        st_box.pack_propagate(False)

        sicon, slabel, _ = _status_meta(status)
        st_chip = ctk.CTkFrame(st_box, fg_color=status_color,
                               corner_radius=CHIP_RADIUS)
        st_chip.pack(side="left")
        ctk.CTkLabel(
            st_chip, text=f"  {sicon} {slabel}  ",
            font=(FONT_FAMILY, 9, "bold"),
            text_color="#FFFFFF").pack(padx=2, pady=2)

        # Joined
        ctk.CTkLabel(
            inner, text=_fmt_date(created), width=120, anchor="w",
            font=(FONT_FAMILY, 10),
            text_color=COLORS["text_muted"],
        ).pack(side="left")

        # Actions
        act_box = ctk.CTkFrame(inner, fg_color="transparent", width=260)
        act_box.pack(side="left")
        act_box.pack_propagate(False)

        self.secondary_button(
            act_box, "✏️ Edit",
            command=lambda u_=u: self._show_edit_dialog(u_),
            width=80, height=28,
        ).pack(side="left", padx=(0, 4))

        # Reset password (skip for admin)
        if role.lower() != ROLE_ADMIN:
            self.secondary_button(
                act_box, "🔑 Reset",
                command=lambda u_=u: self._reset_password(u_),
                width=80, height=28,
            ).pack(side="left", padx=(0, 4))

        # Delete (only for non-admin)
        if role.lower() != ROLE_ADMIN:
            self.danger_button(
                act_box, "🗑 Delete",
                command=lambda u_=u: self._delete_user(u_),
                width=80, height=28,
            ).pack(side="left")

    # =========================================================
    # ADD DIALOG
    # =========================================================

    def _show_add_dialog(self):
        dialog = _UserFormDialog(
            self.winfo_toplevel(),
            title="Add New User",
            on_submit=self._create_user,
        )
        dialog.show()

    def _create_user(self, data: dict):
        try:
            uid = str(uuid.uuid4())
            now = datetime.now().isoformat()

            # Check duplicate email
            existing = self.db.query(
                "SELECT 1 FROM users WHERE LOWER(email)=LOWER(?)",
                (data["email"],))
            if not existing.empty:
                self.toast("Email already exists.", "error")
                return False

            # Check duplicate USN (students only)
            if data.get("usn"):
                usn_check = self.db.query(
                    "SELECT 1 FROM users WHERE usn=?", (data["usn"],))
                if not usn_check.empty:
                    self.toast("USN already exists.", "error")
                    return False

            self.db.execute("""
                INSERT INTO users
                    (id, usn, name, email, password, role, grade, section,
                     avatar_path, status, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (
                uid,
                data.get("usn") or None,
                data["name"],
                data["email"],
                data.get("password") or "demo",
                data["role"],
                data.get("grade"),
                data.get("section"),
                None,
                STATUS_APPROVED,   # admin-created users go straight to approved
                now,
            ))

            self.db.log_audit(
                (self.user or {}).get("id", "admin"),
                "create_user", target=data["email"],
                details=f"role={data['role']}")

            self.toast(f"Created {data['name']}.", "success")
            self._reload()
            return True
        except Exception as e:
            self.toast(f"Create failed: {e}", "error")
            return False

    # =========================================================
    # EDIT DIALOG
    # =========================================================

    def _show_edit_dialog(self, user_row):
        dialog = _UserFormDialog(
            self.winfo_toplevel(),
            title=f"Edit — {_safe_str(user_row.get('name'))}",
            existing=user_row.to_dict(),
            on_submit=lambda d, uid=_safe_str(user_row.get("id")):
                self._update_user(uid, d),
        )
        dialog.show()

    def _update_user(self, user_id: str, data: dict):
        try:
            # Build update — column names come from a fixed whitelist,
            # so f-string interpolation here is safe.
            fields = []
            params = []
            for k in ("name", "email", "usn", "role",
                      "grade", "section", "password", "status"):
                if k in data and data[k] is not None:
                    fields.append(f"{k}=?")
                    params.append(data[k])

            if not fields:
                return False

            params.append(user_id)
            sql = f"UPDATE users SET {', '.join(fields)} WHERE id=?"
            self.db.execute(sql, tuple(params))

            self.db.log_audit(
                (self.user or {}).get("id", "admin"),
                "update_user", target=user_id,
                details=f"fields={[f.split('=')[0] for f in fields]}")

            self.toast("User updated ✓", "success")
            self._reload()
            return True
        except Exception as e:
            self.toast(f"Update failed: {e}", "error")
            return False

    # =========================================================
    # RESET PASSWORD
    # =========================================================

    def _reset_password(self, user_row):
        uid = _safe_str(user_row.get("id"))
        name = _safe_str(user_row.get("name"))

        def on_confirm():
            try:
                self.db.execute(
                    "UPDATE users SET password='demo' WHERE id=?",
                    (uid,))
                self.db.log_audit(
                    (self.user or {}).get("id", "admin"),
                    "reset_password", target=uid)
                self.toast(
                    f"Password reset to 'demo' for {name}.", "success")
            except Exception as e:
                self.toast(f"Reset failed: {e}", "error")

        self.confirm(
            "Reset password?",
            f"Set {name}'s password back to 'demo'? They can change it "
            f"after signing in.",
            on_yes=on_confirm,
            yes_text="Reset",
        )

    # =========================================================
    # DELETE
    # =========================================================

    def _delete_user(self, user_row):
        uid = _safe_str(user_row.get("id"))
        name = _safe_str(user_row.get("name"))
        email = _safe_str(user_row.get("email"))

        def on_confirm():
            try:
                # Delete related rows first
                for table in ("user_interests", "user_badges",
                              "attempts", "mastery", "attendance",
                              "marks", "marks_summary",
                              "activity_scores",
                              "remedial_enrollments",
                              "interventions"):
                    try:
                        if table == "interventions":
                            self.db.execute(
                                f"DELETE FROM {table} WHERE student_id=?",
                                (uid,))
                        else:
                            self.db.execute(
                                f"DELETE FROM {table} WHERE user_id=?",
                                (uid,))
                    except Exception:
                        pass

                # Certificates (column user_id)
                try:
                    self.db.execute(
                        "DELETE FROM certificates WHERE user_id=?", (uid,))
                except Exception:
                    pass

                # Finally the user
                self.db.execute("DELETE FROM users WHERE id=?", (uid,))

                self.db.log_audit(
                    (self.user or {}).get("id", "admin"),
                    "delete_user", target=email)

                clear_cache(uid)
                self.toast(f"Deleted {name}.", "warning")
                self._reload()
            except Exception as e:
                self.toast(f"Delete failed: {e}", "error")

        self.confirm(
            "Delete this user?",
            f"Permanently delete {name} ({email})? This will remove all "
            f"their data — marks, attendance, badges, etc. This cannot "
            f"be undone.",
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
# USER FORM DIALOG
# =============================================================

class _UserFormDialog:
    """Modal form for adding / editing users."""

    def __init__(self, parent, title, on_submit, existing=None):
        self.parent = parent
        self.title = title
        self.on_submit = on_submit
        self.existing = existing or {}

        self.top = None
        self.fields = {}
        self._labels = {}

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

        W, H = 480, 660
        self.top.geometry(f"{W}x{H}")

        # Center
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

        # Close handlers
        try:
            self.top.bind("<Escape>", lambda e: self._close())
            self.top.protocol("WM_DELETE_WINDOW", self._close)
        except Exception:
            pass

        # Top gradient bar
        bar = ctk.CTkFrame(self.top, height=6, fg_color=COLORS["primary"],
                           corner_radius=0)
        bar.pack(fill="x")

        body = ctk.CTkFrame(self.top, fg_color="transparent")
        body.pack(fill="both", expand=True,
                  padx=PAD_XL, pady=PAD_LG)

        ctk.CTkLabel(
            body, text=self.title,
            font=(FONT_FAMILY, 18, "bold"),
            text_color=COLORS["text"]).pack(anchor="w", pady=(0, 16))

        # Fields
        self._add_field(body, "name", "Full Name", required=True)
        self._add_field(body, "email", "Email", required=True)
        self._add_field(body, "usn", "USN (students only)")

        # Password label changes depending on mode
        pw_label = ("Password (leave blank to keep current)"
                    if self.existing else "Password")
        self._add_field(body, "password", pw_label,
                        required=not self.existing, secret=True)

        # Role dropdown
        role_row = ctk.CTkFrame(body, fg_color="transparent")
        role_row.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(
            role_row, text="Role",
            font=(FONT_FAMILY, 10, "bold"),
            text_color=COLORS["text_muted"]).pack(anchor="w")

        self.fields["role"] = ctk.CTkOptionMenu(
            role_row,
            values=["student", "facilitator", "admin"],
            width=420, height=38,
            font=FONTS["small"],
            fg_color=COLORS["surface_alt"],
            button_color=COLORS["primary"],
            button_hover_color=COLORS["primary_hover"],
            text_color=COLORS["text"],
            dropdown_fg_color=COLORS["surface_alt"],
            dropdown_text_color=COLORS["text"],
            corner_radius=10)
        self.fields["role"].set(_safe_str(self.existing.get("role"))
                                or "student")
        self.fields["role"].pack()

        self._add_field(body, "grade", "Grade (optional)")
        self._add_field(body, "section", "Section (optional)")

        # Status dropdown (edit mode only)
        if self.existing:
            status_row = ctk.CTkFrame(body, fg_color="transparent")
            status_row.pack(fill="x", pady=(0, 10))
            ctk.CTkLabel(
                status_row, text="Status",
                font=(FONT_FAMILY, 10, "bold"),
                text_color=COLORS["text_muted"]).pack(anchor="w")

            self.fields["status"] = ctk.CTkOptionMenu(
                status_row,
                values=["approved", "pending", "rejected"],
                width=420, height=38,
                font=FONTS["small"],
                fg_color=COLORS["surface_alt"],
                button_color=COLORS["primary"],
                button_hover_color=COLORS["primary_hover"],
                text_color=COLORS["text"],
                dropdown_fg_color=COLORS["surface_alt"],
                dropdown_text_color=COLORS["text"],
                corner_radius=10)
            self.fields["status"].set(
                _safe_str(self.existing.get("status")) or "approved")
            self.fields["status"].pack()

        # Error label
        self.error_label = ctk.CTkLabel(
            body, text="",
            font=(FONT_FAMILY, 10),
            text_color=STATUS["red"],
            wraplength=420, justify="left")
        self.error_label.pack(anchor="w", pady=(6, 0))

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
            btn_row, text="Save", width=110, height=38,
            font=(FONT_FAMILY, 11, "bold"),
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            text_color=COLORS["text"],
            corner_radius=BUTTON_RADIUS,
            command=self._submit,
        ).pack(side="right")

        # Prefill if editing
        if self.existing:
            for k in ("name", "email", "usn", "grade", "section"):
                if k in self.fields and k in self.existing:
                    try:
                        self.fields[k].insert(0, _safe_str(self.existing[k]))
                    except Exception:
                        pass

        # Enter submits from any field
        for w in self.fields.values():
            try:
                w.bind("<Return>", lambda e: self._submit())
            except Exception:
                pass

        # Focus first field
        try:
            self.fields["name"].focus_set()
        except Exception:
            pass

    def _add_field(self, parent, key: str, label: str,
                   required=False, secret=False):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, 10))

        lbl_text = label + (" *" if required else "")
        lbl = ctk.CTkLabel(
            row, text=lbl_text,
            font=(FONT_FAMILY, 10, "bold"),
            text_color=COLORS["text_muted"])
        lbl.pack(anchor="w")
        self._labels[key] = lbl

        entry = ctk.CTkEntry(
            row, width=420, height=38,
            font=FONTS["small"],
            fg_color=COLORS["surface_alt"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            corner_radius=10,
            show="•" if secret else "")
        entry.pack()
        self.fields[key] = entry

    def _submit(self):
        data = {}
        for k, w in self.fields.items():
            try:
                if hasattr(w, "get"):
                    v = w.get()
                    if isinstance(v, str):
                        v = v.strip()
                    data[k] = v
            except Exception:
                pass

        # ---- Validate ----
        name = data.get("name") or ""
        email = data.get("email") or ""
        role = (data.get("role") or "student").lower()

        if not name:
            self.error_label.configure(text="⚠  Name is required.")
            return
        if len(name) < 2:
            self.error_label.configure(text="⚠  Name looks too short.")
            return

        if not email:
            self.error_label.configure(text="⚠  Email is required.")
            return
        if "@" not in email or "." not in email.split("@")[-1]:
            self.error_label.configure(text="⚠  Please enter a valid email.")
            return

        # USN required for students
        if role == "student":
            usn = data.get("usn") or ""
            if not usn:
                self.error_label.configure(
                    text="⚠  USN is required for students.")
                return

        # Password: required on create; optional on edit
        password = data.get("password") or ""
        if not self.existing and not password:
            self.error_label.configure(
                text="⚠  Password is required for new users.")
            return
        if password and len(password) < 4:
            self.error_label.configure(
                text="⚠  Password must be at least 4 characters.")
            return

        # Clear error
        self.error_label.configure(text="")

        # Don't send an empty password on edit
        if self.existing and not password:
            data.pop("password", None)

        # Empty optional strings → None
        for k in ("usn", "grade", "section", "password"):
            if k in data and not data[k]:
                data[k] = None

        # Normalize role + status
        data["role"] = role
        if "status" in data:
            data["status"] = (data.get("status") or "approved").lower()

        # Hand off; only close if the caller returns truthy
        try:
            ok = self.on_submit(data)
        except Exception:
            ok = False

        if ok:
            self._close()

    def _close(self):
        try:
            if self.top is not None:
                self.top.grab_release()
        except Exception:
            pass
        try:
            if self.top is not None:
                self.top.destroy()
        except Exception:
            pass
        self.top = None


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
            print(f"[users] → show_page('{key}')  args={kw}")

        def go_back(self):
            print("[users] back")

        def logout(self):
            print("[users] logout")

    root = ctk.CTk()
    W, H = 1500, 900
    root.geometry(f"{W}x{H}")
    root.configure(fg_color=COLORS["bg"])
    root.title(f"{APP_NAME} — user management")

    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - W) // 2
    y = (sh - H) // 2
    root.geometry(f"{W}x{H}+{x}+{y}")

    app = _FakeApp()
    page = AdminUserManagementPage(root, app)
    page.pack(fill="both", expand=True)
    root.mainloop()
    print("\n✅ pages/admin/user_management.py OK")