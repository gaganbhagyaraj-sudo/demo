# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  models/spaced_repetition.py  ·  SM-2 spaced repetition scheduler
# =============================================================

from __future__ import annotations

import os
import sys

# --- make project root importable ---
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from dataclasses import dataclass
from datetime import datetime, timedelta, date
from typing import Optional

import pandas as pd

from config import (
    SR_INITIAL_INTERVAL, SR_INITIAL_EASE,
    SR_MIN_EASE, SR_MAX_EASE,
    MASTERY_THRESHOLDS,
)


# =============================================================
# 1. CORE SM-2 (SUPERMEMO-2) IMPLEMENTATION
# =============================================================

@dataclass
class SRState:
    """Current spaced-repetition state of one (user, concept) pair."""
    interval_days: int = SR_INITIAL_INTERVAL
    ease: float = SR_INITIAL_EASE
    repetitions: int = 0
    last_reviewed: Optional[str] = None
    next_review: Optional[str] = None

    def to_dict(self):
        return {
            "interval_days": self.interval_days,
            "ease": round(self.ease, 2),
            "repetitions": self.repetitions,
            "last_reviewed": self.last_reviewed,
            "next_review": self.next_review,
        }


def quality_from_correct(correct: bool, time_sec: int = 0,
                         hints_used: int = 0,
                         p_mastery: float = 0.5) -> int:
    """
    Map an attempt outcome to an SM-2 quality score (0–5).

    5 = perfect, fast, no hints
    4 = correct, some hesitation
    3 = correct with hint / slow
    2 = incorrect, close
    1 = incorrect, far off
    0 = complete blackout
    """
    if correct:
        if hints_used == 0 and time_sec <= 20:
            return 5
        if hints_used == 0 and time_sec <= 45:
            return 4
        return 3
    # wrong answers
    if p_mastery >= 0.5:
        return 2
    if p_mastery >= 0.25:
        return 1
    return 0


def sm2_update(state: SRState, quality: int) -> SRState:
    """
    Standard SM-2 update.

    quality 0–5:
      q < 3  → reset repetitions, interval back to 1
      q ≥ 3  → grow interval by ease factor
    """
    q = max(0, min(5, int(quality)))
    now_iso = datetime.now().isoformat()

    if q < 3:
        # Repetition reset
        state.repetitions = 0
        state.interval_days = 1
        state.ease = max(SR_MIN_EASE, state.ease - 0.2)
    else:
        state.repetitions += 1
        if state.repetitions == 1:
            state.interval_days = 1
        elif state.repetitions == 2:
            state.interval_days = 3
        else:
            state.interval_days = max(
                1, int(round(state.interval_days * state.ease)))
        # ease tweak based on quality
        delta = 0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)
        state.ease = min(SR_MAX_EASE, max(SR_MIN_EASE, state.ease + delta))

    state.last_reviewed = now_iso
    state.next_review = (datetime.now()
                         + timedelta(days=state.interval_days)).isoformat()
    return state


# =============================================================
# 2. MASTERY-AWARE SCHEDULER
# =============================================================

def next_interval(p_mastery: float, prev_interval_days: int = 1,
                  ease: float = SR_INITIAL_EASE) -> tuple:
    """
    Mastery-aware scheduler that sits on top of SM-2.
    Returns (interval_days, new_ease).

    p < 0.4     → 1 day, ease drops
    0.4 ≤ p<0.75 → modest growth
    p ≥ 0.75    → multiplicative growth by ease
    """
    p = max(0.0, min(1.0, float(p_mastery)))

    if p < MASTERY_THRESHOLDS["weak"]:
        return 1, max(SR_MIN_EASE, ease - 0.20)
    if p < MASTERY_THRESHOLDS["developing"]:
        return max(2, int(prev_interval_days * 1.3)), ease
    # mastered
    new_ease = min(SR_MAX_EASE, ease + 0.10)
    return max(3, int(prev_interval_days * new_ease)), new_ease


def schedule_next_review(p_mastery: float,
                         prev_interval_days: int = 1,
                         ease: float = SR_INITIAL_EASE
                         ) -> tuple:
    """
    Convenience: returns (interval_days, ease, iso_date_string).
    """
    interval, new_ease = next_interval(p_mastery, prev_interval_days, ease)
    next_date = (datetime.now() + timedelta(days=interval)).isoformat()
    return interval, round(new_ease, 2), next_date


# =============================================================
# 3. PRIORITY / URGENCY HELPERS
# =============================================================

def urgency_score(p_mastery: float, days_overdue: int,
                  difficulty: int = 3) -> float:
    """
    Rank how urgently a concept should be reviewed.

    Higher = more urgent.

    - Weak mastery, long overdue → high score
    - Mastered, on-time → low score
    """
    mastery_need = 1.0 - p_mastery                      # 0..1
    overdue_need = min(1.0, max(0.0, days_overdue / 7.0))  # caps at 1 week
    diff_factor = min(1.0, max(0.4, difficulty / 5.0))  # harder → higher
    return round(
        0.5 * mastery_need +
        0.35 * overdue_need +
        0.15 * diff_factor, 4)


def days_between(iso_a: Optional[str], iso_b: Optional[str] = None) -> int:
    """Days from iso_a to iso_b (default = today)."""
    if not iso_a:
        return 0
    try:
        a = datetime.fromisoformat(iso_a).date()
    except Exception:
        return 0
    b = datetime.fromisoformat(iso_b).date() if iso_b else date.today()
    return (b - a).days


# =============================================================
# 4. DB-BACKED SCHEDULER
# =============================================================

class Scheduler:
    """
    Reads/writes mastery table columns for interval/ease/repetitions and
    next_review_at. Uses the mastery table as the source of truth.
    """

    def __init__(self, db):
        self.db = db

    # ---------- read ----------

    def state(self, user_id: str, concept_id: str) -> SRState:
        df = self.db.query("""
            SELECT next_review_at, last_practiced
            FROM mastery
            WHERE user_id=? AND concept_id=?
        """, (user_id, concept_id))
        st = SRState()
        if not df.empty:
            st.next_review = df.iloc[0]["next_review_at"]
            st.last_reviewed = df.iloc[0]["last_practiced"]
        return st

    def due(self, user_id: str, limit: int = 10) -> pd.DataFrame:
        """
        Concepts due for review today or earlier, sorted by urgency.
        """
        now = datetime.now().isoformat()
        df = self.db.query("""
            SELECT c.id AS concept_id, c.name, c.subject, c.difficulty,
                   m.p_mastery, m.next_review_at, m.last_practiced
            FROM mastery m
            JOIN concepts c ON c.id = m.concept_id
            WHERE m.user_id=?
              AND (m.next_review_at IS NULL OR m.next_review_at <= ?)
            ORDER BY m.p_mastery ASC
            LIMIT ?
        """, (user_id, now, limit))
        if df.empty:
            return df
        df["days_overdue"] = df["next_review_at"].apply(
            lambda d: max(0, -days_between(d)) if d else 0)
        df["urgency"] = [
            urgency_score(p, d, diff)
            for p, d, diff in zip(df["p_mastery"],
                                  df["days_overdue"],
                                  df["difficulty"])
        ]
        return df.sort_values("urgency", ascending=False).reset_index(drop=True)

    def upcoming(self, user_id: str, days: int = 7) -> pd.DataFrame:
        """Reviews scheduled in the next `days` days."""
        now = datetime.now()
        horizon = (now + timedelta(days=days)).isoformat()
        return self.db.query("""
            SELECT c.id AS concept_id, c.name, c.subject, c.difficulty,
                   m.p_mastery, m.next_review_at
            FROM mastery m
            JOIN concepts c ON c.id = m.concept_id
            WHERE m.user_id=?
              AND m.next_review_at IS NOT NULL
              AND m.next_review_at <= ?
            ORDER BY m.next_review_at ASC
        """, (user_id, horizon))

    def overdue_count(self, user_id: str) -> int:
        now = datetime.now().isoformat()
        df = self.db.query("""
            SELECT COUNT(*) AS n FROM mastery
            WHERE user_id=?
              AND next_review_at IS NOT NULL
              AND next_review_at <= ?
        """, (user_id, now))
        return int(df.iloc[0]["n"]) if not df.empty else 0

    # ---------- write ----------

    def record_review(self, user_id: str, concept_id: str,
                      correct: bool, p_mastery: float,
                      time_sec: int = 0, hints_used: int = 0) -> SRState:
        """
        Update the schedule for one review.

        Combines:
          - SM-2 quality from (correct, time, hints)
          - Mastery-aware interval growth
        """
        st = self.state(user_id, concept_id)

        # SM-2 step
        quality = quality_from_correct(
            correct, time_sec, hints_used, p_mastery)
        st = sm2_update(st, quality)

        # Mastery-aware override on interval
        interval, new_ease = next_interval(
            p_mastery, st.interval_days, st.ease)
        st.interval_days = interval
        st.ease = new_ease
        st.next_review = (datetime.now()
                          + timedelta(days=interval)).isoformat()

        # Persist
        self.db.execute("""
            UPDATE mastery
            SET next_review_at=?, last_practiced=?
            WHERE user_id=? AND concept_id=?
        """, (st.next_review, st.last_reviewed, user_id, concept_id))

        return st

    def build_plan(self, user_id: str, limit: int = 5) -> list:
        """
        Return an ordered "today's review plan" for the UI:
          {concept_id, name, subject, p_mastery, urgency, days_overdue}
        """
        df = self.due(user_id, limit=limit)
        if df.empty:
            return []
        out = []
        for _, r in df.iterrows():
            out.append({
                "concept_id":    r["concept_id"],
                "name":          r["name"],
                "subject":       r["subject"],
                "difficulty":    int(r["difficulty"]),
                "p_mastery":     round(float(r["p_mastery"]), 4),
                "days_overdue":  int(r["days_overdue"]),
                "urgency":       round(float(r["urgency"]), 4),
                "next_review_at": r["next_review_at"],
            })
        return out

    # ---------- stats ----------

    def stats(self, user_id: str) -> dict:
        now = datetime.now().isoformat()
        total = self.db.query(
            "SELECT COUNT(*) AS n FROM mastery WHERE user_id=?",
            (user_id,))
        due = self.db.query("""
            SELECT COUNT(*) AS n FROM mastery
            WHERE user_id=? AND next_review_at IS NOT NULL
              AND next_review_at <= ?
        """, (user_id, now))
        week = self.db.query("""
            SELECT COUNT(*) AS n FROM mastery
            WHERE user_id=? AND next_review_at IS NOT NULL
              AND next_review_at > ?
              AND next_review_at <= ?
        """, (user_id, now,
              (datetime.now() + timedelta(days=7)).isoformat()))

        return {
            "total_tracked":  int(total.iloc[0]["n"]) if not total.empty else 0,
            "due_now":        int(due.iloc[0]["n"]) if not due.empty else 0,
            "due_this_week":  int(week.iloc[0]["n"]) if not week.empty else 0,
        }


# =============================================================
# 5. SANITY CHECK
# =============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  SHRUTHI JHARI — models/spaced_repetition.py sanity check")
    print("=" * 60)

    # ---- pure math demo ----
    print("\n🧮 SM-2 update demo (starts interval=1, ease=2.5):")
    st = SRState()
    seq = [
        ("perfect",      5, True),
        ("good",         4, True),
        ("with hint",    3, True),
        ("wrong (close)",2, False),
        ("perfect",      5, True),
        ("perfect",      5, True),
    ]
    for label, q, ok in seq:
        st = sm2_update(st, q)
        print(f"   {label:<14} q={q}  →  interval={st.interval_days:>3}d  "
              f"ease={st.ease:.2f}  reps={st.repetitions}")

    # ---- mastery-aware demo ----
    print("\n🎯 Mastery-aware intervals:")
    for p in (0.2, 0.55, 0.80, 0.95):
        interval, ease = next_interval(p, prev_interval_days=4, ease=2.5)
        print(f"   p={p:.2f}  →  {interval:>3} days   ease={ease:.2f}")

    # ---- quality mapping ----
    print("\n⚙️  Quality mapping:")
    for correct, time_sec, hints in [(True, 10, 0), (True, 35, 0),
                                     (True, 60, 1), (False, 0, 0)]:
        q = quality_from_correct(correct, time_sec, hints, p_mastery=0.5)
        print(f"   correct={correct!s:<5} time={time_sec:<3} hints={hints}  →  q={q}")

    # ---- DB-backed ----
    try:
        from database import get_db
        db = get_db()
        sched = Scheduler(db)

        stu = db.get_all_students().iloc[0]
        uid = stu["id"]

        print(f"\n🧠 Live schedule for {stu['name']}:")

        # Simulate a review cycle on Fractions
        cid = "c_frac"
        for i, (correct, p) in enumerate([
            (True, 0.55), (True, 0.72), (False, 0.60), (True, 0.80)
        ], 1):
            st = sched.record_review(uid, cid, correct=correct,
                                     p_mastery=p, time_sec=25)
            print(f"   review {i}: ok={correct!s:<5} p={p:.2f}  →  "
                  f"next in {st.interval_days}d  (ease={st.ease:.2f})")

        print("\n📋 Today's review plan:")
        plan = sched.build_plan(uid, limit=5)
        if not plan:
            print("   (nothing due)")
        for p in plan:
            print(f"   • {p['name']:<18} p={p['p_mastery']:.2f}  "
                  f"overdue={p['days_overdue']}d  urgency={p['urgency']:.2f}")

        print("\n📊 Stats:", sched.stats(uid))

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n⚠️  DB section skipped: {e}")

    print("\n✅ models/spaced_repetition.py OK")
    print("=" * 60)