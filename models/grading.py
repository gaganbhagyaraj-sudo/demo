# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  models/grading.py  ·  Grade + Zone engine
# =============================================================

from __future__ import annotations

import os
import sys

# --- make project root importable ---
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from dataclasses import dataclass
from typing import Optional

from config import (
    GRADE_SCALE, GRADE_ORDER,
    SUBJECTS, SUBJECT_COLUMNS, MARKS_MAX, TOTAL_MAX,
    ZONE_RULES, RED_TRIGGER_SUBJECT,
    ZONE_COLORS, ZONE_LABELS, ZONE_ICONS,
)


# =============================================================
# 1. GRADE  (percentage → letter grade)
# =============================================================

@dataclass(frozen=True)
class GradeInfo:
    grade: str          # O / A+ / A / B+ / B / C / F
    label: str          # Outstanding / Excellent / ...
    color: str          # hex
    min_percent: int    # lower bound


def grade_from_percent(pct: float) -> GradeInfo:
    """Return GradeInfo for a given percentage (0–100)."""
    pct = float(pct)
    for min_p, g, label, color in GRADE_SCALE:
        if pct >= min_p:
            return GradeInfo(grade=g, label=label, color=color,
                             min_percent=min_p)
    # fallback
    g, label, color = GRADE_SCALE[-1][1], GRADE_SCALE[-1][2], GRADE_SCALE[-1][3]
    return GradeInfo(grade=g, label=label, color=color,
                     min_percent=GRADE_SCALE[-1][0])


def grade_letter(pct: float) -> str:
    return grade_from_percent(pct).grade


def grade_label(pct: float) -> str:
    return grade_from_percent(pct).label


def grade_color(pct: float) -> str:
    return grade_from_percent(pct).color


def grade_index(grade_letter: str) -> int:
    """0 = best (O), higher = worse."""
    try:
        return GRADE_ORDER.index(grade_letter)
    except ValueError:
        return len(GRADE_ORDER) - 1


def is_pass(pct: float) -> bool:
    return grade_letter(pct) != "F"


# =============================================================
# 2. SUBJECT-LEVEL HELPERS
# =============================================================

def subject_percent(marks: float, max_marks: float = MARKS_MAX) -> float:
    if not max_marks:
        return 0.0
    return round((float(marks) / float(max_marks)) * 100, 2)


def subject_grade(marks: float, max_marks: float = MARKS_MAX) -> GradeInfo:
    return grade_from_percent(subject_percent(marks, max_marks))


def subject_color(marks: float, max_marks: float = MARKS_MAX) -> str:
    return subject_grade(marks, max_marks).color


# =============================================================
# 3. ZONE (Red / Yellow / Green / Gold)
# =============================================================

@dataclass(frozen=True)
class ZoneInfo:
    zone: str           # red / yellow / green / gold
    label: str          # At Risk / Developing / Strong / Achiever
    color: str          # hex
    icon: str           # 🔴 / 🟡 / 🟢 / 🏆
    percentage: float
    total: float
    grade: str
    min_subject: float
    reason: str         # human-readable why this zone


def zone_from_marks(maths: float, phy: float,
                    che: float, cs: float,
                    max_per_subject: float = MARKS_MAX) -> ZoneInfo:
    """
    Compute the full ZoneInfo from 4 subject marks.

    Rules (priority order):
      1. Any subject below RED_TRIGGER_SUBJECT  → red
      2. pct ≥ 90 AND every subject ≥ 85       → gold
      3. pct ≥ 75 AND every subject ≥ 60       → green
      4. pct ≥ 50                              → yellow
      5. otherwise                             → red
    """
    subjects = {
        "Maths":            float(maths),
        "Physics":          float(phy),
        "Chemistry":        float(che),
        "Computer Science": float(cs),
    }
    total = round(sum(subjects.values()), 2)
    pct = round((total / (max_per_subject * 4)) * 100, 2) if max_per_subject else 0
    min_subject = round(min(subjects.values()), 2)
    grade_info = grade_from_percent(pct)

    # --- decide zone ---
    reason = ""
    if min_subject < RED_TRIGGER_SUBJECT:
        zone = "red"
        low = [s for s, m in subjects.items() if m < RED_TRIGGER_SUBJECT]
        reason = f"Below {RED_TRIGGER_SUBJECT} in {', '.join(low)}"
    elif (pct >= ZONE_RULES["gold"]["min_percent"]
          and min_subject >= ZONE_RULES["gold"]["min_subject"]):
        zone = "gold"
        reason = "Outstanding across all subjects"
    elif (pct >= ZONE_RULES["green"]["min_percent"]
          and min_subject >= ZONE_RULES["green"]["min_subject"]):
        zone = "green"
        reason = "Strong performance with no weak subject"
    elif pct >= ZONE_RULES["yellow"]["min_percent"]:
        zone = "yellow"
        reason = "Average — needs targeted support"
    else:
        zone = "red"
        reason = f"Overall percentage below {ZONE_RULES['yellow']['min_percent']}%"

    return ZoneInfo(
        zone=zone,
        label=ZONE_LABELS[zone],
        color=ZONE_COLORS[zone],
        icon=ZONE_ICONS[zone],
        percentage=pct,
        total=total,
        grade=grade_info.grade,
        min_subject=min_subject,
        reason=reason,
    )


def zone_from_dict(marks: dict, max_per_subject: float = MARKS_MAX) -> ZoneInfo:
    """Convenience wrapper: marks dict must contain keys for all 4 subjects."""
    return zone_from_marks(
        marks.get("Maths", 0),
        marks.get("Physics", 0),
        marks.get("Chemistry", 0),
        marks.get("Computer Science", 0),
        max_per_subject=max_per_subject,
    )


def zone_color(zone: str) -> str:
    return ZONE_COLORS.get(zone, "#94A3B8")


def zone_label(zone: str) -> str:
    return ZONE_LABELS.get(zone, "—")


def zone_icon(zone: str) -> str:
    return ZONE_ICONS.get(zone, "•")


# =============================================================
# 4. TREND / IMPROVEMENT
# =============================================================

def improvement(before_pct: float, after_pct: float) -> dict:
    """Compare two percentages and describe the change."""
    delta = round(after_pct - before_pct, 2)
    if delta >= 15:
        kind = "big_gain"
    elif delta >= 5:
        kind = "gain"
    elif delta <= -15:
        kind = "big_drop"
    elif delta <= -5:
        kind = "drop"
    else:
        kind = "stable"

    return {
        "delta":  delta,
        "kind":   kind,
        "label":  {
            "big_gain": "Major improvement",
            "gain":     "Improving",
            "stable":   "Stable",
            "drop":     "Slipping",
            "big_drop": "Sharp decline",
        }[kind],
        "icon": {
            "big_gain": "📈",
            "gain":     "↗",
            "stable":   "→",
            "drop":     "↘",
            "big_drop": "📉",
        }[kind],
        "color": {
            "big_gain": "#10B981",
            "gain":     "#34D399",
            "stable":   "#94A3B8",
            "drop":     "#F59E0B",
            "big_drop": "#EF4444",
        }[kind],
    }


def color_transition(from_zone: str, to_zone: str) -> dict:
    """Describe a zone transition (e.g. red → green = comeback)."""
    rank = {"red": 0, "yellow": 1, "green": 2, "gold": 3}
    delta = rank.get(to_zone, 0) - rank.get(from_zone, 0)
    if delta >= 2:
        kind = "comeback"
        label = "Comeback Kid"
        icon = "🚀"
    elif delta == 1:
        kind = "improved"
        label = "Improving"
        icon = "📈"
    elif delta == 0:
        kind = "stable"
        label = "Steady"
        icon = "→"
    elif delta == -1:
        kind = "slipped"
        label = "Slipped"
        icon = "↘"
    else:
        kind = "declined"
        label = "Declining"
        icon = "📉"
    return {"kind": kind, "label": label, "icon": icon, "delta": delta}


# =============================================================
# 5. BULK HELPERS  (for entire sheets of marks)
# =============================================================

def compute_row(maths: float, phy: float, che: float, cs: float,
                max_per_subject: float = MARKS_MAX) -> dict:
    """
    One-stop helper used by the marks-entry page and Excel importer.
    Returns everything you need for a single student's row.
    """
    info = zone_from_marks(maths, phy, che, cs, max_per_subject)
    return {
        "maths":           round(float(maths), 2),
        "phy":             round(float(phy),   2),
        "che":             round(float(che),   2),
        "cs":              round(float(cs),    2),
        "total":           info.total,
        "percentage":      info.percentage,
        "grade":           info.grade,
        "grade_label":     grade_label(info.percentage),
        "grade_color":     grade_color(info.percentage),
        "zone":            info.zone,
        "zone_label":      info.label,
        "zone_color":      info.color,
        "zone_icon":       info.icon,
        "min_subject":     info.min_subject,
        "reason":          info.reason,
        "is_pass":         is_pass(info.percentage),
    }


def classify_rows(rows: list) -> dict:
    """
    Given a list of dicts with keys maths/phy/che/cs, return:
      - zone_counts     : {red, yellow, green, gold}
      - grade_counts    : {O, A+, A, B+, B, C, F}
      - subject_averages: {Maths, Physics, Chemistry, CS}
      - topper          : row with highest percentage
      - failing         : list of rows with any subject < 40
    """
    if not rows:
        return {
            "zone_counts":      {"red": 0, "yellow": 0, "green": 0, "gold": 0},
            "grade_counts":     {g: 0 for g in GRADE_ORDER},
            "subject_averages": {s: 0 for s in SUBJECTS},
            "topper":           None,
            "failing":          [],
        }

    zone_counts = {"red": 0, "yellow": 0, "green": 0, "gold": 0}
    grade_counts = {g: 0 for g in GRADE_ORDER}
    failing = []
    sums = {s: 0.0 for s in SUBJECTS}
    best = None

    for r in rows:
        info = compute_row(r["maths"], r["phy"], r["che"], r["cs"])
        zone_counts[info["zone"]] += 1
        grade_counts[info["grade"]] = grade_counts.get(info["grade"], 0) + 1
        sums["Maths"]            += info["maths"]
        sums["Physics"]          += info["phy"]
        sums["Chemistry"]        += info["che"]
        sums["Computer Science"] += info["cs"]

        if not info["is_pass"] or info["min_subject"] < RED_TRIGGER_SUBJECT:
            failing.append(r)

        if best is None or info["percentage"] > best["percentage"]:
            best = {**r, **info}

    n = len(rows)
    subject_averages = {s: round(sums[s] / n, 2) for s in SUBJECTS}

    return {
        "zone_counts":      zone_counts,
        "grade_counts":     grade_counts,
        "subject_averages": subject_averages,
        "topper":           best,
        "failing":          failing,
    }


# =============================================================
# 6. SANITY CHECK
# =============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  SHRUTHI JHARI — models/grading.py sanity check")
    print("=" * 60)

    # ---- grade scale ----
    print("\n📊 Grade scale:")
    for pct in [95, 85, 75, 65, 55, 45, 30]:
        g = grade_from_percent(pct)
        print(f"   {pct:>3}%  →  {g.grade:<3} {g.label:<12} {g.color}")

    # ---- zone checks ----
    print("\n🎨 Zone classification:")
    test_cases = [
        ("Gold achiever",    92, 88, 95, 90),
        ("Green strong",     82, 78, 75, 80),
        ("Yellow medium",    62, 58, 55, 68),
        ("Red low",          35, 45, 40, 50),
        ("Red forced",       85, 30, 80, 88),
        ("Borderline pass",  45, 42, 48, 44),
    ]
    for label, m, p, c, cs in test_cases:
        info = zone_from_marks(m, p, c, cs)
        print(f"   {label:<18} → {info.icon} {info.zone:<7} "
              f"({info.percentage}%, grade {info.grade}) — {info.reason}")

    # ---- improvement ----
    print("\n📈 Improvement analysis:")
    for before, after in [(30, 78), (55, 62), (60, 60), (70, 62), (85, 60)]:
        imp = improvement(before, after)
        print(f"   {before}% → {after}%  : {imp['icon']} {imp['label']:<18} ({imp['delta']:+.1f})")

    # ---- color transition ----
    print("\n🎬 Zone transitions:")
    for frm, to in [("red", "green"), ("red", "yellow"),
                    ("yellow", "green"), ("green", "green"),
                    ("green", "red")]:
        t = color_transition(frm, to)
        print(f"   {frm:<7} → {to:<7}  {t['icon']} {t['label']}")

    # ---- bulk classify ----
    print("\n📦 Bulk classify sample (5 students):")
    rows = [
        {"name": "A", "maths": 92, "phy": 88, "che": 95, "cs": 90},
        {"name": "B", "maths": 82, "phy": 78, "che": 75, "cs": 80},
        {"name": "C", "maths": 62, "phy": 58, "che": 55, "cs": 68},
        {"name": "D", "maths": 35, "phy": 45, "che": 40, "cs": 50},
        {"name": "E", "maths": 85, "phy": 30, "che": 80, "cs": 88},
    ]
    summary = classify_rows(rows)
    print(f"   Zone counts  : {summary['zone_counts']}")
    print(f"   Topper       : {summary['topper']['name']} "
          f"({summary['topper']['percentage']}%)")
    print(f"   Failing rows : {[r['name'] for r in summary['failing']]}")
    print(f"   Subject avg  : {summary['subject_averages']}")

    print("\n✅ models/grading.py OK")
    print("=" * 60)