# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  main.py  ·  Application entry point and page router
# =============================================================

from __future__ import annotations

import os
import sys

# --- make project root importable ---
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import importlib
import traceback

import tkinter as tk
import customtkinter as ctk

from config import (
    APP_NAME, APP_TAGLINE, APP_VERSION, APP_YEAR,
    COLORS, STATUS,
    FONTS, FONT_FAMILY,
    WINDOW_DEFAULT_W, WINDOW_DEFAULT_H,
    WINDOW_MIN_W, WINDOW_MIN_H,
    PAD_SM, PAD_MD, PAD_LG, PAD_XL,
    PAGES,
    ROLE_ADMIN, ROLE_FACILITATOR, ROLE_STUDENT,
)


# =============================================================
# PAGE LOADER  (lazy import via registry in config.PAGES)
# =============================================================

# Map config.PAGES string → (module, class name)
# Class names follow a stable convention derived from the module name.
CLASS_NAMES = {
    # root
    "splash":       "SplashPage",
    "landing":      "LandingPage",
    # auth
    "login":        "LoginPage",
    "register":     "RegisterPage",
    "pending":      "PendingPage",
    # student
    "stu_dashboard":         "StudentDashboardPage",
    "stu_profile":           "StudentProfilePage",
    "stu_marks":             "StudentMarksPage",
    "stu_attendance":        "StudentAttendancePage",
    "stu_learning":          "StudentLearningPathPage",
    "stu_learning_screen":   "LearningScreenPage",
    "stu_mastery":           "StudentMasteryMapPage",
    "stu_activities":        "StudentActivitiesPage",
    "stu_badges":            "StudentBadgesPage",
    "stu_certificates":      "StudentCertificatesPage",
    "stu_remedial":          "StudentRemedialPage",
    "stu_leaderboard":       "StudentLeaderboardPage",
    "stu_topper_wall":       "StudentTopperWallPage",
    # facilitator
    "fac_command":        "FacilitatorCommandCenterPage",
    "fac_roster":         "FacilitatorClassRosterPage",
    "fac_deepdive":       "FacilitatorStudentDeepdivePage",
    "fac_alerts":         "FacilitatorAlertsFeedPage",
    "fac_marks":          "FacilitatorMarksAnalysisPage",
    "fac_attendance":     "FacilitatorAttendanceViewPage",
    "fac_heatmap":        "FacilitatorHeatmapPage",
    "fac_remedial":       "FacilitatorRemedialSessionsPage",
    "fac_interventions":  "FacilitatorInterventionsLogPage",
    "fac_badges":         "FacilitatorBadgeManagerPage",
    "fac_reports":        "FacilitatorReportsExportPage",
    # admin
    "admin_dashboard":         "AdminDashboardPage",
    "admin_approval":          "AdminApprovalQueuePage",
    "admin_users":             "AdminUserManagementPage",
    "admin_marks_manual":      "AdminMarksEntryManualPage",
    "admin_marks_excel":       "AdminMarksEntryExcelPage",
    "admin_attendance":        "AdminAttendanceManagerPage",
    "admin_analytics":         "AdminClassAnalyticsPage",
    "admin_certificates":      "AdminCertificateGeneratorPage",
    "admin_activities":        "AdminActivityManagerPage",
    "admin_audit":             "AdminAuditLogPage",
}

# Some pages take no kwargs; others (like deepdive, learning_screen)
# accept specific kwargs. Handle via inspect.
_NO_KWARG_PAGES = {
    "splash", "landing", "login", "register", "pending",
    "stu_dashboard", "stu_profile", "stu_marks", "stu_attendance",
    "stu_learning", "stu_mastery", "stu_activities", "stu_badges",
    "stu_certificates", "stu_remedial", "stu_leaderboard",
    "stu_topper_wall",
    "fac_command", "fac_roster", "fac_alerts", "fac_marks",
    "fac_attendance", "fac_heatmap", "fac_remedial",
    "fac_interventions", "fac_badges", "fac_reports",
    "admin_dashboard", "admin_approval", "admin_users",
    "admin_marks_manual", "admin_marks_excel", "admin_attendance",
    "admin_analytics", "admin_certificates", "admin_activities",
    "admin_audit",
}


def load_page_class(key: str):
    """
    Import the module and return the class for a page key.
    Uses config.PAGES for the module path and CLASS_NAMES for the class.
    """
    if key not in PAGES:
        raise KeyError(f"Unknown page: {key}")
    if key not in CLASS_NAMES:
        raise KeyError(f"No class mapping for page: {key}")

    module_path = PAGES[key]
    class_name = CLASS_NAMES[key]

    try:
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
        return cls
    except Exception as e:
        raise ImportError(
            f"Failed to load page '{key}' from '{module_path}.{class_name}': {e}"
        ) from e


# =============================================================
# APP
# =============================================================

class ShruthiJhariApp(ctk.CTk):
    """Main application window + router."""

    def __init__(self):
        super().__init__()

        # ---- Window setup ----
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.title(f"{APP_NAME} — {APP_TAGLINE}")
        self.geometry(f"{WINDOW_DEFAULT_W}x{WINDOW_DEFAULT_H}")
        self.minsize(WINDOW_MIN_W, WINDOW_MIN_H)
        self.configure(fg_color=COLORS["bg"])

        # Center on screen
        self._center_window()

        # ---- State ----
        self.current_user = None
        self.db = None
        self._current_page_key = None
        self._current_page = None
        self._stack = []   # back stack of (key, kwargs)

        # ---- Database ----
        self._init_db()

        # ---- Keyboard shortcuts ----
        self.bind("<Escape>", lambda e: self._on_escape())
        self.bind("<Control-q>", lambda e: self.quit())

        # ---- Show splash ----
        self.after(50, lambda: self.show_page("splash"))

    # =========================================================
    # INIT
    # =========================================================

    def _init_db(self):
        try:
            from database import get_db
            self.db = get_db()
        except Exception as e:
            print(f"[app] DB init failed: {e}")
            self.db = None

    def _center_window(self):
        try:
            self.update_idletasks()
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            w = WINDOW_DEFAULT_W
            h = WINDOW_DEFAULT_H
            x = (sw - w) // 2
            y = (sh - h) // 2
            self.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            pass

    # =========================================================
    # NAVIGATION
    # =========================================================

    def show_page(self, key: str, *, push_history: bool = True,
                  **kwargs):
        """
        Replace the current page with the page identified by `key`.
        If push_history is True and we're leaving a page, the previous
        (key, kwargs) is pushed onto the back stack.
        """
        if key == self._current_page_key:
            # Same page — just refresh it
            self._reload_current()
            return

        # Push current page to history
        if push_history and self._current_page_key:
            self._stack.append(
                (self._current_page_key, self._last_kwargs or {}))

        # Destroy old page
        try:
            if self._current_page is not None:
                if hasattr(self._current_page, "on_hide"):
                    try:
                        self._current_page.on_hide()
                    except Exception:
                        pass
                self._current_page.destroy()
        except Exception:
            pass

        self._current_page = None
        self._current_page_key = None

        # Load new page
        try:
            cls = load_page_class(key)
        except Exception as e:
            traceback.print_exc()
            self._render_error(key, str(e))
            return

        try:
            if key in _NO_KWARG_PAGES:
                page = cls(self, self)
            else:
                page = cls(self, self, **kwargs)

            page.pack(fill="both", expand=True)

            self._current_page = page
            self._current_page_key = key
            self._last_kwargs = dict(kwargs)

            # Notify page it's been shown (for refresh hooks)
            if hasattr(page, "on_show"):
                try:
                    page.on_show(**kwargs)
                except Exception:
                    pass

        except Exception as e:
            traceback.print_exc()
            self._render_error(key, str(e))

    def _reload_current(self):
        """Reload the current page from scratch."""
        key = self._current_page_key
        kw = getattr(self, "_last_kwargs", {}) or {}
        if key:
            self._current_page_key = None  # force re-create
            self.show_page(key, push_history=False, **kw)

    def go_back(self):
        """Return to the previous page, if any."""
        if not self._stack:
            # No history — go to landing (or login if signed in)
            if self.current_user:
                self._go_home_for_role()
            else:
                self.show_page("landing", push_history=False)
            return

        key, kwargs = self._stack.pop()
        self.show_page(key, push_history=False, **kwargs)

    def _on_escape(self):
        # Esc triggers back navigation
        self.go_back()

    # =========================================================
    # AUTH / ROLE ROUTING
    # =========================================================

    def set_user(self, user):
        """Called by login / pending pages after successful auth."""
        self.current_user = user
        self._stack = []   # reset history
        self._go_home_for_role()

    def _go_home_for_role(self):
        role = (self.current_user or {}).get("role", "")
        if role == ROLE_ADMIN:
            self.show_page("admin_dashboard", push_history=False)
        elif role == ROLE_FACILITATOR:
            self.show_page("fac_command", push_history=False)
        elif role == ROLE_STUDENT:
            self.show_page("stu_dashboard", push_history=False)
        else:
            self.show_page("landing", push_history=False)

    def logout(self):
        self.current_user = None
        self._stack = []
        # Clear avatar cache just in case
        try:
            from utils.avatars import clear_cache
            clear_cache()
        except Exception:
            pass
        self.show_page("landing", push_history=False)

    # =========================================================
    # ERROR PAGE
    # =========================================================

    def _render_error(self, key: str, message: str):
        # Destroy everything
        for w in self.winfo_children():
            try:
                w.destroy()
            except Exception:
                pass

        frame = ctk.CTkFrame(self, fg_color=COLORS["bg"])
        frame.pack(fill="both", expand=True)

        body = ctk.CTkFrame(frame, fg_color=COLORS["surface"],
                            corner_radius=16,
                            border_width=1,
                            border_color=STATUS["red"])
        body.place(relx=0.5, rely=0.5, anchor="center",
                   width=640, height=380)

        inner = ctk.CTkFrame(body, fg_color="transparent")
        inner.pack(fill="both", expand=True,
                   padx=PAD_XL, pady=PAD_XL)

        ctk.CTkLabel(
            inner, text="😵",
            font=(FONT_FAMILY, 42),
            text_color=STATUS["red"]).pack(pady=(0, 8))

        ctk.CTkLabel(
            inner, text="Something went wrong",
            font=(FONT_FAMILY, 22, "bold"),
            text_color=COLORS["text"]).pack()

        ctk.CTkLabel(
            inner, text=f"Could not load page: {key}",
            font=(FONT_FAMILY, 11),
            text_color=COLORS["text_muted"]).pack(pady=(4, 16))

        # Error box
        err_box = ctk.CTkTextbox(
            inner, width=560, height=140,
            font=("Consolas", 10),
            fg_color=COLORS["surface_alt"],
            text_color=STATUS["red"],
            corner_radius=10)
        err_box.pack(pady=(0, 16))
        err_box.insert("1.0", message)
        err_box.configure(state="disabled")

        # Buttons
        btns = ctk.CTkFrame(inner, fg_color="transparent")
        btns.pack()

        ctk.CTkButton(
            btns, text="← Back", width=140, height=40,
            font=FONTS["small_bold"],
            fg_color=COLORS["surface_alt"],
            hover_color=COLORS["surface_hi"],
            text_color=COLORS["text"],
            corner_radius=10,
            command=self.go_back,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btns, text="🏠 Home", width=140, height=40,
            font=FONTS["small_bold"],
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            text_color=COLORS["text"],
            corner_radius=10,
            command=lambda: self.show_page(
                "landing" if not self.current_user
                else "stu_dashboard" if (self.current_user.get("role")
                                         == ROLE_STUDENT)
                else "fac_command" if (self.current_user.get("role")
                                       == ROLE_FACILITATOR)
                else "admin_dashboard",
                push_history=False),
        ).pack(side="left")

        self._current_page_key = "__error__"

    # =========================================================
    # CONVENIENCE
    # =========================================================

    def toast(self, message: str, kind: str = "info"):
        try:
            from theme import Toast
            Toast(self, message, kind)
        except Exception:
            print(f"[toast] {kind}: {message}")


# =============================================================
# ENTRY POINT
# =============================================================

def main():
    # One-time DB sanity: ensure database module can be imported
    try:
        from database import get_db
        db = get_db()
        print(f"✨ {APP_NAME} v{APP_VERSION}")
        print(f"   DB ready. Tables loaded.")
    except Exception as e:
        print(f"⚠️  DB init failed: {e}")
        # still try to start UI

    app = ShruthiJhariApp()
    try:
        app.mainloop()
    except KeyboardInterrupt:
        print("\n[app] Shutting down.")
    finally:
        try:
            app.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    main()