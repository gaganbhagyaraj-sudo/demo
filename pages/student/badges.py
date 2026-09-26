# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  pages/student/badges.py  ·  Badges showcase
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
    APP_NAME, COLORS, STATUS,
    FONTS, FONT_FAMILY,
    CARD_RADIUS, BUTTON_RADIUS, CHIP_RADIUS,
    PAD_SM, PAD_MD, PAD_LG, PAD_XL,
    BADGES,
)
from pages.base_page import BasePage
from theme import BadgeCard
from models.badges import BadgeEngine


# =============================================================
# BADGES PAGE
# =============================================================

class StudentBadgesPage(BasePage):

    def __init__(self, master, app, target_user_id: str = None):
        super().__init__(master, app)

        self.target_id = target_user_id or (self.user or {}).get("id")
        self.is_self = (self.target_id == (self.user or {}).get("id"))
        self.target = self.db.get_user(self.target_id) if self.target_id else None

        self.build_header(
            "My Badges" if self.is_self else f"{self.target.get('name', '')} — Badges",
            "Achievements you've unlocked on your journey",
            back=not self.is_self,
        )
        self.build_content(scrollable=True)
        self.build_footer()

        self._engine = BadgeEngine(self.db)
        self.render()

    # =========================================================
    # RENDER
    # =========================================================

    def render(self):
        if not self.target:
            self._render_empty("Student not found.")
            return

        uid = self.target["id"]
        content = self._content

        # Load
        try:
            progress = self._engine.progress_for_user(uid)
        except Exception:
            progress = []

        if not progress:
            self._render_empty("No badges configured.")
            return

        earned = [p for p in progress if p["earned"]]
        locked = [p for p in progress if not p["earned"]]

        # 1. Top summary
        self._render_summary(content, len(earned), len(progress))

        # 2. Earned section
        if earned:
            self.section_title(f"🏆  Earned  ({len(earned)})", parent=content)
            self._render_badge_grid(content, earned, earned=True)
        else:
            self.section_title("🏆  Earned", parent=content)
            ctk.CTkLabel(
                content,
                text="No badges earned yet. Complete activities, ace assessments, "
                     "and stay consistent to unlock your first badge! 🌱",
                font=FONTS["body"],
                text_color=COLORS["text_muted"],
                wraplength=900, justify="left",
            ).pack(anchor="w", pady=(0, PAD_MD))

        # 3. Locked section
        if locked:
            self.section_title(f"🔒  Locked  ({len(locked)})", parent=content)
            self._render_badge_grid(content, locked, earned=False)

        # 4. Stretch goals preview — what you'd earn next
        try:
            would_earn = self._engine.preview_user(uid)
        except Exception:
            would_earn = []

        if would_earn:
            self.section_title("🎯  Almost there", parent=content)
            self._render_almost(content, would_earn)

    # =========================================================
    # SUMMARY
    # =========================================================

    def _render_summary(self, parent, earned_count: int, total: int):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        pct = (earned_count / total * 100) if total else 0
        accent = STATUS["gold"] if pct >= 80 else \
                 (STATUS["green"] if pct >= 50 else COLORS["primary"])

        self.stat_card(
            row, f"{earned_count}/{total}", "Badges earned",
            accent=accent, icon="🏅",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, f"{pct:.0f}%", "Completion",
            accent=accent, icon="📊",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, total - earned_count, "Still to unlock",
            accent=COLORS["text_muted"], icon="🔒",
        ).pack(side="left", padx=(0, PAD_MD))

        # Progress bar as a wider card
        card = self.card(row)
        card.pack(side="left", fill="both", expand=True)

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=PAD_LG, pady=PAD_MD)

        ctk.CTkLabel(
            body, text="Your journey",
            font=(FONT_FAMILY, 12, "bold"),
            text_color=COLORS["text_muted"]).pack(anchor="w")

        bar = ctk.CTkProgressBar(
            body, height=12,
            progress_color=accent,
            fg_color=COLORS["surface_alt"])
        bar.pack(fill="x", pady=(6, 0))
        bar.set(min(1.0, pct / 100.0))

        ctk.CTkLabel(
            body,
            text=f"{earned_count} of {total} badges unlocked",
            font=(FONT_FAMILY, 10),
            text_color=COLORS["text"]).pack(anchor="w", pady=(6, 0))

    # =========================================================
    # BADGE GRID
    # =========================================================

    def _render_badge_grid(self, parent, items: list, earned: bool):
        grid = ctk.CTkFrame(parent, fg_color="transparent")
        grid.pack(fill="x", pady=(0, PAD_MD))

        per_row = 5
        for c in range(per_row):
            grid.grid_columnconfigure(c, weight=1, uniform="badge")

        for i, item in enumerate(items):
            b = item["badge"]
            r, col = divmod(i, per_row)

            # Card wrapper (for name + date below the circular badge)
            card = ctk.CTkFrame(
                grid,
                fg_color=COLORS["surface"],
                corner_radius=CARD_RADIUS,
                border_width=1, border_color=COLORS["border_soft"],
                width=200, height=180)
            card.grid(row=r, column=col, padx=6, pady=6, sticky="nsew")
            card.pack_propagate(False)

            body = ctk.CTkFrame(card, fg_color="transparent")
            body.pack(fill="both", expand=True,
                      padx=PAD_MD, pady=PAD_MD)

            # Circular badge (from theme)
            BadgeCard(
                body,
                icon=b["icon"],
                name="",  # we render the name ourselves below
                color=b.get("color") or STATUS["gold"],
                size=84,
                earned=earned,
                parent_bg=COLORS["surface"],
            ).pack()

            # Name
            ctk.CTkLabel(
                body, text=b["name"],
                font=(FONT_FAMILY, 11, "bold"),
                text_color=COLORS["text"] if earned
                           else COLORS["text_dim"],
                wraplength=170, justify="center",
            ).pack(pady=(8, 0))

            # Earned date OR lock hint
            if earned and item.get("earned_at"):
                when = item["earned_at"][:10]
                ctk.CTkLabel(
                    body, text=f"Unlocked {when}",
                    font=(FONT_FAMILY, 9),
                    text_color=STATUS["green"]).pack(pady=(2, 0))
            else:
                # Show unlock criteria in tiny text
                ctk.CTkLabel(
                    body, text=b["desc"],
                    font=(FONT_FAMILY, 8),
                    text_color=COLORS["text_muted"],
                    wraplength=170, justify="center",
                ).pack(pady=(2, 0))

            # Hover to show full description on earned badges
            if earned:
                def _enter(_, card=card, b=b):
                    try:
                        card.configure(border_color=b.get("color", STATUS["gold"]))
                    except Exception:
                        pass
                def _leave(_, card=card):
                    try:
                        card.configure(border_color=COLORS["border_soft"])
                    except Exception:
                        pass
                card.bind("<Enter>", _enter)
                card.bind("<Leave>", _leave)

    # =========================================================
    # ALMOST THERE
    # =========================================================

    def _render_almost(self, parent, would_earn: list):
        card = self.card(parent)
        card.pack(fill="x", pady=(0, PAD_MD))

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        ctk.CTkLabel(
            body,
            text="Keep going — you're about to unlock these!",
            font=FONTS["small"],
            text_color=COLORS["text_muted"],
        ).pack(anchor="w", pady=(0, 12))

        row = ctk.CTkFrame(body, fg_color="transparent")
        row.pack(fill="x")

        for b in would_earn:
            item = ctk.CTkFrame(
                row,
                fg_color=COLORS["surface_alt"],
                corner_radius=CHIP_RADIUS)
            item.pack(side="left", padx=(0, PAD_SM), pady=2)

            ctk.CTkLabel(
                item, text=f"  {b['icon']}  {b['name']}  ",
                font=(FONT_FAMILY, 10, "bold"),
                text_color=b.get("color", STATUS["gold"]),
            ).pack(padx=6, pady=4)

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
            print(f"[badges] → show_page('{key}')  args={kw}")

        def go_back(self):
            print("[badges] back")

        def logout(self):
            print("[badges] logout")

    root = ctk.CTk()
    W, H = 1280, 900
    root.geometry(f"{W}x{H}")
    root.configure(fg_color=COLORS["bg"])
    root.title(f"{APP_NAME} — badges preview")

    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - W) // 2
    y = (sh - H) // 2
    root.geometry(f"{W}x{H}+{x}+{y}")

    app = _FakeApp()
    page = StudentBadgesPage(root, app)
    page.pack(fill="both", expand=True)
    root.mainloop()
    print("\n✅ pages/student/badges.py OK")