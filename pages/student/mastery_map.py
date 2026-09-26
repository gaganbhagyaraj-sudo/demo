# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  pages/student/mastery_map.py  ·  Concept mastery visualizer
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
    SUBJECT_COLORS, SUBJECT_SHORT,
    FONTS, FONT_FAMILY,
    CARD_RADIUS, BUTTON_RADIUS, CHIP_RADIUS,
    PAD_SM, PAD_MD, PAD_LG, PAD_XL,
)
from pages.base_page import BasePage
from models.bkt import BKTTracker
from utils.charts import radar_chart, gauge_chart


# =============================================================
# HELPERS
# =============================================================

MASTERY_COLORS = {
    "weak":       ZONE_COLORS["red"],
    "developing": ZONE_COLORS["yellow"],
    "mastered":   ZONE_COLORS["green"],
}

MASTERY_ICONS = {
    "weak":       "🔴",
    "developing": "🟡",
    "mastered":   "🟢",
}


# =============================================================
# MASTERY MAP PAGE
# =============================================================

class StudentMasteryMapPage(BasePage):

    def __init__(self, master, app, target_user_id: str = None):
        super().__init__(master, app)

        self.target_id = target_user_id or (self.user or {}).get("id")
        self.is_self = (self.target_id == (self.user or {}).get("id"))
        self.target = self.db.get_user(self.target_id) if self.target_id else None

        self.build_header(
            "Mastery Map" if self.is_self else f"{self.target.get('name', '')} — Mastery",
            "Where you stand across every concept",
            back=not self.is_self,
        )
        self.build_content(scrollable=True)
        self.build_footer()

        self._tracker = BKTTracker(self.db)
        self._selected_cid = None

        self.render()

    # =========================================================
    # RENDER
    # =========================================================

    def render(self):
        if not self.target:
            self._render_empty("Student not found.")
            return

        uid = self.target["id"]

        try:
            self._df = self._tracker.summary(uid)
        except Exception:
            self._df = None

        if self._df is None or self._df.empty:
            self._render_empty("No concepts found in the system yet.")
            return

        content = self._content

        # 1. Top overview stats
        self._render_overview(content, uid)

        # 2. Legend
        self._render_legend(content)

        # 3. Concept grid (grouped by subject)
        self.section_title("Concept Map", parent=content)
        self._render_grid(content)

        # 4. Weakest concepts + next steps
        self.section_title("Focus Areas", parent=content)
        self._render_focus(content)

    # =========================================================
    # OVERVIEW
    # =========================================================

    def _render_overview(self, parent, uid):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        df = self._df
        total = len(df)
        mastered = (df["label"] == "mastered").sum()
        developing = (df["label"] == "developing").sum()
        weak = (df["label"] == "weak").sum()
        avg = df["p_mastery"].mean() * 100

        accent = STATUS["green"] if avg >= 75 else \
                 (STATUS["amber"] if avg >= 40 else STATUS["red"])

        self.stat_card(
            row, f"{avg:.0f}%", "Average mastery",
            accent=accent, icon="🎯",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, int(mastered), "🟢 Mastered",
            accent=STATUS["green"], icon="✅",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, int(developing), "🟡 Developing",
            accent=STATUS["amber"], icon="⚡",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, int(weak), "🔴 Weak",
            accent=STATUS["red"], icon="⚠️",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, total, "Total concepts",
            accent=COLORS["primary"], icon="📚",
        ).pack(side="left")

    # =========================================================
    # LEGEND
    # =========================================================

    def _render_legend(self, parent):
        card = self.card(parent)
        card.pack(fill="x", pady=(0, PAD_MD))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=PAD_LG, pady=PAD_MD)

        ctk.CTkLabel(
            inner, text="Legend:",
            font=(FONT_FAMILY, 10, "bold"),
            text_color=COLORS["text_muted"]).pack(side="left", padx=(0, 14))

        for label, color, icon in [
            ("Mastered (≥75%)", STATUS["green"], "🟢"),
            ("Developing (40–75%)", STATUS["amber"], "🟡"),
            ("Weak (<40%)", STATUS["red"], "🔴"),
        ]:
            chip = ctk.CTkFrame(inner, fg_color="transparent")
            chip.pack(side="left", padx=(0, 20))
            dot = ctk.CTkFrame(chip, fg_color=color,
                               width=12, height=12, corner_radius=6)
            dot.pack(side="left", padx=(0, 6))
            dot.pack_propagate(False)
            ctk.CTkLabel(
                chip, text=label,
                font=(FONT_FAMILY, 10),
                text_color=COLORS["text_muted"]).pack(side="left")

    # =========================================================
    # CONCEPT GRID
    # =========================================================

    def _render_grid(self, parent):
        df = self._df

        # Group by subject
        for subject in df["subject"].unique():
            sub = df[df["subject"] == subject].sort_values("difficulty")

            self.section_title(f"{subject}", parent=parent)

            grid = ctk.CTkFrame(parent, fg_color="transparent")
            grid.pack(fill="x", pady=(0, PAD_MD))

            per_row = 4
            for col in range(per_row):
                grid.grid_columnconfigure(col, weight=1, uniform="concept")

            for i, (_, c) in enumerate(sub.iterrows()):
                r, col = divmod(i, per_row)
                self._render_concept_tile(grid, c, row=r, col=col)

    def _render_concept_tile(self, parent, concept, row: int, col: int):
        label = concept["label"]
        color = MASTERY_COLORS.get(label, COLORS["surface_alt"])
        icon = MASTERY_ICONS.get(label, "•")
        p = float(concept["p_mastery"])
        cid = concept["concept_id"]

        tile = ctk.CTkFrame(
            parent,
            fg_color=COLORS["surface"],
            corner_radius=CARD_RADIUS,
            border_width=2,
            border_color=color,
            width=220, height=120)
        tile.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")
        tile.pack_propagate(False)

        # Top: icon + mastery %
        top = ctk.CTkFrame(tile, fg_color="transparent")
        top.pack(fill="x", padx=12, pady=(10, 0))

        ctk.CTkLabel(
            top, text=icon,
            font=(FONT_FAMILY, 16),
            text_color=color).pack(side="left")

        ctk.CTkLabel(
            top, text=f"{p*100:.0f}%",
            font=(FONT_FAMILY, 14, "bold"),
            text_color=color).pack(side="right")

        # Name
        ctk.CTkLabel(
            tile, text=concept["name"],
            font=(FONT_FAMILY, 12, "bold"),
            text_color=COLORS["text"],
            anchor="w",
            wraplength=200, justify="left",
        ).pack(anchor="w", padx=12, pady=(4, 0))

        # Difficulty + attempts line
        sub = f"Diff {int(concept['difficulty'])}  ·  " \
              f"{int(concept['attempts'])} attempts"
        ctk.CTkLabel(
            tile, text=sub,
            font=(FONT_FAMILY, 9),
            text_color=COLORS["text_muted"],
            anchor="w",
        ).pack(anchor="w", padx=12)

        # Progress bar
        bar = ctk.CTkProgressBar(
            tile, height=6,
            progress_color=color,
            fg_color=COLORS["surface_alt"])
        bar.pack(fill="x", padx=12, pady=(8, 0))
        bar.set(min(1.0, p))

        # Hover + click
        def _enter(_, t=tile, c=color):
            try:
                t.configure(fg_color=COLORS["surface_alt"])
            except Exception:
                pass

        def _leave(_, t=tile):
            try:
                t.configure(fg_color=COLORS["surface"])
            except Exception:
                pass

        def _click(_, cid=cid):
            self._show_concept_details(cid)

        for w in (tile, top):
            w.bind("<Enter>", _enter)
            w.bind("<Leave>", _leave)
            w.bind("<Button-1>", _click)
            try:
                w.configure(cursor="hand2")
            except Exception:
                pass

    # =========================================================
    # CONCEPT DETAILS (modal-like)
    # =========================================================

    def _show_concept_details(self, concept_id: str):
        row = self._df[self._df["concept_id"] == concept_id]
        if row.empty:
            return
        c = row.iloc[0]

        top = ctk.CTkToplevel(self.winfo_toplevel())
        top.title(c["name"])
        top.configure(fg_color=COLORS["bg"])
        top.geometry("480x420")
        top.transient(self.winfo_toplevel())
        try:
            top.grab_set()
        except Exception:
            pass

        # Center
        try:
            top.update_idletasks()
            px = self.winfo_toplevel().winfo_rootx()
            py = self.winfo_toplevel().winfo_rooty()
            pw = self.winfo_toplevel().winfo_width()
            ph = self.winfo_toplevel().winfo_height()
            top.geometry(f"480x420+{px + (pw - 480)//2}+{py + (ph - 420)//2}")
        except Exception:
            pass

        # Accent bar
        bar = ctk.CTkFrame(top, height=6, fg_color=MASTERY_COLORS.get(
            c["label"], COLORS["primary"]), corner_radius=0)
        bar.pack(fill="x")

        body = ctk.CTkFrame(top, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=PAD_LG, pady=PAD_LG)

        ctk.CTkLabel(
            body, text=f"{MASTERY_ICONS.get(c['label'], '•')}  {c['name']}",
            font=(FONT_FAMILY, 20, "bold"),
            text_color=COLORS["text"]).pack(anchor="w")

        ctk.CTkLabel(
            body, text=f"{c['subject']}  ·  Difficulty {int(c['difficulty'])}",
            font=FONTS["small"],
            text_color=COLORS["text_muted"]).pack(anchor="w", pady=(2, 14))

        # Mastery bar
        ctk.CTkLabel(
            body, text=f"Mastery: {c['p_mastery']*100:.1f}%",
            font=(FONT_FAMILY, 13, "bold"),
            text_color=MASTERY_COLORS.get(c["label"], COLORS["text"])
        ).pack(anchor="w")

        bar2 = ctk.CTkProgressBar(
            body, height=10,
            progress_color=MASTERY_COLORS.get(c["label"], COLORS["primary"]),
            fg_color=COLORS["surface_alt"])
        bar2.pack(fill="x", pady=(4, 14))
        bar2.set(min(1.0, float(c["p_mastery"])))

        # Info rows
        self._kv(body, "Attempts", str(int(c["attempts"])))
        self._kv(body, "Label", c["label"].title())
        self._kv(body, "Last practiced",
                 (c.get("last_practiced") or "—")[:10])
        self._kv(body, "Next review",
                 (c.get("next_review_at") or "—")[:10])

        # Prerequisites
        try:
            pre = self.db.query("""
                SELECT c2.name AS name, c2.id AS id
                FROM prerequisites p
                JOIN concepts c2 ON c2.id = p.prereq_id
                WHERE p.concept_id=?
            """, (concept_id,))
            if not pre.empty:
                ctk.CTkLabel(
                    body, text="Prerequisites:",
                    font=FONTS["small_bold"],
                    text_color=COLORS["text_muted"]).pack(
                    anchor="w", pady=(12, 2))
                for _, r in pre.iterrows():
                    ctk.CTkLabel(
                        body, text=f"• {r['name']}",
                        font=FONTS["small"],
                        text_color=COLORS["text"]).pack(anchor="w")
        except Exception:
            pass

        # Buttons
        btns = ctk.CTkFrame(body, fg_color="transparent")
        btns.pack(side="bottom", fill="x", pady=(PAD_MD, 0))

        ctk.CTkButton(
            btns, text="Close", width=110, height=38,
            font=FONTS["small_bold"],
            fg_color=COLORS["surface_alt"],
            hover_color=COLORS["surface_hi"],
            text_color=COLORS["text"],
            corner_radius=BUTTON_RADIUS,
            command=top.destroy).pack(side="right")

        ctk.CTkButton(
            btns, text="Practice", width=130, height=38,
            font=FONTS["small_bold"],
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            text_color=COLORS["text"],
            corner_radius=BUTTON_RADIUS,
            command=lambda cid=concept_id: (
                top.destroy(),
                self.navigate("stu_learning_screen", concept_id=cid))
        ).pack(side="right", padx=(0, 8))

    def _kv(self, parent, key: str, value: str):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=2)
        ctk.CTkLabel(
            row, text=key, width=140, anchor="w",
            font=FONTS["small"],
            text_color=COLORS["text_muted"]).pack(side="left")
        ctk.CTkLabel(
            row, text=value, anchor="w",
            font=FONTS["small_bold"],
            text_color=COLORS["text"]).pack(side="left")

    # =========================================================
    # FOCUS AREAS
    # =========================================================

    def _render_focus(self, parent):
        df = self._df.sort_values("p_mastery")

        cols = ctk.CTkFrame(parent, fg_color="transparent")
        cols.pack(fill="x", pady=(0, PAD_MD))

        # Weak concepts list
        left = ctk.CTkFrame(cols, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=(0, PAD_MD))

        card = self.card(left)
        card.pack(fill="both", expand=True)

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="both", expand=True,
                  padx=PAD_LG, pady=PAD_LG)

        ctk.CTkLabel(
            body, text="🩺 Weakest Concepts",
            font=(FONT_FAMILY, 13, "bold"),
            text_color=COLORS["text"]).pack(anchor="w", pady=(0, 10))

        weakest = df.head(5)
        for _, c in weakest.iterrows():
            row = ctk.CTkFrame(body, fg_color=COLORS["surface_alt"],
                               corner_radius=8)
            row.pack(fill="x", pady=3)

            color = MASTERY_COLORS.get(c["label"], COLORS["primary"])
            bar = ctk.CTkFrame(row, fg_color=color, width=4, corner_radius=2)
            bar.pack(side="left", fill="y", padx=(0, 10))

            inner = ctk.CTkFrame(row, fg_color="transparent")
            inner.pack(side="left", fill="x", expand=True,
                       padx=(0, 10), pady=8)

            ctk.CTkLabel(
                inner, text=c["name"],
                font=FONTS["small_bold"],
                text_color=COLORS["text"], anchor="w").pack(anchor="w")

            ctk.CTkLabel(
                inner, text=f"{c['subject']}  ·  mastery "
                            f"{c['p_mastery']*100:.0f}%",
                font=FONTS["tiny"],
                text_color=COLORS["text_muted"], anchor="w").pack(anchor="w")

            ctk.CTkButton(
                row, text="Practice", width=80, height=30,
                font=(FONT_FAMILY, 10),
                fg_color=COLORS["primary"],
                hover_color=COLORS["primary_hover"],
                text_color=COLORS["text"],
                corner_radius=8,
                command=lambda cid=c["concept_id"]: self.navigate(
                    "stu_learning_screen", concept_id=cid),
            ).pack(side="right", padx=10)

        # Right: gauge of overall mastery
        right = ctk.CTkFrame(cols, fg_color="transparent")
        right.pack(side="left", fill="both", expand=False)

        gauge_card = self.card(right, width=300)
        gauge_card.pack_propagate(False)
        gauge_card.pack(fill="both", expand=True)

        try:
            avg = float(df["p_mastery"].mean() * 100)
            fig = gauge_chart(
                avg, label="Overall mastery",
                color=STATUS["green"] if avg >= 75
                      else (STATUS["amber"] if avg >= 40 else STATUS["red"]),
                animate=False, figsize=(3.4, 3.4))
            self.chart_frame(gauge_card, fig, height=280).pack(
                fill="both", expand=True, padx=8, pady=8)
        except Exception as e:
            ctk.CTkLabel(
                gauge_card, text=f"(gauge unavailable: {e})",
                font=FONTS["tiny"],
                text_color=COLORS["text_muted"]).pack(pady=20)

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
            print(f"[mastery] → show_page('{key}')  args={kw}")

        def go_back(self):
            print("[mastery] back")

        def logout(self):
            print("[mastery] logout")

    root = ctk.CTk()
    W, H = 1280, 900
    root.geometry(f"{W}x{H}")
    root.configure(fg_color=COLORS["bg"])
    root.title(f"{APP_NAME} — mastery map preview")

    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - W) // 2
    y = (sh - H) // 2
    root.geometry(f"{W}x{H}+{x}+{y}")

    app = _FakeApp()
    page = StudentMasteryMapPage(root, app)
    page.pack(fill="both", expand=True)
    root.mainloop()
    print("\n✅ pages/student/mastery_map.py OK")