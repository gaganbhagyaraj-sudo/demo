# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  utils/excel_io.py  ·  Excel import + export
# =============================================================

from __future__ import annotations

import os
import sys

# --- make project root importable ---
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional, List, Dict, Tuple

import pandas as pd

from config import (
    TEMPLATES_DIR, DATA_DIR, IA_LIST,
    SUBJECTS, SUBJECT_COLUMNS, MARKS_MAX, TOTAL_MAX,
)
from models.grading import compute_row


# =============================================================
# 0. DIRS
# =============================================================

os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)


# =============================================================
# 1. COLUMN SCHEMAS
# =============================================================

MARKS_COLUMNS = [
    "Sl No", "USN", "Name",
    "Maths", "Phy", "Che", "CS",
    "Total", "%", "Grade",
]

ATTENDANCE_COLUMNS = ["USN", "Name", "Date", "Status"]

ACTIVITIES_COLUMNS = [
    "USN", "Name", "Activity", "Type", "Score", "Max Score", "Completed On",
]


# =============================================================
# 2. DATA STRUCTURES
# =============================================================

@dataclass
class ImportReport:
    """Result of an Excel import."""
    total_rows: int = 0
    valid_rows: int = 0
    invalid_rows: int = 0
    missing_usn: int = 0
    duplicate_usn: int = 0
    non_numeric: int = 0
    missing_name: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    valid_data: List[dict] = field(default_factory=list)
    invalid_data: List[dict] = field(default_factory=list)

    def ok(self) -> bool:
        return self.invalid_rows == 0 and self.valid_rows > 0

    def summary(self) -> str:
        return (f"Total {self.total_rows} · "
                f"Valid {self.valid_rows} · "
                f"Invalid {self.invalid_rows}")


# =============================================================
# 3. TEMPLATE GENERATION
# =============================================================

def _write_template(path: str, columns: List[str], sample_rows: List[dict]):
    """Write an xlsx template with header + sample rows + formatting."""
    df = pd.DataFrame(sample_rows, columns=columns)

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Data")

        # Auto-width columns
        wb = writer.book
        ws = wb["Data"]
        for i, col in enumerate(columns, 1):
            max_len = max([len(str(col))] + [len(str(v)) for v in df[col]]) + 3
            ws.column_dimensions[
                ws.cell(row=1, column=i).column_letter
            ].width = min(40, max(12, max_len))

        # Bold header
        from openpyxl.styles import Font, PatternFill, Alignment
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill("solid", fgColor="6D28D9")
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[1].height = 26

        # Freeze top row
        ws.freeze_panes = "A2"


def make_marks_template(path: Optional[str] = None) -> str:
    """Create a blank marks template."""
    path = path or os.path.join(TEMPLATES_DIR, "marks_template.xlsx")
    sample = [
        {"Sl No": 1, "USN": "1RV21CS001", "Name": "Rahul Sharma",
         "Maths": 78, "Phy": 65, "Che": 72, "CS": 88,
         "Total": "", "%": "", "Grade": ""},
        {"Sl No": 2, "USN": "1RV21CS002", "Name": "Priya Nair",
         "Maths": 92, "Phy": 88, "Che": 90, "CS": 95,
         "Total": "", "%": "", "Grade": ""},
    ]
    _write_template(path, MARKS_COLUMNS, sample)
    return path


def make_attendance_template(path: Optional[str] = None) -> str:
    path = path or os.path.join(TEMPLATES_DIR, "attendance_template.xlsx")
    sample = [
        {"USN": "1RV21CS001", "Name": "Rahul Sharma",
         "Date": "2025-01-15", "Status": "P"},
        {"USN": "1RV21CS002", "Name": "Priya Nair",
         "Date": "2025-01-15", "Status": "P"},
    ]
    _write_template(path, ATTENDANCE_COLUMNS, sample)
    return path


def make_activities_template(path: Optional[str] = None) -> str:
    path = path or os.path.join(TEMPLATES_DIR, "activities_template.xlsx")
    sample = [
        {"USN": "1RV21CS001", "Name": "Rahul Sharma",
         "Activity": "Aptitude Test 1", "Type": "aptitude",
         "Score": 85, "Max Score": 100, "Completed On": "2025-01-20"},
    ]
    _write_template(path, ACTIVITIES_COLUMNS, sample)
    return path


def make_all_templates() -> dict:
    return {
        "marks":      make_marks_template(),
        "attendance": make_attendance_template(),
        "activities": make_activities_template(),
    }


# =============================================================
# 4. MARKS IMPORT
# =============================================================

def _clean_usn(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    return str(v).strip().upper()


def _to_float(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def read_marks_excel(path: str) -> ImportReport:
    """
    Read an xlsx marks file. Returns an ImportReport with valid + invalid rows.
    Does NOT touch the database.
    """
    report = ImportReport()

    try:
        df = pd.read_excel(path, engine="openpyxl")
    except Exception as e:
        report.errors.append(f"Cannot read file: {e}")
        return report

    # Normalize headers
    df.columns = [str(c).strip() for c in df.columns]

    # Check required columns
    required = ["USN", "Name", "Maths", "Phy", "Che", "CS"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        report.errors.append(
            f"Missing required columns: {', '.join(missing)}")
        return report

    seen_usn = set()
    report.total_rows = len(df)

    for idx, raw in df.iterrows():
        row_num = idx + 2   # +2 because header is row 1

        usn = _clean_usn(raw.get("USN"))
        name = str(raw.get("Name", "")).strip()

        # Validate USN
        if not usn:
            report.missing_usn += 1
            report.invalid_rows += 1
            report.warnings.append(f"Row {row_num}: missing USN")
            report.invalid_data.append({"row": row_num, "reason": "missing USN"})
            continue

        if usn in seen_usn:
            report.duplicate_usn += 1
            report.invalid_rows += 1
            report.warnings.append(f"Row {row_num}: duplicate USN {usn}")
            report.invalid_data.append({"row": row_num, "reason": "duplicate USN"})
            continue
        seen_usn.add(usn)

        if not name:
            report.missing_name += 1
            report.warnings.append(f"Row {row_num}: empty name (USN={usn})")
            # continue — name can be filled by DB lookup later

        # Validate numeric columns
        vals = {}
        bad_numeric = False
        for col in ("Maths", "Phy", "Che", "CS"):
            v = _to_float(raw.get(col))
            if v is None:
                report.non_numeric += 1
                report.warnings.append(
                    f"Row {row_num}: invalid number in '{col}'")
                bad_numeric = True
                v = 0.0
            if v < 0 or v > MARKS_MAX:
                report.warnings.append(
                    f"Row {row_num}: {col}={v} outside [0,{MARKS_MAX}]")
                v = max(0.0, min(MARKS_MAX, v))
            vals[col] = v

        if bad_numeric:
            report.invalid_rows += 1
            report.invalid_data.append({
                "row": row_num, "usn": usn, "reason": "non-numeric marks"})
            continue

        # Compute total / % / grade
        info = compute_row(vals["Maths"], vals["Phy"],
                           vals["Che"], vals["CS"])

        report.valid_rows += 1
        report.valid_data.append({
            "usn":        usn,
            "name":       name,
            "maths":      vals["Maths"],
            "phy":        vals["Phy"],
            "che":        vals["Che"],
            "cs":         vals["CS"],
            "total":      info["total"],
            "percentage": info["percentage"],
            "grade":      info["grade"],
            "zone":       info["zone"],
        })

    return report


def import_marks_to_db(db, path: str, ia_number: int,
                       entered_by: str = "admin") -> ImportReport:
    """Read + validate + save valid rows into the DB."""
    report = read_marks_excel(path)
    if not report.valid_data:
        return report

    try:
        db.save_marks_sheet(ia_number, report.valid_data,
                            entered_by=entered_by)
    except Exception as e:
        report.errors.append(f"DB save failed: {e}")

    return report


# =============================================================
# 5. ATTENDANCE IMPORT
# =============================================================

def read_attendance_excel(path: str) -> ImportReport:
    report = ImportReport()
    try:
        df = pd.read_excel(path, engine="openpyxl")
    except Exception as e:
        report.errors.append(f"Cannot read file: {e}")
        return report

    df.columns = [str(c).strip() for c in df.columns]
    required = ["USN", "Date", "Status"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        report.errors.append(
            f"Missing required columns: {', '.join(missing)}")
        return report

    report.total_rows = len(df)
    valid_status = {"P", "A", "L", "E"}

    for idx, raw in df.iterrows():
        row_num = idx + 2
        usn = _clean_usn(raw.get("USN"))
        d = raw.get("Date")
        status = str(raw.get("Status", "")).strip().upper()

        if not usn:
            report.invalid_rows += 1
            report.warnings.append(f"Row {row_num}: missing USN")
            continue

        # Date parse
        try:
            if isinstance(d, (datetime, date)):
                d_str = d.strftime("%Y-%m-%d")
            else:
                d_str = pd.to_datetime(str(d)).strftime("%Y-%m-%d")
        except Exception:
            report.invalid_rows += 1
            report.warnings.append(f"Row {row_num}: invalid date '{d}'")
            continue

        if status not in valid_status:
            report.invalid_rows += 1
            report.warnings.append(
                f"Row {row_num}: status must be one of {valid_status}")
            continue

        report.valid_rows += 1
        report.valid_data.append({
            "usn":    usn,
            "name":   str(raw.get("Name", "")).strip(),
            "date":   d_str,
            "status": status,
        })

    return report


def import_attendance_to_db(db, path: str,
                            marked_by: str = "admin") -> ImportReport:
    report = read_attendance_excel(path)
    for row in report.valid_data:
        user = db.get_user_by_usn(row["usn"])
        if not user:
            report.warnings.append(
                f"USN {row['usn']} not found — skipped")
            continue
        try:
            db.mark_attendance(user["id"], row["date"], row["status"],
                               subject="ALL", marked_by=marked_by)
        except Exception as e:
            report.errors.append(
                f"Failed saving attendance for {row['usn']}: {e}")
    return report


# =============================================================
# 6. ACTIVITIES IMPORT
# =============================================================

def read_activities_excel(path: str) -> ImportReport:
    report = ImportReport()
    try:
        df = pd.read_excel(path, engine="openpyxl")
    except Exception as e:
        report.errors.append(f"Cannot read file: {e}")
        return report

    df.columns = [str(c).strip() for c in df.columns]
    required = ["USN", "Activity", "Type", "Score", "Max Score"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        report.errors.append(
            f"Missing required columns: {', '.join(missing)}")
        return report

    report.total_rows = len(df)

    for idx, raw in df.iterrows():
        row_num = idx + 2
        usn = _clean_usn(raw.get("USN"))
        activity = str(raw.get("Activity", "")).strip()
        atype = str(raw.get("Type", "")).strip().lower()
        score = _to_float(raw.get("Score"))
        mx = _to_float(raw.get("Max Score"))

        if not usn or not activity or score is None or not mx:
            report.invalid_rows += 1
            report.warnings.append(
                f"Row {row_num}: missing required fields")
            continue

        report.valid_rows += 1
        report.valid_data.append({
            "usn":      usn,
            "name":     str(raw.get("Name", "")).strip(),
            "activity": activity,
            "type":     atype,
            "score":    score,
            "max":      mx,
            "completed_on": str(raw.get("Completed On", "")).strip(),
        })
    return report


def import_activities_to_db(db, path: str) -> ImportReport:
    report = read_activities_excel(path)
    for row in report.valid_data:
        user = db.get_user_by_usn(row["usn"])
        if not user:
            report.warnings.append(
                f"USN {row['usn']} not found — skipped")
            continue
        # Find or create activity
        existing = db.query("""
            SELECT id FROM activities WHERE name=? AND type=?
        """, (row["activity"], row["type"]))
        if existing.empty:
            db.execute("""
                INSERT INTO activities(id,name,type,subject,max_score,created_at)
                VALUES (?,?,?,?,?,?)
            """, (row["activity"].lower().replace(" ", "_"),
                  row["activity"], row["type"], None,
                  row["max"], datetime.now().isoformat()))
            act_id = row["activity"].lower().replace(" ", "_")
        else:
            act_id = existing.iloc[0]["id"]

        try:
            db.log_activity_score(user["id"], act_id,
                                  row["score"], row["max"])
        except Exception as e:
            report.errors.append(f"Failed saving activity: {e}")
    return report


# =============================================================
# 7. EXPORTS
# =============================================================

def export_class_marks(db, ia_number: int,
                       out_path: Optional[str] = None) -> str:
    """Export the class marks summary for a given IA as xlsx."""
    out_path = out_path or os.path.join(
        DATA_DIR, f"class_marks_IA{ia_number}.xlsx")

    df = db.get_class_marks_summary(ia_number)
    if df.empty:
        df = pd.DataFrame(columns=MARKS_COLUMNS)

    # Rename for the export
    df = df.rename(columns={
        "usn": "USN", "name": "Name",
        "maths": "Maths", "phy": "Phy", "che": "Che", "cs": "CS",
        "total": "Total", "percentage": "%", "grade": "Grade",
    })

    # Compute zone counts
    summary_row = {
        "USN": "", "Name": f"Class of IA-{ia_number}",
        "Maths": df["Maths"].mean() if "Maths" in df else 0,
        "Phy": df["Phy"].mean() if "Phy" in df else 0,
        "Che": df["Che"].mean() if "Che" in df else 0,
        "CS": df["CS"].mean() if "CS" in df else 0,
        "Total": df["Total"].mean() if "Total" in df else 0,
        "%": df["%"].mean() if "%" in df else 0,
        "Grade": "—",
    }

    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Marks")
        pd.DataFrame([summary_row]).to_excel(
            writer, index=False, sheet_name="Summary")

    return out_path


def export_student_report(db, user_id: str,
                          out_path: Optional[str] = None) -> str:
    """Export a single student's full report (marks per IA + attendance)."""
    user = db.get_user(user_id)
    if not user:
        raise ValueError(f"User {user_id} not found")
    out_path = out_path or os.path.join(
        DATA_DIR, f"report_{user['usn'] or user['id']}.xlsx")

    # Marks per IA
    marks = db.get_marks_summary(user_id)
    marks_df = marks.rename(columns={
        "ia_number": "IA", "maths": "Maths", "phy": "Phy",
        "che": "Che", "cs": "CS", "total": "Total",
        "percentage": "%", "grade": "Grade",
    })[["IA", "Maths", "Phy", "Che", "CS", "Total", "%", "Grade"]]

    # Attendance
    att = db.get_attendance(user_id, days=90)
    att_df = att[["att_date", "status"]].rename(
        columns={"att_date": "Date", "status": "Status"})

    # Activities
    acts = db.get_user_activities(user_id)
    acts_df = acts.rename(columns={
        "name": "Activity", "type": "Type",
        "score": "Score", "max_score": "Max",
        "percentage": "%",
    })[["Activity", "Type", "Score", "Max", "%"]]

    # Badges
    badges = db.get_user_badges(user_id)
    badges_df = badges[["name", "earned_at"]].rename(
        columns={"name": "Badge", "earned_at": "Earned At"})

    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        marks_df.to_excel(writer, index=False, sheet_name="Marks")
        att_df.to_excel(writer, index=False, sheet_name="Attendance")
        acts_df.to_excel(writer, index=False, sheet_name="Activities")
        badges_df.to_excel(writer, index=False, sheet_name="Badges")

    return out_path


def export_class_analytics(db, ia_number: int,
                           out_path: Optional[str] = None) -> str:
    """Multi-sheet analytics export: marks, zone counts, subject averages."""
    out_path = out_path or os.path.join(
        DATA_DIR, f"analytics_IA{ia_number}.xlsx")

    marks = db.get_class_marks_summary(ia_number)

    zone_counts = db.class_zone_counts(ia_number)
    zone_df = pd.DataFrame(
        [{"Zone": z.title(), "Count": c}
         for z, c in zone_counts.items()])

    subj_avg = db.class_subject_averages(ia_number)
    avg_df = pd.DataFrame(
        [{"Subject": s, "Average": v} for s, v in subj_avg.items()])

    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        marks.to_excel(writer, index=False, sheet_name="All Marks")
        zone_df.to_excel(writer, index=False, sheet_name="Zone Counts")
        avg_df.to_excel(writer, index=False, sheet_name="Subject Averages")

    return out_path


# =============================================================
# 8. SANITY CHECK
# =============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  SHRUTHI JHARI — utils/excel_io.py sanity check")
    print("=" * 60)

    # ---- 1. Make all templates ----
    print("\n📄 Generating templates...")
    paths = make_all_templates()
    for k, p in paths.items():
        exists = os.path.exists(p)
        size = os.path.getsize(p) if exists else 0
        print(f"   {k:<12}  {'✅' if exists else '❌'}  {size:>6} bytes  {p}")

    # ---- 2. Read the marks template back ----
    print("\n📊 Reading back marks template...")
    rep = read_marks_excel(paths["marks"])
    print(f"   {rep.summary()}")
    if rep.valid_data:
        r = rep.valid_data[0]
        print(f"   Sample: {r['name']} ({r['usn']})  "
              f"M={r['maths']} P={r['phy']} C={r['che']} CS={r['cs']}  "
              f"→ {r['percentage']}% Grade {r['grade']} Zone {r['zone']}")

    # ---- 3. Import into DB ----
    print("\n💾 Importing marks into DB (IA-1)...")
    try:
        from database import get_db
        db = get_db()
        rep = import_marks_to_db(db, paths["marks"],
                                 ia_number=1, entered_by="admin")
        print(f"   {rep.summary()}")
        if rep.warnings:
            print(f"   Warnings: {len(rep.warnings)}")
            for w in rep.warnings[:3]:
                print(f"     · {w}")
    except Exception as e:
        print(f"   ⚠️  {e}")

    # ---- 4. Export class marks ----
    print("\n📤 Exporting class marks...")
    try:
        out = export_class_marks(db, ia_number=1)
        print(f"   💾  {out}  ({os.path.getsize(out)} bytes)")
    except Exception as e:
        print(f"   ⚠️  {e}")

    # ---- 5. Export student report ----
    print("\n📤 Exporting student report...")
    try:
        stu = db.get_all_students().iloc[0]
        out = export_student_report(db, stu["id"])
        print(f"   💾  {out}  ({os.path.getsize(out)} bytes)")
    except Exception as e:
        print(f"   ⚠️  {e}")

    # ---- 6. Export class analytics ----
    print("\n📤 Exporting class analytics...")
    try:
        out = export_class_analytics(db, ia_number=1)
        print(f"   💾  {out}  ({os.path.getsize(out)} bytes)")
    except Exception as e:
        print(f"   ⚠️  {e}")

    print("\n✅ utils/excel_io.py OK")
    print("=" * 60)