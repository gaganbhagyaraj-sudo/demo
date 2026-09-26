# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  models/recommender.py  ·  Next-Best-Content recommendation engine
# =============================================================

from __future__ import annotations

import os
import sys

# --- make project root importable ---
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd

from config import MASTERY_THRESHOLDS, SUBJECTS
from models.bkt import (
    BKTTracker, DEFAULT_PARAMS,
    mastery_label, mastery_color, mastery_icon,
)


# =============================================================
# 1. WEIGHTS
# =============================================================

WEIGHTS = {
    "mastery_gap":  0.30,
    "prereq_ready": 0.25,
    "interest":     0.20,
    "difficulty":   0.15,
    "review_due":   0.05,
    "freshness":    0.05,
}

# Target success rate for the "sweet spot" (ZPD)
ZPD_TARGET = 0.70


# =============================================================
# 2. DATA STRUCTURES
# =============================================================

@dataclass
class Recommendation:
    concept_id: str
    concept_name: str
    subject: str
    difficulty: int
    p_mastery: float
    score: float
    reason: str
    mastery_label: str = ""
    mastery_color: str = ""
    mastery_icon: str = ""
    content: list = field(default_factory=list)   # list of content rows

    def __post_init__(self):
        self.mastery_label = mastery_label(self.p_mastery)
        self.mastery_color = mastery_color(self.p_mastery)
        self.mastery_icon  = mastery_icon(self.p_mastery)


# =============================================================
# 3. RECOMMENDER
# =============================================================

class Recommender:
    """
    Content recommendation engine driven by mastery + prerequisites +
    interests + difficulty + spaced-repetition + freshness.
    """

    def __init__(self, db, tracker: Optional[BKTTracker] = None):
        self.db = db
        self.tracker = tracker or BKTTracker(db)

    # ---------- public API ----------

    def next_best(self, user_id: str, top_k: int = 5) -> list:
        """
        Return the top-K recommendations as Recommendation objects.
        The FIRST one is "Today's Path".
        """
        mastery_df = self.tracker.summary(user_id).set_index("concept_id")
        interests = set(self.db.get_user_interests(user_id))
        concepts_df = self.db.query("SELECT * FROM concepts ORDER BY difficulty")
        content_df = self.db.query("SELECT * FROM content")

        # Detect recently-served content types to penalize repetition
        recent = self._recent_content_types(user_id)

        scored = []
        for _, c in concepts_df.iterrows():
            cid = c["id"]

            p_mastery = (float(mastery_df.loc[cid, "p_mastery"])
                         if cid in mastery_df.index else DEFAULT_PARAMS.init)

            # Signal 1 — mastery gap (sweet spot: 0.4 < p < 0.75)
            mastery_gap = self._mastery_gap_score(p_mastery)

            # Signal 2 — prerequisite readiness
            prereq_score = 1.0 if self.tracker.concept_ready(user_id, cid) else 0.2

            # Signal 3 — interest match
            items = content_df[content_df["concept_id"] == cid]
            has_interest_hit = (
                items["interest_tag"].isin(interests).any()
                if not items.empty else False
            )
            interest_score = 1.0 if has_interest_hit else 0.4

            # Signal 4 — difficulty fit (ZPD)
            difficulty_score = self._difficulty_fit(p_mastery, int(c["difficulty"]))

            # Signal 5 — review due?
            review_score = self._review_due_score(user_id, cid)

            # Signal 6 — freshness (avoid same content type as recent)
            freshness_score = self._freshness_score(items, recent)

            score = (
                WEIGHTS["mastery_gap"]  * mastery_gap +
                WEIGHTS["prereq_ready"] * prereq_score +
                WEIGHTS["interest"]     * interest_score +
                WEIGHTS["difficulty"]   * difficulty_score +
                WEIGHTS["review_due"]   * review_score +
                WEIGHTS["freshness"]    * freshness_score
            )

            reason = self._build_reason(
                c["name"], p_mastery, prereq_score,
                has_interest_hit, review_score,
                mastery_df, cid)

            # Pick best-matching content items for this concept
            content_rows = self._pick_content_for_concept(
                items, interests)

            scored.append(Recommendation(
                concept_id=cid,
                concept_name=c["name"],
                subject=c["subject"],
                difficulty=int(c["difficulty"]),
                p_mastery=round(p_mastery, 4),
                score=round(float(score), 4),
                reason=reason,
                content=content_rows,
            ))

        scored.sort(key=lambda r: (-r.score, r.difficulty))
        return scored[:top_k]

    def todays_path(self, user_id: str) -> Optional[Recommendation]:
        """The single best thing to do RIGHT NOW."""
        recs = self.next_best(user_id, top_k=1)
        return recs[0] if recs else None

    def weak_priority_list(self, user_id: str, top_k: int = 5) -> list:
        """
        Concepts that need remedial attention: low mastery + prereqs OK.
        Different from next_best — this is for facilitators deciding what
        to reteach, not what the student should self-study next.
        """
        mastery_df = self.tracker.summary(user_id).set_index("concept_id")
        concepts = self.db.query("SELECT * FROM concepts")

        rows = []
        for _, c in concepts.iterrows():
            cid = c["id"]
            if cid not in mastery_df.index:
                continue
            p = float(mastery_df.loc[cid, "p_mastery"])
            if p >= MASTERY_THRESHOLDS["weak"]:
                continue
            rows.append({
                "concept_id":    cid,
                "concept_name":  c["name"],
                "subject":       c["subject"],
                "difficulty":    int(c["difficulty"]),
                "p_mastery":     round(p, 4),
                "mastery_label": mastery_label(p),
                "mastery_icon":  mastery_icon(p),
                "mastery_color": mastery_color(p),
            })
        rows.sort(key=lambda r: (r["p_mastery"], r["difficulty"]))
        return rows[:top_k]

    def reason_for(self, user_id: str, concept_id: str) -> str:
        """Explain in one sentence why this concept was recommended."""
        mastery_df = self.tracker.summary(user_id).set_index("concept_id")
        p = (float(mastery_df.loc[concept_id, "p_mastery"])
             if concept_id in mastery_df.index else DEFAULT_PARAMS.init)
        interests = self.db.get_user_interests(user_id)
        return (
            f"You're at {int(p*100)}% mastery on this concept. "
            f"Personalized for your interests: {', '.join(interests) or 'general'}."
        )

    # ---------- internals ----------

    def _mastery_gap_score(self, p: float) -> float:
        """
        Peak score when p ≈ 0.55 (learning zone).
        Low when p near 0 (too hard) or p near 1 (already mastered).
        """
        ideal = 0.55
        return round(max(0.0, 1.0 - abs(p - ideal) / 0.55), 4)

    def _difficulty_fit(self, p_mastery: float, difficulty: int) -> float:
        """
        Difficulty 1..5. If student's mastery is high, harder concepts fit.
        expected_difficulty = 1 + 4 * p_mastery   (1..5)
        """
        expected = 1.0 + 4.0 * p_mastery
        return round(max(0.0, 1.0 - abs(expected - difficulty) / 4.0), 4)

    def _review_due_score(self, user_id: str, concept_id: str) -> float:
        try:
            df = self.db.query(
                """SELECT next_review_at FROM mastery
                   WHERE user_id=? AND concept_id=?""",
                (user_id, concept_id))
            if df.empty or not df.iloc[0]["next_review_at"]:
                return 0.3
            nxt = df.iloc[0]["next_review_at"]
            try:
                nxt_dt = datetime.fromisoformat(nxt)
            except Exception:
                return 0.3
            return 1.0 if nxt_dt <= datetime.now() else 0.2
        except Exception:
            return 0.3

    def _recent_content_types(self, user_id: str, lookback: int = 10) -> set:
        df = self.db.query("""
            SELECT c.type
            FROM attempts a
            JOIN content c ON c.id = a.content_id
            WHERE a.user_id=?
            ORDER BY a.created_at DESC
            LIMIT ?
        """, (user_id, lookback))
        return set(df["type"].tolist()) if not df.empty else set()

    def _freshness_score(self, items: pd.DataFrame, recent: set) -> float:
        if items.empty:
            return 0.5
        types = set(items["type"].tolist())
        if not types:
            return 0.5
        # If the concept has types the student hasn't seen recently → fresher
        new_types = types - recent
        return 1.0 if new_types else 0.3

    def _pick_content_for_concept(self, items: pd.DataFrame,
                                  interests: set,
                                  limit: int = 3) -> list:
        """Rank content items: interest-tagged first, then by difficulty."""
        if items.empty:
            return []
        items = items.copy()
        items["interest_hit"] = items["interest_tag"].apply(
            lambda t: 1 if (t and t in interests) else 0)
        items = items.sort_values(
            by=["interest_hit", "difficulty"],
            ascending=[False, True])
        out = []
        for _, r in items.head(limit).iterrows():
            out.append({
                "id":           r["id"],
                "type":         r["type"],
                "title":        r["title"],
                "body":         r["body"],
                "interest_tag": r["interest_tag"],
                "difficulty":   int(r["difficulty"]),
                "est_minutes":  int(r["est_minutes"] or 10),
            })
        return out

    def _build_reason(self, name, p, prereq_score, interest_hit,
                      review_score, mastery_df, cid) -> str:
        parts = []
        if p < 0.4:
            parts.append("you're still building this up")
        elif p < 0.75:
            parts.append("you're close to mastering this")
        else:
            parts.append("maintain this skill")

        if prereq_score < 0.5:
            parts.append("but prerequisites need review first")
        if interest_hit:
            parts.append("personalized to your interests")
        if review_score >= 1.0:
            parts.append("scheduled for review today")
        return f"{name}: " + ", ".join(parts).capitalize() + "."


# =============================================================
# 4. SANITY CHECK
# =============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  SHRUTHI JHARI — models/recommender.py sanity check")
    print("=" * 60)

    try:
        from database import get_db
        db = get_db()
        rec = Recommender(db)

        students = db.get_all_students()
        stu = students.iloc[0]
        print(f"\n👤 Student: {stu['name']}  ({stu['usn']})")
        print(f"   Interests: {', '.join(db.get_user_interests(stu['id'])) or '—'}")

        print("\n🎯 Today's Path (top recommendation):")
        today = rec.todays_path(stu["id"])
        if today:
            print(f"   {today.mastery_icon} {today.concept_name} "
                  f"({today.subject} · diff {today.difficulty})")
            print(f"   mastery: {today.p_mastery:.2f}  score: {today.score:.3f}")
            print(f"   reason:  {today.reason}")
            if today.content:
                print("   content:")
                for c in today.content:
                    tag = f" [{c['interest_tag']}]" if c["interest_tag"] else ""
                    print(f"     · {c['type']:<8} {c['title']}{tag}")

        print("\n📚 Top 5 recommendations:")
        for i, r in enumerate(rec.next_best(stu["id"], top_k=5), 1):
            print(f"   {i}. {r.mastery_icon} {r.concept_name:<18} "
                  f"({r.subject:<18})  score={r.score:.3f}  p={r.p_mastery:.2f}")

        print("\n🩺 Weak priority list (for facilitator):")
        for r in rec.weak_priority_list(stu["id"], top_k=5):
            print(f"   {r['mastery_icon']} {r['concept_name']:<18} "
                  f"p={r['p_mastery']:.2f}  diff={r['difficulty']}")

        print("\n👥 Quick scan across all students (top pick each):")
        for _, s in students.head(5).iterrows():
            t = rec.todays_path(s["id"])
            if t:
                print(f"   {s['name']:<20} → "
                      f"{t.mastery_icon} {t.concept_name:<18} "
                      f"(p={t.p_mastery:.2f}, score={t.score:.2f})")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n⚠️  {e}")

    print("\n✅ models/recommender.py OK")
    print("=" * 60)