# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  pages/student/learning_screen.py  ·  Interactive learning screen
# =============================================================

from __future__ import annotations

import os
import sys

# --- make project root importable ---
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import re
import time

import customtkinter as ctk

from config import (
    APP_NAME, COLORS, STATUS, ZONE_COLORS,
    FONTS, FONT_FAMILY,
    CARD_RADIUS, BUTTON_RADIUS, CHIP_RADIUS,
    PAD_SM, PAD_MD, PAD_LG, PAD_XL,
)
from pages.base_page import BasePage
from models.bkt import BKTTracker
from models.recommender import Recommender
from models.spaced_repetition import Scheduler
from utils.llm import get_hint, interest_example


# =============================================================
# HELPERS
# =============================================================

def extract_numbers(s: str):
    """Return list of floats present in a string (fractions normalized)."""
    if not s:
        return []
    fracs = re.findall(r"(\d+)\s*/\s*(\d+)", s)
    for a, b in fracs:
        try:
            s = s.replace(f"{a}/{b}", str(float(a) / float(b)))
        except ZeroDivisionError:
            pass
    nums = re.findall(r"-?\d+\.?\d*", s)
    out = []
    for n in nums:
        try:
            out.append(float(n))
        except ValueError:
            continue
    return out


def parse_answer(user_input: str):
    """Parse the student's answer into a number if possible."""
    if user_input is None:
        return None
    s = user_input.strip()
    if not s:
        return None
    # Try "3/4" style fraction first
    m = re.fullmatch(r"(-?\d+)\s*/\s*(\d+)", s)
    if m:
        try:
            return float(m.group(1)) / float(m.group(2))
        except ZeroDivisionError:
            return None
    # Try percent
    s = s.replace("%", "")
    try:
        return float(s)
    except ValueError:
        return None


def evaluate_answer(problem: str, expected, user_val):
    """
    Very simple answer check:
      - If expected is a number → compare with tolerance.
      - Otherwise → string compare (case-insensitive, trimmed).
    """
    if user_val is None:
        return False
    if isinstance(expected, (int, float)):
        try:
            return abs(float(user_val) - float(expected)) < 0.01
        except Exception:
            return False
    if isinstance(expected, str):
        return user_val.strip().lower() == expected.strip().lower()
    return False


# =============================================================
# LEARNING SCREEN PAGE
# =============================================================

class LearningScreenPage(BasePage):

    def __init__(self, master, app, concept_id: str = None):
        super().__init__(master, app)

        self.concept_id = concept_id
        self.concept = None
        self.items = []          # list of content dicts
        self.index = 0
        self.hints_used = 0
        self.current_hint_level = 0

        self._started_at = time.time()

        # Models
        self._tracker = BKTTracker(self.db)
        self._recommender = Recommender(self.db, tracker=self._tracker)
        self._scheduler = Scheduler(self.db)

        # Resolve concept
        self._load_concept()

        title = self.concept["name"] if self.concept else "Learning"
        subj = self.concept["subject"] if self.concept else ""
        self.build_header(title, subj, back=True)
        self.build_content(scrollable=False)
        self.build_footer()

        self.render()

    # =========================================================
    # DATA
    # =========================================================

    def _load_concept(self):
        if not self.concept_id:
            return
        try:
            row = self.db.query("SELECT * FROM concepts WHERE id=?",
                                (self.concept_id,))
            if not row.empty:
                self.concept = row.iloc[0].to_dict()
            items = self.db.query(
                "SELECT * FROM content WHERE concept_id=? ORDER BY difficulty",
                (self.concept_id,))
            # Sort interest-tagged items first for the student's interests
            interests = set()
            if self.user:
                try:
                    interests = set(self.db.get_user_interests(self.user["id"]))
                except Exception:
                    pass
            rows = []
            for _, r in items.iterrows():
                tag = r["interest_tag"]
                hits = 1 if (tag and tag in interests) else 0
                rows.append((hits, r.to_dict()))
            rows.sort(key=lambda x: -x[0])   # interest hits first
            self.items = [r for _, r in rows]
        except Exception:
            self.concept = None
            self.items = []

    # =========================================================
    # RENDER
    # =========================================================

    def render(self):
        if not self.concept or not self.items:
            self._render_empty("No content available for this concept yet.")
            return

        content = self._content

        # 1. Progress + mastery strip
        self._render_top_strip(content)

        # 2. Content card (rebuilt each step)
        self._item_container = ctk.CTkFrame(content, fg_color="transparent")
        self._item_container.pack(fill="both", expand=True,
                                  pady=(PAD_MD, 0))
        self._render_current_item()

    # =========================================================
    # TOP STRIP
    # =========================================================

    def _render_top_strip(self, parent):
        strip = ctk.CTkFrame(parent, fg_color=COLORS["surface"],
                             corner_radius=CARD_RADIUS,
                             border_width=1,
                             border_color=COLORS["border_soft"])
        strip.pack(fill="x")

        inner = ctk.CTkFrame(strip, fg_color="transparent")
        inner.pack(fill="x", padx=PAD_LG, pady=PAD_MD)

        # Progress ring (as text) + bar
        left = ctk.CTkFrame(inner, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            left, text=f"Question {self.index + 1} of {len(self.items)}",
            font=FONTS["small_bold"],
            text_color=COLORS["text"]).pack(anchor="w")

        progress = (self.index) / max(1, len(self.items))
        bar = ctk.CTkProgressBar(
            left, width=320, height=8,
            progress_color=COLORS["primary"],
            fg_color=COLORS["surface_alt"])
        bar.pack(anchor="w", pady=(4, 0))
        bar.set(min(1.0, progress))

        # Mastery state
        right = ctk.CTkFrame(inner, fg_color="transparent")
        right.pack(side="right")

        try:
            m = self._tracker.mastery(self.user["id"], self.concept_id)
            p = m["p_mastery"]
            color = m["color"]
            label = m["label"].title()
            icon = m["icon"]
        except Exception:
            p, color, label, icon = 0.0, COLORS["primary"], "Unknown", "•"

        ctk.CTkLabel(
            right, text=f"{icon}  Mastery: {int(p*100)}%",
            font=(FONT_FAMILY, 13, "bold"),
            text_color=color).pack(anchor="e")

        ctk.CTkLabel(
            right, text=label,
            font=FONTS["tiny"],
            text_color=COLORS["text_muted"]).pack(anchor="e")

    # =========================================================
    # CURRENT ITEM
    # =========================================================

    def _render_current_item(self):
        # Clear
        for w in self._item_container.winfo_children():
            w.destroy()

        item = self.items[self.index]
        self.hints_used = 0
        self.current_hint_level = 0

        card = self.card(self._item_container)
        card.pack(fill="both", expand=True)

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="both", expand=True,
                  padx=PAD_XL, pady=PAD_LG)

        # Item type badge
        type_colors = {
            "video":   "#8B5CF6",
            "article": "#60A5FA",
            "problem": "#F59E0B",
            "quiz":    "#EC4899",
            "project": "#10B981",
        }
        chip = ctk.CTkFrame(
            body,
            fg_color=type_colors.get(item["type"], COLORS["primary"]),
            corner_radius=CHIP_RADIUS)
        chip.pack(anchor="w")
        ctk.CTkLabel(
            chip,
            text=f"  {item['type'].title()}  ",
            font=(FONT_FAMILY, 10, "bold"),
            text_color="#FFFFFF").pack(padx=4, pady=2)

        if item.get("interest_tag"):
            interest_chip = ctk.CTkFrame(
                body, fg_color=COLORS["surface_alt"],
                corner_radius=CHIP_RADIUS)
            interest_chip.pack(anchor="w", pady=(6, 0))
            ctk.CTkLabel(
                interest_chip,
                text=f"  🎯 Personalized for {item['interest_tag']}  ",
                font=(FONT_FAMILY, 10),
                text_color=COLORS["text"]).pack(padx=4, pady=2)

        # Title
        ctk.CTkLabel(
            body, text=item["title"],
            font=(FONT_FAMILY, 20, "bold"),
            text_color=COLORS["text"],
            anchor="w", wraplength=900, justify="left",
        ).pack(anchor="w", pady=(14, 6))

        # Body
        text = item.get("body") or "(no description)"
        ctk.CTkLabel(
            body, text=text,
            font=FONTS["body"],
            text_color=COLORS["text_muted"],
            anchor="w", wraplength=900, justify="left",
        ).pack(anchor="w", pady=(0, 16))

        # For problems/quizzes: answer input + hints
        if item["type"] in ("problem", "quiz"):
            self._render_problem_area(body, item)
        else:
            self._render_read_only_area(body, item)

    # =========================================================
    # READ-ONLY AREA (video/article)
    # =========================================================

    def _render_read_only_area(self, parent, item):
        # Hint button (still useful for videos/articles)
        hint_row = ctk.CTkFrame(parent, fg_color="transparent")
        hint_row.pack(anchor="w", pady=(0, PAD_MD))

        self.secondary_button(
            hint_row, "💡 Get a hint",
            command=lambda: self._reveal_hint(parent, item),
            width=160, height=38,
        ).pack(side="left")

        # Bottom actions
        actions = ctk.CTkFrame(parent, fg_color="transparent")
        actions.pack(side="bottom", fill="x", pady=(PAD_MD, 0))

        self.secondary_button(
            actions, "← Back",
            command=lambda: self.navigate("stu_learning"),
            width=120, height=42,
        ).pack(side="left")

        self.primary_button(
            actions,
            "Mark as read  →" if self.index < len(self.items) - 1
            else "Finish  ✓",
            command=self._on_read_advance,
            width=200, height=44,
        ).pack(side="right")

    def _on_read_advance(self):
        # Log a "completed" attempt (neutral)
        try:
            self._tracker.update_from_attempt(
                self.user["id"], self.concept_id,
                correct=True, time_sec=0, hints_used=self.hints_used,
                content_id=self.items[self.index]["id"],
            )
        except Exception:
            pass
        self._advance()

    # =========================================================
    # PROBLEM AREA (problem/quiz)
    # =========================================================

    def _render_problem_area(self, parent, item):
        # Number extraction for expected answer (heuristic)
        self._problem_text = item.get("body") or ""
        self._expected = self._guess_expected(self._problem_text, item)

        # Answer entry row
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        ctk.CTkLabel(
            row, text="Your answer:",
            font=FONTS["small_bold"],
            text_color=COLORS["text_muted"]).pack(anchor="w")

        entry_row = ctk.CTkFrame(row, fg_color="transparent")
        entry_row.pack(anchor="w", pady=(4, 0))

        self._answer_entry = ctk.CTkEntry(
            entry_row, width=320, height=42,
            font=(FONT_FAMILY, 14),
            fg_color=COLORS["surface_alt"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            corner_radius=10,
            placeholder_text="Type your answer…")
        self._answer_entry.pack(side="left")
        self._answer_entry.bind("<Return>", lambda e: self._check_answer(parent, item))

        self.primary_button(
            entry_row, "Check",
            command=lambda: self._check_answer(parent, item),
            width=110, height=42,
        ).pack(side="left", padx=(PAD_MD, 0))

        # Feedback line
        self._feedback_label = ctk.CTkLabel(
            parent, text="",
            font=FONTS["small_bold"],
            text_color=COLORS["text_muted"],
            wraplength=900, justify="left")
        self._feedback_label.pack(anchor="w", pady=(6, 6))

        # Hint buttons row
        hint_row = ctk.CTkFrame(parent, fg_color="transparent")
        hint_row.pack(anchor="w", pady=(6, 0))

        self._hint_buttons = []
        for level, label in [(1, "💡 Nudge"),
                             (2, "🔎 Hint"),
                             (3, "📘 Explain")]:
            btn = self.secondary_button(
                hint_row, label,
                command=lambda l=level: self._reveal_hint(parent, item, l),
                width=140, height=36,
            )
            btn.pack(side="left", padx=(0, 8))
            self._hint_buttons.append((level, btn))

        # Hint display area
        self._hint_box = ctk.CTkFrame(
            parent,
            fg_color=COLORS["surface_alt"],
            corner_radius=10)
        self._hint_box.pack(fill="x", pady=(10, 0))
        self._hint_label = ctk.CTkLabel(
            self._hint_box, text="",
            font=FONTS["small"],
            text_color=COLORS["text"],
            wraplength=880, justify="left")
        self._hint_label.pack(padx=14, pady=12, anchor="w")
        # Hide hint box until used
        self._hint_box.pack_forget()

        # Bottom actions
        actions = ctk.CTkFrame(parent, fg_color="transparent")
        actions.pack(side="bottom", fill="x", pady=(PAD_MD, 0))

        self.secondary_button(
            actions, "← Back",
            command=lambda: self.navigate("stu_learning"),
            width=120, height=42,
        ).pack(side="left")

        self._next_btn = self.primary_button(
            actions,
            "Next  →" if self.index < len(self.items) - 1 else "Finish  ✓",
            command=self._advance,
            width=200, height=44,
        )
        self._next_btn.pack(side="right")
        # Disable until answered correctly
        try:
            self._next_btn.configure(state="disabled", text="Answer to continue")
        except Exception:
            pass

    def _guess_expected(self, problem: str, item: dict):
        """
        Very light heuristics to derive the expected answer for common cases.
        Falls back to None (so we mark it as 'reviewed', not graded).
        """
        p = problem.lower()
        nums = extract_numbers(problem)
        try:
            # Simple arithmetic cases
            if "+" in problem and len(nums) >= 2:
                return sum(nums[:2])
            if ("-" in problem or "−" in problem) and len(nums) >= 2:
                return nums[0] - nums[1]
            if "×" in problem or "*" in problem and len(nums) >= 2:
                return nums[0] * nums[1]
            if ("÷" in problem or "/" in problem) and len(nums) >= 2 and nums[1] != 0:
                return nums[0] / nums[1]
            if "%" in problem and len(nums) >= 2:
                # "What is 25% of 80" style
                return (nums[0] / 100.0) * nums[1]
        except Exception:
            pass
        return None

    def _reveal_hint(self, parent, item, level: int = None):
        if level is None:
            level = min(3, self.current_hint_level + 1)
        self.current_hint_level = max(self.current_hint_level, level)
        self.hints_used += 1

        # Fetch hint
        try:
            h = get_hint(
                problem=self._problem_text if hasattr(self, "_problem_text")
                        else (item.get("body") or ""),
                concept=self.concept["name"] if self.concept else "concept",
                level=level,
                subject=self.concept["subject"] if self.concept else "Maths",
                interest=None,
                student_name=(self.user or {}).get("name"),
            )
            text = h.text
        except Exception:
            text = f"Hint level {level} unavailable."

        # Show
        try:
            self._hint_box.pack(fill="x", pady=(10, 0))
            self._hint_label.configure(text=text)
        except Exception:
            pass

        # Disable used level button
        try:
            for lvl, btn in getattr(self, "_hint_buttons", []):
                if lvl <= level:
                    btn.configure(state="disabled")
        except Exception:
            pass

    def _check_answer(self, parent, item):
        user_input = self._answer_entry.get() if hasattr(self, "_answer_entry") else ""
        user_val = parse_answer(user_input)
        expected = self._expected

        # If we couldn't derive expected, treat any non-empty answer as "reviewed"
        if expected is None:
            ok = (user_val is not None)
        else:
            ok = evaluate_answer(self._problem_text, expected, user_val)

        # Log attempt
        try:
            self._tracker.update_from_attempt(
                self.user["id"], self.concept_id,
                correct=ok, time_sec=0, hints_used=self.hints_used,
                content_id=item["id"],
            )
        except Exception:
            pass

        # Feedback
        if ok:
            correct_txt = "✓ Correct!"
            if expected is not None:
                correct_txt += f"  (Answer: {expected:g})"
            try:
                self._feedback_label.configure(
                    text=correct_txt,
                    text_color=STATUS["green"])
                self._next_btn.configure(
                    state="normal",
                    text=("Next  →" if self.index < len(self.items) - 1
                          else "Finish  ✓"))
            except Exception:
                pass
        else:
            try:
                self._feedback_label.configure(
                    text="✗ Not quite. Try again or use a hint.",
                    text_color=STATUS["red"])
            except Exception:
                pass

        # Refresh mastery display on top strip
        try:
            for w in self._content.winfo_children():
                if isinstance(w, ctk.CTkFrame):
                    # rebuild top strip in place
                    pass
        except Exception:
            pass

    # =========================================================
    # ADVANCE
    # =========================================================

    def _advance(self):
        if self.index + 1 < len(self.items):
            self.index += 1
            # Rebuild whole content to refresh strip
            for w in self._content.winfo_children():
                w.destroy()
            self.render()
        else:
            # Finished all items
            self._finish()

    def _finish(self):
        # Schedule next review
        try:
            m = self._tracker.mastery(self.user["id"], self.concept_id)
            self._scheduler.record_review(
                self.user["id"], self.concept_id,
                correct=True, p_mastery=m["p_mastery"],
                time_sec=int(time.time() - self._started_at),
                hints_used=self.hints_used)
        except Exception:
            pass

        # Show completion card
        for w in self._content.winfo_children():
            w.destroy()

        done = self.card(self._content)
        done.pack(fill="both", expand=True, padx=PAD_XL, pady=PAD_XL)

        body = ctk.CTkFrame(done, fg_color="transparent")
        body.pack(expand=True, pady=PAD_XL)

        ctk.CTkLabel(
            body, text="🎉",
            font=(FONT_FAMILY, 64),
            text_color=STATUS["gold"]).pack(pady=(0, 10))

        ctk.CTkLabel(
            body, text="Great work!",
            font=(FONT_FAMILY, 26, "bold"),
            text_color=COLORS["text"]).pack()

        ctk.CTkLabel(
            body,
            text=f"You completed {len(self.items)} items on "
                 f"{self.concept['name']}.",
            font=FONTS["body"],
            text_color=COLORS["text_muted"]).pack(pady=(6, 20))

        # Live mastery
        try:
            m = self._tracker.mastery(self.user["id"], self.concept_id)
            ctk.CTkLabel(
                body, text=f"{m['icon']}  Mastery: {int(m['p_mastery']*100)}%",
                font=(FONT_FAMILY, 16, "bold"),
                text_color=m["color"]).pack(pady=(0, 20))
        except Exception:
            pass

        btn_row = ctk.CTkFrame(body, fg_color="transparent")
        btn_row.pack()

        self.secondary_button(
            btn_row, "Learning path",
            command=lambda: self.navigate("stu_learning"),
            width=160, height=42).pack(side="left", padx=(0, 8))

        self.primary_button(
            btn_row, "Back to dashboard",
            command=lambda: self.navigate("stu_dashboard"),
            width=200, height=44).pack(side="left")

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
            print(f"[learn] → show_page('{key}')  args={kw}")

        def go_back(self):
            print("[learn] back")

        def logout(self):
            print("[learn] logout")

    root = ctk.CTk()
    W, H = 1280, 900
    root.geometry(f"{W}x{H}")
    root.configure(fg_color=COLORS["bg"])
    root.title(f"{APP_NAME} — learning screen preview")

    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - W) // 2
    y = (sh - H) // 2
    root.geometry(f"{W}x{H}+{x}+{y}")

    app = _FakeApp()
    # Start learning fractions
    page = LearningScreenPage(root, app, concept_id="c_frac")
    page.pack(fill="both", expand=True)
    root.mainloop()
    print("\n✅ pages/student/learning_screen.py OK")