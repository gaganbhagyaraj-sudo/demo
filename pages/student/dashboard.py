# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  pages/student/dashboard.py  ·  Student home
# =============================================================

from __future__ import annotations

import os
import sys

# --- make project root importable ---
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from datetime import date

import customtkinter as ctk

from config import (
    APP_NAME, COLORS, STATUS, ZONE_COLORS, ZONE_LABELS,
    FONTS, FONT_FAMILY,
    CARD_RADIUS, BUTTON_RADIUS, CHIP_RADIUS,
    PAD_SM, PAD_MD, PAD_LG, PAD_XL,
)
from pages.base_page import BasePage
from utils.avatars import load_avatar
from models.bkt import BKTTracker
from models.recommender import Recommender
from models.spaced_repetition import Scheduler
from models.badges import BadgeEngine


# =============================================================
# STUDENT DASHBOARD
# =============================================================

class StudentDashboardPage(BasePage):

    def __init__(self, master, app):
        super().__init__(master, app)
        self.build_header("Dashboard", "Your learning at a glance")
        self.build_content(scrollable=True)
        self.build_footer()

        # Models
        self._tracker = BKTTracker(self.db)
        self._recommender = Recommender(self.db, tracker=self._tracker)
        self._scheduler = Scheduler(self.db)
        self._badges = BadgeEngine(self.db)

        self.render()

    # =========================================================
    # RENDER
    # =========================================================

    def render(self):
        user = self.user or {}
        uid = user.get("id")

        if not uid:
            self._render_empty("Not signed in.")
            return

        content = self._content

        # ---------------------------------------------------
        # 1. HERO CARD — avatar, name, zone, KPIs
        # ---------------------------------------------------
        self._render_hero(content, user)

        # ---------------------------------------------------
        # 2. QUICK KPI ROW
        # ---------------------------------------------------
        self.section_title("Overview", parent=content)
        self._render_kpis(content, uid)

        # ---------------------------------------------------
        # 3. TODAY'S PATH
        # ---------------------------------------------------
        self.section_title("Today's Path", parent=content)
        self._render_todays_path(content, uid)

        # ---------------------------------------------------
        # 4. TWO COLUMN — Reviews + Badges
        # ---------------------------------------------------
        cols = ctk.CTkFrame(content, fg_color="transparent")
        cols.pack(fill="x", pady=(PAD_MD, 0))

        left = ctk.CTkFrame(cols, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=(0, PAD_MD))

        right = ctk.CTkFrame(cols, fg_color="transparent")
        right.pack(side="left", fill="both", expand=True)

        self.section_title("Upcoming Reviews", parent=left)
        self._render_reviews(left, uid)

        self.section_title("Recent Badges", parent=right)
        self._render_recent_badges(right, uid)

        # ---------------------------------------------------
        # 5. QUICK ACTIONS
        # ---------------------------------------------------
        self.section_title("Quick Actions", parent=content)
        self._render_actions(content)

    # =========================================================
    # HERO
    # =========================================================

    def _render_hero(self, parent, user):
        hero = self.card(parent)
        hero.pack(fill="x", pady=(0, PAD_MD))

        inner = ctk.CTkFrame(hero, fg_color="transparent")
        inner.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        # Avatar with zone ring
        zone = self._current_zone(user.get("id"))
        try:
            avatar = load_avatar(
                user_id=user.get("id", ""),
                name=user.get("name", ""),
                size=96,
                shape="circle",
                zone=zone,
                ring_width=6 if zone else 0,
            )
            ctk.CTkLabel(inner, image=avatar, text="").pack(side="left")
        except Exception:
            pass

        # Name + chips
        info = ctk.CTkFrame(inner, fg_color="transparent")
        info.pack(side="left", padx=(PAD_LG, 0), fill="both", expand=True)

        first_name = (user.get("name") or "").split()[0] or "there"
        ctk.CTkLabel(
            info, text=f"Hi, {first_name}! 👋",
            font=(FONT_FAMILY, 22, "bold"),
            text_color=COLORS["text"], anchor="w",
        ).pack(anchor="w")

        meta_parts = []
        if user.get("usn"):
            meta_parts.append(user["usn"])
        if user.get("grade"):
            meta_parts.append(user["grade"])
        if user.get("section"):
            meta_parts.append(f"Sec {user['section']}")
        ctk.CTkLabel(
            info, text="  ·  ".join(meta_parts) or "Student",
            font=FONTS["small"],
            text_color=COLORS["text_muted"], anchor="w",
        ).pack(anchor="w", pady=(2, 10))

        # Chips: zone + interests
        chips = ctk.CTkFrame(info, fg_color="transparent")
        chips.pack(anchor="w", fill="x")

        if zone:
            self.zone_chip(chips, zone).pack(side="left", padx=(0, 6))

        try:
            for tag in self.db.get_user_interests(user["id"])[:4]:
                self.chip(chips, tag).pack(side="left", padx=(0, 6))
        except Exception:
            pass

    # =========================================================
    # KPI ROW
    # =========================================================

    def _render_kpis(self, parent, uid):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        # Latest IA %
        latest_pct = "—"
        zone = "yellow"
        try:
            ms = self.db.get_marks_summary(uid)
            if not ms.empty:
                latest = ms.iloc[-1]
                latest_pct = f"{latest['percentage']:.1f}%"
                zone = latest["zone"]
        except Exception:
            pass

        # Attendance %
        att = 0.0
        try:
            att = self.db.attendance_percent(uid, days=45)
        except Exception:
            pass

        # Badges
        badges_count = 0
        try:
            badges_count = len(self.db.get_user_badges(uid))
        except Exception:
            pass

        # Mastery
        try:
            overall = self._tracker.overall_mastery(uid)
            mastered = overall.get("mastered", 0)
            total_concepts = overall.get("total_concepts", 0)
        except Exception:
            mastered, total_concepts = 0, 0

        self.stat_card(
            row, latest_pct, "Latest IA average",
            accent=ZONE_COLORS.get(zone, COLORS["primary"]),
            icon="📊",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, f"{att:.0f}%", "Attendance (45d)",
            accent=STATUS["green"] if att >= 85 else STATUS["amber"],
            icon="📅",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, badges_count, "Badges earned",
            accent=STATUS["gold"],
            icon="🏅",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, f"{mastered}/{total_concepts}", "Concepts mastered",
            accent=COLORS["primary"],
            icon="🎯",
        ).pack(side="left")

    # =========================================================
    # TODAY'S PATH
    # =========================================================

    def _render_todays_path(self, parent, uid):
        card = self.card(parent)
        card.pack(fill="x", pady=(0, PAD_MD))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        try:
            rec = self._recommender.todays_path(uid)
        except Exception as e:
            ctk.CTkLabel(inner, text=f"Could not load recommendation: {e}",
                         font=FONTS["small"],
                         text_color=STATUS["red"]).pack()
            return

        if not rec:
            ctk.CTkLabel(inner,
                         text="All caught up! Nothing recommended right now.",
                         font=FONTS["body"],
                         text_color=COLORS["text_muted"]).pack()
            return

        # Left: big icon
        icon = ctk.CTkFrame(inner, fg_color=COLORS["surface_alt"],
                            width=88, height=88, corner_radius=44)
        icon.pack(side="left")
        icon.pack_propagate(False)
        ctk.CTkLabel(
            icon, text=rec.mastery_icon or "📚",
            font=(FONT_FAMILY, 38),
            text_color=COLORS["text"],
        ).place(relx=0.5, rely=0.5, anchor="center")

        # Middle: name + reason + content list
        mid = ctk.CTkFrame(inner, fg_color="transparent")
        mid.pack(side="left", padx=(PAD_LG, 0), fill="both", expand=True)

        ctk.CTkLabel(
            mid, text=rec.concept_name,
            font=(FONT_FAMILY, 18, "bold"),
            text_color=COLORS["text"], anchor="w",
        ).pack(anchor="w")

        ctk.CTkLabel(
            mid,
            text=f"{rec.subject}  ·  Difficulty {rec.difficulty}  ·  "
                 f"Mastery {rec.p_mastery*100:.0f}%",
            font=FONTS["small"],
            text_color=COLORS["text_muted"], anchor="w",
        ).pack(anchor="w", pady=(2, 6))

        ctk.CTkLabel(
            mid, text=rec.reason,
            font=FONTS["small"],
            text_color=COLORS["text"], anchor="w",
            wraplength=520, justify="left",
        ).pack(anchor="w", pady=(0, 10))

        # First 2 content items
        for item in (rec.content or [])[:2]:
            row = ctk.CTkFrame(mid, fg_color="transparent")
            row.pack(anchor="w", pady=1)
            tag_txt = f"[{item['interest_tag']}]" if item.get("interest_tag") else ""
            ctk.CTkLabel(
                row,
                text=f"• {item['type'].title()}: {item['title']}  {tag_txt}",
                font=FONTS["tiny"],
                text_color=COLORS["text_muted"], anchor="w",
            ).pack(anchor="w")

        # Right: CTA
        right = ctk.CTkFrame(inner, fg_color="transparent")
        right.pack(side="right")

        self.primary_button(
            right,
            text="Start learning",
            command=lambda c=rec.concept_id: self.navigate(
                "stu_learning", concept_id=c),
            width=170, height=44,
        ).pack()

    # =========================================================
    # UPCOMING REVIEWS
    # =========================================================

    def _render_reviews(self, parent, uid):
        card = self.card(parent)
        card.pack(fill="both", expand=True)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True,
                   padx=PAD_LG, pady=PAD_LG)

        try:
            plan = self._scheduler.build_plan(uid, limit=5)
        except Exception:
            plan = []

        if not plan:
            ctk.CTkLabel(inner, text="No reviews due — nice! ✨",
                         font=FONTS["small"],
                         text_color=COLORS["text_muted"]).pack()
            return

        for p in plan:
            row = ctk.CTkFrame(inner, fg_color=COLORS["surface_alt"],
                               corner_radius=10)
            row.pack(fill="x", pady=3)

            # Color bar
            p_bar_color = STATUS["red"] if p["p_mastery"] < 0.4 \
                else (STATUS["amber"] if p["p_mastery"] < 0.75
                      else STATUS["green"])
            bar = ctk.CTkFrame(row, fg_color=p_bar_color,
                               width=4, corner_radius=2)
            bar.pack(side="left", fill="y", padx=(0, 10))

            body = ctk.CTkFrame(row, fg_color="transparent")
            body.pack(side="left", fill="x", expand=True,
                      padx=(0, 10), pady=8)

            ctk.CTkLabel(
                body, text=p["name"],
                font=FONTS["small_bold"],
                text_color=COLORS["text"], anchor="w",
            ).pack(anchor="w")

            sub = f"{p['subject']}  ·  mastery {p['p_mastery']*100:.0f}%"
            if p["days_overdue"] > 0:
                sub += f"  ·  {p['days_overdue']}d overdue"
            ctk.CTkLabel(
                body, text=sub,
                font=FONTS["tiny"],
                text_color=COLORS["text_muted"], anchor="w",
            ).pack(anchor="w")

            ctk.CTkLabel(
                row, text=f"⚡ {p['urgency']:.2f}",
                font=FONTS["tiny"],
                text_color=COLORS["text_muted"]).pack(side="right", padx=10)

    # =========================================================
    # RECENT BADGES
    # =========================================================

    def _render_recent_badges(self, parent, uid):
        card = self.card(parent)
        card.pack(fill="both", expand=True)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True,
                   padx=PAD_LG, pady=PAD_LG)

        try:
            earned = self.db.get_user_badges(uid)
        except Exception:
            earned = None

        if earned is None or earned.empty:
            ctk.CTkLabel(inner, text="No badges yet — keep going! 🚀",
                         font=FONTS["small"],
                         text_color=COLORS["text_muted"]).pack()
            return

        # Show top 4 most recent
        for _, b in earned.head(4).iterrows():
            row = ctk.CTkFrame(inner, fg_color=COLORS["surface_alt"],
                               corner_radius=10)
            row.pack(fill="x", pady=3)

            body = ctk.CTkFrame(row, fg_color="transparent")
            body.pack(fill="x", padx=12, pady=8)

            head = ctk.CTkFrame(body, fg_color="transparent")
            head.pack(fill="x")

            ctk.CTkLabel(
                head, text=f"{b['icon']}  {b['name']}",
                font=FONTS["small_bold"],
                text_color=b.get("color") or COLORS["text"],
                anchor="w",
            ).pack(side="left")

            when = (b["earned_at"] or "")[:10]
            ctk.CTkLabel(
                head, text=when,
                font=FONTS["tiny"],
                text_color=COLORS["text_muted"],
            ).pack(side="right")

        # "View all" link
        ctk.CTkButton(
            inner, text="View all badges →",
            font=FONTS["tiny"],
            fg_color="transparent", hover=False,
            text_color=COLORS["primary"],
            command=lambda: self.navigate("stu_badges"),
        ).pack(pady=(8, 0))

    # =========================================================
    # QUICK ACTIONS
    # =========================================================

    def _render_actions(self, parent):
        grid = ctk.CTkFrame(parent, fg_color="transparent")
        grid.pack(fill="x", pady=(0, PAD_LG))

        actions = [
            ("📊", "My Marks",        "stu_marks"),
            ("📅", "Attendance",      "stu_attendance"),
            ("📚", "Learning Path",   "stu_learning"),
            ("🎯", "Mastery Map",     "stu_mastery"),
            ("🏅", "My Badges",       "stu_badges"),
            ("📜", "Certificates",    "stu_certificates"),
            ("🎗️", "Activities",     "stu_activities"),
            ("🏆", "Leaderboard",     "stu_leaderboard"),
        ]

        per_row = 4
        for i, (icon, label, key) in enumerate(actions):
            r, c = divmod(i, per_row)
            tile = ctk.CTkFrame(
                grid,
                fg_color=COLORS["surface"],
                corner_radius=CARD_RADIUS,
                border_width=1, border_color=COLORS["border_soft"],
                width=180, height=110)
            tile.grid(row=r, column=c, padx=6, pady=6, sticky="nsew")
            tile.pack_propagate(False)

            for col in range(per_row):
                grid.grid_columnconfigure(col, weight=1)

            # Hover
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

            for w in (tile,):
                w.bind("<Enter>", _enter)
                w.bind("<Leave>", _leave)
                w.bind("<Button-1>", _click)

            # Inner widgets
            icon_lbl = ctk.CTkLabel(
                tile, text=icon, font=(FONT_FAMILY, 26),
                text_color=COLORS["primary"])
            icon_lbl.pack(pady=(18, 6))

            label_lbl = ctk.CTkLabel(
                tile, text=label, font=FONTS["small_bold"],
                text_color=COLORS["text"])
            label_lbl.pack()

            for w in (icon_lbl, label_lbl):
                w.bind("<Button-1>", _click)
                try:
                    w.configure(cursor="hand2")
                except Exception:
                    pass

            try:
                tile.configure(cursor="hand2")
            except Exception:
                pass

    # =========================================================
    # HELPERS
    # =========================================================

    def _current_zone(self, uid):
        try:
            ms = self.db.get_marks_summary(uid)
            if not ms.empty:
                return ms.iloc[-1]["zone"]
        except Exception:
            pass
        return None

    def _render_empty(self, msg: str):
        ctk.CTkLabel(
            self._content, text=msg,
            font=FONTS["h3"],
            text_color=COLORS["text_muted"]).pack(pady=60)


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
                # Sign in as first student for preview
                stu = self.db.get_all_students().iloc[0]
                self._user = stu.to_dict()
            except Exception as e:
                print(f"(no DB: {e})")
                self.db = None

        @property
        def current_user(self):
            return self._user

        def show_page(self, key, **kw):
            print(f"[dashboard] → show_page('{key}')  args={kw}")

        def go_back(self):
            print("[dashboard] back")

        def logout(self):
            print("[dashboard] logout")

        def set_user(self, user):
            self._user = user

    root = ctk.CTk()
    W, H = 1280, 860
    root.geometry(f"{W}x{H}")
    root.configure(fg_color=COLORS["bg"])
    root.title(f"{APP_NAME} — student dashboard preview")

    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - W) // 2
    y = (sh - H) // 2
    root.geometry(f"{W}x{H}+{x}+{y}")

    app = _FakeApp()
    page = StudentDashboardPage(root, app)
    page.pack(fill="both", expand=True)
    root.mainloop()
    print("\n✅ pages/student/dashboard.py OK")