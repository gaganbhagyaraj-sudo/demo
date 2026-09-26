# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  models/badges.py  ·  Automatic badge awarding engine
# =============================================================

from __future__ import annotations

import os
import sys

# --- make project root importable ---
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from datetime import datetime, timedelta, date
from typing import Optional, List, Dict

import pandas as pd

from config import BADGES, BADGE_BY_ID, SUBJECTS
from models.grading import (
    compute_row, zone_from_marks, improvement, color_transition,
)


# =============================================================
# 1. BADGE RULE DEFINITIONS
# =============================================================

# Each rule returns True/False for one (user, badge) pair.
# All rules are pure: they read from the DB but never write.

def _rule_perfect_attendance(db, user_id: str) -> bool:
    """100% attendance in the last 30 days (min 15 marked days)."""
    since = (date.today() - timedelta(days=30)).isoformat()
    df = db.query("""SELECT status FROM attendance
                     WHERE user_id=? AND att_date>=?""", (user_id, since))
    if df.empty or len(df) < 15:
        return False
    return bool((df["status"].isin(["P", "L", "E"])).all())


def _rule_aptitude_ace(db, user_id: str) -> bool:
    """Score ≥ 90% in any aptitude activity."""
    df = db.query("""
        SELECT s.percentage
        FROM activity_scores s
        JOIN activities a ON a.id = s.activity_id
        WHERE s.user_id=? AND a.type='aptitude'
    """, (user_id,))
    return bool(not df.empty and (df["percentage"] >= 90).any())


def _rule_brain_teaser_master(db, user_id: str) -> bool:
    """Complete 10 brain-teaser activities (or 10 attempts)."""
    df = db.query("""
        SELECT COUNT(*) AS n
        FROM activity_scores s
        JOIN activities a ON a.id = s.activity_id
        WHERE s.user_id=? AND a.type='brain_teaser'
    """, (user_id,))
    return bool(not df.empty and int(df.iloc[0]["n"]) >= 10)


def _rule_comeback_kid(db, user_id: str) -> bool:
    """
    Moved from red → green (or better) across IAs, using color_history.
    """
    df = db.query("""SELECT ia_number, zone FROM color_history
                     WHERE user_id=? ORDER BY ia_number""", (user_id,))
    if len(df) < 2:
        return False
    first = df.iloc[0]["zone"]
    last  = df.iloc[-1]["zone"]
    t = color_transition(first, last)
    return t["kind"] == "comeback"


def _rule_subject_topper(db, user_id: str) -> bool:
    """Student has the highest marks in any subject in their last IA."""
    last_ia = _last_ia_number(db, user_id)
    if last_ia is None:
        return False
    toppers = _subject_toppers_for_ia(db, last_ia)
    return user_id in toppers.values()


def _rule_consistent_performer(db, user_id: str) -> bool:
    """All three IAs have percentage ≥ 80."""
    df = db.query("""SELECT ia_number, percentage FROM marks_summary
                     WHERE user_id=? ORDER BY ia_number""", (user_id,))
    if len(df) < 3:
        return False
    return bool((df["percentage"] >= 80).all())


def _rule_all_rounder(db, user_id: str) -> bool:
    """Every subject ≥ 75 in the latest IA."""
    last_ia = _last_ia_number(db, user_id)
    if last_ia is None:
        return False
    row = _marks_row(db, user_id, last_ia)
    if not row:
        return False
    return all(row[s] >= 75 for s in SUBJECTS)


def _rule_streak_master(db, user_id: str) -> bool:
    """30-day learning streak (based on attempt dates)."""
    df = db.query("""SELECT DISTINCT DATE(created_at) AS d
                     FROM attempts WHERE user_id=?
                     ORDER BY d DESC""", (user_id,))
    if df.empty:
        return False
    dates = set(df["d"].tolist())
    today = date.today()
    streak = 0
    for i in range(30):
        d = (today - timedelta(days=i)).isoformat()
        if d in dates:
            streak += 1
        else:
            break
    return streak >= 30


def _rule_achiever(db, user_id: str) -> bool:
    """In the GOLD zone AND completed ≥ 3 activities."""
    last_ia = _last_ia_number(db, user_id)
    if last_ia is None:
        return False
    row = _marks_row(db, user_id, last_ia)
    if not row:
        return False
    info = zone_from_marks(row["Maths"], row["Physics"],
                           row["Chemistry"], row["Computer Science"])
    if info.zone != "gold":
        return False
    acts = db.query("SELECT COUNT(*) AS n FROM activity_scores WHERE user_id=?",
                    (user_id,))
    return bool(not acts.empty and int(acts.iloc[0]["n"]) >= 3)


def _rule_remedial_graduate(db, user_id: str) -> bool:
    """Completed a remedial session AND improved ≥ 20% across IAs."""
    attended = db.query("""
        SELECT COUNT(*) AS n
        FROM remedial_enrollments
        WHERE user_id=? AND attended=1
    """, (user_id,))
    if attended.empty or int(attended.iloc[0]["n"]) == 0:
        return False

    df = db.query("""SELECT ia_number, percentage FROM marks_summary
                     WHERE user_id=? ORDER BY ia_number""", (user_id,))
    if len(df) < 2:
        return False
    first = float(df.iloc[0]["percentage"])
    last  = float(df.iloc[-1]["percentage"])
    return (last - first) >= 20


# Map badge_id → rule function
BADGE_RULES = {
    "perfect_attendance":   _rule_perfect_attendance,
    "aptitude_ace":         _rule_aptitude_ace,
    "brain_teaser_master":  _rule_brain_teaser_master,
    "comeback_kid":         _rule_comeback_kid,
    "subject_topper":       _rule_subject_topper,
    "consistent_performer": _rule_consistent_performer,
    "all_rounder":          _rule_all_rounder,
    "streak_master":        _rule_streak_master,
    "achiever":             _rule_achiever,
    "remedial_graduate":    _rule_remedial_graduate,
}


# =============================================================
# 2. HELPERS
# =============================================================

def _last_ia_number(db, user_id: str) -> Optional[int]:
    df = db.query("""SELECT MAX(ia_number) AS ia FROM marks_summary
                     WHERE user_id=?""", (user_id,))
    if df.empty or pd.isna(df.iloc[0]["ia"]):
        return None
    return int(df.iloc[0]["ia"])


def _marks_row(db, user_id: str, ia_number: int) -> Optional[Dict[str, float]]:
    df = db.query("""SELECT subject, marks FROM marks
                     WHERE user_id=? AND ia_number=?""",
                  (user_id, ia_number))
    if df.empty:
        return None
    out = {s: 0.0 for s in SUBJECTS}
    for _, r in df.iterrows():
        out[r["subject"]] = float(r["marks"])
    return out


def _subject_toppers_for_ia(db, ia_number: int) -> Dict[str, str]:
    """Return {subject_name: user_id} for toppers in the given IA."""
    toppers = {}
    for subj in SUBJECTS:
        df = db.query("""
            SELECT user_id, marks FROM marks
            WHERE ia_number=? AND subject=?
            ORDER BY marks DESC LIMIT 1
        """, (ia_number, subj))
        if not df.empty:
            toppers[subj] = df.iloc[0]["user_id"]
    return toppers


# =============================================================
# 3. BADGE ENGINE
# =============================================================

class BadgeEngine:
    """
    Evaluates all badge rules for a user and awards any newly-earned badges.
    Safe to call after: saving marks, marking attendance, logging activity.
    """

    def __init__(self, db):
        self.db = db

    # ---------- public ----------

    def evaluate_user(self, user_id: str) -> List[dict]:
        """
        Check all badge rules for one user. Award new badges.
        Returns the list of NEWLY awarded badges (may be empty).
        """
        awarded = []
        for badge in BADGES:
            bid = badge["id"]
            rule = BADGE_RULES.get(bid)
            if not rule:
                continue
            if self._already_has(user_id, bid):
                continue
            try:
                if rule(self.db, user_id):
                    self.db.award_badge(user_id, bid, note="auto")
                    awarded.append(badge)
            except Exception:
                # never let a badge rule crash the app
                pass
        return awarded

    def evaluate_all_students(self) -> Dict[str, List[dict]]:
        """Run rules for every student. Returns {user_id: [new_badges]}."""
        results = {}
        students = self.db.get_all_students()
        for _, s in students.iterrows():
            new = self.evaluate_user(s["id"])
            if new:
                results[s["id"]] = new
        return results

    def preview_user(self, user_id: str) -> List[dict]:
        """
        Return list of badges the user WOULD earn if we ran evaluate_user,
        without persisting. Useful for a 'stretch goals' UI on the profile.
        """
        would = []
        for badge in BADGES:
            bid = badge["id"]
            rule = BADGE_RULES.get(bid)
            if not rule or self._already_has(user_id, bid):
                continue
            try:
                if rule(self.db, user_id):
                    would.append(badge)
            except Exception:
                pass
        return would

    def progress_for_user(self, user_id: str) -> List[dict]:
        """
        Return a list of all badges with status:
          {badge, earned: bool, earned_at: str|None}
        Perfect for the profile badge showcase wall.
        """
        earned_map = {}
        df = self.db.get_user_badges(user_id)
        for _, r in df.iterrows():
            earned_map[r["id"]] = r["earned_at"]

        out = []
        for badge in BADGES:
            out.append({
                "badge":     badge,
                "earned":    badge["id"] in earned_map,
                "earned_at": earned_map.get(badge["id"]),
            })
        return out

    # ---------- internals ----------

    def _already_has(self, user_id: str, badge_id: str) -> bool:
        df = self.db.query("""
            SELECT 1 FROM user_badges
            WHERE user_id=? AND badge_id=? LIMIT 1
        """, (user_id, badge_id))
        return not df.empty


# =============================================================
# 4. CONVENIENCE FUNCTIONS
# =============================================================

def evaluate_user_badges(db, user_id: str) -> List[dict]:
    return BadgeEngine(db).evaluate_user(user_id)


def evaluate_all_badges(db) -> Dict[str, List[dict]]:
    return BadgeEngine(db).evaluate_all_students()


def badge_progress(db, user_id: str) -> List[dict]:
    return BadgeEngine(db).progress_for_user(user_id)


# =============================================================
# 5. SANITY CHECK
# =============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  SHRUTHI JHARI — models/badges.py sanity check")
    print("=" * 60)

    try:
        from database import get_db
        db = get_db()
        engine = BadgeEngine(db)

        print("\n📋 Badge rules loaded:")
        for bid in BADGE_RULES:
            meta = BADGE_BY_ID[bid]
            print(f"   {meta['icon']} {meta['name']:<22} — {meta['desc']}")

        print("\n🧪 Preview (dry-run) for each student:")
        students = db.get_all_students()
        for _, s in students.head(5).iterrows():
            would = engine.preview_user(s["id"])
            have = db.get_user_badges(s["id"])
            names = ", ".join(b["name"] for b in would) or "—"
            print(f"   {s['name']:<20} have={len(have):>2}  "
                  f"would-earn: {names}")

        print("\n⚡ Running full evaluation across all students...")
        results = engine.evaluate_all_students()
        if not results:
            print("   (no new badges)")
        for uid, new in results.items():
            user = db.get_user(uid)
            for b in new:
                print(f"   ✅ {user['name']:<20} earned {b['icon']} {b['name']}")

        print("\n🏅 Showcase wall for first student:")
        stu = students.iloc[0]
        wall = engine.progress_for_user(stu["id"])
        earned = [w for w in wall if w["earned"]]
        locked = [w for w in wall if not w["earned"]]
        print(f"   {stu['name']} — {len(earned)}/{len(wall)} badges")
        for w in earned:
            b = w["badge"]
            print(f"     {b['icon']} {b['name']:<22} earned {w['earned_at'][:10]}")
        print("   Locked:")
        for w in locked[:5]:
            b = w["badge"]
            print(f"     🔒 {b['name']:<22} — {b['desc']}")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n⚠️  {e}")

    print("\n✅ models/badges.py OK")
    print("=" * 60)