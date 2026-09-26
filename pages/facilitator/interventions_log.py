# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  pages/facilitator/interventions_log.py  ·  Interventions history
# =============================================================

from __future__ import annotations

import os
import sys

# --- make project root importable ---
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import json
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


INTERVENTION_META = {
    "hint":      ("💡", "Hint",            "#8B5CF6"),
    "nudge":     ("👋", "Nudge",           "#60A5FA"),
    "assign":    ("📝", "Assignment",      "#F59E0B"),
    "pair":      ("👥", "Peer pairing",    "#10B981"),
    "schedule":  ("📅", "Scheduled 1:1",   "#EC4899"),
    "message":   ("📩", "Message",         "#34D399"),
    "remedial":  ("🩺", "Remedial",        "#EF4444"),
    "badge":     ("🏅", "Badge awarded",   "#FBBF24"),
}


def _meta_for(itype: str):
    return INTERVENTION_META.get(_safe_str(itype).lower(),
                                 ("⚙️", _safe_str(itype).title() or "Action",
                                  COLORS["text_muted"]))


def _fmt_time(iso: str) -> str:
    if not iso:
        return "—"
    try:
        d = datetime.fromisoformat(iso)
        return d.strftime("%d %b %Y · %I:%M %p")
    except Exception:
        return iso[:16]


# =============================================================
# INTERVENTIONS LOG PAGE
# =============================================================

class FacilitatorInterventionsLogPage(BasePage):

    def __init__(self, master, app):
        super().__init__(master, app)

        self.build_header("Interventions Log",
                          "Every action you've taken for your students",
                          back=False)
        self.build_sidebar(self._build_nav_items())
        self.build_content(scrollable=True)
        self.build_footer()

        # State
        self._type_filter = "all"
        self._search_text = ""
        self._scope = "mine"     # "mine" | "all"
        self._list_container = None
        self._filter_btns = {}
        self._scope_btns = {}
        self._search_entry = None

        self.render()

    def _build_nav_items(self):
        items = _facilitator_nav()
        for it in items:
            if it["key"] == "fac_interventions":
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
        self._render_stats(content)

        # 2. Controls
        self.section_title("Search & Filter", parent=content)
        self._render_controls(content)

        # 3. List
        self.section_title("Recent Interventions", parent=content)
        self._list_container = ctk.CTkFrame(content, fg_color="transparent")
        self._list_container.pack(fill="x", pady=(0, PAD_MD))
        self._render_list()

    # =========================================================
    # LOAD
    # =========================================================

    def _load_data(self):
        fac_id = (self.user or {}).get("id", "fac1")

        # All interventions
        try:
            self._all = self.db.get_interventions()
        except Exception:
            self._all = pd.DataFrame()

        # Mine
        try:
            self._mine = self.db.get_interventions(facilitator_id=fac_id)
        except Exception:
            self._mine = pd.DataFrame()

    # =========================================================
    # STATS
    # =========================================================

    def _render_stats(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        mine = self._mine
        allv = self._all

        n_mine = 0 if mine is None else len(mine)
        n_all = 0 if allv is None else len(allv)

        # This week
        this_week = 0
        if mine is not None and not mine.empty:
            cutoff = datetime.now() - timedelta(days=7)
            for _, r in mine.iterrows():
                try:
                    d = datetime.fromisoformat(_safe_str(r.get("created_at")))
                    if d >= cutoff:
                        this_week += 1
                except Exception:
                    pass

        # Unique students touched
        unique_students = 0
        if mine is not None and not mine.empty:
            unique_students = mine["student_id"].nunique()

        # By type
        type_counts = {}
        if mine is not None and not mine.empty:
            for _, r in mine.iterrows():
                t = _safe_str(r.get("itype")).lower()
                type_counts[t] = type_counts.get(t, 0) + 1

        top_type = "—"
        if type_counts:
            top_type = max(type_counts, key=type_counts.get)

        self.stat_card(
            row, n_mine, "My interventions",
            accent=COLORS["primary"], icon="🛠️",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, n_all, "Team total",
            accent=COLORS["text_muted"], icon="👥",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, this_week, "This week",
            accent=STATUS["info"], icon="🗓️",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, unique_students, "Students reached",
            accent=STATUS["green"], icon="🎯",
        ).pack(side="left", padx=(0, PAD_MD))

        meta = _meta_for(top_type)
        self.stat_card(
            row, f"{meta[0]} {meta[1]}", "Most common",
            accent=meta[2], icon="📊",
        ).pack(side="left")

    # =========================================================
    # CONTROLS
    # =========================================================

    def _render_controls(self, parent):
        card = self.card(parent)
        card.pack(fill="x", pady=(0, PAD_MD))

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        # Row 1: Scope
        scope_row = ctk.CTkFrame(body, fg_color="transparent")
        scope_row.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            scope_row, text="Scope:",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_muted"]).pack(side="left", padx=(0, 8))

        for key, label in [("mine", "My interventions"),
                           ("all", "All facilitators")]:
            is_active = (self._scope == key)
            btn = ctk.CTkButton(
                scope_row, text=label, width=160, height=34,
                font=(FONT_FAMILY, 10),
                fg_color=COLORS["primary"] if is_active
                         else COLORS["surface_alt"],
                hover_color=COLORS["surface_hi"],
                text_color=COLORS["text"],
                corner_radius=BUTTON_RADIUS,
                command=lambda k=key: self._set_scope(k),
            )
            btn.pack(side="left", padx=(0, PAD_SM))
            self._scope_btns[key] = btn

        # Row 2: Search
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
            placeholder_text="Search by student name…")
        self._search_entry.pack(side="left")
        self._search_entry.bind("<KeyRelease>", self._on_search_change)

        self.secondary_button(
            search_row, "Clear",
            command=self._clear_search,
            width=90, height=36,
        ).pack(side="left", padx=(PAD_SM, 0))

        # Row 3: Type filter
        filter_row = ctk.CTkFrame(body, fg_color="transparent")
        filter_row.pack(fill="x")

        ctk.CTkLabel(
            filter_row, text="Type:",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_muted"]).pack(side="left", padx=(0, 8))

        filters = [("all", "All")] + [
            (k, f"{v[0]} {v[1]}") for k, v in INTERVENTION_META.items()
        ]
        for key, label in filters:
            is_active = (self._type_filter == key)
            btn = ctk.CTkButton(
                filter_row, text=label, width=120, height=32,
                font=(FONT_FAMILY, 9),
                fg_color=COLORS["primary"] if is_active
                         else COLORS["surface_alt"],
                hover_color=COLORS["surface_hi"],
                text_color=COLORS["text"],
                corner_radius=BUTTON_RADIUS,
                command=lambda k=key: self._set_type_filter(k),
            )
            btn.pack(side="left", padx=(0, 6), pady=2)
            self._filter_btns[key] = btn

    def _set_scope(self, key: str):
        self._scope = key
        for k, b in self._scope_btns.items():
            try:
                b.configure(fg_color=COLORS["primary"] if k == key
                            else COLORS["surface_alt"])
            except Exception:
                pass
        self._render_list()

    def _set_type_filter(self, key: str):
        self._type_filter = key
        for k, b in self._filter_btns.items():
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

        df = self._mine if self._scope == "mine" else self._all
        if df is None or df.empty:
            ctk.CTkLabel(
                self._list_container,
                text="No interventions logged yet.",
                font=FONTS["body"],
                text_color=COLORS["text_muted"]).pack(pady=30)
            return

        # Filter by type
        if self._type_filter != "all":
            df = df[df["itype"].astype(str).str.lower()
                    == self._type_filter]

        # Search
        if self._search_text:
            q = self._search_text
            if "student_name" in df.columns:
                df = df[df["student_name"].apply(
                    lambda x: q in _safe_str(x).lower())]

        if df.empty:
            ctk.CTkLabel(
                self._list_container,
                text="No interventions match your filters.",
                font=FONTS["body"],
                text_color=COLORS["text_muted"]).pack(pady=20)
            return

        # Sort by created_at desc
        try:
            df = df.sort_values("created_at", ascending=False)
        except Exception:
            pass

        # Count label
        ctk.CTkLabel(
            self._list_container,
            text=f"Showing {len(df)} interventions",
            font=(FONT_FAMILY, 9),
            text_color=COLORS["text_muted"],
        ).pack(anchor="w", pady=(0, PAD_SM))

        # Render cards (limit to 50 to avoid huge pages)
        for _, r in df.head(50).iterrows():
            self._render_intervention_card(r)

        if len(df) > 50:
            ctk.CTkLabel(
                self._list_container,
                text=f"... and {len(df) - 50} more",
                font=FONTS["small"],
                text_color=COLORS["text_muted"]).pack(pady=10)

    def _render_intervention_card(self, r):
        itype = _safe_str(r.get("itype")).lower()
        icon, label, color = _meta_for(itype)

        student_id = _safe_str(r.get("student_id"))
        student_name = _safe_str(r.get("student_name")) or "—"
        when = _fmt_time(_safe_str(r.get("created_at")))

        # Parse payload
        payload = None
        try:
            p = r.get("payload")
            if p:
                payload = json.loads(p) if isinstance(p, str) else p
        except Exception:
            payload = None

        card = ctk.CTkFrame(
            self._list_container,
            fg_color=COLORS["surface"],
            corner_radius=CARD_RADIUS,
            border_width=1,
            border_color=color)
        card.pack(fill="x", pady=4)

        # Left color bar
        bar = ctk.CTkFrame(card, fg_color=color, width=6, corner_radius=0)
        bar.pack(side="left", fill="y")

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(side="left", fill="x", expand=True,
                   padx=PAD_LG, pady=PAD_MD)

        # Head: type chip + student + time
        head = ctk.CTkFrame(inner, fg_color="transparent")
        head.pack(fill="x")

        type_chip = ctk.CTkFrame(head, fg_color=color,
                                 corner_radius=CHIP_RADIUS)
        type_chip.pack(side="left")
        ctk.CTkLabel(
            type_chip,
            text=f"  {icon}  {label}  ",
            font=(FONT_FAMILY, 10, "bold"),
            text_color="#FFFFFF").pack(padx=4, pady=3)

        ctk.CTkLabel(
            head, text=when,
            font=(FONT_FAMILY, 9),
            text_color=COLORS["text_muted"]).pack(side="right")

        # Student row
        student_row = ctk.CTkFrame(inner, fg_color="transparent")
        student_row.pack(fill="x", pady=(10, 0))

        try:
            avatar = load_avatar(
                user_id=student_id,
                name=student_name,
                size=36, shape="circle",
            )
            ctk.CTkLabel(student_row, image=avatar, text="").pack(
                side="left", padx=(0, 10))
        except Exception:
            pass

        info_box = ctk.CTkFrame(student_row, fg_color="transparent")
        info_box.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            info_box, text=student_name,
            font=(FONT_FAMILY, 12, "bold"),
            text_color=COLORS["text"], anchor="w",
        ).pack(anchor="w")

        # Payload details (if any)
        if payload and isinstance(payload, dict):
            details = []
            for k, v in payload.items():
                if k in ("alert_id",):
                    continue
                details.append(f"{k.replace('_', ' ')}: {v}")
            detail_text = "  ·  ".join(details)

            if detail_text:
                ctk.CTkLabel(
                    info_box, text=detail_text,
                    font=(FONT_FAMILY, 10),
                    text_color=COLORS["text_muted"], anchor="w",
                    wraplength=800, justify="left",
                ).pack(anchor="w", pady=(2, 0))

        # View student button
        self.secondary_button(
            student_row, "View",
            command=lambda u=student_id: self.navigate("fac_deepdive",
                                                       user_id=u),
            width=80, height=30,
        ).pack(side="right")


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
            print(f"[interventions] → show_page('{key}')  args={kw}")

        def go_back(self):
            print("[interventions] back")

        def logout(self):
            print("[interventions] logout")

    root = ctk.CTk()
    W, H = 1400, 900
    root.geometry(f"{W}x{H}")
    root.configure(fg_color=COLORS["bg"])
    root.title(f"{APP_NAME} — interventions log")

    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - W) // 2
    y = (sh - H) // 2
    root.geometry(f"{W}x{H}+{x}+{y}")

    app = _FakeApp()
    page = FacilitatorInterventionsLogPage(root, app)
    page.pack(fill="both", expand=True)
    root.mainloop()
    print("\n✅ pages/facilitator/interventions_log.py OK")