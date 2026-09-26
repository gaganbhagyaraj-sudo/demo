# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  models/bkt.py  ·  Bayesian Knowledge Tracing engine
# =============================================================

from __future__ import annotations

import os
import sys

# --- make the project root importable (so `from config import ...` works) ---
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, Optional

import numpy as np
import pandas as pd

from config import BKT_PARAMS, MASTERY_THRESHOLDS


# =============================================================
# 1. CONCEPT-LEVEL BKT PARAMETERS
# =============================================================

@dataclass
class BKTParams:
    slip:  float = BKT_PARAMS["slip"]
    guess: float = BKT_PARAMS["guess"]
    learn: float = BKT_PARAMS["learn"]
    init:  float = BKT_PARAMS["init"]

    def validate(self):
        for name in ("slip", "guess", "learn", "init"):
            v = getattr(self, name)
            if not (0.0 <= v <= 1.0):
                raise ValueError(f"BKT param {name}={v} must be in [0,1]")
        return self


DEFAULT_PARAMS = BKTParams().validate()
EASY_PARAMS    = BKTParams(slip=0.08, guess=0.25, learn=0.35, init=0.15).validate()
HARD_PARAMS    = BKTParams(slip=0.12, guess=0.15, learn=0.22, init=0.05).validate()


def params_for_difficulty(difficulty: int) -> BKTParams:
    if difficulty is None:
        return DEFAULT_PARAMS
    if difficulty <= 2:
        return EASY_PARAMS
    if difficulty >= 4:
        return HARD_PARAMS
    return DEFAULT_PARAMS


# =============================================================
# 2. CORE UPDATE FUNCTIONS
# =============================================================

def bkt_update(p_mastery: float, correct: bool,
               params: BKTParams = DEFAULT_PARAMS) -> float:
    p = float(max(0.0, min(1.0, p_mastery)))
    if correct:
        num = p * (1.0 - params.slip)
        den = num + (1.0 - p) * params.guess
    else:
        num = p * params.slip
        den = num + (1.0 - p) * (1.0 - params.guess)
    p_obs = num / den if den > 0 else p
    p_new = p_obs + (1.0 - p_obs) * params.learn
    return round(float(max(0.0, min(1.0, p_new))), 4)


def bkt_predict_correct(p_mastery: float,
                        params: BKTParams = DEFAULT_PARAMS) -> float:
    p = float(max(0.0, min(1.0, p_mastery)))
    return round(p * (1.0 - params.slip) + (1.0 - p) * params.guess, 4)


def bkt_sequence(p_start: float, correct_flags: Iterable[bool],
                 params: BKTParams = DEFAULT_PARAMS) -> list:
    p = p_start
    traj = [round(p, 4)]
    for ok in correct_flags:
        p = bkt_update(p, ok, params)
        traj.append(p)
    return traj


# =============================================================
# 3. LABELS + COLORS
# =============================================================

ZONE_COLORS = {
    "weak":       "#EF4444",
    "developing": "#F59E0B",
    "mastered":   "#10B981",
}

ZONE_ICONS = {
    "weak":       "🔴",
    "developing": "🟡",
    "mastered":   "🟢",
}


def mastery_label(p: float) -> str:
    if p < MASTERY_THRESHOLDS["weak"]:
        return "weak"
    if p < MASTERY_THRESHOLDS["developing"]:
        return "developing"
    return "mastered"


def mastery_color(p: float) -> str:
    return ZONE_COLORS[mastery_label(p)]


def mastery_icon(p: float) -> str:
    return ZONE_ICONS[mastery_label(p)]


# =============================================================
# 4. SPACED-REPETITION SCHEDULING
# =============================================================

def next_review_date(p_mastery: float, last_interval_days: int = 1,
                     ease: float = 2.5) -> tuple:
    if p_mastery < 0.5:
        interval = 1
        ease = max(1.3, ease - 0.2)
    elif p_mastery < 0.75:
        interval = max(2, int(last_interval_days * 1.3))
    else:
        interval = max(3, int(last_interval_days * ease))
        ease = min(2.8, ease + 0.1)
    next_date = (datetime.now() + timedelta(days=interval)).isoformat()
    return interval, round(ease, 2), next_date


# =============================================================
# 5. DB-BACKED TRACKER
# =============================================================

class BKTTracker:
    def __init__(self, db, params_for_concept: Optional[dict] = None):
        self.db = db
        self.params_for_concept = params_for_concept or {}

    def _params(self, concept_id: str) -> BKTParams:
        if concept_id in self.params_for_concept:
            return self.params_for_concept[concept_id]
        try:
            row = self.db.query("SELECT difficulty FROM concepts WHERE id=?",
                                (concept_id,))
            if not row.empty:
                return params_for_difficulty(int(row.iloc[0]["difficulty"]))
        except Exception:
            pass
        return DEFAULT_PARAMS

    def _current_p(self, user_id: str, concept_id: str) -> float:
        df = self.db.query(
            "SELECT p_mastery FROM mastery WHERE user_id=? AND concept_id=?",
            (user_id, concept_id))
        if df.empty:
            return DEFAULT_PARAMS.init
        return float(df.iloc[0]["p_mastery"])

    def update_from_attempt(self, user_id: str, concept_id: str,
                            correct: bool, time_sec: int = 0,
                            hints_used: int = 0,
                            content_id: Optional[str] = None) -> float:
        params = self._params(concept_id)
        p_before = self._current_p(user_id, concept_id)
        p_after = bkt_update(p_before, correct, params)

        try:
            self.db.log_attempt(
                user_id=user_id,
                content_id=content_id or "",
                concept_id=concept_id,
                correct=1 if correct else 0,
                score=1.0 if correct else 0.0,
                time_sec=time_sec,
                hints=hints_used,
            )
        except Exception:
            pass

        prev = self.db.query(
            "SELECT attempts FROM mastery WHERE user_id=? AND concept_id=?",
            (user_id, concept_id))
        prev_attempts = int(prev.iloc[0]["attempts"]) if not prev.empty else 0
        interval, ease, next_date = next_review_date(
            p_after, last_interval_days=max(1, prev_attempts), ease=2.5)

        self.db.execute(
            """
            INSERT INTO mastery
                (user_id, concept_id, p_mastery, attempts,
                 last_practiced, next_review_at)
            VALUES (?,?,?,?,?,?)
            ON CONFLICT(user_id, concept_id) DO UPDATE SET
                p_mastery=excluded.p_mastery,
                attempts=excluded.attempts,
                last_practiced=excluded.last_practiced,
                next_review_at=excluded.next_review_at
            """,
            (user_id, concept_id, p_after, prev_attempts + 1,
             datetime.now().isoformat(), next_date))
        return p_after

    def predict_correct(self, user_id: str, concept_id: str) -> float:
        p = self._current_p(user_id, concept_id)
        return bkt_predict_correct(p, self._params(concept_id))

    def mastery(self, user_id: str, concept_id: str) -> dict:
        p = self._current_p(user_id, concept_id)
        return {
            "concept_id": concept_id,
            "p_mastery":  round(p, 4),
            "label":      mastery_label(p),
            "color":      mastery_color(p),
            "icon":       mastery_icon(p),
        }

    def summary(self, user_id: str) -> pd.DataFrame:
        rows = self.db.query("""
            SELECT c.id AS concept_id, c.name, c.subject, c.difficulty,
                   COALESCE(m.p_mastery, ?) AS p_mastery,
                   COALESCE(m.attempts, 0)  AS attempts,
                   m.last_practiced, m.next_review_at
            FROM concepts c
            LEFT JOIN mastery m
                   ON m.concept_id = c.id AND m.user_id = ?
            ORDER BY c.difficulty, c.name
        """, (DEFAULT_PARAMS.init, user_id))
        if rows.empty:
            return rows
        rows["label"] = rows["p_mastery"].apply(mastery_label)
        rows["color"] = rows["p_mastery"].apply(mastery_color)
        rows["icon"]  = rows["p_mastery"].apply(mastery_icon)
        return rows

    def due_for_review(self, user_id: str, limit: int = 5) -> pd.DataFrame:
        now = datetime.now().isoformat()
        return self.db.query("""
            SELECT c.id AS concept_id, c.name, c.subject, c.difficulty,
                   m.p_mastery, m.next_review_at
            FROM mastery m
            JOIN concepts c ON c.id = m.concept_id
            WHERE m.user_id=?
              AND (m.next_review_at IS NULL OR m.next_review_at <= ?)
            ORDER BY m.p_mastery ASC
            LIMIT ?
        """, (user_id, now, limit))

    def weak_concepts(self, user_id: str, threshold: float = 0.4) -> pd.DataFrame:
        return self.db.query("""
            SELECT c.id AS concept_id, c.name, c.subject, c.difficulty,
                   m.p_mastery, m.attempts
            FROM mastery m
            JOIN concepts c ON c.id = m.concept_id
            WHERE m.user_id=? AND m.p_mastery < ?
            ORDER BY m.p_mastery ASC
        """, (user_id, threshold))

    def mastered_concepts(self, user_id: str,
                          threshold: float = None) -> pd.DataFrame:
        threshold = (threshold if threshold is not None
                     else MASTERY_THRESHOLDS["mastered"])
        return self.db.query("""
            SELECT c.id AS concept_id, c.name, c.subject, c.difficulty,
                   m.p_mastery, m.attempts
            FROM mastery m
            JOIN concepts c ON c.id = m.concept_id
            WHERE m.user_id=? AND m.p_mastery >= ?
            ORDER BY m.p_mastery DESC
        """, (user_id, threshold))

    def concept_ready(self, user_id: str, concept_id: str) -> bool:
        prereqs = self.db.query(
            "SELECT prereq_id FROM prerequisites WHERE concept_id=?",
            (concept_id,))
        if prereqs.empty:
            return True
        for _, row in prereqs.iterrows():
            p = self._current_p(user_id, row["prereq_id"])
            if p < MASTERY_THRESHOLDS["developing"]:
                return False
        return True

    def overall_mastery(self, user_id: str) -> dict:
        df = self.summary(user_id)
        if df.empty:
            return {"avg_mastery": 0.0, "mastered": 0, "developing": 0,
                    "weak": 0, "total_concepts": 0}
        counts = df["label"].value_counts().to_dict()
        return {
            "avg_mastery":    round(float(df["p_mastery"].mean()), 4),
            "mastered":       int(counts.get("mastered", 0)),
            "developing":     int(counts.get("developing", 0)),
            "weak":           int(counts.get("weak", 0)),
            "total_concepts": int(len(df)),
        }


# =============================================================
# 6. SANITY CHECK
# =============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  SHRUTHI JHARI — models/bkt.py sanity check")
    print("=" * 60)

    print("\n🧮 Pure BKT update demo (p_start = 0.1):")
    p = 0.1
    print(f"   start          → {p:.3f}")
    for label, ok in [("correct", True), ("correct", True),
                      ("wrong",   False), ("correct", True),
                      ("correct", True), ("correct", True)]:
        p = bkt_update(p, ok)
        print(f"   after {label:<8} → {p:.3f}   {mastery_icon(p)} {mastery_label(p)}")

    print("\n📉 Struggling student (5 wrong in a row):")
    p = 0.1
    for _ in range(5):
        p = bkt_update(p, False)
    print(f"   final mastery → {p:.3f}  {mastery_icon(p)} {mastery_label(p)}")

    print("\n📈 Rising student (7 correct in a row):")
    p = 0.1
    for _ in range(7):
        p = bkt_update(p, True)
    print(f"   final mastery → {p:.3f}  {mastery_icon(p)} {mastery_label(p)}")

    print("\n📊 Trajectory (mixed):")
    traj = bkt_sequence(0.1, [True, False, True, True, False, True, True, True])
    print("   " + " → ".join(f"{x:.2f}" for x in traj))

    print("\n⏰ Next review scheduling:")
    for p_val in (0.3, 0.6, 0.85):
        interval, ease, iso = next_review_date(p_val, last_interval_days=3)
        print(f"   mastery {p_val:.2f} → review in {interval:>2} day(s), ease={ease}")

    try:
        from database import get_db
        db = get_db()
        tracker = BKTTracker(db)
        stu = db.get_all_students().iloc[0]
        uid = stu["id"]
        cid = "c_frac"
        print(f"\n🧠 Live tracker on {stu['name']} / concept 'Fractions':")
        for ok in [False, True, False, True, True]:
            p = tracker.update_from_attempt(uid, cid, correct=ok, time_sec=25)
            print(f"   attempt ok={ok!s:<5} → p={p:.3f} "
                  f"{mastery_icon(p)} {mastery_label(p)}")

        print(f"\n   Predicted next correct: "
              f"{tracker.predict_correct(uid, cid) * 100:.1f}%")
        overall = tracker.overall_mastery(uid)
        print(f"   Overall for {stu['name']}: "
              f"{overall['avg_mastery']:.2f} avg · "
              f"{overall['mastered']} mastered · "
              f"{overall['developing']} developing · "
              f"{overall['weak']} weak")
    except Exception as e:
        print(f"\n⚠️  DB-backed tracker skipped: {e}")

    print("\n✅ models/bkt.py OK")
    print("=" * 60)
