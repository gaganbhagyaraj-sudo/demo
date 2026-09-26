# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  models/clustering.py  ·  Student segmentation (sklearn KMeans)
# =============================================================

from __future__ import annotations

import os
import sys

# --- make project root importable ---
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from typing import Optional, List, Dict

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

from config import SUBJECTS


# =============================================================
# 1. FEATURE BUILDER
# =============================================================

FEATURE_COLUMNS = [
    "avg_marks",       # average of 4 subjects in latest IA
    "ia_trend",        # IA-3 − IA-1 (improvement direction)
    "attendance_pct",  # 0..100
    "activity_count",  # # of logged activity scores
    "min_subject",     # weakest subject mark
]

SEGMENT_NAMES = ["Needs Support", "Developing", "Advanced"]

SEGMENT_COLORS = {
    "Needs Support": "#EF4444",
    "Developing":    "#F59E0B",
    "Advanced":      "#10B981",
}

SEGMENT_ICONS = {
    "Needs Support": "🔴",
    "Developing":    "🟡",
    "Advanced":      "🟢",
}


def build_features(db, ia_number: Optional[int] = None) -> pd.DataFrame:
    """
    Return a DataFrame: one row per student with clustering features.

    Columns:
        user_id, usn, name,
        avg_marks, ia_trend, attendance_pct,
        activity_count, min_subject
    """
    students = db.get_all_students()

    # Pick latest IA if not given
    if ia_number is None:
        last_ia = db.query(
            "SELECT MAX(ia_number) AS ia FROM marks_summary")
        ia_number = int(last_ia.iloc[0]["ia"] or 1)

    # Pre-fetch aggregates
    summary = db.query("""
        SELECT u.id AS user_id, u.usn, u.name,
               ms.ia_number, ms.maths, ms.phy, ms.che, ms.cs,
               ms.percentage
        FROM marks_summary ms
        JOIN users u ON u.id = ms.user_id
        WHERE u.role='student' AND u.status='approved'
        ORDER BY u.usn, ms.ia_number
    """)

    att = db.query("""
        SELECT user_id,
               SUM(CASE WHEN status IN ('P','L','E') THEN 1 ELSE 0 END) AS present,
               COUNT(*) AS total
        FROM attendance
        GROUP BY user_id
    """)

    acts = db.query("""
        SELECT user_id, COUNT(*) AS n
        FROM activity_scores
        GROUP BY user_id
    """)

    rows = []
    for _, s in students.iterrows():
        uid = s["id"]

        student_marks = summary[summary["user_id"] == uid]
        if student_marks.empty:
            avg_marks = 0.0
            trend = 0.0
            min_subject = 0.0
        else:
            latest = student_marks[
                student_marks["ia_number"] == student_marks["ia_number"].max()]
            latest = latest.iloc[0]
            avg_marks = float(np.mean([latest["maths"], latest["phy"],
                                       latest["che"], latest["cs"]]))
            min_subject = float(min([latest["maths"], latest["phy"],
                                     latest["che"], latest["cs"]]))

            if len(student_marks) >= 2:
                first = student_marks.iloc[0]
                last = student_marks.iloc[-1]
                trend = float(last["percentage"] - first["percentage"])
            else:
                trend = 0.0

        # Attendance
        ar = att[att["user_id"] == uid]
        if not ar.empty and int(ar.iloc[0]["total"]) > 0:
            attendance_pct = float(
                (ar.iloc[0]["present"] / ar.iloc[0]["total"]) * 100)
        else:
            attendance_pct = 0.0

        # Activities
        ac = acts[acts["user_id"] == uid]
        activity_count = int(ac.iloc[0]["n"]) if not ac.empty else 0

        rows.append({
            "user_id":        uid,
            "usn":            s["usn"],
            "name":           s["name"],
            "avg_marks":      round(avg_marks, 2),
            "ia_trend":       round(trend, 2),
            "attendance_pct": round(attendance_pct, 2),
            "activity_count": activity_count,
            "min_subject":    round(min_subject, 2),
        })

    return pd.DataFrame(rows)


# =============================================================
# 2. CLUSTERING
# =============================================================

def cluster_students(db,
                     n_clusters: int = 3,
                     ia_number: Optional[int] = None,
                     random_state: int = 42) -> pd.DataFrame:
    """
    Cluster students into segments.

    Returns the feature DataFrame with added columns:
        cluster          (int label)
        segment          ("Needs Support" / "Developing" / "Advanced")
        segment_color    (hex)
        segment_icon     (emoji)
        pca_x, pca_y     (2D coordinates for scatter visualizations)
    """
    df = build_features(db, ia_number=ia_number)
    if df.empty:
        return df

    # Scale features
    X = df[FEATURE_COLUMNS].values.astype(float)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Choose k — never more than students, min 2
    k = max(1, min(n_clusters, len(df)))
    if k < 2 or len(df) < 3:
        # Fallback: single segment
        df["cluster"] = 0
        df["segment"] = _name_by_score(df)
        df["segment_color"] = df["segment"].map(SEGMENT_COLORS)
        df["segment_icon"] = df["segment"].map(SEGMENT_ICONS)
        df["pca_x"] = 0.0
        df["pca_y"] = 0.0
        return df

    km = KMeans(n_clusters=k, n_init=10, random_state=random_state)
    labels = km.fit_predict(X_scaled)
    df["cluster"] = labels

    # Rename clusters by avg performance
    cluster_order = (df.groupby("cluster")["avg_marks"]
                     .mean()
                     .sort_values()
                     .index.tolist())
    mapping = {cid: SEGMENT_NAMES[i] for i, cid in enumerate(cluster_order)}
    df["segment"] = df["cluster"].map(mapping)
    df["segment_color"] = df["segment"].map(SEGMENT_COLORS)
    df["segment_icon"] = df["segment"].map(SEGMENT_ICONS)

    # PCA for visualization
    try:
        pca = PCA(n_components=2, random_state=random_state)
        coords = pca.fit_transform(X_scaled)
        df["pca_x"] = coords[:, 0]
        df["pca_y"] = coords[:, 1]
    except Exception:
        df["pca_x"] = 0.0
        df["pca_y"] = 0.0

    return df


def _name_by_score(df: pd.DataFrame) -> pd.Series:
    """Fallback naming when k<2."""
    def classify(avg, att, acts):
        score = 0.6 * (avg / 100) + 0.25 * (att / 100) + 0.15 * min(1, acts / 3)
        if score < 0.5:
            return "Needs Support"
        if score < 0.75:
            return "Developing"
        return "Advanced"
    return df.apply(
        lambda r: classify(r["avg_marks"], r["attendance_pct"],
                           r["activity_count"]), axis=1)


# =============================================================
# 3. SEGMENT SUMMARY
# =============================================================

def segment_summary(df: pd.DataFrame) -> List[dict]:
    """
    Group the clustered DataFrame into segment-level stats.
    Each item:
        {segment, icon, color, count, avg_marks, avg_attendance,
         avg_trend, students: [names...]}
    """
    if df.empty or "segment" not in df.columns:
        return []
    out = []
    for seg in SEGMENT_NAMES:
        sub = df[df["segment"] == seg]
        if sub.empty:
            continue
        out.append({
            "segment":        seg,
            "icon":           SEGMENT_ICONS[seg],
            "color":          SEGMENT_COLORS[seg],
            "count":          int(len(sub)),
            "avg_marks":      round(float(sub["avg_marks"].mean()), 2),
            "avg_attendance": round(float(sub["attendance_pct"].mean()), 2),
            "avg_trend":      round(float(sub["ia_trend"].mean()), 2),
            "avg_activities": round(float(sub["activity_count"].mean()), 2),
            "students":       sub["name"].tolist(),
        })
    return out


def students_in_segment(df: pd.DataFrame, segment: str) -> pd.DataFrame:
    if df.empty or "segment" not in df.columns:
        return df
    return df[df["segment"] == segment].sort_values(
        "avg_marks", ascending=(segment == "Needs Support"))


# =============================================================
# 4. BEST K VIA ELBOW / SILHOUETTE
# =============================================================

def best_k(df: pd.DataFrame, k_range=(2, 5)) -> Dict:
    """
    Suggest the best number of clusters using silhouette score.
    Returns {best_k, scores: {k: score}}.
    """
    try:
        from sklearn.metrics import silhouette_score
    except Exception:
        return {"best_k": 3, "scores": {}}

    if df.empty or len(df) < 3:
        return {"best_k": 1, "scores": {}}

    X = df[FEATURE_COLUMNS].values.astype(float)
    X_scaled = StandardScaler().fit_transform(X)

    scores = {}
    for k in range(k_range[0], min(k_range[1], len(df)) + 1):
        try:
            km = KMeans(n_clusters=k, n_init=10, random_state=42)
            labels = km.fit_predict(X_scaled)
            scores[k] = round(float(silhouette_score(X_scaled, labels)), 4)
        except Exception:
            continue

    if not scores:
        return {"best_k": 2, "scores": {}}
    best = max(scores, key=scores.get)
    return {"best_k": best, "scores": scores}


# =============================================================
# 5. CONVENIENCE WRAPPERS
# =============================================================

def class_overview(db) -> Dict:
    """One-shot call for the facilitator dashboard."""
    df = cluster_students(db)
    return {
        "dataframe": df,
        "segments":  segment_summary(df),
        "k_used":    int(df["cluster"].nunique()) if not df.empty else 0,
    }


def students_for_remedial(db, segment: str = "Needs Support") -> pd.DataFrame:
    """Return students in a segment (defaults to at-risk)."""
    df = cluster_students(db)
    return students_in_segment(df, segment)


# =============================================================
# 6. SANITY CHECK
# =============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  SHRUTHI JHARI — models/clustering.py sanity check")
    print("=" * 60)

    try:
        from database import get_db
        db = get_db()

        print("\n📊 Building feature matrix for all students...")
        feats = build_features(db)
        print(f"   Rows    : {len(feats)}")
        print(f"   Columns : {list(feats.columns)}")

        print("\n⚙️  Suggesting best k...")
        res = best_k(feats)
        print(f"   Best k  : {res['best_k']}")
        print(f"   Scores  : {res['scores']}")

        print("\n🔬 Clustering with k=3...")
        df = cluster_students(db, n_clusters=3)

        print("\n👥 Segment summary:")
        for seg in segment_summary(df):
            print(f"   {seg['icon']} {seg['segment']:<16} "
                  f"n={seg['count']:<2}  avg_marks={seg['avg_marks']:<6} "
                  f"attendance={seg['avg_attendance']:.1f}%  "
                  f"trend={seg['avg_trend']:+.1f}")

        print("\n📋 Students by segment:")
        for seg in SEGMENT_NAMES:
            sub = students_in_segment(df, seg)
            if sub.empty:
                continue
            print(f"\n   {SEGMENT_ICONS[seg]} {seg} ({len(sub)})")
            for _, r in sub.iterrows():
                print(f"      {r['name']:<20}  avg={r['avg_marks']:<6}  "
                      f"trend={r['ia_trend']:+6.1f}  att={r['attendance_pct']:.0f}%")

        print("\n🎯 PCA coordinates (first 3):")
        for _, r in df.head(3).iterrows():
            print(f"   {r['name']:<20} "
                  f"({r['pca_x']:+.2f}, {r['pca_y']:+.2f})  →  {r['segment']}")

        print("\n🩺 At-risk students for remedial:")
        risk = students_for_remedial(db, "Needs Support")
        for _, r in risk.iterrows():
            print(f"   • {r['name']:<20} avg={r['avg_marks']} "
                  f"(weak subject min={r['min_subject']})")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n⚠️  {e}")

    print("\n✅ models/clustering.py OK")
    print("=" * 60)