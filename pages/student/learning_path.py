# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  pages/student/learning_path.py  ·  Adaptive learning path
# =============================================================

from __future__ import annotations

import os
import sys

# --- make project root importable ---
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import customtkinter as ctk

from config import (
    APP_NAME, COLORS, STATUS, ZONE_COLORS,
    SUBJECTS, SUBJECT_COLORS,
    FONTS, FONT_FAMILY,
    CARD_RADIUS, BUTTON_RADIUS, CHIP_RADIUS,
    PAD_SM, PAD_MD, PAD_LG, PAD_XL,
)
from pages.base_page import BasePage
from models.bkt import BKTTracker
from models.recommender import Recommender
from models.spaced_repetition import Scheduler


# =============================================================
# LEARNING PATH PAGE
# =============================================================

class StudentLearningPathPage(BasePage):

    def __init__(self, master, app):
        super().__init__(master, app)
        self.build_header("Learning Path",
                          "Personalized recommendations just for you")
        self.build_content(scrollable=True)
        self.build_footer()

        self._tracker = BKTTracker(self.db)
        self._recommender = Recommender(self.db, tracker=self._tracker)
        self._scheduler = Scheduler(self.db)

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

        # 1. Header stat strip
        self._render_header_stats(content, uid)

        # 2. Today's top pick
        self.section_title("Today's Path", parent=content)
        self._render_todays_pick(content, uid)

        # 3. Full ranked list
        self.section_title("Your Recommended Journey", parent=content)
        self._render_full_list(content, uid)

        # 4. Reviews due today (compact strip)
        self.section_title("Reviews Due", parent=content)
        self._render_due_reviews(content, uid)

    # =========================================================
    # HEADER STATS
    # =========================================================

    def _render_header_stats(self, parent, uid):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        try:
            overall = self._tracker.overall_mastery(uid)
        except Exception:
            overall = {"avg_mastery": 0, "mastered": 0,
                       "developing": 0, "weak": 0, "total_concepts": 0}

        try:
            stats = self._scheduler.stats(uid)
        except Exception:
            stats = {"total_tracked": 0, "due_now": 0, "due_this_week": 0}

        avg_pct = overall.get("avg_mastery", 0) * 100
        accent = STATUS["green"] if avg_pct >= 75 else \
                 (STATUS["amber"] if avg_pct >= 40 else STATUS["red"])

        self.stat_card(
            row, f"{avg_pct:.0f}%", "Average mastery",
            accent=accent, icon="🎯",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, overall.get("mastered", 0), "Concepts mastered",
            accent=STATUS["green"], icon="✅",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, overall.get("weak", 0), "Need work",
            accent=STATUS["red"], icon="⚠️",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, stats.get("due_now", 0), "Reviews due",
            accent=STATUS["amber"], icon="⏰",
        ).pack(side="left")

    # =========================================================
    # TODAY'S PICK
    # =========================================================

    def _render_todays_pick(self, parent, uid):
        try:
            rec = self._recommender.todays_path(uid)
        except Exception as e:
            ctk.CTkLabel(
                parent, text=f"Could not load recommendation: {e}",
                font=FONTS["small"],
                text_color=STATUS["red"]).pack()
            return

        if not rec:
            ctk.CTkLabel(
                parent, text="You're all caught up! Nothing recommended right now.",
                font=FONTS["body"],
                text_color=COLORS["text_muted"]).pack(pady=20)
            return

        card = self.card(parent)
        card.pack(fill="x", pady=(0, PAD_MD))

        # Gradient accent bar at top
        from theme import make_ctk_image, make_gradient_image
        topbar = ctk.CTkFrame(card, fg_color=COLORS["surface"],
                              height=6, corner_radius=0)
        topbar.pack(fill="x")
        grad = make_ctk_image(make_gradient_image(1000, 6, radius=0))
        ctk.CTkLabel(topbar, image=grad, text="", height=6).pack(fill="x")

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        # Left: big icon block
        icon_box = ctk.CTkFrame(
            body,
            width=110, height=110,
            fg_color=ZONE_COLORS.get(rec.mastery_label, COLORS["primary"])
                       if rec.mastery_label in ZONE_COLORS
                       else COLORS["primary"],
            corner_radius=18)
        icon_box.pack(side="left")
        icon_box.pack_propagate(False)

        ctk.CTkLabel(
            icon_box, text=rec.mastery_icon or "📘",
            font=(FONT_FAMILY, 48),
            text_color="#FFFFFF",
        ).place(relx=0.5, rely=0.5, anchor="center")

        # Middle: info
        mid = ctk.CTkFrame(body, fg_color="transparent")
        mid.pack(side="left", padx=(PAD_LG, 0), fill="both", expand=True)

        ctk.CTkLabel(
            mid, text=rec.concept_name,
            font=(FONT_FAMILY, 22, "bold"),
            text_color=COLORS["text"], anchor="w",
        ).pack(anchor="w")

        meta = f"{rec.subject}  ·  Difficulty {rec.difficulty}"
        ctk.CTkLabel(
            mid, text=meta,
            font=FONTS["small"],
            text_color=COLORS["text_muted"], anchor="w",
        ).pack(anchor="w", pady=(2, 8))

        # Mastery progress bar
        m_row = ctk.CTkFrame(mid, fg_color="transparent")
        m_row.pack(anchor="w", fill="x", pady=(0, 8))

        ctk.CTkLabel(
            m_row, text=f"Mastery: {rec.p_mastery*100:.0f}%",
            font=FONTS["small_bold"],
            text_color=COLORS["text"]).pack(side="left", padx=(0, 8))

        bar = ctk.CTkProgressBar(
            m_row, width=200, height=8,
            progress_color=ZONE_COLORS.get(rec.mastery_label,
                                           COLORS["primary"]),
            fg_color=COLORS["surface_alt"])
        bar.pack(side="left")
        bar.set(min(1.0, rec.p_mastery))

        # Reason
        ctk.CTkLabel(
            mid, text=f"💡 {rec.reason}",
            font=FONTS["small"],
            text_color=COLORS["text"], anchor="w",
            wraplength=560, justify="left",
        ).pack(anchor="w", pady=(6, 0))

        # Content items
        if rec.content:
            ctk.CTkLabel(
                mid, text="Content available:",
                font=FONTS["tiny"],
                text_color=COLORS["text_muted"], anchor="w",
            ).pack(anchor="w", pady=(10, 4))

            for item in rec.content[:3]:
                row = ctk.CTkFrame(mid, fg_color="transparent")
                row.pack(anchor="w", fill="x", pady=1)

                tag = f"  [{item['interest_tag']}]" if item.get("interest_tag") else ""
                ctk.CTkLabel(
                    row,
                    text=f"• {item['type'].title()}: {item['title']}{tag}",
                    font=FONTS["tiny"],
                    text_color=COLORS["text"], anchor="w",
                ).pack(anchor="w")

        # Right: CTA
        right = ctk.CTkFrame(body, fg_color="transparent")
        right.pack(side="right", padx=(PAD_MD, 0))

        self.primary_button(
            right, "▶  Start now",
            command=lambda c=rec.concept_id: self.navigate(
                "stu_learning_screen", concept_id=c),
            width=170, height=46,
        ).pack()

    # =========================================================
    # FULL LIST
    # =========================================================

    def _render_full_list(self, parent, uid):
        try:
            recs = self._recommender.next_best(uid, top_k=10)
        except Exception as e:
            ctk.CTkLabel(
                parent, text=f"Could not load recommendations: {e}",
                font=FONTS["small"],
                text_color=STATUS["red"]).pack()
            return

        if not recs:
            ctk.CTkLabel(
                parent, text="No recommendations available.",
                font=FONTS["body"],
                text_color=COLORS["text_muted"]).pack(pady=20)
            return

        for i, rec in enumerate(recs, start=1):
            self._render_rec_card(parent, rec, rank=i)

    def _render_rec_card(self, parent, rec, rank: int):
        card = self.card(parent)
        card.pack(fill="x", pady=4)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=PAD_LG, pady=PAD_MD)

        # Rank badge
        rank_badge = ctk.CTkFrame(
            inner,
            width=42, height=42,
            fg_color=COLORS["surface_alt"],
            corner_radius=12)
        rank_badge.pack(side="left")
        rank_badge.pack_propagate(False)
        ctk.CTkLabel(
            rank_badge, text=f"#{rank}",
            font=(FONT_FAMILY, 14, "bold"),
            text_color=COLORS["primary"],
        ).place(relx=0.5, rely=0.5, anchor="center")

        # Middle: info
        mid = ctk.CTkFrame(inner, fg_color="transparent")
        mid.pack(side="left", fill="x", expand=True, padx=(PAD_LG, 0))

        # Title row
        t_row = ctk.CTkFrame(mid, fg_color="transparent")
        t_row.pack(anchor="w", fill="x")

        ctk.CTkLabel(
            t_row, text=f"{rec.mastery_icon}  {rec.concept_name}",
            font=(FONT_FAMILY, 15, "bold"),
            text_color=COLORS["text"], anchor="w",
        ).pack(side="left")

        subj_color = SUBJECT_COLORS.get(rec.subject, COLORS["primary"])
        subj_chip = ctk.CTkFrame(
            t_row, fg_color=subj_color, corner_radius=CHIP_RADIUS)
        subj_chip.pack(side="left", padx=(10, 0))
        ctk.CTkLabel(
            subj_chip, text=f"  {rec.subject}  ",
            font=(FONT_FAMILY, 9, "bold"),
            text_color="#FFFFFF",
        ).pack(padx=2, pady=2)

        # Sub row
        sub_row = ctk.CTkFrame(mid, fg_color="transparent")
        sub_row.pack(anchor="w", fill="x", pady=(4, 0))

        ctk.CTkLabel(
            sub_row,
            text=f"Difficulty {rec.difficulty}  ·  "
                 f"Mastery {rec.p_mastery*100:.0f}%  ·  "
                 f"Score {rec.score:.2f}",
            font=FONTS["tiny"],
            text_color=COLORS["text_muted"], anchor="w",
        ).pack(side="left")

        # Reason line (compact)
        if rec.reason:
            ctk.CTkLabel(
                mid, text=rec.reason,
                font=FONTS["tiny"],
                text_color=COLORS["text_muted"], anchor="w",
                wraplength=700, justify="left",
            ).pack(anchor="w", pady=(4, 0))

        # Right: Start
        self.secondary_button(
            inner, "Start",
            command=lambda c=rec.concept_id: self.navigate(
                "stu_learning_screen", concept_id=c),
            width=90, height=36,
        ).pack(side="right")

    # =========================================================
    # DUE REVIEWS
    # =========================================================

    def _render_due_reviews(self, parent, uid):
        try:
            plan = self._scheduler.build_plan(uid, limit=5)
        except Exception:
            plan = []

        if not plan:
            ctk.CTkLabel(
                parent, text="Nothing due for review — great! ✨",
                font=FONTS["small"],
                text_color=COLORS["text_muted"]).pack(pady=10)
            return

        card = self.card(parent)
        card.pack(fill="x", pady=(0, PAD_MD))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        for p in plan:
            row = ctk.CTkFrame(inner, fg_color=COLORS["surface_alt"],
                               corner_radius=10)
            row.pack(fill="x", pady=3)

            # Color bar based on mastery
            pc = STATUS["red"] if p["p_mastery"] < 0.4 else \
                 (STATUS["amber"] if p["p_mastery"] < 0.75 else STATUS["green"])
            bar = ctk.CTkFrame(row, fg_color=pc, width=4, corner_radius=2)
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

            self.secondary_button(
                row, "Review",
                command=lambda c=p["concept_id"]: self.navigate(
                    "stu_learning_screen", concept_id=c),
                width=80, height=30,
            ).pack(side="right", padx=10)

    # =========================================================
    # HELPERS
    # =========================================================

    def _render_empty(self, msg):
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
                stu = self.db.get_all_students().iloc[0]
                self._user = stu.to_dict()
            except Exception as e:
                print(f"(no DB: {e})")
                self.db = None

        @property
        def current_user(self):
            return self._user

        def show_page(self, key, **kw):
            print(f"[learning] → show_page('{key}')  args={kw}")

        def go_back(self):
            print("[learning] back")

        def logout(self):
            print("[learning] logout")

    root = ctk.CTk()
    W, H = 1280, 900
    root.geometry(f"{W}x{H}")
    root.configure(fg_color=COLORS["bg"])
    root.title(f"{APP_NAME} — learning path preview")

    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - W) // 2
    y = (sh - H) // 2
    root.geometry(f"{W}x{H}+{x}+{y}")

    app = _FakeApp()
    page = StudentLearningPathPage(root, app)
    page.pack(fill="both", expand=True)
    root.mainloop()
    print("\n✅ pages/student/learning_path.py OK")