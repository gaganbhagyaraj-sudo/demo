# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  config.py  ·  Single source of truth for the entire app
# =============================================================

import os

# -------------------------------------------------------------
# 1. BRAND IDENTITY
# -------------------------------------------------------------
APP_NAME        = "Shruthi Jhari"
APP_TAGLINE     = "Cascade of divine knowledge"
APP_VERSION     = "1.0.0"
APP_AUTHOR      = "Team Shruthi Jhari"
APP_YEAR        = "2025"

# -------------------------------------------------------------
# 2. PATHS
# -------------------------------------------------------------
BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR      = os.path.join(BASE_DIR, "assets")
AVATAR_DIR      = os.path.join(ASSETS_DIR, "avatars")
BADGE_DIR       = os.path.join(ASSETS_DIR, "badges")
CERT_DIR        = os.path.join(ASSETS_DIR, "certificates")
GRADIENT_DIR    = os.path.join(ASSETS_DIR, "gradients")
TEMPLATES_DIR   = os.path.join(BASE_DIR, "templates")
DATA_DIR        = os.path.join(BASE_DIR, "data")
DB_PATH         = os.path.join(DATA_DIR, "shruthi_jhari.db")
LOGO_PATH       = os.path.join(ASSETS_DIR, "SJ.png")

# Ensure writable folders exist
for _p in (AVATAR_DIR, BADGE_DIR, CERT_DIR, GRADIENT_DIR, DATA_DIR):
    os.makedirs(_p, exist_ok=True)

# -------------------------------------------------------------
# 3. THE 2-COLOR GRADIENT  (used everywhere)
# -------------------------------------------------------------
# Deep Divine Purple  →  Saffron Gold
GRADIENT_START  = "#6D28D9"   # violet-700 — wisdom, depth
GRADIENT_END    = "#F59E0B"   # amber-500 — divine light
GRADIENT_ANGLE  = 135         # top-left → bottom-right

# Gradient variants (for subtle layering)
GRADIENT_SOFT   = ("#7C3AED", "#FBBF24")   # lighter for hover
GRADIENT_DEEP   = ("#4C1D95", "#B45309")   # darker for pressed
GRADIENT_GLOW   = ("#8B5CF6", "#FCD34D")   # for glow effects

# -------------------------------------------------------------
# 4. NEUTRAL PALETTE  (flats, no gradient)
# -------------------------------------------------------------
COLORS = {
    "bg":            "#0B0A1F",   # deep night violet
    "surface":       "#17142E",   # card background
    "surface_alt":   "#241F45",   # hover / secondary card
    "surface_hi":    "#2E2757",   # highlighted surface
    "border":        "#3D3569",   # dividers
    "border_soft":   "#2A2354",   # subtle dividers

    "text":          "#F5F3FF",   # soft white
    "text_muted":    "#A79FC9",   # muted violet
    "text_dim":      "#6B6390",   # disabled text
    "text_inverse":  "#0B0A1F",   # text on gold buttons

    "primary":       GRADIENT_START,
    "primary_hover": "#7C3AED",
    "primary_press": "#5B21B6",
    "accent":        GRADIENT_END,

    "overlay":       "#0B0A1FCC", # modal backdrop (80% opacity)
    "shadow":        "#00000066", # card shadow
    "skeleton":      "#241F45",   # loading skeleton base
    "skeleton_hi":   "#2E2757",   # shimmer highlight
}

# -------------------------------------------------------------
# 5. SEMANTIC STATUS COLORS  (data meaning only)
# -------------------------------------------------------------
STATUS = {
    "red":     "#EF4444",   # 🔴 at risk
    "amber":   "#F59E0B",   # 🟡 medium
    "green":   "#10B981",   # 🟢 strong
    "gold":    "#FBBF24",   # 🏆 achiever
    "info":    "#60A5FA",   # ℹ️ neutral
    "purple":  "#8B5CF6",   # 🏅 badges
    "danger":  "#DC2626",   # destructive hover
    "success": "#059669",   # success hover
}

# Zone names → color (used by grading engine)
ZONE_RED     = "red"
ZONE_YELLOW  = "yellow"
ZONE_GREEN   = "green"
ZONE_GOLD    = "gold"

ZONE_COLORS = {
    ZONE_RED:    STATUS["red"],
    ZONE_YELLOW: STATUS["amber"],
    ZONE_GREEN:  STATUS["green"],
    ZONE_GOLD:   STATUS["gold"],
}

ZONE_LABELS = {
    ZONE_RED:    "At Risk",
    ZONE_YELLOW: "Developing",
    ZONE_GREEN:  "Strong",
    ZONE_GOLD:   "Achiever",
}

ZONE_ICONS = {
    ZONE_RED:    "🔴",
    ZONE_YELLOW: "🟡",
    ZONE_GREEN:  "🟢",
    ZONE_GOLD:   "🏆",
}

# -------------------------------------------------------------
# 6. SUBJECT COLORS  (for charts — consistent brand palette)
# -------------------------------------------------------------
SUBJECTS = ["Maths", "Physics", "Chemistry", "Computer Science"]

SUBJECT_COLORS = {
    "Maths":            "#8B5CF6",   # violet
    "Physics":          "#EC4899",   # rose
    "Chemistry":        "#10B981",   # emerald
    "Computer Science": "#F59E0B",   # gold
}

SUBJECT_SHORT = {
    "Maths":            "Maths",
    "Physics":          "Phy",
    "Chemistry":        "Che",
    "Computer Science": "CS",
}

# Excel column headers (matches upload template exactly)
SUBJECT_COLUMNS = {
    "Maths":            "Maths",
    "Physics":          "Phy",
    "Chemistry":        "Che",
    "Computer Science": "CS",
}

# -------------------------------------------------------------
# 7. IA CONFIG
# -------------------------------------------------------------
IA_LIST = ["IA-1", "IA-2", "IA-3"]

IA_COLORS = {
    "IA-1": "#60A5FA",   # sky
    "IA-2": "#8B5CF6",   # violet
    "IA-3": "#F59E0B",   # gold
}

# Marks per subject per IA
MARKS_MAX       = 100     # change to 20/30 if your IA is out of that
TOTAL_MAX       = 400     # 4 subjects × 100

# -------------------------------------------------------------
# 8. GRADE SCALE
# -------------------------------------------------------------
# (min_percent, grade, label, color)
GRADE_SCALE = [
    (90, "O",  "Outstanding",  "#FBBF24"),
    (80, "A+", "Excellent",    "#10B981"),
    (70, "A",  "Very Good",    "#34D399"),
    (60, "B+", "Good",         "#60A5FA"),
    (50, "B",  "Average",      "#818CF8"),
    (40, "C",  "Pass",         "#F59E0B"),
    ( 0, "F",  "Fail",         "#EF4444"),
]

GRADE_ORDER = [g[1] for g in GRADE_SCALE]   # ['O','A+','A','B+','B','C','F']

# -------------------------------------------------------------
# 9. ZONE RULES (drives student profile color)
# -------------------------------------------------------------
# Priority: GOLD > GREEN > YELLOW > RED
ZONE_RULES = {
    "gold": {
        "min_percent": 90,
        "min_subject": 85,        # every subject ≥ 85
        "requires_all_subjects": True,
    },
    "green": {
        "min_percent": 75,
        "min_subject": 60,        # every subject ≥ 60
        "requires_all_subjects": True,
    },
    "yellow": {
        "min_percent": 50,
        "min_subject": 0,
        "requires_all_subjects": False,
    },
    "red": {
        "min_percent": 0,         # anything below yellow
        "min_subject": 0,
        "requires_all_subjects": False,
    },
}

# Extra red trigger: any subject below this → forced red
RED_TRIGGER_SUBJECT = 40

# -------------------------------------------------------------
# 10. BADGE SYSTEM
# -------------------------------------------------------------
BADGES = [
    {
        "id": "perfect_attendance",
        "name": "Perfect Attendance",
        "icon": "🌟",
        "desc": "100% attendance in a month",
        "color": "#FBBF24",
    },
    {
        "id": "aptitude_ace",
        "name": "Aptitude Ace",
        "icon": "🧠",
        "desc": "Score ≥ 90% in an aptitude test",
        "color": "#8B5CF6",
    },
    {
        "id": "brain_teaser_master",
        "name": "Brain Teaser Master",
        "icon": "🧩",
        "desc": "Solve 10 brain teasers",
        "color": "#EC4899",
    },
    {
        "id": "comeback_kid",
        "name": "Comeback Kid",
        "icon": "📈",
        "desc": "Move from Red → Green in one term",
        "color": "#10B981",
    },
    {
        "id": "subject_topper",
        "name": "Subject Topper",
        "icon": "🏆",
        "desc": "Highest marks in any subject",
        "color": "#FBBF24",
    },
    {
        "id": "consistent_performer",
        "name": "Consistent Performer",
        "icon": "🎯",
        "desc": "IA-1, IA-2, IA-3 all ≥ 80",
        "color": "#60A5FA",
    },
    {
        "id": "all_rounder",
        "name": "All-Rounder",
        "icon": "💯",
        "desc": "≥ 75 in all 4 subjects",
        "color": "#8B5CF6",
    },
    {
        "id": "streak_master",
        "name": "Streak Master",
        "icon": "🔥",
        "desc": "30-day learning streak",
        "color": "#EF4444",
    },
    {
        "id": "achiever",
        "name": "Achiever",
        "icon": "🎓",
        "desc": "Gold zone + 3 activities completed",
        "color": "#FBBF24",
    },
    {
        "id": "remedial_graduate",
        "name": "Remedial Graduate",
        "icon": "📚",
        "desc": "Complete remedial + improve 20%",
        "color": "#10B981",
    },
]

BADGE_BY_ID = {b["id"]: b for b in BADGES}

# -------------------------------------------------------------
# 11. CERTIFICATE TYPES
# -------------------------------------------------------------
CERTIFICATES = [
    {"id": "academic_excellence", "name": "Academic Excellence",
     "desc": "Gold zone achiever", "color": "#FBBF24"},
    {"id": "subject_topper", "name": "Subject Topper",
     "desc": "Highest in a subject", "color": "#8B5CF6"},
    {"id": "perfect_attendance", "name": "Perfect Attendance",
     "desc": "100% attendance", "color": "#60A5FA"},
    {"id": "most_improved", "name": "Most Improved",
     "desc": "Biggest Red → Green jump", "color": "#10B981"},
    {"id": "all_rounder", "name": "All-Rounder",
     "desc": "Excellence in all 4 subjects", "color": "#EC4899"},
    {"id": "activity_champion", "name": "Activity Champion",
     "desc": "Most activities completed", "color": "#F59E0B"},
]

CERT_BY_ID = {c["id"]: c for c in CERTIFICATES}

# -------------------------------------------------------------
# 12. BKT (Bayesian Knowledge Tracing) PARAMS
# -------------------------------------------------------------
BKT_PARAMS = {
    "slip":  0.10,   # P(wrong | mastered)
    "guess": 0.20,   # P(correct | not mastered)
    "learn": 0.30,   # P(transition to mastered per attempt)
    "init":  0.10,   # P(mastery) at start
}

MASTERY_THRESHOLDS = {
    "weak":       0.40,
    "developing": 0.75,
    "mastered":   0.75,
}

# -------------------------------------------------------------
# 13. SPACED REPETITION
# -------------------------------------------------------------
SR_INITIAL_INTERVAL = 1        # days
SR_INITIAL_EASE     = 2.5
SR_MIN_EASE         = 1.3
SR_MAX_EASE         = 2.8

# -------------------------------------------------------------
# 14. ANIMATION TIMINGS (milliseconds)
# -------------------------------------------------------------
ANIM = {
    "page_fade":        300,
    "page_slide_px":    30,
    "button_hover":     150,
    "card_hover":       200,
    "carousel_slide":   600,
    "carousel_interval": 3000,   # 3 s
    "chart_grow":       700,
    "chart_fade":       500,
    "color_tween":      800,
    "modal_open":       250,
    "badge_pop":        1200,
    "skeleton_loop":    1400,
    "toast_slide":      350,
    "toast_duration":   3000,
    "splash_hold":      1800,
}

# Frame interval for animation loop (~60 fps)
ANIM_FRAME_MS = 16

# -------------------------------------------------------------
# 15. FONTS
# -------------------------------------------------------------
# Uses Segoe UI on Windows, falls back gracefully.
FONT_FAMILY      = "Segoe UI"
FONT_FAMILY_MONO = "Consolas"

FONTS = {
    "display":   (FONT_FAMILY, 40, "bold"),    # splash
    "h1":        (FONT_FAMILY, 28, "bold"),
    "h2":        (FONT_FAMILY, 22, "bold"),
    "h3":        (FONT_FAMILY, 17, "bold"),
    "h4":        (FONT_FAMILY, 14, "bold"),
    "body":      (FONT_FAMILY, 12),
    "body_bold": (FONT_FAMILY, 12, "bold"),
    "small":     (FONT_FAMILY, 11),
    "small_bold":(FONT_FAMILY, 11, "bold"),
    "tiny":      (FONT_FAMILY, 10),
    "micro":     (FONT_FAMILY, 9),
    "mono":      (FONT_FAMILY_MONO, 11),
    "numeral_big": (FONT_FAMILY, 32, "bold"),
    "numeral":   (FONT_FAMILY, 20, "bold"),
}

# -------------------------------------------------------------
# 16. LAYOUT DIMENSIONS
# -------------------------------------------------------------
WINDOW_MIN_W = 1280
WINDOW_MIN_H = 760
WINDOW_DEFAULT_W = 1400
WINDOW_DEFAULT_H = 860

HEADER_H     = 64
SIDEBAR_W    = 220
CARD_RADIUS  = 14
BUTTON_RADIUS = 10
CHIP_RADIUS  = 20
AVATAR_SM    = 40
AVATAR_MD    = 64
AVATAR_LG    = 96
AVATAR_XL    = 140

PAD_SM = 8
PAD_MD = 16
PAD_LG = 24
PAD_XL = 40

# -------------------------------------------------------------
# 17. ROLES
# -------------------------------------------------------------
ROLE_ADMIN       = "admin"
ROLE_FACILITATOR = "facilitator"
ROLE_STUDENT     = "student"

ROLES = [ROLE_ADMIN, ROLE_FACILITATOR, ROLE_STUDENT]

ROLE_LABELS = {
    ROLE_ADMIN:       "Administrator",
    ROLE_FACILITATOR: "Facilitator",
    ROLE_STUDENT:     "Student",
}

# Registration status
STATUS_PENDING  = "pending"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"

# -------------------------------------------------------------
# 18. ATTENDANCE
# -------------------------------------------------------------
ATTENDANCE_STATUS = {
    "P": "Present",
    "A": "Absent",
    "L": "Late",
    "E": "Excused",
}

ATTENDANCE_COLORS = {
    "P": "#10B981",
    "A": "#EF4444",
    "L": "#F59E0B",
    "E": "#60A5FA",
}

# -------------------------------------------------------------
# 19. ACTIVITY TYPES
# -------------------------------------------------------------
ACTIVITY_TYPES = [
    {"id": "aptitude",      "name": "Aptitude",       "icon": "🧠", "color": "#8B5CF6"},
    {"id": "brain_teaser",  "name": "Brain Teaser",   "icon": "🧩", "color": "#EC4899"},
    {"id": "quiz",          "name": "Quiz",           "icon": "❓", "color": "#60A5FA"},
    {"id": "coding",        "name": "Coding Challenge","icon": "💻", "color": "#10B981"},
    {"id": "reading",       "name": "Reading",        "icon": "📖", "color": "#F59E0B"},
]

# -------------------------------------------------------------
# 20. ALERT CONFIG
# -------------------------------------------------------------
ALERT_TYPES = {
    "stuck":           {"severity": "high",   "icon": "🔴", "color": "#EF4444"},
    "disengaged":      {"severity": "high",   "icon": "🚪", "color": "#EF4444"},
    "slipping":        {"severity": "medium", "icon": "📉", "color": "#F59E0B"},
    "ahead":           {"severity": "low",    "icon": "🚀", "color": "#10B981"},
    "cohort_struggle": {"severity": "medium", "icon": "👥", "color": "#F59E0B"},
    "attendance_drop": {"severity": "medium", "icon": "📅", "color": "#F59E0B"},
    "fail_subject":    {"severity": "high",   "icon": "❌", "color": "#EF4444"},
}

ALERT_RULES = {
    "stuck_attempts":        3,     # wrong attempts on same concept
    "stuck_hours":           48,
    "disengage_days":        4,
    "slipping_success_rate": 0.50,
    "ahead_mastery":         0.90,
    "cohort_struggle_pct":   0.40,
}

# -------------------------------------------------------------
# 21. CHART STYLING (matplotlib + seaborn)
# -------------------------------------------------------------
CHART_STYLE = {
    "fig_bg":     COLORS["surface"],
    "axes_bg":    COLORS["surface_alt"],
    "grid":       COLORS["border_soft"],
    "text":       COLORS["text"],
    "text_muted": COLORS["text_muted"],
    "spine":      COLORS["border"],
    "palette": [
        "#8B5CF6", "#EC4899", "#10B981", "#F59E0B",
        "#60A5FA", "#FBBF24", "#EF4444", "#A78BFA",
    ],
    "figsize_sm": (5, 3),
    "figsize_md": (7, 4),
    "figsize_lg": (10, 5),
    "dpi":        110,
    "line_w":     2.5,
    "bar_w":      0.6,
    "marker_sz":  8,
    "font_size":  10,
}

# -------------------------------------------------------------
# 22. DEMO / SEED DATA
# -------------------------------------------------------------
SEED_STUDENT_COUNT = 15

DEMO_ADMIN       = {"email": "admin@sj.com",   "password": "demo"}
DEMO_FACILITATOR = {"email": "kavya@sj.com",   "password": "demo"}
DEMO_STUDENT     = {"email": "rahul@sj.com",   "password": "demo"}

# -------------------------------------------------------------
# 23. TOAST MESSAGES (default)
# -------------------------------------------------------------
TOAST = {
    "success": "✅  Done!",
    "error":   "⚠️  Something went wrong.",
    "info":    "ℹ️  Heads up.",
    "warning": "⚡  Careful.",
}

# -------------------------------------------------------------
# 24. PAGE REGISTRY  (used by main.py router)
# -------------------------------------------------------------
PAGES = {
    # root
    "splash":       "pages.splash",
    "landing":      "pages.landing",
    # auth
    "login":        "pages.auth.login",
    "register":     "pages.auth.register",
    "pending":      "pages.auth.pending",
    # admin
    "admin_dashboard":         "pages.admin.dashboard",
    "admin_approval":          "pages.admin.approval_queue",
    "admin_users":             "pages.admin.user_management",
    "admin_marks_manual":      "pages.admin.marks_entry_manual",
    "admin_marks_excel":       "pages.admin.marks_entry_excel",
    "admin_attendance":        "pages.admin.attendance_manager",
    "admin_analytics":         "pages.admin.class_analytics",
    "admin_certificates":      "pages.admin.certificate_generator",
    "admin_activities":        "pages.admin.activity_manager",
    "admin_audit":             "pages.admin.audit_log",
    # facilitator
    "fac_command":             "pages.facilitator.command_center",
    "fac_roster":              "pages.facilitator.class_roster",
    "fac_deepdive":            "pages.facilitator.student_deepdive",
    "fac_alerts":              "pages.facilitator.alerts_feed",
    "fac_marks":               "pages.facilitator.marks_analysis",
    "fac_attendance":          "pages.facilitator.attendance_view",
    "fac_heatmap":             "pages.facilitator.heatmap",
    "fac_remedial":            "pages.facilitator.remedial_sessions",
    "fac_interventions":       "pages.facilitator.interventions_log",
    "fac_profile":             "pages.facilitator.profile_viewer",
    "fac_badges":              "pages.facilitator.badge_manager",
    "fac_reports":             "pages.facilitator.reports_export",
    # student
    "stu_dashboard":           "pages.student.dashboard",
    "stu_profile":             "pages.student.profile",
    "stu_marks":               "pages.student.marks",
    "stu_attendance":          "pages.student.attendance",
    "stu_learning":            "pages.student.learning_path",
    "stu_learning_screen":     "pages.student.learning_screen",
    "stu_mastery":             "pages.student.mastery_map",
    "stu_activities":          "pages.student.activities",
    "stu_badges":              "pages.student.badges",
    "stu_certificates":        "pages.student.certificates",
    "stu_remedial":            "pages.student.remedial",
    "stu_leaderboard":         "pages.student.leaderboard",
    "stu_topper_wall":         "pages.student.topper_wall",
}

# -------------------------------------------------------------
# 25. EXPORT HELPERS
# -------------------------------------------------------------
def gradient_tuple():
    """Return the canonical gradient pair."""
    return (GRADIENT_START, GRADIENT_END)

def zone_color(zone: str) -> str:
    return ZONE_COLORS.get(zone, STATUS["info"])

def grade_meta(grade: str):
    for _, g, label, color in GRADE_SCALE:
        if g == grade:
            return {"grade": g, "label": label, "color": color}
    return {"grade": "F", "label": "Fail", "color": STATUS["red"]}

# -------------------------------------------------------------
# 26. SANITY CHECK
# -------------------------------------------------------------
if __name__ == "__main__":
    print(f"✨ {APP_NAME} — {APP_TAGLINE}")
    print(f"   Version : {APP_VERSION}")
    print(f"   DB      : {DB_PATH}")
    print(f"   Logo    : {LOGO_PATH}  (exists: {os.path.exists(LOGO_PATH)})")
    print(f"   Gradient: {GRADIENT_START} → {GRADIENT_END}")
    print(f"   Subjects: {', '.join(SUBJECTS)}")
    print(f"   IA      : {', '.join(IA_LIST)}")
    print(f"   Badges  : {len(BADGES)} defined")
    print(f"   Pages   : {len(PAGES)} registered")
    print("   ✅ config.py OK")