# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  pages/student/activities.py  ·  Student activities view
# =============================================================

from __future__ import annotations

import os
import sys

# --- make project root importable ---
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import customtkinter as ctk
import pandas as pd

from config import (
    APP_NAME, COLORS, STATUS,
    ACTIVITY_TYPES,
    FONTS, FONT_FAMILY,
    CARD_RADIUS, BUTTON_RADIUS, CHIP_RADIUS,
    PAD_SM, PAD_MD, PAD_LG, PAD_XL,
)
from pages.base_page import BasePage


# =============================================================
# HELPERS
# =============================================================

ACTIVITY_META = {a["id"]: a for a in ACTIVITY_TYPES}
ACTIVITY_COLORS = {a["id"]: a["color"] for a in ACTIVITY_TYPES}
ACTIVITY_ICONS  = {a["id"]: a["icon"] for a in ACTIVITY_TYPES}


def _color_for_pct(pct: float) -> str:
    if pct >= 80:
        return STATUS["green"]
    if pct >= 50:
        return STATUS["amber"]
    return STATUS["red"]


# =============================================================
# ACTIVITIES PAGE
# =============================================================

class StudentActivitiesPage(BasePage):

    def __init__(self, master, app, target_user_id: str = None):
        super().__init__(master, app)

        self.target_id = target_user_id or (self.user or {}).get("id")
        self.is_self = (self.target_id == (self.user or {}).get("id"))
        self.target = self.db.get_user(self.target_id) if self.target_id else None

        self.build_header(
            "My Activities" if self.is_self else f"{self.target.get('name', '')} — Activities",
            "Aptitude, brain teasers, quizzes, and more",
            back=not self.is_self,
        )
        self.build_content(scrollable=True)
        self.build_footer()

        # State
        self._filter_type = "All"
        self._grid_container = None
        self._filter_btns = {}

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

        # Load data
        try:
            self._my_acts = self.db.get_user_activities(uid)
        except Exception:
            self._my_acts = pd.DataFrame()

        try:
            self._all_acts = self.db.get_activities()
        except Exception:
            self._all_acts = pd.DataFrame()

        # 1. Top stats
        self._render_top_stats(content)

        # 2. Filter chips
        self.section_title("Filter by type", parent=content)
        self._render_filter_row(content)

        # 3. Completed activities grid
        self.section_title("Completed", parent=content)
        self._grid_container = ctk.CTkFrame(content, fg_color="transparent")
        self._grid_container.pack(fill="x", pady=(0, PAD_MD))
        self._render_completed_grid()

        # 4. Available / not-yet-done
        self.section_title("Available to try", parent=content)
        self._render_available(content)

    # =========================================================
    # TOP STATS
    # =========================================================

    def _render_top_stats(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        acts = self._my_acts
        total = len(acts)
        if total == 0:
            avg_pct = best_pct = 0
        else:
            avg_pct = acts["percentage"].mean() if "percentage" in acts else 0
            best_pct = acts["percentage"].max() if "percentage" in acts else 0

        # Counts per type
        types_done = set()
        if not acts.empty and "type" in acts.columns:
            types_done = set(acts["type"].dropna().tolist())

        self.stat_card(
            row, total, "Activities completed",
            accent=COLORS["primary"], icon="🎗️",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, f"{avg_pct:.0f}%" if total else "—", "Average score",
            accent=_color_for_pct(avg_pct) if total else COLORS["text_muted"],
            icon="📊",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, f"{best_pct:.0f}%" if total else "—", "Best score",
            accent=STATUS["gold"] if total else COLORS["text_muted"],
            icon="🏆",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, len(types_done), f"Of {len(ACTIVITY_TYPES)} types",
            accent=COLORS["primary"], icon="🎯",
        ).pack(side="left")

    # =========================================================
    # FILTER
    # =========================================================

    def _render_filter_row(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        options = ["All"] + [a["name"] for a in ACTIVITY_TYPES]
        for name in options:
            is_active = (self._filter_type == name)
            btn = ctk.CTkButton(
                row, text=name, width=110, height=34,
                font=FONTS["small_bold"],
                fg_color=COLORS["primary"] if is_active
                         else COLORS["surface_alt"],
                hover_color=COLORS["surface_hi"],
                text_color=COLORS["text"],
                corner_radius=BUTTON_RADIUS,
                command=lambda n=name: self._set_filter(n),
            )
            btn.pack(side="left", padx=(0, PAD_SM))
            self._filter_btns[name] = btn

    def _set_filter(self, name: str):
        self._filter_type = name
        for n, b in self._filter_btns.items():
            try:
                b.configure(
                    fg_color=COLORS["primary"] if n == name
                             else COLORS["surface_alt"])
            except Exception:
                pass
        self._render_completed_grid()

    # =========================================================
    # COMPLETED GRID
    # =========================================================

    def _render_completed_grid(self):
        for w in self._grid_container.winfo_children():
            w.destroy()

        acts = self._my_acts
        if acts is None or acts.empty:
            ctk.CTkLabel(
                self._grid_container,
                text="No activities logged yet. Try one below! 🚀",
                font=FONTS["body"],
                text_color=COLORS["text_muted"]).pack(pady=20)
            return

        # Filter
        if self._filter_type != "All":
            wanted_id = None
            for a in ACTIVITY_TYPES:
                if a["name"] == self._filter_type:
                    wanted_id = a["id"]
                    break
            if wanted_id and "type" in acts.columns:
                acts = acts[acts["type"] == wanted_id]

        if acts.empty:
            ctk.CTkLabel(
                self._grid_container,
                text="No activities match this filter.",
                font=FONTS["small"],
                text_color=COLORS["text_muted"]).pack(pady=20)
            return

        grid = ctk.CTkFrame(self._grid_container, fg_color="transparent")
        grid.pack(fill="x")

        per_row = 3
        for c in range(per_row):
            grid.grid_columnconfigure(c, weight=1, uniform="act")

        for i, (_, a) in enumerate(acts.iterrows()):
            r, col = divmod(i, per_row)
            self._render_activity_card(grid, a, row=r, col=col)

    def _render_activity_card(self, parent, act, row: int, col: int):
        atype = (act.get("type") or "quiz").lower()
        color = ACTIVITY_COLORS.get(atype, COLORS["primary"])
        icon = ACTIVITY_ICONS.get(atype, "🎗️")
        pct = float(act.get("percentage") or 0)
        pct_color = _color_for_pct(pct)

        card = ctk.CTkFrame(
            parent,
            fg_color=COLORS["surface"],
            corner_radius=CARD_RADIUS,
            border_width=1, border_color=COLORS["border_soft"],
            width=340, height=170)
        card.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")
        card.pack_propagate(False)

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="both", expand=True,
                  padx=PAD_LG, pady=PAD_MD)

        # Head row: icon + type
        head = ctk.CTkFrame(body, fg_color="transparent")
        head.pack(fill="x")

        ctk.CTkLabel(
            head, text=icon,
            font=(FONT_FAMILY, 22),
            text_color=color).pack(side="left")

        chip = ctk.CTkFrame(head, fg_color=color,
                            corner_radius=CHIP_RADIUS)
        chip.pack(side="right")
        ctk.CTkLabel(
            chip, text=f"  {atype.title()}  ",
            font=(FONT_FAMILY, 9, "bold"),
            text_color="#FFFFFF").pack(padx=4, pady=2)

        # Name
        ctk.CTkLabel(
            body, text=act.get("name", "Activity"),
            font=(FONT_FAMILY, 14, "bold"),
            text_color=COLORS["text"], anchor="w",
            wraplength=280, justify="left",
        ).pack(anchor="w", pady=(8, 4))

        # Score row
        score_row = ctk.CTkFrame(body, fg_color="transparent")
        score_row.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(
            score_row,
            text=f"{int(act.get('score', 0))}/{int(act.get('max_score', 100))}",
            font=(FONT_FAMILY, 12, "bold"),
            text_color=COLORS["text"]).pack(side="left")

        ctk.CTkLabel(
            score_row,
            text=f"{pct:.0f}%",
            font=(FONT_FAMILY, 16, "bold"),
            text_color=pct_color).pack(side="right")

        # Progress bar
        bar = ctk.CTkProgressBar(
            body, height=8,
            progress_color=pct_color,
            fg_color=COLORS["surface_alt"])
        bar.pack(fill="x", pady=(0, 6))
        bar.set(min(1.0, pct / 100.0))

        # Date
        when = (act.get("completed_at") or "")[:10]
        if when:
            ctk.CTkLabel(
                body, text=f"Completed {when}",
                font=(FONT_FAMILY, 9),
                text_color=COLORS["text_muted"], anchor="w",
            ).pack(anchor="w")

    # =========================================================
    # AVAILABLE
    # =========================================================

    def _render_available(self, parent):
        # Activities that exist but the student hasn't done yet
        done_names = set()
        if self._my_acts is not None and not self._my_acts.empty:
            done_names = set(self._my_acts["name"].astype(str).tolist())

        all_acts = self._all_acts
        if all_acts is None or all_acts.empty:
            ctk.CTkLabel(
                parent,
                text="No activities available right now.",
                font=FONTS["small"],
                text_color=COLORS["text_muted"]).pack(pady=10)
            return

        not_done = all_acts[~all_acts["name"].isin(done_names)]
        if not_done.empty:
            ctk.CTkLabel(
                parent,
                text="🎉 You've completed every available activity!",
                font=FONTS["body"],
                text_color=STATUS["green"]).pack(pady=12)
            return

        grid = ctk.CTkFrame(parent, fg_color="transparent")
        grid.pack(fill="x", pady=(0, PAD_MD))

        per_row = 3
        for c in range(per_row):
            grid.grid_columnconfigure(c, weight=1, uniform="avail")

        for i, (_, a) in enumerate(not_done.iterrows()):
            r, col = divmod(i, per_row)
            atype = (a.get("type") or "quiz").lower()
            color = ACTIVITY_COLORS.get(atype, COLORS["primary"])
            icon = ACTIVITY_ICONS.get(atype, "🎗️")

            card = ctk.CTkFrame(
                grid,
                fg_color=COLORS["surface"],
                corner_radius=CARD_RADIUS,
                border_width=1, border_color=COLORS["border_soft"],
                width=340, height=120)
            card.grid(row=r, column=col, padx=6, pady=6, sticky="nsew")
            card.pack_propagate(False)

            body = ctk.CTkFrame(card, fg_color="transparent")
            body.pack(fill="both", expand=True,
                      padx=PAD_LG, pady=PAD_MD)

            head = ctk.CTkFrame(body, fg_color="transparent")
            head.pack(fill="x")

            ctk.CTkLabel(
                head, text=icon,
                font=(FONT_FAMILY, 18),
                text_color=color).pack(side="left")

            ctk.CTkLabel(
                head, text=a.get("name", "Activity"),
                font=(FONT_FAMILY, 13, "bold"),
                text_color=COLORS["text"], anchor="w",
            ).pack(side="left", padx=(8, 0))

            meta_bits = [atype.title()]
            if a.get("subject"):
                meta_bits.append(a["subject"])
            meta_bits.append(f"Max {int(a.get('max_score', 100))}")
            ctk.CTkLabel(
                body, text="  ·  ".join(meta_bits),
                font=(FONT_FAMILY, 9),
                text_color=COLORS["text_muted"], anchor="w",
            ).pack(anchor="w", pady=(6, 4))

            self.secondary_button(
                body, "Coming soon", width=120, height=30,
            ).pack(anchor="w")

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
            print(f"[activities] → show_page('{key}')  args={kw}")

        def go_back(self):
            print("[activities] back")

        def logout(self):
            print("[activities] logout")

    root = ctk.CTk()
    W, H = 1280, 900
    root.geometry(f"{W}x{H}")
    root.configure(fg_color=COLORS["bg"])
    root.title(f"{APP_NAME} — activities preview")

    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - W) // 2
    y = (sh - H) // 2
    root.geometry(f"{W}x{H}+{x}+{y}")

    app = _FakeApp()
    page = StudentActivitiesPage(root, app)
    page.pack(fill="both", expand=True)
    root.mainloop()
    print("\n✅ pages/student/activities.py OK")