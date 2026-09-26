# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  pages/student/remedial.py  ·  Student remedial sessions
# =============================================================

from __future__ import annotations

import os
import sys

# --- make project root importable ---
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from datetime import datetime

import customtkinter as ctk

from config import (
    APP_NAME, COLORS, STATUS, SUBJECT_COLORS,
    FONTS, FONT_FAMILY,
    CARD_RADIUS, BUTTON_RADIUS, CHIP_RADIUS,
    PAD_SM, PAD_MD, PAD_LG, PAD_XL,
)
from pages.base_page import BasePage


# =============================================================
# HELPERS
# =============================================================

STATUS_META = {
    "scheduled": ("🕒", "Scheduled", STATUS["info"]),
    "attended":  ("✅", "Attended",  STATUS["green"]),
    "missed":    ("❌", "Missed",    STATUS["red"]),
    "cancelled": ("🚫", "Cancelled", COLORS["text_muted"]),
}


def _fmt_date(iso: str) -> str:
    if not iso:
        return "—"
    try:
        d = datetime.fromisoformat(iso)
        return d.strftime("%d %b %Y, %I:%M %p")
    except Exception:
        return iso[:16]


def _session_status(session_row, enrollment_row) -> str:
    """Determine current status of an enrollment."""
    enrolled_at = enrollment_row.get("enrolled_at") or ""
    attended = bool(enrollment_row.get("attended"))
    outcome = (enrollment_row.get("outcome") or "").lower()
    scheduled_at = session_row.get("scheduled_at") or ""

    if outcome in ("cancelled", "canceled"):
        return "cancelled"
    if attended or outcome == "attended":
        return "attended"

    # If scheduled in the past and not attended → missed
    try:
        sched = datetime.fromisoformat(scheduled_at)
        if sched < datetime.now():
            return "missed"
    except Exception:
        pass

    return "scheduled"


# =============================================================
# REMEDIAL PAGE
# =============================================================

class StudentRemedialPage(BasePage):

    def __init__(self, master, app, target_user_id: str = None):
        super().__init__(master, app)

        self.target_id = target_user_id or (self.user or {}).get("id")
        self.is_self = (self.target_id == (self.user or {}).get("id"))
        self.target = self.db.get_user(self.target_id) if self.target_id else None

        self.build_header(
            "My Remedial Sessions" if self.is_self
            else f"{self.target.get('name', '')} — Remedial",
            "Targeted support to help you level up",
            back=not self.is_self,
        )
        self.build_content(scrollable=True)
        self.build_footer()

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
            self._sessions = self.db.get_user_remedial(uid)
        except Exception:
            self._sessions = None

        # 1. Top stats
        self._render_top_stats(content)

        # 2. Upcoming sessions
        self.section_title("Upcoming Sessions", parent=content)
        self._render_section(content, upcoming=True)

        # 3. Past sessions
        self.section_title("Past Sessions", parent=content)
        self._render_section(content, upcoming=False)

    # =========================================================
    # STATS
    # =========================================================

    def _render_top_stats(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        s = self._sessions
        total = 0 if s is None else len(s)
        attended = 0
        missed = 0
        upcoming = 0
        total_improvement = 0.0

        if s is not None and not s.empty:
            for _, r in s.iterrows():
                status = _session_status(r, r)
                if status == "attended":
                    attended += 1
                    try:
                        total_improvement += float(r.get("improvement") or 0)
                    except Exception:
                        pass
                elif status == "missed":
                    missed += 1
                elif status == "scheduled":
                    upcoming += 1

        avg_improvement = (total_improvement / attended) if attended else 0.0

        self.stat_card(
            row, total, "Total sessions",
            accent=COLORS["primary"], icon="📚",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, upcoming, "Upcoming",
            accent=STATUS["info"], icon="🕒",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, attended, "Attended",
            accent=STATUS["green"], icon="✅",
        ).pack(side="left", padx=(0, PAD_MD))

        self.stat_card(
            row, f"{avg_improvement:+.1f}%", "Avg improvement",
            accent=STATUS["green"] if avg_improvement > 0
                   else COLORS["text_muted"],
            icon="📈",
        ).pack(side="left")

    # =========================================================
    # SECTIONS
    # =========================================================

    def _render_section(self, parent, upcoming: bool):
        s = self._sessions
        if s is None or s.empty:
            ctk.CTkLabel(
                parent,
                text="No remedial sessions enrolled." if not upcoming
                     else "You're all caught up! 🎉 No upcoming sessions.",
                font=FONTS["body"],
                text_color=COLORS["text_muted"]).pack(pady=16)
            return

        rows = []
        for _, r in s.iterrows():
            st = _session_status(r, r)
            is_upcoming = (st == "scheduled")
            if (upcoming and is_upcoming) or (not upcoming and not is_upcoming):
                rows.append((st, r))

        if not rows:
            msg = "Nothing scheduled — check back later." if upcoming \
                  else "No past sessions yet."
            ctk.CTkLabel(
                parent, text=msg,
                font=FONTS["body"],
                text_color=COLORS["text_muted"]).pack(pady=16)
            return

        # Sort: upcoming ascending, past descending
        try:
            rows.sort(key=lambda x: x[1].get("scheduled_at") or "",
                      reverse=not upcoming)
        except Exception:
            pass

        for st, r in rows:
            self._render_session_card(parent, r, st)

    def _render_session_card(self, parent, s, status: str):
        icon, label, color = STATUS_META.get(
            status, ("•", status.title(), COLORS["text_muted"]))

        card = self.card(parent)
        card.pack(fill="x", pady=4)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=PAD_LG, pady=PAD_MD)

        # Left: subject block
        subj = s.get("subject") or "Remedial"
        subj_color = SUBJECT_COLORS.get(subj, COLORS["primary"])

        block = ctk.CTkFrame(
            inner,
            width=60, height=60,
            fg_color=subj_color,
            corner_radius=14)
        block.pack(side="left")
        block.pack_propagate(False)

        subj_short = "".join(
            w[0] for w in subj.split() if w)[:2].upper() or "RM"
        ctk.CTkLabel(
            block, text=subj_short,
            font=(FONT_FAMILY, 20, "bold"),
            text_color="#FFFFFF",
        ).place(relx=0.5, rely=0.5, anchor="center")

        # Middle: title + meta
        mid = ctk.CTkFrame(inner, fg_color="transparent")
        mid.pack(side="left", fill="x", expand=True, padx=(PAD_LG, 0))

        ctk.CTkLabel(
            mid, text=s.get("topic") or f"{subj} — remedial",
            font=(FONT_FAMILY, 15, "bold"),
            text_color=COLORS["text"], anchor="w",
        ).pack(anchor="w")

        # Meta line
        meta_bits = [subj]
        dur = s.get("duration_min")
        if dur:
            meta_bits.append(f"{int(dur)} min")
        ctk.CTkLabel(
            mid, text="  ·  ".join(meta_bits),
            font=(FONT_FAMILY, 10),
            text_color=COLORS["text_muted"], anchor="w",
        ).pack(anchor="w", pady=(2, 0))

        # Schedule line
        sched = _fmt_date(s.get("scheduled_at"))
        ctk.CTkLabel(
            mid, text=f"🗓️  {sched}",
            font=(FONT_FAMILY, 11),
            text_color=COLORS["text"], anchor="w",
        ).pack(anchor="w", pady=(4, 0))

        # Notes
        if s.get("notes"):
            ctk.CTkLabel(
                mid, text=f"📝  {s['notes']}",
                font=(FONT_FAMILY, 10),
                text_color=COLORS["text_muted"], anchor="w",
                wraplength=500, justify="left",
            ).pack(anchor="w", pady=(4, 0))

        # Right: status chip + improvement badge
        right = ctk.CTkFrame(inner, fg_color="transparent")
        right.pack(side="right")

        chip = ctk.CTkFrame(
            right, fg_color=color, corner_radius=CHIP_RADIUS)
        chip.pack(anchor="e")
        ctk.CTkLabel(
            chip, text=f"  {icon}  {label}  ",
            font=(FONT_FAMILY, 10, "bold"),
            text_color="#FFFFFF",
        ).pack(padx=4, pady=3)

        # Improvement badge (if attended)
        if status == "attended":
            try:
                imp = float(s.get("improvement") or 0)
                if imp != 0:
                    imp_color = STATUS["green"] if imp > 0 else STATUS["red"]
                    ctk.CTkLabel(
                        right,
                        text=f"{imp:+.1f}%",
                        font=(FONT_FAMILY, 13, "bold"),
                        text_color=imp_color,
                    ).pack(anchor="e", pady=(6, 0))
            except Exception:
                pass

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
            print(f"[remedial] → show_page('{key}')  args={kw}")

        def go_back(self):
            print("[remedial] back")

        def logout(self):
            print("[remedial] logout")

    root = ctk.CTk()
    W, H = 1280, 900
    root.geometry(f"{W}x{H}")
    root.configure(fg_color=COLORS["bg"])
    root.title(f"{APP_NAME} — remedial preview")

    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - W) // 2
    y = (sh - H) // 2
    root.geometry(f"{W}x{H}+{x}+{y}")

    app = _FakeApp()
    page = StudentRemedialPage(root, app)
    page.pack(fill="both", expand=True)
    root.mainloop()
    print("\n✅ pages/student/remedial.py OK")