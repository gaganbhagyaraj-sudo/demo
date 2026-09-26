# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  pages/student/profile.py  ·  Full student profile
# =============================================================

from __future__ import annotations

import os
import sys

# --- make project root importable ---
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tkinter import filedialog

import customtkinter as ctk

from config import (
    APP_NAME, COLORS, STATUS, ZONE_COLORS, ZONE_LABELS,
    SUBJECTS, SUBJECT_SHORT, IA_LIST,
    FONTS, FONT_FAMILY,
    CARD_RADIUS, BUTTON_RADIUS, CHIP_RADIUS,
    PAD_SM, PAD_MD, PAD_LG, PAD_XL,
)
from pages.base_page import BasePage
from utils.avatars import (
    load_avatar, save_uploaded_avatar, delete_uploaded_avatar,
    has_uploaded_avatar, clear_cache,
)
from utils.charts import (
    subject_bar_chart, ia_trend_chart, radar_chart,
    attendance_trend_chart, gauge_chart,
)
from models.bkt import BKTTracker
from models.badges import BadgeEngine
from config import BADGES, BADGE_BY_ID


# =============================================================
# PROFILE PAGE
# =============================================================

class StudentProfilePage(BasePage):
    """
    Full student profile. Renders for the current user by default,
    or for a target user_id passed via navigate("stu_profile", user_id=...).
    """

    def __init__(self, master, app, target_user_id: str = None):
        super().__init__(master, app)

        # Default to self; allow viewing another student (read-only)
        self.target_id = target_user_id or (self.user or {}).get("id")
        self.is_self = (self.target_id == (self.user or {}).get("id"))

        self.target = self.db.get_user(self.target_id) if self.target_id else None

        title = "My Profile" if self.is_self else (self.target or {}).get("name", "Profile")
        subtitle = "Your complete academic record" if self.is_self else "Student record"
        self.build_header(title, subtitle, back=not self.is_self)
        self.build_content(scrollable=True)
        self.build_footer()

        self._tracker = BKTTracker(self.db)
        self._badges = BadgeEngine(self.db)

        self.render()

    # =========================================================
    # RENDER
    # =========================================================

    def render(self):
        if not self.target:
            self._render_empty("Student not found.")
            return

        content = self._content

        # 1. Hero
        self._render_hero(content)

        # 2. Zone + quick actions
        self._render_actions_row(content)

        # 3. Marks table (IA-1/2/3)
        self.section_title("Marks Summary", parent=content)
        self._render_marks_table(content)

        # 4. Two-column charts: Radar + IA Trend
        self.section_title("Performance Charts", parent=content)
        self._render_charts_row(content)

        # 5. Subject bar chart
        self.section_title("Subject Breakdown", parent=content)
        self._render_subject_chart(content)

        # 6. Color journey
        self.section_title("Color Journey (Red → Green)", parent=content)
        self._render_color_journey(content)

        # 7. Badges wall
        self.section_title("Badges Showcase", parent=content)
        self._render_badge_wall(content)

        # 8. Certificates
        self.section_title("Certificates", parent=content)
        self._render_certificates(content)

        # 9. Activities
        self.section_title("Co-curricular Activities", parent=content)
        self._render_activities(content)

    # =========================================================
    # HERO
    # =========================================================

    def _render_hero(self, parent):
        user = self.target
        uid = user["id"]

        hero = self.card(parent)
        hero.pack(fill="x", pady=(0, PAD_MD))

        inner = ctk.CTkFrame(hero, fg_color="transparent")
        inner.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        # -- Avatar with zone ring + upload controls --
        left = ctk.CTkFrame(inner, fg_color="transparent")
        left.pack(side="left")

        zone = self._current_zone(uid)

        try:
            avatar = load_avatar(
                user_id=uid,
                name=user.get("name", ""),
                size=140,
                shape="circle",
                zone=zone,
                ring_width=8 if zone else 0,
            )
            ctk.CTkLabel(left, image=avatar, text="").pack()
        except Exception:
            pass

        if self.is_self:
            avatar_btns = ctk.CTkFrame(left, fg_color="transparent")
            avatar_btns.pack(pady=(8, 0))

            self.secondary_button(
                avatar_btns, "Upload", self._upload_avatar,
                width=100, height=30,
            ).pack(side="left", padx=(0, 6))

            if has_uploaded_avatar(uid):
                self.danger_button(
                    avatar_btns, "Remove", self._remove_avatar,
                    width=100, height=30,
                ).pack(side="left")

        # -- Info --
        info = ctk.CTkFrame(inner, fg_color="transparent")
        info.pack(side="left", padx=(PAD_LG, 0), fill="both", expand=True)

        ctk.CTkLabel(
            info, text=user.get("name", "Student"),
            font=(FONT_FAMILY, 26, "bold"),
            text_color=COLORS["text"], anchor="w",
        ).pack(anchor="w")

        # USN / grade / section line
        meta = []
        if user.get("usn"):
            meta.append(f"USN: {user['usn']}")
        if user.get("grade"):
            meta.append(user["grade"])
        if user.get("section"):
            meta.append(f"Section {user['section']}")
        ctk.CTkLabel(
            info, text="   ·   ".join(meta) or "Student",
            font=FONTS["small"],
            text_color=COLORS["text_muted"], anchor="w",
        ).pack(anchor="w", pady=(2, 12))

        # Zone chip (prominent)
        if zone:
            zc = ctk.CTkFrame(
                info, fg_color=ZONE_COLORS.get(zone, COLORS["primary"]),
                corner_radius=CHIP_RADIUS)
            zc.pack(anchor="w", pady=(0, 12))
            icon = {"red": "🔴", "yellow": "🟡",
                    "green": "🟢", "gold": "🏆"}.get(zone, "•")
            label = ZONE_LABELS.get(zone, zone.title())
            ctk.CTkLabel(
                zc, text=f"  {icon}  {label}  ",
                font=FONTS["small_bold"],
                text_color="#FFFFFF",
            ).pack(padx=6, pady=5)

        # Interests
        try:
            interests = self.db.get_user_interests(uid)
            if interests:
                chips = ctk.CTkFrame(info, fg_color="transparent")
                chips.pack(anchor="w", fill="x")
                ctk.CTkLabel(
                    chips, text="Interests:",
                    font=FONTS["tiny"],
                    text_color=COLORS["text_muted"]).pack(side="left",
                                                          padx=(0, 8))
                for tag in interests:
                    self.chip(chips, tag).pack(side="left", padx=(0, 6))
        except Exception:
            pass

    # =========================================================
    # ACTIONS ROW
    # =========================================================

    def _render_actions_row(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        if self.is_self:
            self.primary_button(
                row, "View Learning Path",
                command=lambda: self.navigate("stu_learning"),
                width=200, height=42,
            ).pack(side="left", padx=(0, PAD_MD))

            self.secondary_button(
                row, "My Marks", width=140, height=42,
                command=lambda: self.navigate("stu_marks"),
            ).pack(side="left", padx=(0, PAD_MD))

            self.secondary_button(
                row, "Attendance", width=140, height=42,
                command=lambda: self.navigate("stu_attendance"),
            ).pack(side="left", padx=(0, PAD_MD))

            self.secondary_button(
                row, "Badges", width=140, height=42,
                command=lambda: self.navigate("stu_badges"),
            ).pack(side="left")

    # =========================================================
    # MARKS TABLE
    # =========================================================

    def _render_marks_table(self, parent):
        uid = self.target["id"]
        card = self.card(parent)
        card.pack(fill="x", pady=(0, PAD_MD))

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        try:
            summary = self.db.get_marks_summary(uid)
        except Exception:
            summary = None

        if summary is None or summary.empty:
            ctk.CTkLabel(
                body, text="No marks yet.",
                font=FONTS["small"],
                text_color=COLORS["text_muted"]).pack()
            return

        # Header row
        headers = ["IA", "Maths", "Phy", "Che", "CS", "Total", "%", "Grade"]
        grid = ctk.CTkFrame(body, fg_color="transparent")
        grid.pack(fill="x")

        for i, h in enumerate(headers):
            ctk.CTkLabel(
                grid, text=h,
                font=(FONT_FAMILY, 11, "bold"),
                text_color=COLORS["text_muted"],
            ).grid(row=0, column=i, padx=6, pady=6, sticky="w")

        for r, (_, row) in enumerate(summary.iterrows(), start=1):
            data = [
                f"IA-{int(row['ia_number'])}",
                f"{row['maths']:.0f}",
                f"{row['phy']:.0f}",
                f"{row['che']:.0f}",
                f"{row['cs']:.0f}",
                f"{int(row['total'])}",
                f"{row['percentage']:.2f}%",
                row["grade"],
            ]
            grade_color = ZONE_COLORS.get(row["zone"],
                                          COLORS["text"])
            for i, val in enumerate(data):
                color = grade_color if i == 7 else COLORS["text"]
                fw = "bold" if i == 7 else "normal"
                ctk.CTkLabel(
                    grid, text=val,
                    font=(FONT_FAMILY, 11, fw),
                    text_color=color,
                ).grid(row=r, column=i, padx=6, pady=5, sticky="w")

        # Average row
        try:
            avg_pct = summary["percentage"].mean()
            avg_grade = summary.iloc[-1]["grade"]
            ctk.CTkLabel(
                body,
                text=f"Average across all IAs: {avg_pct:.2f}%  ·  "
                     f"Latest grade: {avg_grade}",
                font=FONTS["small_bold"],
                text_color=COLORS["text"],
            ).pack(anchor="w", pady=(10, 0))
        except Exception:
            pass

    # =========================================================
    # CHARTS ROW (radar + IA trend)
    # =========================================================

    def _render_charts_row(self, parent):
        uid = self.target["id"]
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, PAD_MD))

        # -- Radar: latest IA subject profile --
        left = ctk.CTkFrame(row, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=(0, PAD_MD))

        try:
            ms = self.db.get_marks_summary(uid)
            if not ms.empty:
                latest = ms.iloc[-1]
                fig = radar_chart(
                    [latest["maths"], latest["phy"],
                     latest["che"], latest["cs"]],
                    title=f"Subject Profile (IA-{int(latest['ia_number'])})",
                    animate=False,
                )
                self.chart_frame(left, fig, height=300).pack(fill="x")
        except Exception as e:
            ctk.CTkLabel(left, text=f"(radar unavailable: {e})",
                         font=FONTS["tiny"],
                         text_color=COLORS["text_muted"]).pack()

        # -- IA trend per subject --
        right = ctk.CTkFrame(row, fg_color="transparent")
        right.pack(side="left", fill="both", expand=True)

        try:
            all_marks = self.db.get_marks(uid)
            ia_data = {}
            for subj in SUBJECTS:
                vals = []
                for ia in (1, 2, 3):
                    sub = all_marks[
                        (all_marks["ia_number"] == ia) &
                        (all_marks["subject"] == subj)]
                    vals.append(float(sub.iloc[0]["marks"]) if not sub.empty
                                else 0.0)
                ia_data[subj] = vals

            fig = ia_trend_chart(ia_data,
                                 title="IA Performance Trend",
                                 animate=False)
            self.chart_frame(right, fig, height=300).pack(fill="x")
        except Exception as e:
            ctk.CTkLabel(right, text=f"(trend unavailable: {e})",
                         font=FONTS["tiny"],
                         text_color=COLORS["text_muted"]).pack()

    # =========================================================
    # SUBJECT BAR CHART
    # =========================================================

    def _render_subject_chart(self, parent):
        uid = self.target["id"]
        try:
            ms = self.db.get_marks_summary(uid)
            if ms.empty:
                return
            latest = ms.iloc[-1]
            avgs = {
                "Maths":            float(latest["maths"]),
                "Physics":          float(latest["phy"]),
                "Chemistry":        float(latest["che"]),
                "Computer Science": float(latest["cs"]),
            }
            fig = subject_bar_chart(
                avgs,
                title=f"Subject Averages (IA-{int(latest['ia_number'])})",
                animate=False)
            self.chart_frame(parent, fig, height=300).pack(
                fill="x", pady=(0, PAD_MD))
        except Exception as e:
            ctk.CTkLabel(parent, text=f"(chart unavailable: {e})",
                         font=FONTS["tiny"],
                         text_color=COLORS["text_muted"]).pack()

    # =========================================================
    # COLOR JOURNEY
    # =========================================================

    def _render_color_journey(self, parent):
        uid = self.target["id"]
        card = self.card(parent)
        card.pack(fill="x", pady=(0, PAD_MD))

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        try:
            hist = self.db.get_color_history(uid)
        except Exception:
            hist = None

        if hist is None or hist.empty:
            ctk.CTkLabel(body, text="No history yet.",
                         font=FONTS["small"],
                         text_color=COLORS["text_muted"]).pack()
            return

        row = ctk.CTkFrame(body, fg_color="transparent")
        row.pack(fill="x")

        for i, (_, h) in enumerate(hist.iterrows()):
            zone = h["zone"]
            color = ZONE_COLORS.get(zone, COLORS["text_dim"])
            icon = {"red": "🔴", "yellow": "🟡",
                    "green": "🟢", "gold": "🏆"}.get(zone, "•")

            # IA bubble
            bubble = ctk.CTkFrame(row, fg_color=color,
                                  width=64, height=64, corner_radius=32)
            bubble.pack(side="left", padx=(0, 6))
            bubble.pack_propagate(False)

            ctk.CTkLabel(
                bubble,
                text=f"IA{int(h['ia_number'])}\n{h['percentage']:.0f}%",
                font=(FONT_FAMILY, 10, "bold"),
                text_color="#FFFFFF",
                justify="center",
            ).place(relx=0.5, rely=0.5, anchor="center")

            # Arrow between
            if i < len(hist) - 1:
                next_zone = hist.iloc[i + 1]["zone"]
                rank = {"red": 0, "yellow": 1, "green": 2, "gold": 3}
                delta = rank.get(next_zone, 0) - rank.get(zone, 0)
                arrow = "→" if delta == 0 else ("↗" if delta > 0 else "↘")
                arrow_color = COLORS["text_muted"] if delta == 0 \
                    else (STATUS["green"] if delta > 0 else STATUS["red"])
                ctk.CTkLabel(
                    row, text=arrow,
                    font=(FONT_FAMILY, 20, "bold"),
                    text_color=arrow_color,
                ).pack(side="left", padx=6)

        # Summary line
        try:
            first = hist.iloc[0]
            last = hist.iloc[-1]
            t = last["percentage"] - first["percentage"]
            arrow = "📈" if t > 0 else ("📉" if t < 0 else "→")
            ctk.CTkLabel(
                body,
                text=f"{arrow}  Improvement from IA-1 to "
                     f"IA-{int(last['ia_number'])}: {t:+.2f}%",
                font=FONTS["small_bold"],
                text_color=STATUS["green"] if t > 0 else
                           (STATUS["red"] if t < 0 else COLORS["text_muted"]),
            ).pack(anchor="w", pady=(14, 0))
        except Exception:
            pass

    # =========================================================
    # BADGES WALL
    # =========================================================

    def _render_badge_wall(self, parent):
        uid = self.target["id"]

        try:
            progress = self._badges.progress_for_user(uid)
        except Exception:
            progress = []

        if not progress:
            ctk.CTkLabel(parent, text="No badges available.",
                         font=FONTS["small"],
                         text_color=COLORS["text_muted"]).pack()
            return

        earned = [w for w in progress if w["earned"]]
        locked = [w for w in progress if not w["earned"]]

        # Earned row
        if earned:
            ctk.CTkLabel(
                parent,
                text=f"Earned ({len(earned)})",
                font=FONTS["small_bold"],
                text_color=STATUS["green"],
            ).pack(anchor="w", pady=(0, 6))

            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", pady=(0, PAD_MD))

            from theme import BadgeCard
            for w in earned:
                b = w["badge"]
                BadgeCard(
                    row,
                    icon=b["icon"],
                    name=b["name"],
                    color=b.get("color") or STATUS["gold"],
                    size=84,
                    earned=True,
                    parent_bg=COLORS["bg"],
                ).pack(side="left", padx=(0, 12))

        # Locked row
        if locked:
            ctk.CTkLabel(
                parent,
                text=f"Locked ({len(locked)})",
                font=FONTS["small_bold"],
                text_color=COLORS["text_muted"],
            ).pack(anchor="w", pady=(0, 6))

            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", pady=(0, PAD_MD))

            from theme import BadgeCard
            for w in locked[:6]:
                b = w["badge"]
                BadgeCard(
                    row,
                    icon=b["icon"],
                    name=b["name"],
                    color=b.get("color") or STATUS["gold"],
                    size=84,
                    earned=False,
                    parent_bg=COLORS["bg"],
                ).pack(side="left", padx=(0, 12))

    # =========================================================
    # CERTIFICATES
    # =========================================================

    def _render_certificates(self, parent):
        uid = self.target["id"]
        card = self.card(parent)
        card.pack(fill="x", pady=(0, PAD_MD))

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        try:
            certs = self.db.get_user_certificates(uid)
        except Exception:
            certs = None

        if certs is None or certs.empty:
            ctk.CTkLabel(
                body, text="No certificates yet. Keep shining! 🌟",
                font=FONTS["small"],
                text_color=COLORS["text_muted"]).pack()
            return

        for _, c in certs.iterrows():
            row = ctk.CTkFrame(body, fg_color=COLORS["surface_alt"],
                               corner_radius=10)
            row.pack(fill="x", pady=3)

            left = ctk.CTkFrame(row, fg_color="transparent")
            left.pack(side="left", padx=12, pady=10, fill="x", expand=True)

            ctk.CTkLabel(
                left, text=f"📜  {c['title']}",
                font=FONTS["small_bold"],
                text_color=COLORS["text"], anchor="w").pack(anchor="w")

            ctk.CTkLabel(
                left, text=f"Issued {(c['issued_at'] or '')[:10]}",
                font=FONTS["tiny"],
                text_color=COLORS["text_muted"], anchor="w").pack(anchor="w")

            if c.get("file_path"):
                self.secondary_button(
                    row, "Open", width=70, height=30,
                    command=lambda p=c["file_path"]: self._open_file(p),
                ).pack(side="right", padx=12)

    # =========================================================
    # ACTIVITIES
    # =========================================================

    def _render_activities(self, parent):
        uid = self.target["id"]
        card = self.card(parent)
        card.pack(fill="x", pady=(0, PAD_MD))

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

        try:
            acts = self.db.get_user_activities(uid)
        except Exception:
            acts = None

        if acts is None or acts.empty:
            ctk.CTkLabel(
                body, text="No activities logged yet.",
                font=FONTS["small"],
                text_color=COLORS["text_muted"]).pack()
            return

        for _, a in acts.head(6).iterrows():
            row = ctk.CTkFrame(body, fg_color=COLORS["surface_alt"],
                               corner_radius=10)
            row.pack(fill="x", pady=3)

            left = ctk.CTkFrame(row, fg_color="transparent")
            left.pack(side="left", padx=12, pady=10, fill="x", expand=True)

            ctk.CTkLabel(
                left, text=a["name"],
                font=FONTS["small_bold"],
                text_color=COLORS["text"], anchor="w").pack(anchor="w")

            meta = f"{a.get('type', '—').title()}"
            if a.get("completed_at"):
                meta += f"  ·  {a['completed_at'][:10]}"
            ctk.CTkLabel(
                left, text=meta,
                font=FONTS["tiny"],
                text_color=COLORS["text_muted"], anchor="w").pack(anchor="w")

            pct = float(a.get("percentage") or 0)
            color = STATUS["green"] if pct >= 80 else \
                    (STATUS["amber"] if pct >= 50 else STATUS["red"])
            ctk.CTkLabel(
                row, text=f"{pct:.0f}%",
                font=(FONT_FAMILY, 14, "bold"),
                text_color=color,
            ).pack(side="right", padx=14)

    # =========================================================
    # HELPERS
    # =========================================================

    def _current_zone(self, uid):
        try:
            ms = self.db.get_marks_summary(uid)
            if not ms.empty:
                return ms.iloc[-1]["zone"]
        except Exception:
            pass
        return None

    def _upload_avatar(self):
        if not self.target:
            return
        path = filedialog.askopenfilename(
            title="Choose a profile photo",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.webp")])
        if not path:
            return
        try:
            save_uploaded_avatar(self.target["id"], path)
            clear_cache(self.target["id"])
            self.toast("Profile photo updated", "success")
            # Rebuild page
            self.navigate("stu_profile")
        except Exception as e:
            self.toast(f"Upload failed: {e}", "error")

    def _remove_avatar(self):
        if not self.target:
            return
        if delete_uploaded_avatar(self.target["id"]):
            clear_cache(self.target["id"])
            self.toast("Photo removed", "info")
            self.navigate("stu_profile")
        else:
            self.toast("No photo to remove", "warning")

    def _open_file(self, path: str):
        try:
            if not os.path.exists(path):
                self.toast("File not found", "error")
                return
            if sys.platform.startswith("win"):
                os.startfile(path)
            elif sys.platform == "darwin":
                os.system(f'open "{path}"')
            else:
                os.system(f'xdg-open "{path}"')
        except Exception as e:
            self.toast(f"Cannot open: {e}", "error")

    def _render_empty(self, msg):
        ctk.CTkLabel(
            self._content, text=msg,
            font=FONTS["h3"],
            text_color=COLORS["text_muted"]).pack(pady=60)


# =============================================================
# SANITY CHECK
# =============================================================

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")

    class _FakeApp:
        def __init__(self):
            self._user = None
            try:
                from database import get_db
                self.db = get_db()
                stu = self.db.get_all_students().iloc[0]
                self._user = stu.to_dict()
            except Exception as e:
                print(f"(no DB: {e})")
                self.db = None

        @property
        def current_user(self):
            return self._user

        def show_page(self, key, **kw):
            print(f"[profile] → show_page('{key}')  args={kw}")

        def go_back(self):
            print("[profile] back")

        def logout(self):
            print("[profile] logout")

    root = ctk.CTk()
    W, H = 1280, 900
    root.geometry(f"{W}x{H}")
    root.configure(fg_color=COLORS["bg"])
    root.title(f"{APP_NAME} — profile preview")

    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - W) // 2
    y = (sh - H) // 2
    root.geometry(f"{W}x{H}+{x}+{y}")

    app = _FakeApp()
    page = StudentProfilePage(root, app)
    page.pack(fill="both", expand=True)
    root.mainloop()
    print("\n✅ pages/student/profile.py OK")