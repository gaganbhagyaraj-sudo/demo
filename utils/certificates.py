# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  utils/certificates.py  ·  PDF certificate generator
# =============================================================

from __future__ import annotations

import os
import sys

# --- make project root importable ---
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import math
import tempfile
from datetime import datetime, date
from typing import Optional

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib import colors as rl_colors
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from config import (
    CERT_DIR, AVATAR_DIR, LOGO_PATH,
    APP_NAME, APP_TAGLINE, APP_YEAR,
    GRADIENT_START, GRADIENT_END,
    COLORS, STATUS, ZONE_COLORS,
    CERT_BY_ID, CERTIFICATES,
)
from utils.images import certificate_seal
from utils.avatars import pil_avatar


# =============================================================
# 0. DIRS + FONTS
# =============================================================

os.makedirs(CERT_DIR, exist_ok=True)

# Register fonts with reportlab (fall back gracefully if missing)
def _try_register(name: str, candidates: list):
    for path in candidates:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                return True
            except Exception:
                continue
    return False


_HAS_SERIF   = _try_register("SJSerif", [
    "C:/Windows/Fonts/georgia.ttf",
    "C:/Windows/Fonts/times.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
])
_HAS_SERIF_B = _try_register("SJSerifB", [
    "C:/Windows/Fonts/georgiab.ttf",
    "C:/Windows/Fonts/timesbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
])
_HAS_SCRIPT  = _try_register("SJScript", [
    "C:/Windows/Fonts/BRUSHSCI.TTF",
    "C:/Windows/Fonts/ITCKRIST.TTF",
])
_HAS_SANS    = _try_register("SJSans", [
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
])
_HAS_SANS_B  = _try_register("SJSansB", [
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
])

# Fallback names
SERIF   = "SJSerif"   if _HAS_SERIF   else "Times-Roman"
SERIF_B = "SJSerifB"  if _HAS_SERIF_B else "Times-Bold"
SCRIPT  = "SJScript"  if _HAS_SCRIPT  else SERIF_B
SANS    = "SJSans"    if _HAS_SANS    else "Helvetica"
SANS_B  = "SJSansB"   if _HAS_SANS_B  else "Helvetica-Bold"


# =============================================================
# 1. HELPERS
# =============================================================

def _hex(h: str) -> rl_colors.Color:
    return rl_colors.HexColor(h)


def _today_str() -> str:
    return date.today().strftime("%d %B %Y")


def _safe_filename(s: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in s)


def _draw_gradient_bar(c: rl_canvas.Canvas, x, y, w, h,
                       color1: str, color2: str, steps: int = 120):
    """Horizontal gradient bar using many thin rectangles."""
    for i in range(steps):
        t = i / max(1, steps - 1)
        col = _mix(color1, color2, t)
        c.setFillColor(col)
        c.rect(x + (w * i / steps), y,
               w / steps + 0.5, h, stroke=0, fill=1)


def _mix(c1: str, c2: str, t: float) -> rl_colors.Color:
    def hx(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4))
    a, b = hx(c1), hx(c2)
    return rl_colors.Color(
        a[0] + (b[0] - a[0]) * t,
        a[1] + (b[1] - a[1]) * t,
        a[2] + (b[2] - a[2]) * t,
    )


def _logo_image_reader(size=120):
    """Return an ImageReader for SJ.png, or None if missing."""
    if os.path.exists(LOGO_PATH):
        try:
            return ImageReader(LOGO_PATH)
        except Exception:
            return None
    return None


def _seal_image_reader(size=220):
    """Return an ImageReader for the generated certificate seal."""
    try:
        seal = certificate_seal(size=size)
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        seal.save(tmp.name, "PNG")
        tmp.close()
        return ImageReader(tmp.name), tmp.name
    except Exception:
        return None, None


def _avatar_image_reader(user_id: str, name: str,
                         size: int = 240, zone: Optional[str] = None):
    """Return an ImageReader for the student's avatar (with optional ring)."""
    try:
        ring = 8 if zone else 0
        img = pil_avatar(user_id, name, size=size,
                         shape="circle", zone=zone, ring_width=ring)
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        img.save(tmp.name, "PNG")
        tmp.close()
        return ImageReader(tmp.name), tmp.name
    except Exception:
        return None, None


# =============================================================
# 2. MAIN CERTIFICATE RENDERER
# =============================================================

# Certificate page: A4 landscape
PAGE_W, PAGE_H = landscape(A4)   # ≈ 842 × 595 pt


def _draw_page_border(c: rl_canvas.Canvas,
                      accent: str = GRADIENT_END,
                      margin: float = 12 * mm):
    """Ornate double border."""
    w, h = PAGE_W, PAGE_H

    # Outer gold thick border
    c.setStrokeColor(_hex(accent))
    c.setLineWidth(4)
    c.rect(margin, margin, w - 2 * margin, h - 2 * margin)

    # Inner thin dark border
    c.setStrokeColor(_hex("#3D3569"))
    c.setLineWidth(1)
    inner = margin + 4 * mm
    c.rect(inner, inner, w - 2 * inner, h - 2 * inner)

    # Corner ornaments
    _draw_corner_ornament(c, margin + 10 * mm, margin + 10 * mm, accent)
    _draw_corner_ornament(c, w - margin - 10 * mm, margin + 10 * mm, accent)
    _draw_corner_ornament(c, margin + 10 * mm, h - margin - 10 * mm, accent)
    _draw_corner_ornament(c, w - margin - 10 * mm, h - margin - 10 * mm,
                          accent, flip_y=True)


def _draw_corner_ornament(c, x, y, color, size=14, flip_y=False):
    """Small diamond flourish at each corner."""
    c.saveState()
    c.translate(x, y)
    if flip_y:
        c.scale(1, -1)
    c.setFillColor(_hex(color))
    c.setStrokeColor(_hex(color))
    c.setLineWidth(1.2)
    r = size
    c.circle(0, 0, r * 0.45, stroke=1, fill=1)
    c.circle(0, 0, r * 0.8, stroke=1, fill=0)
    # spokes
    for ang in (0, 90, 180, 270):
        rad = math.radians(ang)
        c.line(0, 0, r * math.cos(rad), r * math.sin(rad))
    c.restoreState()


def _draw_ribbon(c: rl_canvas.Canvas, text: str, y: float,
                 color: str = GRADIENT_END):
    """Top-of-page ribbon with award title."""
    w = PAGE_W
    ribbon_h = 18 * mm
    ribbon_w = 220 * mm
    x0 = (w - ribbon_w) / 2

    _draw_gradient_bar(c, x0, y, ribbon_w, ribbon_h,
                       GRADIENT_START, color, steps=90)

    c.setFillColor(_hex("#FFFFFF"))
    c.setFont(SANS_B, 15)
    c.drawCentredString(w / 2, y + ribbon_h / 2 - 5, text.upper())


def _draw_title(c: rl_canvas.Canvas, y: float):
    """'Certificate of ...' style title."""
    w = PAGE_W
    c.setFillColor(_hex(GRADIENT_START))
    c.setFont(SERIF_B, 32)
    c.drawCentredString(w / 2, y, "Certificate of Achievement")

    c.setFillColor(_hex("#3D3569"))
    c.setFont(SERIF, 12)
    c.drawCentredString(w / 2, y - 12, "— presented by —")

    c.setFillColor(_hex(GRADIENT_START))
    c.setFont(SANS_B, 15)
    c.drawCentredString(w / 2, y - 30, APP_NAME.upper())
    c.setFillColor(_hex("#6B6390"))
    c.setFont(SERIF, 10)
    c.drawCentredString(w / 2, y - 44, f'"{APP_TAGLINE}"')


def _draw_award_text(c: rl_canvas.Canvas, award_title: str,
                     award_line: str, y: float):
    """The main body: 'is hereby awarded to' + name + description."""
    w = PAGE_W

    c.setFillColor(_hex("#6B6390"))
    c.setFont(SERIF, 13)
    c.drawCentredString(w / 2, y, "This certificate is proudly presented to")

    # Name is drawn separately by caller


def _draw_name(c: rl_canvas.Canvas, name: str, y: float,
               color: str = GRADIENT_START):
    w = PAGE_W
    c.setFillColor(_hex(color))
    c.setFont(SCRIPT, 40)
    c.drawCentredString(w / 2, y, name)

    # Underline flourish
    name_w = c.stringWidth(name, SCRIPT, 40)
    line_w = min(260, name_w + 60)
    c.setStrokeColor(_hex(GRADIENT_END))
    c.setLineWidth(1.4)
    c.line((w - line_w) / 2, y - 8, (w + line_w) / 2, y - 8)


def _draw_body(c: rl_canvas.Canvas, text: str, y: float, max_width_pt=520):
    """Word-wrapped body paragraph, centered."""
    w = PAGE_W
    c.setFillColor(_hex("#2A2354"))
    c.setFont(SERIF, 13)

    words = text.split()
    line = ""
    lines = []
    for word in words:
        trial = (line + " " + word).strip()
        if c.stringWidth(trial, SERIF, 13) > max_width_pt:
            lines.append(line)
            line = word
        else:
            line = trial
    if line:
        lines.append(line)

    for i, ln in enumerate(lines):
        c.drawCentredString(w / 2, y - i * 18, ln)


def _draw_signature_block(c: rl_canvas.Canvas, y: float,
                          left_label="Facilitator",
                          right_label="Administrator"):
    w = PAGE_W
    gap = 100
    line_w = 180

    # Left signature
    c.setStrokeColor(_hex("#3D3569"))
    c.setLineWidth(1)
    c.line(w / 2 - gap - line_w / 2, y, w / 2 - gap + line_w / 2, y)
    c.setFillColor(_hex("#3D3569"))
    c.setFont(SANS, 10)
    c.drawCentredString(w / 2 - gap, y - 12, left_label)

    # Right signature
    c.line(w / 2 + gap - line_w / 2, y, w / 2 + gap + line_w / 2, y)
    c.drawCentredString(w / 2 + gap, y - 12, right_label)

    # Center: date
    c.setFillColor(_hex("#6B6390"))
    c.setFont(SANS, 9)
    c.drawCentredString(w / 2, y - 12, "Date of Issue")
    c.setFont(SANS_B, 11)
    c.setFillColor(_hex("#2A2354"))
    c.drawCentredString(w / 2, y - 26, _today_str())


def _draw_footer(c: rl_canvas.Canvas):
    c.setFillColor(_hex("#A79FC9"))
    c.setFont(SANS, 8)
    c.drawCentredString(
        PAGE_W / 2, 20,
        f"{APP_NAME}  ·  {APP_TAGLINE}  ·  {APP_YEAR}")


# =============================================================
# 3. THE 6 CERTIFICATE TYPES
# =============================================================

def _certificate_common(c: rl_canvas.Canvas, *,
                        ribbon_text: str,
                        ribbon_color: str,
                        recipient_name: str,
                        body_text: str,
                        accent_color: str,
                        avatar_user_id: Optional[str],
                        avatar_zone: Optional[str] = None):
    """
    Draw the shared certificate layout. Type-specific tweaks:
      - ribbon text & color
      - body text
      - accent color
      - optional avatar
    """
    w, h = PAGE_W, PAGE_H

    # Optional avatar top-left
    if avatar_user_id:
        reader, tmp = _avatar_image_reader(
            avatar_user_id, recipient_name, size=280, zone=avatar_zone)
        if reader:
            try:
                c.drawImage(reader, 30 * mm, h - 55 * mm,
                            38 * mm, 38 * mm,
                            mask="auto")
            finally:
                try:
                    if tmp:
                        os.unlink(tmp)
                except Exception:
                    pass

    # Border
    _draw_page_border(c, accent=accent_color)

    # Ribbon
    _draw_ribbon(c, ribbon_text, h - 40 * mm, color=ribbon_color)

    # Title
    _draw_title(c, h - 62 * mm)

    # "Presented to"
    _draw_award_text(c, ribbon_text, "", h - 108 * mm)

    # Name
    _draw_name(c, recipient_name, h - 130 * mm,
               color=accent_color)

    # Body
    _draw_body(c, body_text, h - 155 * mm, max_width_pt=520)

    # Seal (bottom-right)
    seal_reader, seal_tmp = _seal_image_reader(size=260)
    if seal_reader:
        try:
            c.drawImage(seal_reader, w - 55 * mm, 30 * mm,
                        40 * mm, 40 * mm, mask="auto")
        finally:
            try:
                if seal_tmp:
                    os.unlink(seal_tmp)
            except Exception:
                pass

    # Signature block
    _draw_signature_block(c, 55 * mm)

    # Footer
    _draw_footer(c)


# ---------- 1. ACADEMIC EXCELLENCE ----------

def certificate_academic_excellence(
        user_id: str, name: str, usn: str,
        percentage: float, grade: str, zone: str,
        out_path: Optional[str] = None) -> str:
    out_path = out_path or os.path.join(
        CERT_DIR, f"{user_id}_academic_excellence.pdf")

    c = rl_canvas.Canvas(out_path, pagesize=landscape(A4))
    body = (f"in recognition of outstanding academic performance with an "
            f"overall score of {percentage:.2f}% and Grade '{grade}', "
            f"reflecting dedication, curiosity, and excellence across all "
            f"subjects.")
    _certificate_common(
        c,
        ribbon_text="Academic Excellence",
        ribbon_color=ZONE_COLORS["gold"],
        recipient_name=name,
        body_text=body,
        accent_color=GRADIENT_START,
        avatar_user_id=user_id,
        avatar_zone=zone,
    )
    # Small footer line with USN
    c.setFont(SANS, 8)
    c.setFillColor(_hex("#6B6390"))
    c.drawString(30 * mm, 20, f"USN: {usn}")
    c.showPage()
    c.save()
    return out_path


# ---------- 2. SUBJECT TOPPER ----------

def certificate_subject_topper(
        user_id: str, name: str, usn: str,
        subject: str, marks: float,
        out_path: Optional[str] = None) -> str:
    out_path = out_path or os.path.join(
        CERT_DIR, f"{user_id}_subject_topper_{_safe_filename(subject)}.pdf")

    c = rl_canvas.Canvas(out_path, pagesize=landscape(A4))
    body = (f"for securing the highest score of {marks:.0f} marks in "
            f"{subject}, demonstrating mastery, focus, and a true love "
            f"for the subject.")
    _certificate_common(
        c,
        ribbon_text=f"{subject} Topper",
        ribbon_color=GRADIENT_END,
        recipient_name=name,
        body_text=body,
        accent_color=GRADIENT_END,
        avatar_user_id=user_id,
    )
    c.setFont(SANS, 8)
    c.setFillColor(_hex("#6B6390"))
    c.drawString(30 * mm, 20, f"USN: {usn}  ·  Subject: {subject}")
    c.showPage()
    c.save()
    return out_path


# ---------- 3. PERFECT ATTENDANCE ----------

def certificate_perfect_attendance(
        user_id: str, name: str, usn: str,
        attendance_pct: float = 100.0,
        out_path: Optional[str] = None) -> str:
    out_path = out_path or os.path.join(
        CERT_DIR, f"{user_id}_perfect_attendance.pdf")

    c = rl_canvas.Canvas(out_path, pagesize=landscape(A4))
    body = (f"for achieving {attendance_pct:.0f}% attendance and consistent "
            f"presence throughout the term. Reliability and discipline are "
            f"the foundations of every great learner.")
    _certificate_common(
        c,
        ribbon_text="Perfect Attendance",
        ribbon_color=STATUS["info"],
        recipient_name=name,
        body_text=body,
        accent_color=STATUS["info"],
        avatar_user_id=user_id,
    )
    c.setFont(SANS, 8)
    c.setFillColor(_hex("#6B6390"))
    c.drawString(30 * mm, 20, f"USN: {usn}  ·  Attendance: {attendance_pct:.1f}%")
    c.showPage()
    c.save()
    return out_path


# ---------- 4. MOST IMPROVED ----------

def certificate_most_improved(
        user_id: str, name: str, usn: str,
        from_pct: float, to_pct: float,
        out_path: Optional[str] = None) -> str:
    out_path = out_path or os.path.join(
        CERT_DIR, f"{user_id}_most_improved.pdf")

    delta = to_pct - from_pct
    c = rl_canvas.Canvas(out_path, pagesize=landscape(A4))
    body = (f"for an extraordinary improvement of {delta:+.1f}% — from "
            f"{from_pct:.1f}% to {to_pct:.1f}%. This journey reflects grit, "
            f"hard work, and the true spirit of a Comeback Kid.")
    _certificate_common(
        c,
        ribbon_text="Most Improved",
        ribbon_color=STATUS["green"],
        recipient_name=name,
        body_text=body,
        accent_color=STATUS["green"],
        avatar_user_id=user_id,
        avatar_zone="green",
    )
    c.setFont(SANS, 8)
    c.setFillColor(_hex("#6B6390"))
    c.drawString(30 * mm, 20,
                 f"USN: {usn}  ·  {from_pct:.1f}% → {to_pct:.1f}%")
    c.showPage()
    c.save()
    return out_path


# ---------- 5. ALL-ROUNDER ----------

def certificate_all_rounder(
        user_id: str, name: str, usn: str,
        subject_marks: dict,
        out_path: Optional[str] = None) -> str:
    out_path = out_path or os.path.join(
        CERT_DIR, f"{user_id}_all_rounder.pdf")

    subj_line = " · ".join(f"{k.split()[0]} {int(v)}"
                           for k, v in subject_marks.items())
    c = rl_canvas.Canvas(out_path, pagesize=landscape(A4))
    body = (f"for excellence in every subject — {subj_line}. An all-round "
            f"performer who shines across disciplines and inspires peers.")
    _certificate_common(
        c,
        ribbon_text="All-Rounder",
        ribbon_color="#EC4899",
        recipient_name=name,
        body_text=body,
        accent_color="#EC4899",
        avatar_user_id=user_id,
        avatar_zone="gold",
    )
    c.setFont(SANS, 8)
    c.setFillColor(_hex("#6B6390"))
    c.drawString(30 * mm, 20, f"USN: {usn}")
    c.showPage()
    c.save()
    return out_path


# ---------- 6. ACTIVITY CHAMPION ----------

def certificate_activity_champion(
        user_id: str, name: str, usn: str,
        activity_count: int,
        out_path: Optional[str] = None) -> str:
    out_path = out_path or os.path.join(
        CERT_DIR, f"{user_id}_activity_champion.pdf")

    c = rl_canvas.Canvas(out_path, pagesize=landscape(A4))
    body = (f"for outstanding participation in {activity_count} co-curricular "
            f"activities — aptitude, brain teasers, and beyond. A true "
            f"champion of curiosity and holistic growth.")
    _certificate_common(
        c,
        ribbon_text="Activity Champion",
        ribbon_color="#F59E0B",
        recipient_name=name,
        body_text=body,
        accent_color="#F59E0B",
        avatar_user_id=user_id,
    )
    c.setFont(SANS, 8)
    c.setFillColor(_hex("#6B6390"))
    c.drawString(30 * mm, 20,
                 f"USN: {usn}  ·  Activities: {activity_count}")
    c.showPage()
    c.save()
    return out_path


# =============================================================
# 4. BATCH GENERATION
# =============================================================

def generate_class_certificates(db, ia_number: int = 3) -> dict:
    """
    Auto-issue certificates to all eligible students:
      - Academic Excellence: gold zone
      - Subject Topper: highest in each subject
      - Perfect Attendance: 100%
      - Most Improved: biggest IA-1 → IA-3 jump
      - All-Rounder: every subject ≥ 90 in latest IA
      - Activity Champion: top 1 in activity count

    Returns {cert_type: [paths]} and logs each certificate in the DB.
    """
    results = {
        "academic_excellence": [],
        "subject_topper":      [],
        "perfect_attendance":  [],
        "most_improved":       [],
        "all_rounder":         [],
        "activity_champion":   [],
    }

    students = db.get_all_students()

    # --- Academic Excellence + All-Rounder ---
    for _, s in students.iterrows():
        uid = s["id"]
        name = s["name"]
        usn = s["usn"] or uid

        ms = db.get_marks_summary(uid, ia_number)
        if ms.empty:
            continue
        r = ms.iloc[0]
        zone = r["zone"]
        pct = float(r["percentage"])
        grade = r["grade"]

        if zone == "gold":
            try:
                p = certificate_academic_excellence(uid, name, usn,
                                                    pct, grade, zone)
                results["academic_excellence"].append(p)
                db.issue_certificate(uid, "academic_excellence",
                                     "Academic Excellence", p)
            except Exception:
                pass

        row_marks = {
            "Maths":            float(r["maths"]),
            "Physics":          float(r["phy"]),
            "Chemistry":        float(r["che"]),
            "Computer Science": float(r["cs"]),
        }
        if all(v >= 90 for v in row_marks.values()):
            try:
                p = certificate_all_rounder(uid, name, usn, row_marks)
                results["all_rounder"].append(p)
                db.issue_certificate(uid, "all_rounder",
                                     "All-Rounder", p)
            except Exception:
                pass

    # --- Subject Topper ---
    toppers = db.get_subject_toppers(ia_number=ia_number)
    for subj, info in toppers.items():
        if not info:
            continue
        try:
            p = certificate_subject_topper(
                info["user_id"], info["name"], info["usn"],
                subj, float(info["marks"]))
            results["subject_topper"].append(p)
            db.issue_certificate(info["user_id"], "subject_topper",
                                 f"{subj} Topper", p)
        except Exception:
            pass

    # --- Perfect Attendance ---
    for _, s in students.iterrows():
        uid = s["id"]
        pct = db.attendance_percent(uid, days=30)
        if pct >= 99.9:
            try:
                p = certificate_perfect_attendance(
                    uid, s["name"], s["usn"] or uid, pct)
                results["perfect_attendance"].append(p)
                db.issue_certificate(uid, "perfect_attendance",
                                     "Perfect Attendance", p)
            except Exception:
                pass

    # --- Most Improved ---
    best_gain, best_uid = -1e9, None
    for _, s in students.iterrows():
        uid = s["id"]
        hist = db.get_color_history(uid)
        if len(hist) < 2:
            continue
        f = float(hist.iloc[0]["percentage"])
        t = float(hist.iloc[-1]["percentage"])
        if (t - f) > best_gain:
            best_gain, best_uid = (t - f), uid
    if best_uid:
        s = db.get_user(best_uid)
        hist = db.get_color_history(best_uid)
        try:
            p = certificate_most_improved(
                best_uid, s["name"], s["usn"] or best_uid,
                float(hist.iloc[0]["percentage"]),
                float(hist.iloc[-1]["percentage"]))
            results["most_improved"].append(p)
            db.issue_certificate(best_uid, "most_improved",
                                 "Most Improved", p)
        except Exception:
            pass

    # --- Activity Champion ---
    top_user, top_count = None, -1
    for _, s in students.iterrows():
        acts = db.get_user_activities(s["id"])
        n = len(acts)
        if n > top_count:
            top_count, top_user = n, s["id"]
    if top_user and top_count > 0:
        s = db.get_user(top_user)
        try:
            p = certificate_activity_champion(
                top_user, s["name"], s["usn"] or top_user, top_count)
            results["activity_champion"].append(p)
            db.issue_certificate(top_user, "activity_champion",
                                 "Activity Champion", p)
        except Exception:
            pass

    return results


# =============================================================
# 5. SANITY CHECK
# =============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  SHRUTHI JHARI — utils/certificates.py sanity check")
    print("=" * 60)

    try:
        from database import get_db
        db = get_db()

        print("\n🎓 Generating ONE of each certificate type for demo...")

        stu = db.get_all_students().iloc[0]
        uid, name, usn = stu["id"], stu["name"], stu["usn"] or stu["id"]

        # 1. Academic Excellence
        p = certificate_academic_excellence(uid, name, usn,
                                            91.25, "O", "gold")
        print(f"   1. {os.path.basename(p):<40} {os.path.getsize(p):>7} bytes")

        # 2. Subject Topper
        p = certificate_subject_topper(uid, name, usn, "Maths", 96)
        print(f"   2. {os.path.basename(p):<40} {os.path.getsize(p):>7} bytes")

        # 3. Perfect Attendance
        p = certificate_perfect_attendance(uid, name, usn, 100.0)
        print(f"   3. {os.path.basename(p):<40} {os.path.getsize(p):>7} bytes")

        # 4. Most Improved
        p = certificate_most_improved(uid, name, usn, 42.0, 78.5)
        print(f"   4. {os.path.basename(p):<40} {os.path.getsize(p):>7} bytes")

        # 5. All-Rounder
        p = certificate_all_rounder(uid, name, usn,
                                    {"Maths": 92, "Physics": 91,
                                     "Chemistry": 93, "Computer Science": 95})
        print(f"   5. {os.path.basename(p):<40} {os.path.getsize(p):>7} bytes")

        # 6. Activity Champion
        p = certificate_activity_champion(uid, name, usn, 8)
        print(f"   6. {os.path.basename(p):<40} {os.path.getsize(p):>7} bytes")

        print("\n🏫 Batch generating certificates for the whole class (IA-3)...")
        results = generate_class_certificates(db, ia_number=3)
        for ctype, paths in results.items():
            print(f"   {ctype:<22}  →  {len(paths)} issued")

        total = sum(len(v) for v in results.values())
        print(f"\n   Total certificates issued: {total}")

        # Show issued
        print("\n📋 Sample of issued certificates:")
        certs = db.query("""
            SELECT u.name, c.title, c.issued_at
            FROM certificates c
            JOIN users u ON u.id = c.user_id
            ORDER BY c.issued_at DESC
            LIMIT 8
        """)
        for _, r in certs.iterrows():
            print(f"   · {r['name']:<20}  {r['title']:<22} "
                  f"{r['issued_at'][:10]}")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n⚠️  {e}")

    print(f"\n📁 Certificates saved to: {CERT_DIR}")
    print("\n✅ utils/certificates.py OK")
    print("=" * 60)