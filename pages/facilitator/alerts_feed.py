# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  pages/facilitator/alerts_feed.py  ·  Active alerts feed
# =============================================================

from __future__ import annotations

import os
import sys

# --- make project root importable ---
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import json

import customtkinter as ctk
import pandas as pd

from config import (
    APP_NAME, COLORS, STATUS, ZONE_COLORS, ZONE_LABELS,
    ALERT_TYPES, ALERT_RULES,
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


SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}

SEVERITY_COLORS = {
    "high": STATUS["red"],
    "medium": STATUS["amber"],
    "low": STATUS["info"],
}

SEVERITY_LABELS = {
    "high": "High",
    "medium": "Medium",
    "low": "Low",
}


# =============================================================
# ALERTS FEED PAGE
# =============================================================

class FacilitatorAlertsFeedPage(BasePage):

    def __init__(self, master, app):
        super().__init__(master, app)

        self.build_header("Alerts Feed",
                          "Students needing your attention", back=False)
        self.build_sidebar(self._build_nav_items())
        self.build_content(scrollable=True)
        self.build_footer()

        # State
        self._show_resolved = False
        self._severity_filter = "all"
        self._severity_btns = {}
        self._alerts_container = None

        self.render()

    def _build_nav_items(self):
        items = _facilitator_nav()
        for it in items:
            if it["key"] == "fac_alerts":
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

        self._load_alerts()

        # 1. Stats row
        self._render_stats(content)

        # 2. Controls: severity filter + toggle resolved
        self.section_title("Filters", parent=content)
        self._render_controls(content)

        # 3. Alerts list
        title = "Resolved Alerts" if self._show_resolved else "Active Alerts"
        self.section_title(title, parent=content)
        self._alerts_container = ctk.CTkFrame(content, fg_color="transparent")
        self._alerts_container.pack(fill="x", pady=(0, PAD_MD))
        self._render_alerts_list()

    # =========================================================
    # LOAD
    # =========================================================

    def _load_alerts(self):
        try:
            self._active = self.db.get_alerts(resolved=False)
        except Exception:
            self._active = pd.DataFrame()

        try:
            self._resolved = self.db.get_alerts(resolved=True)
        except Exception:
            self._resolved = pd.DataFrame()

    # =========================================================
    # STATS
    # =========================================================

    def _render_stats(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        active = self._active
        resolved = self._resolved

        n_active = 0 if active is None else len(active)
        n_resolved = 0 if resolved is None else len(resolved)

        # Count by severity
        high = med = low = 0
        if active is not None and not active.empty:
            for _, a in active.iterrows():
                sev = _safe_str(a.get("severity", "low")).lower()
                if sev == "high":
                    high += 1
                elif sev == "medium":
                    med += 1
                else:
                    low += 1

        self.stat_card(
            row, n_active, "Active alerts",
            accent=STATUS["red"] if n_active > 0 else STATUS["green"],
            icon="🔔",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, high, "🔴 High severity",
            accent=STATUS["red"], icon="⚠️",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, med, "🟠 Medium",
            accent=STATUS["amber"], icon="⚡",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, low, "🔵 Low",
            accent=STATUS["info"], icon="ℹ️",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, n_resolved, "Resolved",
            accent=STATUS["green"], icon="✅",
        ).pack(side="left")

    # =========================================================
    # CONTROLS
    # =========================================================

    def _render_controls(self, parent):
        card = self.card(parent)
        card.pack(fill="x", pady=(0, PAD_MD))

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        # Row 1: Severity filter
        filter_row = ctk.CTkFrame(body, fg_color="transparent")
        filter_row.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            filter_row, text="Severity:",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_muted"]).pack(side="left", padx=(0, 8))

        filters = [
            ("all", "All", COLORS["primary"]),
            ("high", "🔴 High", STATUS["red"]),
            ("medium", "🟠 Medium", STATUS["amber"]),
            ("low", "🔵 Low", STATUS["info"]),
        ]
        for key, label, color in filters:
            is_active = (self._severity_filter == key)
            btn = ctk.CTkButton(
                filter_row, text=label, width=110, height=34,
                font=(FONT_FAMILY, 10),
                fg_color=color if is_active else COLORS["surface_alt"],
                hover_color=COLORS["surface_hi"],
                text_color=COLORS["text"],
                corner_radius=BUTTON_RADIUS,
                command=lambda k=key: self._set_severity_filter(k),
            )
            btn.pack(side="left", padx=(0, PAD_SM))
            self._severity_btns[key] = btn

        # Row 2: Toggle resolved + refresh
        toggle_row = ctk.CTkFrame(body, fg_color="transparent")
        toggle_row.pack(fill="x")

        ctk.CTkLabel(
            toggle_row, text="View:",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_muted"]).pack(side="left", padx=(0, 8))

        self._view_btn = ctk.CTkButton(
            toggle_row,
            text="Active" if not self._show_resolved else "Resolved",
            width=140, height=34,
            font=(FONT_FAMILY, 10, "bold"),
            fg_color=COLORS["surface_alt"],
            hover_color=COLORS["surface_hi"],
            text_color=COLORS["text"],
            corner_radius=BUTTON_RADIUS,
            command=self._toggle_view,
        )
        self._view_btn.pack(side="left", padx=(0, PAD_SM))

        self.secondary_button(
            toggle_row, "Refresh",
            command=self._refresh,
            width=100, height=34,
        ).pack(side="right")

    def _set_severity_filter(self, key: str):
        self._severity_filter = key
        for k, b in self._severity_btns.items():
            try:
                color = COLORS["primary"]
                if k == "high":
                    color = STATUS["red"]
                elif k == "medium":
                    color = STATUS["amber"]
                elif k == "low":
                    color = STATUS["info"]
                b.configure(fg_color=color if k == key
                            else COLORS["surface_alt"])
            except Exception:
                pass
        self._render_alerts_list()

    def _toggle_view(self):
        self._show_resolved = not self._show_resolved
        try:
            self._view_btn.configure(
                text="Active" if not self._show_resolved else "Resolved")
        except Exception:
            pass
        self._render_alerts_list()

    def _refresh(self):
        self._load_alerts()
        for w in self._content.winfo_children():
            w.destroy()
        self.render()

    # =========================================================
    # LIST
    # =========================================================

    def _render_alerts_list(self):
        for w in self._alerts_container.winfo_children():
            w.destroy()

        df = self._resolved if self._show_resolved else self._active

        if df is None or df.empty:
            msg = "No resolved alerts." if self._show_resolved \
                  else "✅  No active alerts — all clear!"
            ctk.CTkLabel(
                self._alerts_container,
                text=msg,
                font=FONTS["body"],
                text_color=STATUS["green"] if not self._show_resolved
                           else COLORS["text_muted"]).pack(pady=30)
            return

        # Filter by severity
        if self._severity_filter != "all":
            df = df[df["severity"].astype(str).str.lower()
                    == self._severity_filter]

        if df.empty:
            ctk.CTkLabel(
                self._alerts_container,
                text="No alerts match this filter.",
                font=FONTS["body"],
                text_color=COLORS["text_muted"]).pack(pady=20)
            return

        # Sort by severity (high first) then created_at desc
        try:
            df = df.copy()
            df["_sev_rank"] = df["severity"].apply(
                lambda s: SEVERITY_ORDER.get(_safe_str(s).lower(), 3))
            df = df.sort_values(["_sev_rank", "created_at"],
                                ascending=[True, False])
        except Exception:
            pass

        # Render each
        for _, a in df.iterrows():
            self._render_alert_card(a)

    def _render_alert_card(self, a):
        alert_id = _safe_str(a.get("id"))
        user_id = _safe_str(a.get("user_id"))
        student_name = _safe_str(a.get("student_name")) or "Unknown"
        usn = _safe_str(a.get("usn"))
        severity = _safe_str(a.get("severity", "low")).lower()
        alert_type = _safe_str(a.get("alert_type", "alert"))
        message = _safe_str(a.get("message", ""))
        created = _safe_str(a.get("created_at"))[:16]
        resolved = bool(a.get("resolved"))

        sev_color = SEVERITY_COLORS.get(severity, COLORS["text_muted"])
        sev_label = SEVERITY_LABELS.get(severity, severity.title())

        # Get alert meta
        meta = ALERT_TYPES.get(alert_type, {})
        type_icon = meta.get("icon", "•")

        # Parse suggested_action
        suggested = None
        try:
            sa = a.get("suggested_action")
            if sa:
                suggested = json.loads(sa) if isinstance(sa, str) else sa
        except Exception:
            suggested = None

        # Card
        card = ctk.CTkFrame(
            self._alerts_container,
            fg_color=COLORS["surface"],
            corner_radius=CARD_RADIUS,
            border_width=1,
            border_color=sev_color)
        card.pack(fill="x", pady=4)

        # Colored left bar
        bar = ctk.CTkFrame(card, fg_color=sev_color,
                           width=6, corner_radius=0)
        bar.pack(side="left", fill="y")

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(side="left", fill="x", expand=True,
                   padx=PAD_LG, pady=PAD_MD)

        # Head row: avatar + student info + severity chip + date
        head = ctk.CTkFrame(inner, fg_color="transparent")
        head.pack(fill="x")

        left_head = ctk.CTkFrame(head, fg_color="transparent")
        left_head.pack(side="left", fill="x", expand=True)

        # Avatar
        try:
            avatar = load_avatar(
                user_id=user_id or "_",
                name=student_name,
                size=40, shape="circle",
            )
            ctk.CTkLabel(left_head, image=avatar, text="").pack(
                side="left", padx=(0, 10))
        except Exception:
            pass

        # Student info box
        stu_box = ctk.CTkFrame(left_head, fg_color="transparent")
        stu_box.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            stu_box, text=student_name,
            font=(FONT_FAMILY, 13, "bold"),
            text_color=COLORS["text"], anchor="w",
        ).pack(anchor="w")

        sub = usn or "—"
        ctk.CTkLabel(
            stu_box, text=sub,
            font=(FONT_FAMILY, 9),
            text_color=COLORS["text_muted"], anchor="w",
        ).pack(anchor="w")

        # Severity chip (right)
        sev_chip = ctk.CTkFrame(head, fg_color=sev_color,
                                corner_radius=CHIP_RADIUS)
        sev_chip.pack(side="right", padx=(0, 10))
        ctk.CTkLabel(
            sev_chip, text=f"  {sev_label}  ",
            font=(FONT_FAMILY, 10, "bold"),
            text_color="#FFFFFF").pack(padx=4, pady=2)

        # Date (right)
        ctk.CTkLabel(
            head, text=created,
            font=(FONT_FAMILY, 9),
            text_color=COLORS["text_muted"],
        ).pack(side="right", padx=(0, 10))

        # Alert type + message row
        alert_row = ctk.CTkFrame(inner, fg_color="transparent")
        alert_row.pack(fill="x", pady=(10, 6))

        ctk.CTkLabel(
            alert_row, text=f"{type_icon}  {alert_type.replace('_', ' ').title()}",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=sev_color, anchor="w",
        ).pack(anchor="w")

        if message:
            ctk.CTkLabel(
                inner, text=message,
                font=FONTS["small"],
                text_color=COLORS["text"], anchor="w",
                wraplength=900, justify="left",
            ).pack(anchor="w", pady=(0, 10))

        # Suggested action
        if suggested and isinstance(suggested, dict):
            sug_row = ctk.CTkFrame(inner, fg_color=COLORS["surface_alt"],
                                   corner_radius=8)
            sug_row.pack(fill="x", pady=(0, 10))

            sug_txt = []
            for k, v in suggested.items():
                sug_txt.append(f"{k.replace('_',' ')}: {v}")
            ctk.CTkLabel(
                sug_row,
                text="💡  Suggested: " + " · ".join(sug_txt),
                font=(FONT_FAMILY, 10),
                text_color=COLORS["text_muted"],
                anchor="w",
            ).pack(padx=12, pady=6, anchor="w")

        # Actions row
        actions = ctk.CTkFrame(inner, fg_color="transparent")
        actions.pack(fill="x")

        if not resolved:
            self.secondary_button(
                actions, "👤 View student",
                command=lambda u=user_id: self.navigate("fac_deepdive",
                                                        user_id=u),
                width=150, height=32,
            ).pack(side="left", padx=(0, 8))

            self.secondary_button(
                actions, "💡 Send hint",
                command=lambda u=user_id, aid=alert_id:
                    self._send_hint(u, aid),
                width=130, height=32,
            ).pack(side="left", padx=(0, 8))

            self.secondary_button(
                actions, "🩺 Remedial",
                command=lambda u=user_id:
                    self.navigate("fac_remedial", user_id=u),
                width=130, height=32,
            ).pack(side="left", padx=(0, 8))

            self.primary_button(
                actions, "✓ Mark resolved",
                command=lambda aid=alert_id: self._mark_resolved(aid),
                width=160, height=32,
            ).pack(side="left")

        else:
            ctk.CTkLabel(
                actions,
                text=f"✅  Resolved {(a.get('resolved_at') or '')[:10]}",
                font=(FONT_FAMILY, 10, "bold"),
                text_color=STATUS["green"],
            ).pack(side="left")

            self.secondary_button(
                actions, "👤 View student",
                command=lambda u=user_id: self.navigate("fac_deepdive",
                                                        user_id=u),
                width=150, height=32,
            ).pack(side="left", padx=(PAD_MD, 0))

    # =========================================================
    # ACTIONS
    # =========================================================

    def _send_hint(self, user_id: str, alert_id: str):
        try:
            facilitator_id = (self.user or {}).get("id", "fac1")
            self.db.log_intervention(
                facilitator_id, user_id, "hint",
                {"alert_id": alert_id, "message": "Facilitator sent a hint"})
            self.toast("Hint logged — student will see it.", "success")
        except Exception as e:
            self.toast(f"Could not log hint: {e}", "error")

    def _mark_resolved(self, alert_id: str):
        def on_confirm():
            try:
                self.db.resolve_alert(alert_id)
                self.toast("Alert marked resolved.", "success")
                self._refresh()
            except Exception as e:
                self.toast(f"Could not resolve: {e}", "error")

        self.confirm(
            "Mark alert as resolved?",
            "This will move the alert out of the active feed.",
            on_yes=on_confirm,
            yes_text="Mark resolved",
        )


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
            print(f"[alerts] → show_page('{key}')  args={kw}")

        def go_back(self):
            print("[alerts] back")

        def logout(self):
            print("[alerts] logout")

    root = ctk.CTk()
    W, H = 1400, 900
    root.geometry(f"{W}x{H}")
    root.configure(fg_color=COLORS["bg"])
    root.title(f"{APP_NAME} — alerts feed")

    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - W) // 2
    y = (sh - H) // 2
    root.geometry(f"{W}x{H}+{x}+{y}")

    app = _FakeApp()
    page = FacilitatorAlertsFeedPage(root, app)
    page.pack(fill="both", expand=True)
    root.mainloop()
    print("\n✅ pages/facilitator/alerts_feed.py OK")