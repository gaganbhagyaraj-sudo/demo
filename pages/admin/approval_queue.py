# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  pages/admin/approval_queue.py  ·  Pending registrations queue
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
    APP_NAME, COLORS, STATUS,
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


def _role_badge(role: str):
    role = _safe_str(role).lower()
    return {
        ROLE_STUDENT:     ("🎓", "Student",     "#8B5CF6"),
        ROLE_FACILITATOR: ("👨‍🏫", "Facilitator", "#EC4899"),
        ROLE_ADMIN:       ("👑", "Admin",       "#FBBF24"),
    }.get(role, ("•", role.title() or "User", COLORS["primary"]))


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
# APPROVAL QUEUE PAGE
# =============================================================

class AdminApprovalQueuePage(BasePage):

    def __init__(self, master, app):
        super().__init__(master, app)

        self.build_header("Approval Queue",
                          "Review new registrations", back=False)
        self.build_sidebar(self._build_nav_items())
        self.build_content(scrollable=True)
        self.build_footer()

        # State
        self._role_filter = "all"
        self._search_text = ""
        self._filter_btns = {}
        self._search_entry = None
        self._queue_container = None

        self.render()

    def _build_nav_items(self):
        items = _admin_nav()
        for it in items:
            if it["key"] == "admin_approval":
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

        self._load_pending()

        # 1. Stats
        self._render_stats(content)

        # 2. Bulk actions
        self._render_bulk_actions(content)

        # 3. Controls (search + role filter)
        self.section_title("Filter", parent=content)
        self._render_controls(content)

        # 4. Queue
        self.section_title("Pending Registrations", parent=content)
        self._queue_container = ctk.CTkFrame(content, fg_color="transparent")
        self._queue_container.pack(fill="x", pady=(0, PAD_MD))
        self._render_queue()

    # =========================================================
    # LOAD
    # =========================================================

    def _load_pending(self):
        try:
            self._pending = self.db.get_pending_users()
        except Exception:
            self._pending = pd.DataFrame()

        # Counts by role
        self._counts_by_role = {"student": 0, "facilitator": 0, "admin": 0}
        if self._pending is not None and not self._pending.empty:
            for _, r in self._pending.iterrows():
                rl = _safe_str(r.get("role")).lower()
                if rl in self._counts_by_role:
                    self._counts_by_role[rl] += 1

        # Recently approved / rejected (last 7 days)
        self._recent_approved = 0
        self._recent_rejected = 0
        try:
            cutoff = (datetime.now() - timedelta(days=7)).isoformat()
            a = self.db.query("""
                SELECT COUNT(*) AS n FROM users
                WHERE status=? AND created_at >= ?
            """, (STATUS_APPROVED, cutoff))
            self._recent_approved = int(a.iloc[0]["n"]) if not a.empty else 0

            r = self.db.query("""
                SELECT COUNT(*) AS n FROM users
                WHERE status=? AND created_at >= ?
            """, (STATUS_REJECTED, cutoff))
            self._recent_rejected = int(r.iloc[0]["n"]) if not r.empty else 0
        except Exception:
            pass

    # =========================================================
    # STATS
    # =========================================================

    def _render_stats(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        n_total = 0 if self._pending is None else len(self._pending)
        n_students = self._counts_by_role.get("student", 0)
        n_facs = self._counts_by_role.get("facilitator", 0)

        self.stat_card(
            row, n_total, "Pending",
            accent=STATUS["amber"] if n_total > 0
                   else COLORS["text_muted"],
            icon="⏳",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, n_students, "Students",
            accent="#8B5CF6", icon="🎓",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, n_facs, "Facilitators",
            accent="#EC4899", icon="👨‍🏫",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, self._recent_approved, "Approved (7d)",
            accent=STATUS["green"], icon="✅",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, self._recent_rejected, "Rejected (7d)",
            accent=STATUS["red"], icon="❌",
        ).pack(side="left")

    # =========================================================
    # BULK ACTIONS
    # =========================================================

    def _render_bulk_actions(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        p = self._pending
        n = 0 if p is None else len(p)

        self.primary_button(
            row, f"✅  Approve all ({n})",
            command=self._approve_all,
            width=200, height=42,
        ).pack(side="left", padx=(0, PAD_MD))

        self.danger_button(
            row, f"❌  Reject all ({n})",
            command=self._reject_all,
            width=200, height=42,
        ).pack(side="left", padx=(0, PAD_MD))

        self.secondary_button(
            row, "🔄  Refresh",
            command=self._reload,
            width=120, height=42,
        ).pack(side="left")

    def _approve_all(self):
        p = self._pending
        if p is None or p.empty:
            self.toast("No pending users.", "info")
            return

        # Build list of uids + names
        uids = [_safe_str(r.get("id")) for _, r in p.iterrows()]
        uids = [u for u in uids if u]

        def on_confirm():
            n_ok = 0
            for uid in uids:
                try:
                    self.db.approve_user(uid)
                    n_ok += 1
                except Exception:
                    pass
            self.toast(f"Approved {n_ok} user(s).", "success")
            self._reload()

        self.confirm(
            "Approve all pending users?",
            f"This will approve {len(uids)} user(s). They'll be able to "
            f"sign in immediately.",
            on_yes=on_confirm,
            yes_text=f"Approve {len(uids)}",
        )

    def _reject_all(self):
        p = self._pending
        if p is None or p.empty:
            self.toast("No pending users.", "info")
            return

        uids = [_safe_str(r.get("id")) for _, r in p.iterrows()]
        uids = [u for u in uids if u]

        def on_confirm():
            n_ok = 0
            for uid in uids:
                try:
                    self.db.reject_user(uid)
                    n_ok += 1
                except Exception:
                    pass
            self.toast(f"Rejected {n_ok} user(s).", "warning")
            self._reload()

        self.confirm(
            "Reject all pending users?",
            f"This will reject {len(uids)} user(s). They won't be able "
            f"to sign in.",
            on_yes=on_confirm,
            yes_text=f"Reject {len(uids)}",
        )

    # =========================================================
    # CONTROLS
    # =========================================================

    def _render_controls(self, parent):
        card = self.card(parent)
        card.pack(fill="x", pady=(0, PAD_MD))

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        # Row 1: Search
        search_row = ctk.CTkFrame(body, fg_color="transparent")
        search_row.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            search_row, text="🔍  Search:",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_muted"]).pack(side="left", padx=(0, 8))

        self._search_entry = ctk.CTkEntry(
            search_row, width=340, height=36,
            font=FONTS["small"],
            fg_color=COLORS["surface_alt"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            corner_radius=10,
            placeholder_text="Search by name, email, or USN…")
        self._search_entry.pack(side="left")
        self._search_entry.bind("<KeyRelease>", self._on_search_change)

        self.secondary_button(
            search_row, "Clear",
            command=self._clear_search,
            width=90, height=36,
        ).pack(side="left", padx=(PAD_SM, 0))

        # Row 2: Role filter
        role_row = ctk.CTkFrame(body, fg_color="transparent")
        role_row.pack(fill="x")

        ctk.CTkLabel(
            role_row, text="Role:",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_muted"]).pack(side="left", padx=(0, 8))

        for key, label in [("all", "All"),
                           ("student", "🎓 Students"),
                           ("facilitator", "👨‍🏫 Facilitators")]:
            is_active = (self._role_filter == key)
            btn = ctk.CTkButton(
                role_row, text=label, width=140, height=34,
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

    def _set_role_filter(self, key: str):
        self._role_filter = key
        for k, b in self._filter_btns.items():
            try:
                b.configure(fg_color=COLORS["primary"] if k == key
                            else COLORS["surface_alt"])
            except Exception:
                pass
        self._render_queue()

    def _on_search_change(self, event=None):
        try:
            self._search_text = (self._search_entry.get() or "").strip().lower()
        except Exception:
            self._search_text = ""
        self._render_queue()

    def _clear_search(self):
        try:
            self._search_entry.delete(0, "end")
        except Exception:
            pass
        self._search_text = ""
        self._render_queue()

    # =========================================================
    # QUEUE
    # =========================================================

    def _render_queue(self):
        for w in self._queue_container.winfo_children():
            w.destroy()

        p = self._pending
        if p is None or p.empty:
            ctk.CTkLabel(
                self._queue_container,
                text="✅  No pending registrations — everyone's approved!",
                font=FONTS["body"],
                text_color=STATUS["green"]).pack(pady=30)
            return

        df = p.copy()

        # Filter by role
        if self._role_filter != "all":
            df = df[df["role"].astype(str).str.lower() == self._role_filter]

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
                self._queue_container,
                text="No registrations match your filters.",
                font=FONTS["body"],
                text_color=COLORS["text_muted"]).pack(pady=20)
            return

        # Count label
        ctk.CTkLabel(
            self._queue_container,
            text=f"Showing {len(df)} pending registration(s)",
            font=(FONT_FAMILY, 10),
            text_color=COLORS["text_muted"],
        ).pack(anchor="w", pady=(0, PAD_SM))

        for _, u in df.iterrows():
            self._render_pending_card(u)

    def _render_pending_card(self, u):
        uid = _safe_str(u.get("id"))
        name = _safe_str(u.get("name")) or "—"
        email = _safe_str(u.get("email"))
        usn = _safe_str(u.get("usn"))
        role = _safe_str(u.get("role"))
        grade = _safe_str(u.get("grade"))
        section = _safe_str(u.get("section"))
        created = _safe_str(u.get("created_at"))

        icon, role_label, role_color = _role_badge(role)

        # Card
        card = ctk.CTkFrame(
            self._queue_container,
            fg_color=COLORS["surface"],
            corner_radius=CARD_RADIUS,
            border_width=1,
            border_color=role_color)
        card.pack(fill="x", pady=4)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=PAD_LG, pady=PAD_MD)

        # Head: avatar + name + role chip + time
        head = ctk.CTkFrame(inner, fg_color="transparent")
        head.pack(fill="x")

        # Avatar
        try:
            avatar = load_avatar(
                user_id=uid, name=name,
                size=52, shape="circle")
            ctk.CTkLabel(head, image=avatar, text="").pack(
                side="left", padx=(0, 12))
        except Exception:
            pass

        # Name + meta
        info = ctk.CTkFrame(head, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            info, text=name,
            font=(FONT_FAMILY, 14, "bold"),
            text_color=COLORS["text"], anchor="w",
        ).pack(anchor="w")

        meta_line = email
        if usn:
            meta_line += f"  ·  {usn}"
        ctk.CTkLabel(
            info, text=meta_line,
            font=(FONT_FAMILY, 10),
            text_color=COLORS["text_muted"], anchor="w",
        ).pack(anchor="w", pady=(2, 0))

        # Class info for students
        if role.lower() == "student" and (grade or section):
            class_line = "  ·  ".join(
                [p for p in [grade, f"Sec {section}" if section else ""]
                 if p])
            ctk.CTkLabel(
                info, text=class_line,
                font=(FONT_FAMILY, 9),
                text_color=COLORS["text_muted"], anchor="w",
            ).pack(anchor="w", pady=(2, 0))

        # Right: role chip + submitted time
        right = ctk.CTkFrame(head, fg_color="transparent")
        right.pack(side="right")

        role_chip = ctk.CTkFrame(right, fg_color=role_color,
                                 corner_radius=CHIP_RADIUS)
        role_chip.pack(anchor="e")
        ctk.CTkLabel(
            role_chip,
            text=f"  {icon}  {role_label}  ",
            font=(FONT_FAMILY, 10, "bold"),
            text_color="#FFFFFF").pack(padx=4, pady=3)

        ctk.CTkLabel(
            right,
            text=f"Submitted {_fmt_time(created)}",
            font=(FONT_FAMILY, 9),
            text_color=COLORS["text_muted"],
        ).pack(anchor="e", pady=(4, 0))

        # Actions row
        actions = ctk.CTkFrame(inner, fg_color="transparent")
        actions.pack(fill="x", pady=(12, 0))

        self.primary_button(
            actions, "✅  Approve",
            command=lambda i=uid, n=name: self._approve_one(i, n),
            width=140, height=36,
        ).pack(side="left", padx=(0, 8))

        self.danger_button(
            actions, "❌  Reject",
            command=lambda i=uid, n=name: self._reject_one(i, n),
            width=140, height=36,
        ).pack(side="left")

    # =========================================================
    # ACTIONS
    # =========================================================

    def _approve_one(self, user_id: str, name: str):
        def on_confirm():
            try:
                self.db.approve_user(user_id)
                self.toast(f"Approved {name}.", "success")
                self._reload()
            except Exception as e:
                self.toast(f"Failed: {e}", "error")

        self.confirm(
            "Approve this user?",
            f"Approve {name}'s registration? They'll be able to sign in.",
            on_yes=on_confirm,
            yes_text="Approve",
        )

    def _reject_one(self, user_id: str, name: str):
        def on_confirm():
            try:
                self.db.reject_user(user_id)
                self.toast(f"Rejected {name}.", "warning")
                self._reload()
            except Exception as e:
                self.toast(f"Failed: {e}", "error")

        self.confirm(
            "Reject this user?",
            f"Reject {name}'s registration? They won't be able to sign in.",
            on_yes=on_confirm,
            yes_text="Reject",
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
                # For demo: if no pending, create some fake pending users
                pending = self.db.get_pending_users()
                if pending.empty:
                    import uuid
                    now = datetime.now().isoformat()
                    for i, (nm, em, role) in enumerate([
                        ("Test Student A", "sa@test.com", "student"),
                        ("Test Student B", "sb@test.com", "student"),
                        ("Test Fac A", "fa@test.com", "facilitator"),
                    ]):
                        self.db.execute("""
                            INSERT INTO users(id,usn,name,email,password,
                                              role,grade,section,avatar_path,
                                              status,created_at)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?)
                        """, (str(uuid.uuid4()), f"TEST{i}",
                              nm, em, "demo", role,
                              "Grade 7", "A", None,
                              "pending", now))
            except Exception as e:
                print(f"(no DB: {e})")
                self.db = None

        @property
        def current_user(self):
            return self._user

        def show_page(self, key, **kw):
            print(f"[approval] → show_page('{key}')  args={kw}")

        def go_back(self):
            print("[approval] back")

        def logout(self):
            print("[approval] logout")

    root = ctk.CTk()
    W, H = 1400, 900
    root.geometry(f"{W}x{H}")
    root.configure(fg_color=COLORS["bg"])
    root.title(f"{APP_NAME} — approval queue")

    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - W) // 2
    y = (sh - H) // 2
    root.geometry(f"{W}x{H}+{x}+{y}")

    app = _FakeApp()
    page = AdminApprovalQueuePage(root, app)
    page.pack(fill="both", expand=True)
    root.mainloop()
    print("\n✅ pages/admin/approval_queue.py OK")