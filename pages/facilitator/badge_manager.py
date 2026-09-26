# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  pages/facilitator/badge_manager.py  ·  Badge management
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
    FONTS, FONT_FAMILY,
    CARD_RADIUS, BUTTON_RADIUS, CHIP_RADIUS,
    PAD_SM, PAD_MD, PAD_LG, PAD_XL,
    BADGES,
)
from pages.base_page import BasePage
from utils.avatars import load_avatar
from models.badges import BadgeEngine


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


# =============================================================
# BADGE MANAGER PAGE
# =============================================================

class FacilitatorBadgeManagerPage(BasePage):

    def __init__(self, master, app):
        super().__init__(master, app)

        self.build_header("Badge Manager",
                          "Award, revoke, and review badges", back=False)
        self.build_sidebar(self._build_nav_items())
        self.build_content(scrollable=True)
        self.build_footer()

        self._engine = BadgeEngine(self.db)

        # Matrix container (rebuilt on refresh)
        self._matrix_container = None

        # Award form state
        self._award_student = None
        self._award_badge = None

        self.render()

    def _build_nav_items(self):
        items = _facilitator_nav()
        for it in items:
            if it["key"] == "fac_badges":
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

        # 2. Actions row (auto-award + refresh)
        self._render_actions(content)

        # 3. Manual award form
        self.section_title("Award a Badge Manually", parent=content)
        self._render_award_form(content)

        # 4. Badge popularity
        self.section_title("Badge Popularity", parent=content)
        self._render_popularity(content)

        # 5. Full matrix
        self.section_title("Student × Badge Matrix", parent=content)
        self._matrix_container = ctk.CTkFrame(content, fg_color="transparent")
        self._matrix_container.pack(fill="x", pady=(0, PAD_MD))
        self._render_matrix()

    # =========================================================
    # LOAD
    # =========================================================

    def _load_data(self):
        # All students
        try:
            self._students = self.db.get_all_students()
        except Exception:
            self._students = pd.DataFrame()

        # All badges earned by anyone
        try:
            self._all_awarded = self.db.query("""
                SELECT ub.*, u.name AS student_name, u.usn,
                       b.name AS badge_name, b.icon, b.color
                FROM user_badges ub
                JOIN users u ON u.id = ub.user_id
                JOIN badges b ON b.id = ub.badge_id
                ORDER BY ub.earned_at DESC
            """)
        except Exception:
            self._all_awarded = pd.DataFrame()

        # Lookup dict: {user_id: set(badge_id)}
        self._earned_lookup = {}
        if self._all_awarded is not None and not self._all_awarded.empty:
            for _, r in self._all_awarded.iterrows():
                uid = _safe_str(r.get("user_id"))
                bid = _safe_str(r.get("badge_id"))
                self._earned_lookup.setdefault(uid, set()).add(bid)

    # =========================================================
    # STATS
    # =========================================================

    def _render_stats(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        students = self._students
        all_awarded = self._all_awarded

        n_students = 0 if students is None else len(students)
        n_awarded = 0 if all_awarded is None else len(all_awarded)

        # Students with at least 1 badge
        with_badges = len(self._earned_lookup)
        coverage = (with_badges / n_students * 100) if n_students else 0

        # Top earner
        top_name = "—"
        top_count = 0
        if self._earned_lookup:
            for uid, badges in self._earned_lookup.items():
                if len(badges) > top_count:
                    top_count = len(badges)
                    try:
                        u = self.db.get_user(uid)
                        top_name = (u or {}).get("name", "—")
                    except Exception:
                        top_name = "—"

        # Unique badges awarded (across all students)
        unique_awarded = len(set(
            b for bs in self._earned_lookup.values() for b in bs))

        self.stat_card(
            row, n_awarded, "Total badge awards",
            accent=STATUS["gold"], icon="🏅",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, f"{with_badges}/{n_students}",
            f"Students with badges ({coverage:.0f}%)",
            accent=STATUS["green"], icon="👥",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, f"{unique_awarded}/{len(BADGES)}",
            "Unique badges used",
            accent=COLORS["primary"], icon="🎯",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, top_count, f"Top: {top_name[:18]}",
            accent=STATUS["gold"], icon="🏆",
        ).pack(side="left")

    # =========================================================
    # ACTIONS
    # =========================================================

    def _render_actions(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        self.primary_button(
            row, "⚡  Auto-award all eligible",
            command=self._auto_award,
            width=240, height=42,
        ).pack(side="left", padx=(0, PAD_MD))

        self.secondary_button(
            row, "🔄  Refresh",
            command=self._reload,
            width=120, height=42,
        ).pack(side="left")

    def _auto_award(self):
        def on_confirm():
            try:
                results = self._engine.evaluate_all_students()
                total = sum(len(v) for v in results.values())
                if total > 0:
                    self.toast(
                        f"Awarded {total} badge(s) to "
                        f"{len(results)} student(s).", "success")
                else:
                    self.toast("No new badges to award.", "info")
                self._reload()
            except Exception as e:
                self.toast(f"Auto-award failed: {e}", "error")

        self.confirm(
            "Run auto-award?",
            "This will evaluate every student against all badge rules "
            "and award any that qualify. Safe to run repeatedly.",
            on_yes=on_confirm,
            yes_text="Run now",
        )

    # =========================================================
    # AWARD FORM
    # =========================================================

    def _render_award_form(self, parent):
        card = self.card(parent)
        card.pack(fill="x", pady=(0, PAD_MD))

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        # Student selector
        s_row = ctk.CTkFrame(body, fg_color="transparent")
        s_row.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            s_row, text="Student:",
            width=120, anchor="w",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_muted"]).pack(side="left")

        # Build student list
        student_names = []
        student_lookup = {}
        if self._students is not None and not self._students.empty:
            for _, s in self._students.iterrows():
                label = f"{_safe_str(s.get('name'))} ({_safe_str(s.get('usn'))})"
                student_names.append(label)
                student_lookup[label] = _safe_str(s.get("id"))

        if not student_names:
            ctk.CTkLabel(
                s_row, text="No students available.",
                font=FONTS["small"],
                text_color=STATUS["red"]).pack(side="left")
        else:
            menu = ctk.CTkOptionMenu(
                s_row, values=student_names, width=380, height=38,
                font=FONTS["small"],
                fg_color=COLORS["surface_alt"],
                button_color=COLORS["primary"],
                button_hover_color=COLORS["primary_hover"],
                text_color=COLORS["text"],
                dropdown_fg_color=COLORS["surface_alt"],
                dropdown_text_color=COLORS["text"],
                corner_radius=10)
            menu.set(student_names[0])
            menu.pack(side="left")

            self._student_menu = menu
            self._student_lookup = student_lookup

        # Badge selector
        b_row = ctk.CTkFrame(body, fg_color="transparent")
        b_row.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            b_row, text="Badge:",
            width=120, anchor="w",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_muted"]).pack(side="left")

        badge_labels = [f"{b['icon']}  {b['name']}" for b in BADGES]
        badge_lookup = {f"{b['icon']}  {b['name']}": b["id"] for b in BADGES}

        menu2 = ctk.CTkOptionMenu(
            b_row, values=badge_labels, width=380, height=38,
            font=FONTS["small"],
            fg_color=COLORS["surface_alt"],
            button_color=COLORS["primary"],
            button_hover_color=COLORS["primary_hover"],
            text_color=COLORS["text"],
            dropdown_fg_color=COLORS["surface_alt"],
            dropdown_text_color=COLORS["text"],
            corner_radius=10)
        menu2.set(badge_labels[0])
        menu2.pack(side="left")

        self._badge_menu = menu2
        self._badge_lookup = badge_lookup

        # Optional note
        n_row = ctk.CTkFrame(body, fg_color="transparent")
        n_row.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            n_row, text="Note (optional):",
            width=120, anchor="w",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_muted"]).pack(side="left")

        self._note_entry = ctk.CTkEntry(
            n_row, width=380, height=38,
            font=FONTS["small"],
            fg_color=COLORS["surface_alt"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            corner_radius=10,
            placeholder_text="Reason for awarding…")
        self._note_entry.pack(side="left")

        # Submit
        btn_row = ctk.CTkFrame(body, fg_color="transparent")
        btn_row.pack(fill="x")

        self.primary_button(
            btn_row, "🏅  Award Badge",
            command=self._award_manual,
            width=180, height=42,
        ).pack(side="left")

    def _award_manual(self):
        try:
            student_label = self._student_menu.get()
            badge_label = self._badge_menu.get()
        except Exception:
            self.toast("Please select student and badge.", "warning")
            return

        student_id = self._student_lookup.get(student_label)
        badge_id = self._badge_lookup.get(badge_label)

        if not student_id or not badge_id:
            self.toast("Invalid selection.", "error")
            return

        note = ""
        try:
            note = (self._note_entry.get() or "").strip()
        except Exception:
            pass

        # Confirm
        def on_confirm():
            try:
                self.db.award_badge(student_id, badge_id, note or None)
                self.toast("Badge awarded ✓", "success")
                self._reload()
            except Exception as e:
                self.toast(f"Award failed: {e}", "error")

        self.confirm(
            "Award this badge?",
            f"Award {badge_label} to {student_label}?",
            on_yes=on_confirm,
            yes_text="Award",
        )

    # =========================================================
    # POPULARITY
    # =========================================================

    def _render_popularity(self, parent):
        card = self.card(parent)
        card.pack(fill="x", pady=(0, PAD_MD))

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        # Count per badge
        counts = {}
        for bs in self._earned_lookup.values():
            for b in bs:
                counts[b] = counts.get(b, 0) + 1

        if not counts:
            ctk.CTkLabel(
                body, text="No badges awarded yet.",
                font=FONTS["body"],
                text_color=COLORS["text_muted"]).pack(pady=10)
            return

        # Sort by count desc
        sorted_badges = sorted(counts.items(), key=lambda x: -x[1])
        max_count = sorted_badges[0][1]

        grid = ctk.CTkFrame(body, fg_color="transparent")
        grid.pack(fill="x")

        for i, (bid, count) in enumerate(sorted_badges):
            meta = next((b for b in BADGES if b["id"] == bid), None)
            if not meta:
                continue

            row = ctk.CTkFrame(grid, fg_color="transparent")
            row.pack(fill="x", pady=3)

            ctk.CTkLabel(
                row,
                text=f"{meta['icon']}  {meta['name']}",
                width=240, anchor="w",
                font=(FONT_FAMILY, 11, "bold"),
                text_color=meta.get("color") or COLORS["text"],
            ).pack(side="left")

            # Progress bar
            bar = ctk.CTkProgressBar(
                row,
                width=max(80, int((count / max_count) * 300)),
                height=14,
                progress_color=meta.get("color") or COLORS["primary"],
                fg_color=COLORS["surface_alt"],
                corner_radius=7)
            bar.pack(side="left", padx=(0, 10))
            bar.set(1.0)

            ctk.CTkLabel(
                row, text=f"{count}",
                font=(FONT_FAMILY, 11, "bold"),
                text_color=COLORS["text"]).pack(side="left")

    # =========================================================
    # MATRIX
    # =========================================================

    def _render_matrix(self):
        for w in self._matrix_container.winfo_children():
            w.destroy()

        students = self._students
        if students is None or students.empty:
            ctk.CTkLabel(
                self._matrix_container,
                text="No students.",
                font=FONTS["body"],
                text_color=COLORS["text_muted"]).pack(pady=20)
            return

        # Header row: student name + 10 badge icons
        header = ctk.CTkFrame(self._matrix_container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 4))

        ctk.CTkLabel(
            header, text="Student", width=240, anchor="w",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_muted"]).pack(side="left")

        for b in BADGES:
            ctk.CTkLabel(
                header, text=b["icon"], width=44,
                font=(FONT_FAMILY, 14),
                text_color=COLORS["text_muted"],
            ).pack(side="left")

        # Rows
        for _, s in students.iterrows():
            uid = _safe_str(s.get("id"))
            name = _safe_str(s.get("name")) or "—"
            usn = _safe_str(s.get("usn")) or "—"
            earned_set = self._earned_lookup.get(uid, set())

            row = ctk.CTkFrame(self._matrix_container,
                               fg_color=COLORS["surface_alt"],
                               corner_radius=8)
            row.pack(fill="x", pady=2)

            # Student cell
            cell = ctk.CTkFrame(row, fg_color="transparent", width=240)
            cell.pack(side="left", padx=(8, 0), pady=6)
            cell.pack_propagate(False)

            try:
                avatar = load_avatar(
                    user_id=uid, name=name,
                    size=26, shape="circle")
                ctk.CTkLabel(cell, image=avatar, text="").pack(
                    side="left", padx=(0, 8))
            except Exception:
                pass

            text_box = ctk.CTkFrame(cell, fg_color="transparent")
            text_box.pack(side="left", fill="x", expand=True)

            ctk.CTkLabel(
                text_box, text=name,
                font=(FONT_FAMILY, 10, "bold"),
                text_color=COLORS["text"], anchor="w",
            ).pack(anchor="w")

            ctk.CTkLabel(
                text_box, text=usn,
                font=(FONT_FAMILY, 8),
                text_color=COLORS["text_muted"], anchor="w",
            ).pack(anchor="w")

            # Badge cells
            for b in BADGES:
                has = b["id"] in earned_set
                btn_color = (b.get("color") or STATUS["gold"]) if has \
                    else COLORS["surface"]

                badge_btn = ctk.CTkButton(
                    row,
                    text=b["icon"] if has else "·",
                    width=36, height=32,
                    font=(FONT_FAMILY, 13),
                    fg_color=btn_color,
                    hover_color=COLORS["surface_hi"] if not has
                                else STATUS["danger"],
                    text_color="#FFFFFF" if has else COLORS["text_dim"],
                    corner_radius=8,
                    command=(lambda u=uid, bid=b["id"], has_it=has,
                                    bname=b["name"]:
                             self._toggle_badge(u, bid, has_it, bname)),
                )
                badge_btn.pack(side="left", padx=2)

    def _toggle_badge(self, user_id: str, badge_id: str,
                      has_it: bool, badge_name: str):
        # Get student name
        try:
            u = self.db.get_user(user_id)
            name = (u or {}).get("name", "Student")
        except Exception:
            name = "Student"

        if has_it:
            def on_confirm():
                try:
                    self.db.revoke_badge(user_id, badge_id)
                    self.toast(f"Revoked {badge_name} from {name}.", "info")
                    self._reload()
                except Exception as e:
                    self.toast(f"Revoke failed: {e}", "error")

            self.confirm(
                "Revoke this badge?",
                f"Remove {badge_name} from {name}?",
                on_yes=on_confirm,
                yes_text="Revoke",
            )
        else:
            try:
                self.db.award_badge(user_id, badge_id)
                self.toast(f"Awarded {badge_name} to {name} ✓", "success")
                self._reload()
            except Exception as e:
                self.toast(f"Award failed: {e}", "error")

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
            print(f"[badges] → show_page('{key}')  args={kw}")

        def go_back(self):
            print("[badges] back")

        def logout(self):
            print("[badges] logout")

    root = ctk.CTk()
    W, H = 1400, 900
    root.geometry(f"{W}x{H}")
    root.configure(fg_color=COLORS["bg"])
    root.title(f"{APP_NAME} — badge manager")

    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - W) // 2
    y = (sh - H) // 2
    root.geometry(f"{W}x{H}+{x}+{y}")

    app = _FakeApp()
    page = FacilitatorBadgeManagerPage(root, app)
    page.pack(fill="both", expand=True)
    root.mainloop()
    print("\n✅ pages/facilitator/badge_manager.py OK")