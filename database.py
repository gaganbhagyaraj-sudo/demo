# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  database.py  ·  SQLite + pandas data layer
# =============================================================

import os
import uuid
import json
import sqlite3
import random
from datetime import datetime, timedelta, date

import pandas as pd
import numpy as np

from config import (
    DB_PATH, DATA_DIR,
    SUBJECTS, SUBJECT_COLUMNS, IA_LIST, MARKS_MAX, TOTAL_MAX,
    GRADE_SCALE, ZONE_RULES, RED_TRIGGER_SUBJECT,
    STATUS_PENDING, STATUS_APPROVED, STATUS_REJECTED,
    ROLE_ADMIN, ROLE_FACILITATOR, ROLE_STUDENT,
    BADGES, BADGE_BY_ID, CERTIFICATES, CERT_BY_ID,
    ACTIVITY_TYPES,
    SEED_STUDENT_COUNT,
    DEMO_ADMIN, DEMO_FACILITATOR, DEMO_STUDENT,
)


# =============================================================
# 1. GRADE + ZONE ENGINE  (pure functions, no DB)
# =============================================================

def grade_from_percent(pct: float) -> dict:
    """Return {grade, label, color} for a percent value."""
    for min_p, g, label, color in GRADE_SCALE:
        if pct >= min_p:
            return {"grade": g, "label": label, "color": color}
    return {"grade": "F", "label": "Fail", "color": "#EF4444"}


def zone_from_marks(maths, phy, che, cs) -> dict:
    """
    Compute zone (red/yellow/green/gold) from 4 subject marks.
    Returns {zone, color, label, total, percentage, grade}
    """
    total = float(maths + phy + che + cs)
    pct = round((total / TOTAL_MAX) * 100, 2)
    subjects = [float(maths), float(phy), float(che), float(cs)]
    min_subject = min(subjects)

    # Any failing subject → forced red
    if min_subject < RED_TRIGGER_SUBJECT:
        zone = "red"
    elif (pct >= ZONE_RULES["gold"]["min_percent"]
          and min_subject >= ZONE_RULES["gold"]["min_subject"]):
        zone = "gold"
    elif (pct >= ZONE_RULES["green"]["min_percent"]
          and min_subject >= ZONE_RULES["green"]["min_subject"]):
        zone = "green"
    elif pct >= ZONE_RULES["yellow"]["min_percent"]:
        zone = "yellow"
    else:
        zone = "red"

    g = grade_from_percent(pct)
    colors = {"red": "#EF4444", "yellow": "#F59E0B",
              "green": "#10B981", "gold": "#FBBF24"}
    labels = {"red": "At Risk", "yellow": "Developing",
              "green": "Strong", "gold": "Achiever"}

    return {
        "total": total,
        "percentage": pct,
        "grade": g["grade"],
        "grade_label": g["label"],
        "grade_color": g["color"],
        "zone": zone,
        "zone_color": colors[zone],
        "zone_label": labels[zone],
        "min_subject": min_subject,
    }


# =============================================================
# 2. DATABASE CLASS
# =============================================================

class Database:
    def __init__(self, path=DB_PATH):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.path = path
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        self._seed_if_empty()

    # ---------- RAW ----------
    def query(self, sql, params=()) -> pd.DataFrame:
        return pd.read_sql_query(sql, self.conn, params=params)

    def execute(self, sql, params=()):
        cur = self.conn.cursor()
        cur.execute(sql, params)
        self.conn.commit()
        return cur

    def executemany(self, sql, seq):
        cur = self.conn.cursor()
        cur.executemany(sql, seq)
        self.conn.commit()
        return cur

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass

    # ---------- SCHEMA ----------
    def _create_tables(self):
        cur = self.conn.cursor()
        cur.executescript("""
        -- ============ USERS ============
        CREATE TABLE IF NOT EXISTS users (
            id           TEXT PRIMARY KEY,
            usn          TEXT UNIQUE,
            name         TEXT NOT NULL,
            email        TEXT UNIQUE,
            password     TEXT DEFAULT 'demo',
            role         TEXT NOT NULL DEFAULT 'student',
            grade        TEXT,
            section      TEXT,
            avatar_path  TEXT,
            status       TEXT DEFAULT 'approved',
            created_at   TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
        CREATE INDEX IF NOT EXISTS idx_users_usn ON users(usn);

        -- ============ INTERESTS ============
        CREATE TABLE IF NOT EXISTS interests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        );
        CREATE TABLE IF NOT EXISTS user_interests (
            user_id TEXT,
            interest_id INTEGER,
            weight REAL DEFAULT 1.0,
            PRIMARY KEY (user_id, interest_id)
        );

        -- ============ CONCEPTS + CONTENT ============
        CREATE TABLE IF NOT EXISTS concepts (
            id TEXT PRIMARY KEY,
            name TEXT, subject TEXT,
            difficulty INTEGER, est_minutes INTEGER
        );
        CREATE TABLE IF NOT EXISTS prerequisites (
            concept_id TEXT, prereq_id TEXT,
            PRIMARY KEY (concept_id, prereq_id)
        );
        CREATE TABLE IF NOT EXISTS content (
            id TEXT PRIMARY KEY,
            concept_id TEXT, type TEXT, title TEXT,
            body TEXT, interest_tag TEXT,
            difficulty INTEGER, est_minutes INTEGER
        );

        -- ============ LEARNING ============
        CREATE TABLE IF NOT EXISTS attempts (
            id TEXT PRIMARY KEY,
            user_id TEXT, content_id TEXT, concept_id TEXT,
            correct INTEGER, score REAL, time_spent_sec INTEGER,
            hints_used INTEGER DEFAULT 0,
            created_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_attempts_user ON attempts(user_id);

        CREATE TABLE IF NOT EXISTS mastery (
            user_id TEXT, concept_id TEXT,
            p_mastery REAL DEFAULT 0.1,
            attempts INTEGER DEFAULT 0,
            last_practiced TEXT,
            next_review_at TEXT,
            PRIMARY KEY (user_id, concept_id)
        );

        -- ============ MARKS (per IA) ============
        CREATE TABLE IF NOT EXISTS marks (
            id           TEXT PRIMARY KEY,
            user_id      TEXT NOT NULL,
            ia_number    INTEGER NOT NULL,     -- 1, 2, 3
            subject      TEXT NOT NULL,        -- Maths / Physics / Chemistry / Computer Science
            marks        REAL NOT NULL,
            max_marks    REAL DEFAULT 100,
            entered_by   TEXT,
            entered_at   TEXT,
            UNIQUE(user_id, ia_number, subject)
        );
        CREATE INDEX IF NOT EXISTS idx_marks_user_ia ON marks(user_id, ia_number);

        -- ============ MARKS SUMMARY (per IA, per student) ============
        CREATE TABLE IF NOT EXISTS marks_summary (
            user_id      TEXT,
            ia_number    INTEGER,
            maths        REAL DEFAULT 0,
            phy          REAL DEFAULT 0,
            che          REAL DEFAULT 0,
            cs           REAL DEFAULT 0,
            total        REAL DEFAULT 0,
            percentage   REAL DEFAULT 0,
            grade        TEXT,
            zone         TEXT,
            computed_at  TEXT,
            PRIMARY KEY (user_id, ia_number)
        );

        -- ============ COLOR HISTORY ============
        CREATE TABLE IF NOT EXISTS color_history (
            id           TEXT PRIMARY KEY,
            user_id      TEXT,
            ia_number    INTEGER,
            percentage   REAL,
            grade        TEXT,
            zone         TEXT,
            recorded_at  TEXT
        );

        -- ============ ATTENDANCE ============
        CREATE TABLE IF NOT EXISTS attendance (
            id           TEXT PRIMARY KEY,
            user_id      TEXT,
            att_date     TEXT,       -- YYYY-MM-DD
            subject      TEXT,       -- or 'ALL'
            status       TEXT,       -- P / A / L / E
            marked_by    TEXT,
            marked_at    TEXT,
            UNIQUE(user_id, att_date, subject)
        );
        CREATE INDEX IF NOT EXISTS idx_att_user_date ON attendance(user_id, att_date);

        -- ============ ACTIVITIES ============
        CREATE TABLE IF NOT EXISTS activities (
            id           TEXT PRIMARY KEY,
            name         TEXT,
            type         TEXT,       -- aptitude / brain_teaser / quiz / coding / reading
            subject      TEXT,
            max_score    REAL DEFAULT 100,
            created_at   TEXT
        );
        CREATE TABLE IF NOT EXISTS activity_scores (
            id           TEXT PRIMARY KEY,
            user_id      TEXT,
            activity_id  TEXT,
            score        REAL,
            max_score    REAL,
            percentage   REAL,
            completed_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_actscore_user ON activity_scores(user_id);

        -- ============ BADGES ============
        CREATE TABLE IF NOT EXISTS badges (
            id           TEXT PRIMARY KEY,
            name         TEXT,
            icon         TEXT,
            description  TEXT,
            color        TEXT
        );
        CREATE TABLE IF NOT EXISTS user_badges (
            id           TEXT PRIMARY KEY,
            user_id      TEXT,
            badge_id     TEXT,
            earned_at    TEXT,
            note         TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_ubadge_user ON user_badges(user_id);

        -- ============ CERTIFICATES ============
        CREATE TABLE IF NOT EXISTS certificates (
            id           TEXT PRIMARY KEY,
            user_id      TEXT,
            cert_type    TEXT,       -- academic_excellence / subject_topper / ...
            title        TEXT,
            file_path    TEXT,
            issued_by    TEXT,
            issued_at    TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_cert_user ON certificates(user_id);

        -- ============ REMEDIAL ============
        CREATE TABLE IF NOT EXISTS remedial_sessions (
            id           TEXT PRIMARY KEY,
            subject      TEXT,
            topic        TEXT,
            facilitator_id TEXT,
            scheduled_at TEXT,
            duration_min INTEGER DEFAULT 45,
            notes        TEXT,
            status       TEXT DEFAULT 'scheduled',
            created_at   TEXT
        );
        CREATE TABLE IF NOT EXISTS remedial_enrollments (
            id           TEXT PRIMARY KEY,
            session_id   TEXT,
            user_id      TEXT,
            attended     INTEGER DEFAULT 0,
            outcome      TEXT,
            improvement  REAL DEFAULT 0,
            enrolled_at  TEXT
        );

        -- ============ ALERTS ============
        CREATE TABLE IF NOT EXISTS alerts (
            id           TEXT PRIMARY KEY,
            user_id      TEXT,
            alert_type   TEXT,      -- stuck / slipping / disengaged / fail_subject / ...
            severity     TEXT,      -- low / medium / high
            message      TEXT,
            suggested_action TEXT,
            resolved     INTEGER DEFAULT 0,
            created_at   TEXT,
            resolved_at  TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_alerts_user ON alerts(user_id);
        CREATE INDEX IF NOT EXISTS idx_alerts_resolved ON alerts(resolved);

        -- ============ INTERVENTIONS ============
        CREATE TABLE IF NOT EXISTS interventions (
            id           TEXT PRIMARY KEY,
            facilitator_id TEXT,
            student_id   TEXT,
            itype        TEXT,      -- hint / nudge / assign / pair / schedule / message
            payload      TEXT,
            created_at   TEXT
        );

        -- ============ AUDIT LOG ============
        CREATE TABLE IF NOT EXISTS audit_log (
            id           TEXT PRIMARY KEY,
            actor_id     TEXT,
            action       TEXT,
            target       TEXT,
            details      TEXT,
            created_at   TEXT
        );

        -- ============ SETTINGS ============
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        );
        """)
        self.conn.commit()

    # ---------- SEED ----------
    def _seed_if_empty(self):
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        if cur.fetchone()[0] > 0:
            return

        random.seed(42)
        np.random.seed(42)

        # ---- INTERESTS ----
        interests = ["Cricket", "Cooking", "Gaming", "Space",
                     "Music", "Football", "Movies"]
        for i in interests:
            cur.execute("INSERT OR IGNORE INTO interests(name) VALUES (?)", (i,))

        # ---- CONCEPTS ----
        concepts = [
            ("c_int",  "Integers",         "Maths", 1, 20),
            ("c_frac", "Fractions",        "Maths", 2, 25),
            ("c_dec",  "Decimals",         "Maths", 2, 25),
            ("c_ratio","Ratios",           "Maths", 3, 30),
            ("c_pct",  "Percentages",      "Maths", 3, 30),
            ("c_alg",  "Algebra Basics",   "Maths", 4, 35),
            ("c_lin",  "Linear Equations", "Maths", 5, 40),
        ]
        for c in concepts:
            cur.execute("INSERT INTO concepts VALUES (?,?,?,?,?)", c)

        prereqs = [("c_frac","c_int"),("c_dec","c_frac"),("c_ratio","c_frac"),
                   ("c_pct","c_dec"),("c_alg","c_ratio"),("c_lin","c_alg")]
        for p in prereqs:
            cur.execute("INSERT INTO prerequisites VALUES (?,?)", p)

        contents = [
            ("ct1","c_frac","video","Fractions Intro (Generic)","Video: basics of fractions.",None,1,8),
            ("ct2","c_frac","video","Fractions via Cricket","Learn fractions using cricket overs & run rate!","Cricket",2,10),
            ("ct3","c_frac","problem","Fraction Practice","Add 1/2 + 1/3 = ?",None,2,5),
            ("ct4","c_frac","problem","Pizza Fractions","Ravi ate 2/5 of pizza, Meera ate 1/5. Total?",None,1,4),
            ("ct5","c_dec","video","Decimals via Cooking","Scale a recipe using decimals.","Cooking",2,10),
            ("ct6","c_dec","problem","Decimal Practice","0.25 + 0.75 = ?",None,2,4),
            ("ct7","c_ratio","problem","Ratio via Gaming","K/D ratio: 12 kills, 4 deaths. Ratio?","Gaming",3,5),
            ("ct8","c_pct","video","Percentages via Cricket","Strike rate calculation!","Cricket",3,10),
            ("ct9","c_alg","article","Algebra Basics","Variables & expressions.",None,4,12),
            ("ct10","c_lin","problem","Linear Eq Practice","Solve: 2x + 3 = 11",None,5,6),
        ]
        for ct in contents:
            cur.execute("INSERT INTO content VALUES (?,?,?,?,?,?,?,?)", ct)

        # ---- ADMIN + FACILITATOR ----
        now = datetime.now().isoformat()
        cur.execute("""INSERT INTO users(id,usn,name,email,password,role,grade,section,
                       avatar_path,status,created_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    ("admin1", None, "Administrator", DEMO_ADMIN["email"],
                     DEMO_ADMIN["password"], ROLE_ADMIN, None, None, None,
                     STATUS_APPROVED, now))

        cur.execute("""INSERT INTO users(id,usn,name,email,password,role,grade,section,
                       avatar_path,status,created_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    ("fac1", None, "Ms. Kavya Rao", DEMO_FACILITATOR["email"],
                     DEMO_FACILITATOR["password"], ROLE_FACILITATOR,
                     "Grade 7", "A", None, STATUS_APPROVED, now))

        # ---- STUDENTS ----
        student_names = [
            "Rahul Sharma", "Priya Nair", "Arjun Reddy", "Meera Iyer",
            "Kiran Das", "Ananya Rao", "Vikram Singh", "Sneha Patel",
            "Rohit Kumar", "Divya Menon", "Aditya Verma", "Kavya Joshi",
            "Siddharth Rao", "Pooja Shetty", "Nikhil Bhat",
        ]
        student_interests = [
            ["Cricket", "Gaming"], ["Music", "Cooking"], ["Gaming", "Space"],
            ["Cooking", "Movies"], ["Football", "Cricket"], ["Music", "Space"],
            ["Gaming", "Football"], ["Cooking", "Music"], ["Cricket", "Music"],
            ["Space", "Cooking"], ["Gaming", "Cricket"], ["Music", "Movies"],
            ["Football", "Space"], ["Cooking", "Gaming"], ["Cricket", "Movies"],
        ]

        # Pre-decided profiles so we have a nice red/yellow/green mix
        # Each tuple: (avg_percent, subject_spread)
        profiles = [
            (28, 10),   # very weak  → red
            (92, 5),    # topper     → gold
            (48, 8),    # weak       → red
            (72, 6),    # medium     → yellow
            (68, 10),   # medium     → yellow
            (88, 5),    # strong     → green
            (55, 12),   # low-med    → yellow
            (95, 4),    # topper     → gold
            (42, 14),   # weak       → red
            (78, 6),    # strong     → green
            (63, 10),   # medium     → yellow
            (85, 5),    # strong     → green
            (30, 12),   # very weak  → red
            (74, 8),    # medium     → yellow
            (90, 6),    # strong     → green
        ]

        for i in range(SEED_STUDENT_COUNT):
            sid = f"stu{i+1:02d}"
            usn = f"1RV21CS{i+1:03d}"
            name = student_names[i]
            email = name.lower().replace(" ", ".") + "@sj.com"
            avatar = None
            cur.execute("""INSERT INTO users(id,usn,name,email,password,role,grade,section,
                           avatar_path,status,created_at)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                        (sid, usn, name, email, "demo", ROLE_STUDENT,
                         "Grade 7", "A", avatar, STATUS_APPROVED, now))

            # interests
            for tag in student_interests[i]:
                cur.execute("SELECT id FROM interests WHERE name=?", (tag,))
                row = cur.fetchone()
                if row:
                    cur.execute("INSERT OR IGNORE INTO user_interests VALUES (?,?,?)",
                                (sid, row[0], 1.0))

        # ---- MARKS (3 IAs × 4 subjects) ----
        for i in range(SEED_STUDENT_COUNT):
            sid = f"stu{i+1:02d}"
            base_pct, spread = profiles[i]
            for ia in (1, 2, 3):
                ia_bias = (ia - 2) * 2.0  # IA-2 slightly lower, IA-3 higher trend
                for subj in SUBJECTS:
                    center = base_pct + ia_bias + random.uniform(-spread, spread)
                    center = max(10, min(99, center))
                    marks = round((center / 100) * MARKS_MAX, 1)
                    cur.execute("""INSERT OR REPLACE INTO marks
                                   (id,user_id,ia_number,subject,marks,max_marks,
                                    entered_by,entered_at)
                                   VALUES (?,?,?,?,?,?,?,?)""",
                                (str(uuid.uuid4()), sid, ia, subj,
                                 marks, MARKS_MAX, "fac1", now))

        # ---- MARKS SUMMARY + COLOR HISTORY ----
        for i in range(SEED_STUDENT_COUNT):
            sid = f"stu{i+1:02d}"
            for ia in (1, 2, 3):
                m = self._fetch_marks_dict(sid, ia)
                info = zone_from_marks(m["Maths"], m["Physics"],
                                       m["Chemistry"], m["Computer Science"])
                cur.execute("""INSERT OR REPLACE INTO marks_summary
                               (user_id, ia_number, maths, phy, che, cs,
                                total, percentage, grade, zone, computed_at)
                               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                            (sid, ia, m["Maths"], m["Physics"],
                             m["Chemistry"], m["Computer Science"],
                             info["total"], info["percentage"],
                             info["grade"], info["zone"], now))
                cur.execute("""INSERT INTO color_history
                               (id,user_id,ia_number,percentage,grade,zone,recorded_at)
                               VALUES (?,?,?,?,?,?,?)""",
                            (str(uuid.uuid4()), sid, ia,
                             info["percentage"], info["grade"],
                             info["zone"], now))

        # ---- ATTENDANCE (last 45 days, Mon–Fri) ----
        today = date.today()
        for i in range(SEED_STUDENT_COUNT):
            sid = f"stu{i+1:02d}"
            profile = profiles[i]
            base_att = 0.95 if profile[0] >= 80 else (0.85 if profile[0] >= 60 else 0.72)
            for d in range(45):
                day = today - timedelta(days=d)
                if day.weekday() >= 5:
                    continue
                status = "P" if random.random() < base_att else \
                         random.choice(["A", "L", "E"])
                cur.execute("""INSERT OR IGNORE INTO attendance
                               (id,user_id,att_date,subject,status,marked_by,marked_at)
                               VALUES (?,?,?,?,?,?,?)""",
                            (str(uuid.uuid4()), sid,
                             day.isoformat(), "ALL", status, "fac1", now))

        # ---- ACTIVITIES ----
        activity_rows = [
            ("act_apt1",  "Aptitude Test 1",  "aptitude",       None, 100),
            ("act_bt1",   "Brain Teaser 1",   "brain_teaser",   None, 10),
            ("act_bt2",   "Brain Teaser 2",   "brain_teaser",   None, 10),
            ("act_quiz1", "Science Quiz",     "quiz",           "Physics", 50),
            ("act_code1", "Coding Challenge", "coding",         "Computer Science", 100),
            ("act_read1", "Reading Log",      "reading",        None, 20),
        ]
        for a in activity_rows:
            cur.execute("""INSERT INTO activities(id,name,type,subject,
                           max_score,created_at) VALUES (?,?,?,?,?,?)""",
                        (a[0], a[1], a[2], a[3], a[4], now))

        # Randomly give activity scores
        for i in range(SEED_STUDENT_COUNT):
            sid = f"stu{i+1:02d}"
            base = profiles[i][0]
            for a in activity_rows:
                if random.random() < 0.6:
                    score = max(0, min(a[4],
                                       round(base / 100 * a[4]
                                             + random.uniform(-a[4] * 0.15,
                                                              a[4] * 0.15))))
                    pct = round((score / a[4]) * 100, 2)
                    cur.execute("""INSERT INTO activity_scores
                                   (id,user_id,activity_id,score,max_score,
                                    percentage,completed_at)
                                   VALUES (?,?,?,?,?,?,?)""",
                                (str(uuid.uuid4()), sid, a[0],
                                 score, a[4], pct, now))

        # ---- BADGES (dictionary) ----
        for b in BADGES:
            cur.execute("""INSERT OR IGNORE INTO badges
                           (id,name,icon,description,color)
                           VALUES (?,?,?,?,?)""",
                        (b["id"], b["name"], b["icon"], b["desc"], b["color"]))

        # Award some badges
        for i in range(SEED_STUDENT_COUNT):
            sid = f"stu{i+1:02d}"
            base = profiles[i][0]
            # All-rounder for high performers
            if base >= 85:
                self._award_badge(sid, "all_rounder", now)
                self._award_badge(sid, "subject_topper", now)
            if base >= 90:
                self._award_badge(sid, "achiever", now)
            if base >= 80:
                self._award_badge(sid, "consistent_performer", now)
            if base >= 70:
                self._award_badge(sid, "aptitude_ace", now)
            # Attendance-related
            att_pct = self.attendance_percent(sid)
            if att_pct >= 95:
                self._award_badge(sid, "perfect_attendance", now)
            # Random extras
            if random.random() < 0.35:
                self._award_badge(sid, "brain_teaser_master", now)
            if random.random() < 0.25:
                self._award_badge(sid, "streak_master", now)

        # ---- A few alerts for realism ----
        weak_ids = [f"stu{i+1:02d}" for i in range(SEED_STUDENT_COUNT)
                    if profiles[i][0] < 50]
        for sid in weak_ids:
            cur.execute("""INSERT INTO alerts(id,user_id,alert_type,severity,
                           message,suggested_action,resolved,created_at)
                           VALUES (?,?,?,?,?,?,?,?)""",
                        (str(uuid.uuid4()), sid, "fail_subject", "high",
                         "Student is below pass mark in one or more subjects",
                         json.dumps({"type": "assign_remedial",
                                     "subject": "Maths"}),
                         0, now))

        self.conn.commit()

    # ---------- SEED HELPERS ----------
    def _fetch_marks_dict(self, user_id, ia_number) -> dict:
        df = self.query("""SELECT subject, marks FROM marks
                           WHERE user_id=? AND ia_number=?""",
                        (user_id, ia_number))
        out = {s: 0.0 for s in SUBJECTS}
        for _, row in df.iterrows():
            out[row["subject"]] = float(row["marks"])
        return out

    def _award_badge(self, user_id, badge_id, when=None):
        when = when or datetime.now().isoformat()
        # avoid duplicates
        cur = self.conn.cursor()
        cur.execute("""SELECT 1 FROM user_badges
                       WHERE user_id=? AND badge_id=?""",
                    (user_id, badge_id))
        if cur.fetchone():
            return
        cur.execute("""INSERT INTO user_badges(id,user_id,badge_id,earned_at,note)
                       VALUES (?,?,?,?,?)""",
                    (str(uuid.uuid4()), user_id, badge_id, when, None))

    # =========================================================
    # PUBLIC QUERY HELPERS  (used by the pages)
    # =========================================================

    # ---------- USERS ----------
    def get_user(self, user_id):
        df = self.query("SELECT * FROM users WHERE id=?", (user_id,))
        return df.iloc[0].to_dict() if not df.empty else None

    def get_user_by_email(self, email):
        df = self.query("SELECT * FROM users WHERE LOWER(email)=LOWER(?)",
                        (email,))
        return df.iloc[0].to_dict() if not df.empty else None

    def get_user_by_usn(self, usn):
        df = self.query("SELECT * FROM users WHERE usn=?", (usn,))
        return df.iloc[0].to_dict() if not df.empty else None

    def get_all_students(self, approved_only=True):
        if approved_only:
            return self.query("""SELECT * FROM users
                                 WHERE role='student' AND status='approved'
                                 ORDER BY usn""")
        return self.query("SELECT * FROM users WHERE role='student' ORDER BY usn")

    def get_pending_users(self):
        return self.query("""SELECT * FROM users
                             WHERE status='pending'
                             ORDER BY created_at DESC""")

    def get_user_interests(self, user_id):
        df = self.query("""SELECT i.name FROM user_interests ui
                           JOIN interests i ON i.id=ui.interest_id
                           WHERE ui.user_id=?""", (user_id,))
        return df["name"].tolist()

    def approve_user(self, user_id):
        self.execute("UPDATE users SET status=? WHERE id=?",
                     (STATUS_APPROVED, user_id))
        self.log_audit("system", "approve_user", user_id)

    def reject_user(self, user_id):
        self.execute("UPDATE users SET status=? WHERE id=?",
                     (STATUS_REJECTED, user_id))
        self.log_audit("system", "reject_user", user_id)

    # ---------- MARKS ----------
    def get_marks(self, user_id, ia_number=None):
        if ia_number:
            return self.query("""SELECT * FROM marks
                                 WHERE user_id=? AND ia_number=?
                                 ORDER BY subject""",
                              (user_id, ia_number))
        return self.query("""SELECT * FROM marks
                             WHERE user_id=? ORDER BY ia_number, subject""",
                          (user_id,))

    def get_marks_dict(self, user_id, ia_number) -> dict:
        return self._fetch_marks_dict(user_id, ia_number)

    def get_marks_summary(self, user_id, ia_number=None):
        if ia_number:
            return self.query("""SELECT * FROM marks_summary
                                 WHERE user_id=? AND ia_number=?""",
                              (user_id, ia_number))
        return self.query("""SELECT * FROM marks_summary
                             WHERE user_id=? ORDER BY ia_number""",
                          (user_id,))

    def get_class_marks_summary(self, ia_number=None):
        if ia_number:
            return self.query("""SELECT u.usn, u.name, u.id AS user_id,
                                        ms.*
                                 FROM marks_summary ms
                                 JOIN users u ON u.id = ms.user_id
                                 WHERE ms.ia_number=?
                                 ORDER BY ms.percentage DESC""",
                              (ia_number,))
        return self.query("""SELECT u.usn, u.name, u.id AS user_id, ms.*
                             FROM marks_summary ms
                             JOIN users u ON u.id = ms.user_id
                             ORDER BY ms.percentage DESC""")

    def save_marks_row(self, user_id, ia_number, subject, marks,
                       entered_by="admin", max_marks=None):
        max_marks = max_marks if max_marks is not None else MARKS_MAX
        self.execute("""INSERT INTO marks
                        (id,user_id,ia_number,subject,marks,max_marks,
                         entered_by,entered_at)
                        VALUES (?,?,?,?,?,?,?,?)
                        ON CONFLICT(user_id,ia_number,subject)
                        DO UPDATE SET marks=excluded.marks,
                                      max_marks=excluded.max_marks,
                                      entered_by=excluded.entered_by,
                                      entered_at=excluded.entered_at""",
                     (str(uuid.uuid4()), user_id, ia_number, subject,
                      marks, max_marks, entered_by,
                      datetime.now().isoformat()))
        self._recompute_summary(user_id, ia_number)

    def save_marks_sheet(self, ia_number, rows, entered_by="admin"):
        """
        rows: list of dicts:
            {usn, name, maths, phy, che, cs}
        Creates/updates users by USN if needed.
        """
        for r in rows:
            usn = str(r.get("usn", "")).strip()
            name = str(r.get("name", "")).strip() or f"Student {usn}"
            if not usn:
                continue

            user = self.get_user_by_usn(usn)
            if not user:
                new_id = str(uuid.uuid4())
                self.execute("""INSERT INTO users(id,usn,name,email,password,
                                                   role,grade,section,status,created_at)
                                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                             (new_id, usn, name, None, "demo",
                              ROLE_STUDENT, "Grade 7", "A",
                              STATUS_APPROVED,
                              datetime.now().isoformat()))
                user_id = new_id
            else:
                user_id = user["id"]

            for subj_col, subj_name in SUBJECT_COLUMNS.items():
                val = r.get(subj_col, None)
                if val in (None, "", "nan"):
                    continue
                try:
                    m = float(val)
                except (ValueError, TypeError):
                    continue
                self.save_marks_row(user_id, ia_number, subj_col, m,
                                    entered_by=entered_by)
        return True

    def _recompute_summary(self, user_id, ia_number):
        m = self._fetch_marks_dict(user_id, ia_number)
        info = zone_from_marks(m["Maths"], m["Physics"],
                               m["Chemistry"], m["Computer Science"])
        now = datetime.now().isoformat()
        self.execute("""INSERT INTO marks_summary
                        (user_id, ia_number, maths, phy, che, cs,
                         total, percentage, grade, zone, computed_at)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?)
                        ON CONFLICT(user_id,ia_number)
                        DO UPDATE SET maths=excluded.maths,
                                      phy=excluded.phy,
                                      che=excluded.che,
                                      cs=excluded.cs,
                                      total=excluded.total,
                                      percentage=excluded.percentage,
                                      grade=excluded.grade,
                                      zone=excluded.zone,
                                      computed_at=excluded.computed_at""",
                     (user_id, ia_number,
                      m["Maths"], m["Physics"],
                      m["Chemistry"], m["Computer Science"],
                      info["total"], info["percentage"],
                      info["grade"], info["zone"], now))

        # Log color history
        self.execute("""INSERT INTO color_history
                        (id,user_id,ia_number,percentage,grade,zone,recorded_at)
                        VALUES (?,?,?,?,?,?,?)""",
                     (str(uuid.uuid4()), user_id, ia_number,
                      info["percentage"], info["grade"],
                      info["zone"], now))

    # ---------- SUBJECT-WISE TOPPERS ----------
    def get_subject_toppers(self, ia_number=3):
        """Return {subject_name: {user_id, name, marks, usn}} for a given IA."""
        result = {}
        for subj in SUBJECTS:
            df = self.query("""
                SELECT u.id AS user_id, u.name, u.usn, m.marks
                FROM marks m
                JOIN users u ON u.id = m.user_id
                WHERE m.ia_number=? AND m.subject=?
                ORDER BY m.marks DESC, u.name ASC
                LIMIT 1
            """, (ia_number, subj))
            if not df.empty:
                result[subj] = df.iloc[0].to_dict()
            else:
                result[subj] = None
        return result

    def get_overall_topper(self, ia_number=3):
        df = self.query("""
            SELECT u.id AS user_id, u.name, u.usn,
                   ms.percentage, ms.grade, ms.total
            FROM marks_summary ms
            JOIN users u ON u.id = ms.user_id
            WHERE ms.ia_number=?
            ORDER BY ms.percentage DESC, u.name ASC
            LIMIT 1
        """, (ia_number,))
        return df.iloc[0].to_dict() if not df.empty else None

    # ---------- ATTENDANCE ----------
    def attendance_percent(self, user_id, days=45):
        since = (date.today() - timedelta(days=days)).isoformat()
        df = self.query("""SELECT status FROM attendance
                           WHERE user_id=? AND att_date>=?""",
                        (user_id, since))
        if df.empty:
            return 0.0
        present = (df["status"].isin(["P", "L", "E"])).sum()
        return round((present / len(df)) * 100, 2)

    def get_attendance(self, user_id, days=45):
        since = (date.today() - timedelta(days=days)).isoformat()
        return self.query("""SELECT * FROM attendance
                             WHERE user_id=? AND att_date>=?
                             ORDER BY att_date""",
                          (user_id, since))

    def get_class_attendance_summary(self, days=45):
        since = (date.today() - timedelta(days=days)).isoformat()
        return self.query("""
            SELECT u.id AS user_id, u.name, u.usn,
                   SUM(CASE WHEN a.status IN ('P','L','E') THEN 1 ELSE 0 END) AS present,
                   COUNT(a.id) AS total
            FROM users u
            LEFT JOIN attendance a
                   ON a.user_id = u.id AND a.att_date >= ?
            WHERE u.role='student' AND u.status='approved'
            GROUP BY u.id
            ORDER BY u.usn
        """, (since,))

    def mark_attendance(self, user_id, att_date, status,
                        subject="ALL", marked_by="admin"):
        self.execute("""INSERT INTO attendance
                        (id,user_id,att_date,subject,status,marked_by,marked_at)
                        VALUES (?,?,?,?,?,?,?)
                        ON CONFLICT(user_id,att_date,subject)
                        DO UPDATE SET status=excluded.status,
                                      marked_by=excluded.marked_by,
                                      marked_at=excluded.marked_at""",
                     (str(uuid.uuid4()), user_id, att_date, subject,
                      status, marked_by, datetime.now().isoformat()))

    # ---------- BADGES ----------
    def get_all_badges(self):
        return self.query("SELECT * FROM badges ORDER BY name")

    def get_user_badges(self, user_id):
        return self.query("""
            SELECT b.id, b.name, b.icon, b.description, b.color,
                   ub.earned_at
            FROM user_badges ub
            JOIN badges b ON b.id = ub.badge_id
            WHERE ub.user_id=?
            ORDER BY ub.earned_at DESC
        """, (user_id,))

    def award_badge(self, user_id, badge_id, note=None):
        self._award_badge(user_id, badge_id, datetime.now().isoformat())
        self.log_audit("system", "award_badge",
                       f"{user_id}:{badge_id}")
        self.conn.commit()

    def revoke_badge(self, user_id, badge_id):
        self.execute("DELETE FROM user_badges WHERE user_id=? AND badge_id=?",
                     (user_id, badge_id))
        self.log_audit("system", "revoke_badge", f"{user_id}:{badge_id}")

    # ---------- CERTIFICATES ----------
    def get_user_certificates(self, user_id):
        return self.query("""SELECT * FROM certificates
                             WHERE user_id=?
                             ORDER BY issued_at DESC""",
                          (user_id,))

    def issue_certificate(self, user_id, cert_type, title,
                          file_path=None, issued_by="admin"):
        cid = str(uuid.uuid4())
        self.execute("""INSERT INTO certificates
                        (id,user_id,cert_type,title,file_path,
                         issued_by,issued_at)
                        VALUES (?,?,?,?,?,?,?)""",
                     (cid, user_id, cert_type, title, file_path,
                      issued_by, datetime.now().isoformat()))
        self.log_audit(issued_by, "issue_certificate",
                       f"{user_id}:{cert_type}")
        return cid

    # ---------- ACTIVITIES ----------
    def get_activities(self):
        return self.query("SELECT * FROM activities ORDER BY name")

    def get_user_activities(self, user_id):
        return self.query("""
            SELECT a.id, a.name, a.type, a.subject, a.max_score,
                   s.score, s.percentage, s.completed_at
            FROM activity_scores s
            JOIN activities a ON a.id = s.activity_id
            WHERE s.user_id=?
            ORDER BY s.completed_at DESC
        """, (user_id,))

    def log_activity_score(self, user_id, activity_id, score, max_score):
        pct = round((score / max_score) * 100, 2) if max_score else 0
        self.execute("""INSERT INTO activity_scores
                        (id,user_id,activity_id,score,max_score,
                         percentage,completed_at)
                        VALUES (?,?,?,?,?,?,?)""",
                     (str(uuid.uuid4()), user_id, activity_id,
                      score, max_score, pct,
                      datetime.now().isoformat()))

    # ---------- ALERTS ----------
    def get_alerts(self, resolved=False, user_id=None):
        if user_id:
            return self.query("""SELECT * FROM alerts
                                 WHERE resolved=? AND user_id=?
                                 ORDER BY created_at DESC""",
                              (1 if resolved else 0, user_id))
        return self.query("""SELECT a.*, u.name AS student_name, u.usn
                             FROM alerts a
                             LEFT JOIN users u ON u.id = a.user_id
                             WHERE a.resolved=?
                             ORDER BY a.created_at DESC""",
                          (1 if resolved else 0,))

    def create_alert(self, user_id, alert_type, severity, message,
                     suggested_action=None):
        self.execute("""INSERT INTO alerts
                        (id,user_id,alert_type,severity,message,
                         suggested_action,resolved,created_at)
                        VALUES (?,?,?,?,?,?,?,?)""",
                     (str(uuid.uuid4()), user_id, alert_type, severity,
                      message,
                      json.dumps(suggested_action) if suggested_action else None,
                      0, datetime.now().isoformat()))

    def resolve_alert(self, alert_id):
        self.execute("""UPDATE alerts
                        SET resolved=1, resolved_at=?
                        WHERE id=?""",
                     (datetime.now().isoformat(), alert_id))

    # ---------- INTERVENTIONS ----------
    def log_intervention(self, facilitator_id, student_id, itype,
                         payload=None):
        self.execute("""INSERT INTO interventions
                        (id,facilitator_id,student_id,itype,payload,created_at)
                        VALUES (?,?,?,?,?,?)""",
                     (str(uuid.uuid4()), facilitator_id, student_id,
                      itype,
                      json.dumps(payload) if payload else None,
                      datetime.now().isoformat()))

    def get_interventions(self, facilitator_id=None, student_id=None):
        clauses, params = [], []
        if facilitator_id:
            clauses.append("facilitator_id=?")
            params.append(facilitator_id)
        if student_id:
            clauses.append("student_id=?")
            params.append(student_id)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        return self.query(f"""SELECT i.*, u.name AS student_name
                              FROM interventions i
                              LEFT JOIN users u ON u.id = i.student_id
                              {where}
                              ORDER BY i.created_at DESC""",
                          tuple(params))

    # ---------- REMEDIAL ----------
    def create_remedial(self, subject, topic, facilitator_id,
                        scheduled_at, duration_min=45, notes=None):
        rid = str(uuid.uuid4())
        self.execute("""INSERT INTO remedial_sessions
                        (id,subject,topic,facilitator_id,scheduled_at,
                         duration_min,notes,status,created_at)
                        VALUES (?,?,?,?,?,?,?,?,?)""",
                     (rid, subject, topic, facilitator_id, scheduled_at,
                      duration_min, notes, "scheduled",
                      datetime.now().isoformat()))
        return rid

    def enroll_remedial(self, session_id, user_id):
        self.execute("""INSERT INTO remedial_enrollments
                        (id,session_id,user_id,attended,outcome,
                         improvement,enrolled_at)
                        VALUES (?,?,?,?,?,?,?)""",
                     (str(uuid.uuid4()), session_id, user_id,
                      0, None, 0, datetime.now().isoformat()))

    def get_remedial_sessions(self, facilitator_id=None):
        if facilitator_id:
            return self.query("""SELECT * FROM remedial_sessions
                                 WHERE facilitator_id=?
                                 ORDER BY scheduled_at DESC""",
                              (facilitator_id,))
        return self.query("""SELECT * FROM remedial_sessions
                             ORDER BY scheduled_at DESC""")

    def get_user_remedial(self, user_id):
        return self.query("""
            SELECT rs.*, re.attended, re.outcome, re.improvement
            FROM remedial_enrollments re
            JOIN remedial_sessions rs ON rs.id = re.session_id
            WHERE re.user_id=?
            ORDER BY rs.scheduled_at DESC
        """, (user_id,))

    # ---------- COLORS / HISTORY ----------
    def get_color_history(self, user_id):
        return self.query("""SELECT * FROM color_history
                             WHERE user_id=?
                             ORDER BY ia_number""",
                          (user_id,))

    # ---------- AUDIT ----------
    def log_audit(self, actor_id, action, target=None, details=None):
        self.execute("""INSERT INTO audit_log
                        (id,actor_id,action,target,details,created_at)
                        VALUES (?,?,?,?,?,?)""",
                     (str(uuid.uuid4()), actor_id, action, target,
                      details, datetime.now().isoformat()))

    def get_audit_log(self, limit=200):
        return self.query("""SELECT a.*, u.name AS actor_name
                             FROM audit_log a
                             LEFT JOIN users u ON u.id = a.actor_id
                             ORDER BY a.created_at DESC
                             LIMIT ?""",
                          (limit,))

    # ---------- SETTINGS ----------
    def set_setting(self, key, value):
        self.execute("""INSERT INTO settings(key,value) VALUES (?,?)
                        ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
                     (key, str(value)))

    def get_setting(self, key, default=None):
        df = self.query("SELECT value FROM settings WHERE key=?", (key,))
        return df.iloc[0]["value"] if not df.empty else default

    # ---------- AGGREGATES ----------
    def class_zone_counts(self, ia_number=3):
        df = self.query("""SELECT zone, COUNT(*) AS n
                           FROM marks_summary
                           WHERE ia_number=?
                           GROUP BY zone""", (ia_number,))
        out = {"red": 0, "yellow": 0, "green": 0, "gold": 0}
        for _, row in df.iterrows():
            out[row["zone"]] = int(row["n"])
        return out

    def class_subject_averages(self, ia_number=3):
        df = self.query("""SELECT
                              AVG(maths) AS Maths,
                              AVG(phy)   AS Physics,
                              AVG(che)   AS Chemistry,
                              AVG(cs)    AS "Computer Science"
                           FROM marks_summary
                           WHERE ia_number=?""", (ia_number,))
        if df.empty:
            return {s: 0 for s in SUBJECTS}
        return {s: round(float(df.iloc[0][s] or 0), 2) for s in SUBJECTS}


# =============================================================
# 3. MODULE-LEVEL SINGLETON
# =============================================================

_db_instance = None


def get_db() -> Database:
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance


# =============================================================
# 4. SANITY CHECK
# =============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  SHRUTHI JHARI — database.py sanity check")
    print("=" * 60)

    db = Database()
    students = db.get_all_students()
    print(f"\n👥 Students       : {len(students)}")

    topper = db.get_overall_topper(ia_number=3)
    if topper:
        print(f"🥇 Overall topper : {topper['name']}  "
              f"({topper['percentage']}% · Grade {topper['grade']})")

    print("\n📊 Subject toppers (IA-3):")
    for subj, info in db.get_subject_toppers(ia_number=3).items():
        if info:
            print(f"   {subj:<18} → {info['name']:<20} ({info['marks']} marks)")

    print("\n🎨 Class zone counts (IA-3):")
    for zone, count in db.class_zone_counts(ia_number=3).items():
        emoji = {"red": "🔴", "yellow": "🟡", "green": "🟢", "gold": "🏆"}[zone]
        print(f"   {emoji} {zone:<8} → {count}")

    print("\n📈 Class subject averages (IA-3):")
    for subj, avg in db.class_subject_averages(ia_number=3).items():
        print(f"   {subj:<18} → {avg}")

    print("\n🏅 Badges awarded (first 5 students):")
    for _, s in students.head(5).iterrows():
        badges = db.get_user_badges(s["id"])
        print(f"   {s['name']:<20} → {len(badges)} badges")

    print("\n🔔 Active alerts  :", len(db.get_alerts(resolved=False)))

    print("\n✅ database.py OK")
    print("=" * 60)