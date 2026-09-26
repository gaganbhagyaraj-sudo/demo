# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  pages/base_page.py  ·  Base class inherited by every page
# =============================================================

from __future__ import annotations

import os
import sys

# --- make project root importable ---
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from typing import Optional, Callable, List, Dict, Tuple

import tkinter as tk
import customtkinter as ctk
from PIL import Image

from config import (
    APP_NAME, APP_TAGLINE,
    COLORS, STATUS, ZONE_COLORS,
    FONTS, FONT_FAMILY,
    HEADER_H, SIDEBAR_W,
    CARD_RADIUS, BUTTON_RADIUS, CHIP_RADIUS,
    PAD_SM, PAD_MD, PAD_LG, PAD_XL,
)
from theme import (
    make_gradient_bg, make_gradient_image, load_logo,
    GradientButton, Toast, make_ctk_image,
)
from utils.avatars import load_avatar


# =============================================================
# BASE PAGE
# =============================================================

class BasePage(ctk.CTkFrame):
    """
    Base class for every page. Provides a header, optional sidebar,
    scrollable content, footer, and helper methods.

    Subclasses typically override `on_show()` and call helper methods
    like `build_header()`, `build_sidebar()`, `build_content()`.
    """

    def __init__(self, master, app, *, show_header=True, show_sidebar=False):
        super().__init__(master, fg_color=COLORS["bg"], corner_radius=0)

        self.app = app
        self.db = app.db
        self.user = app.current_user

        self._show_header = show_header
        self._show_sidebar = show_sidebar

        # Layout regions
        self._sidebar = None
        self._header = None
        self._content_outer = None
        self._content = None   # scrollable inner frame
        self._footer = None

        # Sidebar nav items
        self._nav_items: List[Dict] = []
        self._nav_widgets: List[ctk.CTkFrame] = []

    # =========================================================
    # BUILD HELPERS
    # =========================================================

    def build_header(self, title: str = "",
                     subtitle: str = "",
                     back: bool = False,
                     show_user: bool = True):
        """Top header bar with optional back button and user chip."""
        self._header = ctk.CTkFrame(self, fg_color=COLORS["surface"],
                                    height=HEADER_H, corner_radius=0)
        self._header.pack(side="top", fill="x")
        self._header.pack_propagate(False)

        # Gradient bottom border
        border = ctk.CTkFrame(self, fg_color=COLORS["surface"], height=2)
        grad_img = make_ctk_image(make_gradient_image(1200, 2, radius=0))
        border_label = ctk.CTkLabel(border, image=grad_img, text="", height=2)
        border_label.pack(fill="x")
        border.pack(side="top", fill="x")

        # --- Left: back + title ---
        left = ctk.CTkFrame(self._header, fg_color="transparent")
        left.pack(side="left", padx=(PAD_MD, 0), fill="y")

        if back:
            ctk.CTkButton(
                left, text="←", width=38, height=38,
                font=(FONT_FAMILY, 18, "bold"),
                fg_color=COLORS["surface_alt"],
                hover_color=COLORS["primary"],
                text_color=COLORS["text"],
                corner_radius=8,
                command=self.go_back,
            ).pack(side="left", padx=(0, PAD_MD), pady=13)

        title_box = ctk.CTkFrame(left, fg_color="transparent")
        title_box.pack(side="left", pady=11)

        ctk.CTkLabel(
            title_box, text=title or "",
            font=FONTS["h3"], text_color=COLORS["text"],
            anchor="w",
        ).pack(anchor="w")

        if subtitle:
            ctk.CTkLabel(
                title_box, text=subtitle,
                font=FONTS["small"], text_color=COLORS["text_muted"],
                anchor="w",
            ).pack(anchor="w")

        # --- Right: user chip ---
        if show_user and self.user:
            right = ctk.CTkFrame(self._header, fg_color="transparent")
            right.pack(side="right", padx=(0, PAD_MD), fill="y")

            ctk.CTkButton(
                right, text="Logout", width=76, height=32,
                font=FONTS["small"],
                fg_color=COLORS["surface_alt"],
                hover_color=STATUS["danger"],
                text_color=COLORS["text"],
                corner_radius=8,
                command=self.app.logout,
            ).pack(side="right", pady=16)

            name_box = ctk.CTkFrame(right, fg_color="transparent")
            name_box.pack(side="right", padx=(0, PAD_MD), pady=10)

            ctk.CTkLabel(
                name_box, text=self.user.get("name", ""),
                font=FONTS["small_bold"],
                text_color=COLORS["text"], anchor="e",
            ).pack(anchor="e")

            ctk.CTkLabel(
                name_box, text=(self.user.get("role") or "").title(),
                font=FONTS["micro"],
                text_color=COLORS["text_muted"], anchor="e",
            ).pack(anchor="e")

            avatar = load_avatar(
                user_id=self.user.get("id", ""),
                name=self.user.get("name", ""),
                size=38, shape="circle",
            )
            ctk.CTkLabel(right, image=avatar, text="").pack(
                side="right", pady=13, padx=(0, 8))

    # ---------- SIDEBAR ----------

    def build_sidebar(self, items: List[Dict]):
        """
        items = [{"key": "dashboard", "label": "Dashboard",
                  "icon": "🏠", "command": callable}, ...]
        """
        self._nav_items = items

        self._sidebar = ctk.CTkFrame(self, fg_color=COLORS["surface"],
                                     width=SIDEBAR_W, corner_radius=0)
        self._sidebar.pack(side="left", fill="y")
        self._sidebar.pack_propagate(False)

        # Logo + app name at top of sidebar
        logo_box = ctk.CTkFrame(self._sidebar, fg_color="transparent")
        logo_box.pack(fill="x", padx=PAD_MD, pady=(PAD_LG, PAD_MD))

        logo = load_logo(size=44, rounded=True, margin=6)
        ctk.CTkLabel(logo_box, image=logo, text="").pack(side="left")

        name_box = ctk.CTkFrame(logo_box, fg_color="transparent")
        name_box.pack(side="left", padx=(10, 0))
        ctk.CTkLabel(name_box, text=APP_NAME,
                     font=FONTS["small_bold"],
                     text_color=COLORS["text"], anchor="w").pack(anchor="w")
        ctk.CTkLabel(name_box, text="Cascade",
                     font=FONTS["micro"],
                     text_color=COLORS["text_muted"],
                     anchor="w").pack(anchor="w")

        # Divider
        ctk.CTkFrame(self._sidebar, height=1,
                     fg_color=COLORS["border_soft"]).pack(
            fill="x", padx=PAD_MD, pady=(0, PAD_MD))

        # Nav items
        self._nav_widgets = []
        for item in items:
            self._nav_widgets.append(
                self._make_nav_item(self._sidebar, item))

        # Bottom: version
        ctk.CTkLabel(self._sidebar, text=f"v1.0",
                     font=FONTS["micro"],
                     text_color=COLORS["text_dim"]).pack(
            side="bottom", pady=PAD_MD)

    def _make_nav_item(self, parent, item: Dict) -> ctk.CTkFrame:
        key = item["key"]
        label = item["label"]
        icon = item.get("icon", "•")
        command = item.get("command")
        active = item.get("active", False)

        row = ctk.CTkFrame(parent, fg_color="transparent", height=42,
                           corner_radius=8)
        row.pack(fill="x", padx=PAD_SM, pady=2)
        row.pack_propagate(False)

        # Left accent bar (visible when active)
        accent = ctk.CTkFrame(row, fg_color=COLORS["primary"] if active
                              else "transparent", width=3, corner_radius=0)
        accent.pack(side="left", fill="y", padx=(0, 6))

        inner = ctk.CTkFrame(row,
                             fg_color=COLORS["surface_alt"] if active
                             else "transparent",
                             corner_radius=8)
        inner.pack(side="left", fill="both", expand=True)

        icon_lbl = ctk.CTkLabel(inner, text=icon,
                                font=(FONT_FAMILY, 14),
                                text_color=COLORS["text"],
                                width=26)
        icon_lbl.pack(side="left", padx=(10, 0))

        text_lbl = ctk.CTkLabel(
            inner, text=label,
            font=FONTS["small_bold"] if active else FONTS["small"],
            text_color=COLORS["text"] if active else COLORS["text_muted"],
            anchor="w",
        )
        text_lbl.pack(side="left", padx=(4, 10), fill="x", expand=True)

        # Hover + click
        def on_enter(_):
            if not active:
                try:
                    inner.configure(fg_color=COLORS["surface_hi"])
                    text_lbl.configure(text_color=COLORS["text"])
                except Exception:
                    pass

        def on_leave(_):
            if not active:
                try:
                    inner.configure(fg_color="transparent")
                    text_lbl.configure(text_color=COLORS["text_muted"])
                except Exception:
                    pass

        def on_click(_):
            if callable(command):
                command()

        for w in (row, inner, icon_lbl, text_lbl):
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)
            w.bind("<Button-1>", on_click)
            try:
                w.configure(cursor="hand2")
            except Exception:
                pass

        return row

    # ---------- CONTENT ----------

    def build_content(self, scrollable: bool = True, padding: int = PAD_LG):
        """
        Creates the main content area. Returns the Frame to add children to.
        If scrollable=True, this frame sits inside a CTkScrollableFrame.
        """
        outer = ctk.CTkFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        outer.pack(side="top", fill="both", expand=True)
        self._content_outer = outer

        if scrollable:
            self._content = ctk.CTkScrollableFrame(
                outer, fg_color=COLORS["bg"], corner_radius=0)
            self._content.pack(fill="both", expand=True,
                               padx=padding, pady=padding)
        else:
            self._content = ctk.CTkFrame(
                outer, fg_color=COLORS["bg"], corner_radius=0)
            self._content.pack(fill="both", expand=True,
                               padx=padding, pady=padding)

        return self._content

    # ---------- FOOTER ----------

    def build_footer(self):
        self._footer = ctk.CTkFrame(self, fg_color=COLORS["surface"],
                                    height=28, corner_radius=0)
        self._footer.pack(side="bottom", fill="x")
        self._footer.pack_propagate(False)

        ctk.CTkLabel(
            self._footer,
            text=f"{APP_NAME}  ·  {APP_TAGLINE}",
            font=FONTS["micro"],
            text_color=COLORS["text_dim"],
        ).pack(pady=6)

    # =========================================================
    # PRIMITIVE UI BUILDERS
    # =========================================================

    def section_title(self, text: str, parent=None):
        """Bold section heading."""
        p = parent or self._content
        lbl = ctk.CTkLabel(p, text=text,
                           font=FONTS["h4"],
                           text_color=COLORS["text"],
                           anchor="w")
        lbl.pack(anchor="w", pady=(PAD_MD, PAD_SM), fill="x")
        return lbl

    def section_divider(self, parent=None, color=None):
        p = parent or self._content
        d = ctk.CTkFrame(p, height=1,
                         fg_color=color or COLORS["border_soft"])
        d.pack(fill="x", pady=(0, PAD_MD))
        return d

    def stat_card(self, parent, value, label, *,
                  accent=None, width=180, height=92,
                  value_font="numeral_big", icon: Optional[str] = None):
        """KPI card: big value + small label + top color accent bar."""
        accent = accent or COLORS["primary"]
        card = ctk.CTkFrame(parent, fg_color=COLORS["surface"],
                            corner_radius=CARD_RADIUS,
                            width=width, height=height,
                            border_width=1,
                            border_color=COLORS["border_soft"])
        card.pack_propagate(False)

        # Accent strip
        top = ctk.CTkFrame(card, fg_color=accent, height=4,
                           corner_radius=CARD_RADIUS)
        top.pack(fill="x", pady=(0, 6))

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(expand=True, fill="both", padx=12, pady=(0, 10))

        if icon:
            ctk.CTkLabel(body, text=icon,
                         font=(FONT_FAMILY, 14),
                         text_color=accent).pack(anchor="w")

        ctk.CTkLabel(body, text=str(value),
                     font=FONTS[value_font],
                     text_color=COLORS["text"],
                     anchor="w").pack(anchor="w")

        ctk.CTkLabel(body, text=label,
                     font=FONTS["tiny"],
                     text_color=COLORS["text_muted"],
                     anchor="w").pack(anchor="w")

        return card

    def info_row(self, parent, label: str, value: str,
                 value_color: Optional[str] = None):
        """Label — value row for detail panels."""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=3)
        ctk.CTkLabel(row, text=label, width=160, anchor="w",
                     font=FONTS["small"],
                     text_color=COLORS["text_muted"]).pack(side="left")
        ctk.CTkLabel(row, text=value, anchor="w",
                     font=FONTS["small_bold"],
                     text_color=value_color or COLORS["text"]).pack(
            side="left", fill="x", expand=True)
        return row

    def chip(self, parent, text: str, color: Optional[str] = None):
        chip = ctk.CTkFrame(parent,
                            fg_color=color or COLORS["surface_alt"],
                            corner_radius=CHIP_RADIUS)
        ctk.CTkLabel(chip, text=text, font=FONTS["tiny"],
                     text_color=COLORS["text"]).pack(
            padx=10, pady=4)
        return chip

    def primary_button(self, parent, text, command=None,
                       width=180, height=42):
        return GradientButton(
            parent, text=text, command=command,
            width=width, height=height,
            parent_bg=COLORS["bg"],
        )

    def secondary_button(self, parent, text, command=None,
                         width=140, height=38):
        return ctk.CTkButton(
            parent, text=text, width=width, height=height,
            font=FONTS["small_bold"],
            fg_color=COLORS["surface_alt"],
            hover_color=COLORS["surface_hi"],
            text_color=COLORS["text"],
            corner_radius=BUTTON_RADIUS,
            command=command,
        )

    def danger_button(self, parent, text, command=None,
                      width=140, height=38):
        return ctk.CTkButton(
            parent, text=text, width=width, height=height,
            font=FONTS["small_bold"],
            fg_color=STATUS["danger"],
            hover_color="#B91C1C",
            text_color=COLORS["text"],
            corner_radius=BUTTON_RADIUS,
            command=command,
        )

    def card(self, parent, *, width=None, height=None,
             fg=None, radius=CARD_RADIUS, border=True):
        kwargs = dict(fg_color=fg or COLORS["surface"],
                      corner_radius=radius)
        if border:
            kwargs.update(border_width=1,
                          border_color=COLORS["border_soft"])
        if width:
            kwargs["width"] = width
        if height:
            kwargs["height"] = height
        c = ctk.CTkFrame(parent, **kwargs)
        if width or height:
            try:
                c.pack_propagate(False)
            except Exception:
                pass
        return c

    # ---------- CHART EMBED ----------

    def chart_frame(self, parent, fig, *, height: int = 320,
                    width: Optional[int] = None):
        """
        Embed a matplotlib Figure inside a CTk frame.
        Returns the frame so caller can place or pack it.
        """
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from config import CHART_STYLE

        wrap = ctk.CTkFrame(parent, fg_color=CHART_STYLE["fig_bg"],
                            corner_radius=CARD_RADIUS,
                            border_width=1,
                            border_color=COLORS["border_soft"],
                            height=height)
        wrap.pack_propagate(False)
        if width:
            wrap.configure(width=width)

        canvas = FigureCanvasTkAgg(fig, master=wrap)
        canvas.draw()
        widget = canvas.get_tk_widget()
        widget.configure(bg=CHART_STYLE["fig_bg"], highlightthickness=0)
        widget.pack(fill="both", expand=True, padx=6, pady=6)

        # Keep references alive
        wrap._canvas = canvas
        wrap._figure = fig
        return wrap

    def zone_chip(self, parent, zone: str):
        color = ZONE_COLORS.get(zone, COLORS["surface_alt"])
        icon = {"red": "🔴", "yellow": "🟡",
                "green": "🟢", "gold": "🏆"}.get(zone, "•")
        label = {"red": "At Risk", "yellow": "Developing",
                 "green": "Strong", "gold": "Achiever"}.get(zone, zone)
        return self.chip(parent, f"{icon}  {label}", color=color)

    # =========================================================
    # TOASTS / MODALS
    # =========================================================

    def toast(self, message: str, kind: str = "info"):
        """Fire-and-forget toast notification."""
        try:
            Toast(self.winfo_toplevel(), message, kind)
        except Exception:
            pass

    def confirm(self, title: str, message: str,
                on_yes: Callable[[], None],
                yes_text: str = "Confirm",
                no_text: str = "Cancel"):
        """Modal confirm dialog."""
        _Modal(self.winfo_toplevel(),
               title=title, message=message,
               kind="confirm",
               on_yes=on_yes,
               yes_text=yes_text, no_text=no_text)

    def alert(self, title: str, message: str):
        """Modal info alert."""
        _Modal(self.winfo_toplevel(),
               title=title, message=message,
               kind="alert",
               on_yes=None,
               yes_text="OK", no_text=None)

    # =========================================================
    # NAVIGATION
    # =========================================================

    def navigate(self, page_key: str, **kwargs):
        """Ask the app to switch to another page."""
        self.app.show_page(page_key, **kwargs)

    def go_back(self):
        self.app.go_back()

    # =========================================================
    # LIFECYCLE
    # =========================================================

    def on_show(self, **kwargs):
        """
        Override in subclasses. Called by the app whenever this page
        becomes visible. Use to refresh data, restart timers, etc.
        """
        pass

    def on_hide(self):
        """Override if the page needs cleanup when navigated away from."""
        pass


# =============================================================
# MODAL DIALOG
# =============================================================

class _Modal:
    """Lightweight modal — confirm or alert."""

    def __init__(self, parent, *, title, message, kind="confirm",
                 on_yes=None, yes_text="OK", no_text="Cancel"):
        self.parent = parent
        self.on_yes = on_yes

        self.top = ctk.CTkToplevel(parent)
        self.top.title(title)
        self.top.configure(fg_color=COLORS["bg"])
        self.top.resizable(False, False)
        self.top.transient(parent)
        self.top.grab_set()

        w, h = 420, 200
        self.top.geometry(f"{w}x{h}")
        # Center on parent
        try:
            parent.update_idletasks()
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            x = px + (pw - w) // 2
            y = py + (ph - h) // 2
            self.top.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            pass

        # Gradient accent bar
        bar = ctk.CTkFrame(self.top, fg_color=COLORS["surface"],
                           height=6, corner_radius=0)
        bar.pack(fill="x")
        grad_img = make_ctk_image(
            make_gradient_image(w, 6, radius=0))
        ctk.CTkLabel(bar, image=grad_img, text="", height=6).pack(fill="x")

        # Body
        body = ctk.CTkFrame(self.top, fg_color=COLORS["bg"])
        body.pack(fill="both", expand=True, padx=PAD_LG, pady=PAD_LG)

        ctk.CTkLabel(body, text=title,
                     font=FONTS["h4"],
                     text_color=COLORS["text"]).pack(anchor="w", pady=(0, 6))

        ctk.CTkLabel(body, text=message,
                     font=FONTS["body"],
                     text_color=COLORS["text_muted"],
                     wraplength=360, justify="left").pack(anchor="w")

        # Buttons
        btn_row = ctk.CTkFrame(self.top, fg_color=COLORS["bg"])
        btn_row.pack(fill="x", padx=PAD_LG, pady=(0, PAD_LG))

        if no_text:
            ctk.CTkButton(btn_row, text=no_text, width=110, height=36,
                          font=FONTS["small_bold"],
                          fg_color=COLORS["surface_alt"],
                          hover_color=COLORS["surface_hi"],
                          text_color=COLORS["text"],
                          corner_radius=BUTTON_RADIUS,
                          command=self._close).pack(side="right", padx=(6, 0))

        ctk.CTkButton(btn_row, text=yes_text, width=110, height=36,
                      font=FONTS["small_bold"],
                      fg_color=COLORS["primary"],
                      hover_color=COLORS["primary_hover"],
                      text_color=COLORS["text"],
                      corner_radius=BUTTON_RADIUS,
                      command=self._yes).pack(side="right")

        # Esc closes
        try:
            self.top.bind("<Escape>", lambda e: self._close())
        except Exception:
            pass

    def _yes(self):
        cb = self.on_yes
        self._close()
        if callable(cb):
            try:
                cb()
            except Exception:
                pass

    def _close(self):
        try:
            self.top.grab_release()
        except Exception:
            pass
        try:
            self.top.destroy()
        except Exception:
            pass


# =============================================================
# SANITY CHECK
# =============================================================

if __name__ == "__main__":
    """Quick preview — a page inheriting BasePage with all widgets."""
    ctk.set_appearance_mode("dark")

    # ---- Fake app + user for the demo ----
    class _FakeApp:
        def __init__(self):
            self.db = None
            self.current_user = {
                "id": "stu01",
                "name": "Rahul Sharma",
                "role": "student",
                "status": "approved",
            }
            self._stack = []

        def show_page(self, key, **kw):
            print(f"[nav] would show: {key}  args={kw}")

        def go_back(self):
            print("[nav] back")

        def logout(self):
            print("[nav] logout")

    root = ctk.CTk()
    root.geometry("1280x780")
    root.configure(fg_color=COLORS["bg"])
    root.title("Shruthi Jhari — BasePage preview")

    app = _FakeApp()

    class DemoPage(BasePage):
        def __init__(self, master, app):
            super().__init__(master, app)
            self.build_header("Dashboard", "Welcome back!",
                              back=True, show_user=True)
            self.build_sidebar([
                {"key": "dash", "label": "Dashboard", "icon": "🏠",
                 "active": True,
                 "command": lambda: print("nav dashboard")},
                {"key": "marks", "label": "My Marks", "icon": "📊",
                 "command": lambda: print("nav marks")},
                {"key": "att", "label": "Attendance", "icon": "📅",
                 "command": lambda: print("nav attendance")},
                {"key": "learn", "label": "Learning Path", "icon": "📚",
                 "command": lambda: print("nav learning")},
                {"key": "mastery", "label": "Mastery Map", "icon": "🎯",
                 "command": lambda: print("nav mastery")},
                {"key": "badges", "label": "My Badges", "icon": "🏅",
                 "command": lambda: print("nav badges")},
                {"key": "certs", "label": "Certificates", "icon": "📜",
                 "command": lambda: print("nav certs")},
            ])
            content = self.build_content(scrollable=True)
            self.build_footer()

            # Stat cards row
            self.section_title("This week")
            row = ctk.CTkFrame(content, fg_color="transparent")
            row.pack(fill="x", pady=(0, PAD_MD))

            self.stat_card(row, "75.5%", "Latest IA avg",
                           accent=COLORS["primary"], icon="📊").pack(
                side="left", padx=(0, PAD_MD))
            self.stat_card(row, "92%", "Attendance",
                           accent=STATUS["green"], icon="📅").pack(
                side="left", padx=(0, PAD_MD))
            self.stat_card(row, "4", "Badges earned",
                           accent=STATUS["gold"], icon="🏅").pack(
                side="left", padx=(0, PAD_MD))
            self.stat_card(row, "🟢", "Zone: Strong",
                           accent=STATUS["green"], icon="🎯").pack(
                side="left")

            # Info card
            self.section_title("Profile")
            card = self.card(content)
            card.pack(fill="x", pady=(0, PAD_MD))
            body = ctk.CTkFrame(card, fg_color="transparent")
            body.pack(fill="x", padx=PAD_LG, pady=PAD_LG)

            self.info_row(body, "Name", "Rahul Sharma")
            self.info_row(body, "USN", "1RV21CS001")
            self.info_row(body, "Grade", "7 · Section A")
            self.info_row(body, "Zone", "Strong 🟢",
                          value_color=STATUS["green"])

            # Chips
            chips = ctk.CTkFrame(content, fg_color="transparent")
            chips.pack(fill="x", pady=(0, PAD_MD))
            self.chip(chips, "Cricket").pack(side="left", padx=(0, 6))
            self.chip(chips, "Gaming").pack(side="left", padx=(0, 6))
            self.zone_chip(chips, "green").pack(side="left")

            # Buttons
            btns = ctk.CTkFrame(content, fg_color="transparent")
            btns.pack(fill="x", pady=PAD_MD)
            self.primary_button(
                btns, "Show toast",
                command=lambda: self.toast("This is a toast!", "success")
            ).pack(side="left", padx=(0, PAD_MD))
            self.secondary_button(
                btns, "Confirm",
                command=lambda: self.confirm(
                    "Delete item?",
                    "This action cannot be undone.",
                    on_yes=lambda: self.toast("Deleted", "success"))
            ).pack(side="left", padx=(0, PAD_MD))
            self.danger_button(
                btns, "Alert",
                command=lambda: self.alert(
                    "Heads up", "Something happened.")
            ).pack(side="left")

            # Sample chart
            self.section_title("Sample chart (bar)")
            try:
                from utils.charts import subject_bar_chart
                fig = subject_bar_chart(
                    {"Maths": 72, "Physics": 68,
                     "Chemistry": 75, "Computer Science": 80},
                    animate=False)
                self.chart_frame(content, fig, height=280).pack(fill="x")
            except Exception as e:
                ctk.CTkLabel(content, text=f"(chart skipped: {e})",
                             text_color=COLORS["text_muted"]).pack()

    page = DemoPage(root, app)
    page.pack(fill="both", expand=True)
    root.mainloop()