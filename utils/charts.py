# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  utils/charts.py  ·  Animated matplotlib + seaborn chart library
# =============================================================

from __future__ import annotations

import os
import sys

# --- make project root importable ---
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import math
from typing import Optional, List, Dict

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("TkAgg")            # safe for embedding in tkinter
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.patches import Circle, Wedge

import seaborn as sns

from config import (
    SUBJECTS, SUBJECT_COLORS, SUBJECT_SHORT,
    IA_LIST, IA_COLORS,
    COLORS, STATUS, ZONE_COLORS, GRADE_SCALE,
    GRADIENT_START, GRADIENT_END, GRADIENT_SOFT,
    CHART_STYLE,
)


# =============================================================
# 1. GLOBAL THEME
# =============================================================

def apply_theme():
    """Apply the Shruthi Jhari palette to matplotlib + seaborn."""
    sns.set_theme(style="darkgrid", rc={
        "figure.facecolor":      CHART_STYLE["fig_bg"],
        "axes.facecolor":        CHART_STYLE["axes_bg"],
        "axes.edgecolor":        CHART_STYLE["spine"],
        "axes.labelcolor":       CHART_STYLE["text"],
        "axes.titlecolor":       CHART_STYLE["text"],
        "axes.titleweight":      "bold",
        "axes.titlesize":        12,
        "axes.labelsize":        10,
        "axes.grid":             True,
        "grid.color":            CHART_STYLE["grid"],
        "grid.linewidth":        0.6,
        "grid.alpha":            0.6,
        "xtick.color":           CHART_STYLE["text_muted"],
        "ytick.color":           CHART_STYLE["text_muted"],
        "text.color":            CHART_STYLE["text"],
        "legend.facecolor":      CHART_STYLE["axes_bg"],
        "legend.edgecolor":      CHART_STYLE["spine"],
        "legend.labelcolor":     CHART_STYLE["text"],
        "font.family":           "sans-serif",
        "figure.dpi":            CHART_STYLE["dpi"],
    })
    sns.set_palette(CHART_STYLE["palette"])


apply_theme()


# =============================================================
# 2. HELPERS
# =============================================================

def new_figure(w=7, h=4):
    fig = Figure(figsize=(w, h), dpi=CHART_STYLE["dpi"],
                 facecolor=CHART_STYLE["fig_bg"])
    ax = fig.add_subplot(111)
    style_axes(ax)
    fig.tight_layout(pad=1.4)
    return fig, ax


def style_axes(ax):
    ax.set_facecolor(CHART_STYLE["axes_bg"])
    for spine in ax.spines.values():
        spine.set_color(CHART_STYLE["spine"])
    ax.tick_params(colors=CHART_STYLE["text_muted"], labelsize=9)
    ax.xaxis.label.set_color(CHART_STYLE["text"])
    ax.yaxis.label.set_color(CHART_STYLE["text"])
    ax.title.set_color(CHART_STYLE["text"])
    ax.grid(color=CHART_STYLE["grid"], linewidth=0.6, alpha=0.6)


def gradient_colors(n: int) -> List:
    """N even RGB colors interpolated between brand gradient endpoints."""
    def hx(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4))

    a, b = hx(GRADIENT_START), hx(GRADIENT_END)
    out = []
    for i in range(max(1, n)):
        t = i / max(1, n - 1) if n > 1 else 0.5
        out.append(tuple(a[k] + (b[k] - a[k]) * t for k in range(3)))
    return out


def zone_color_of(pct: float) -> str:
    if pct < 40: return ZONE_COLORS["red"]
    if pct < 50: return ZONE_COLORS["red"]
    if pct < 75: return ZONE_COLORS["yellow"]
    if pct < 90: return ZONE_COLORS["green"]
    return ZONE_COLORS["gold"]


def add_footer(fig, text="Shruthi Jhari · Cascade of divine knowledge"):
    fig.text(0.5, 0.005, text, ha="center", va="bottom",
             fontsize=7, color=CHART_STYLE["text_muted"], alpha=0.7)


# =============================================================
# 3. ANIMATION PRIMITIVES  (bar-grow, line-draw, pie-sweep)
# =============================================================

def animate_bars(ax, bars, fig, steps: int = 20, interval: int = 25):
    """Bars grow from 0 → final height, with value labels appearing at the end."""
    final_heights = [b.get_height() for b in bars]
    for b, h in zip(bars, final_heights):
        b.set_height(0)

    def update(frame):
        t = (frame + 1) / steps
        t = 1 - (1 - t) ** 3            # ease_out
        for b, h in zip(bars, final_heights):
            b.set_height(h * t)
        return bars

    ani = animation.FuncAnimation(
        fig, update, frames=steps, interval=interval,
        blit=False, repeat=False)
    return ani


def animate_line(ax, line, fig, steps: int = 25, interval: int = 25):
    """Line draws itself from left to right."""
    x, y = line.get_data()
    total = len(x)
    for i in range(total):
        line.set_data(x[:i], y[:i])

    def update(frame):
        i = int(frame * total / steps) + 1
        i = min(i, total)
        line.set_data(x[:i], y[:i])
        return [line]

    return animation.FuncAnimation(
        fig, update, frames=steps, interval=interval,
        blit=False, repeat=False)


def animate_pie_sweep(ax, wedges, fig,
                      steps: int = 25, interval: int = 25):
    """Wedges sweep in clockwise from 0 → full size."""
    finals = [w.theta2 - w.theta1 for w in wedges]

    def update(frame):
        t = (frame + 1) / steps
        for w, f in zip(wedges, finals):
            w.theta2 = w.theta1 + f * t
        return wedges

    return animation.FuncAnimation(
        fig, update, frames=steps, interval=interval,
        blit=False, repeat=False)


# =============================================================
# 4. SUBJECT BAR CHART  (marks per subject, animated)
# =============================================================

def subject_bar_chart(averages: Dict[str, float],
                      title: str = "Subject Averages",
                      animate: bool = True,
                      figsize=(7, 4)) -> Figure:
    fig, ax = new_figure(*figsize)
    subjects = SUBJECTS
    values = [averages.get(s, 0) for s in subjects]
    colors = [SUBJECT_COLORS[s] for s in subjects]

    bars = ax.bar(subjects, values, color=colors,
                  edgecolor=CHART_STYLE["spine"], width=0.62)
    ax.set_ylim(0, max(values + [100]) * 1.15)
    ax.set_ylabel("Average marks")
    ax.set_title(title, pad=12)

    # Value labels
    for bar, v in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2,
                v + 2, f"{v:.1f}",
                ha="center", va="bottom",
                color=CHART_STYLE["text"], fontsize=9, fontweight="bold")

    add_footer(fig)
    if animate:
        fig._ani = animate_bars(ax, bars, fig)
    return fig


# =============================================================
# 5. IA TREND CHART  (line per subject across IA-1, IA-2, IA-3)
# =============================================================

def ia_trend_chart(ia_data: Dict[str, List[float]],
                   title: str = "IA Performance Trend",
                   animate: bool = True,
                   figsize=(7, 4)) -> Figure:
    """
    ia_data = {"Maths": [75, 78, 82], "Physics": [...], ...}
    Each list has 3 values (IA-1, IA-2, IA-3).
    """
    fig, ax = new_figure(*figsize)
    x = list(range(len(IA_LIST)))
    ax.set_xticks(x)
    ax.set_xticklabels(IA_LIST)
    ax.set_ylim(0, 105)
    ax.set_ylabel("Marks")
    ax.set_title(title, pad=12)

    lines = []
    for subj, values in ia_data.items():
        color = SUBJECT_COLORS.get(subj, GRADIENT_START)
        ln, = ax.plot(x, values, marker="o", markersize=CHART_STYLE["marker_sz"],
                      linewidth=CHART_STYLE["line_w"], color=color,
                      label=SUBJECT_SHORT.get(subj, subj), zorder=5)
        lines.append((ln, values))

    ax.legend(loc="best", fontsize=9, frameon=True)

    add_footer(fig)
    if animate:
        # Simple reveal using line.set_data interpolation
        def update(frame):
            t = (frame + 1) / 25
            t = 1 - (1 - t) ** 3
            for ln, values in lines:
                # interpolate values from 0 → final
                ln.set_data(x, [v * t for v in values])
            return [ln for ln, _ in lines]
        fig._ani = animation.FuncAnimation(
            fig, update, frames=25, interval=25,
            blit=False, repeat=False)
    return fig


# =============================================================
# 6. ZONE PIE / DONUT  (Red / Yellow / Green / Gold distribution)
# =============================================================

def zone_donut(zone_counts: Dict[str, int],
               title: str = "Class Distribution",
               animate: bool = True,
               figsize=(5.5, 5.5)) -> Figure:
    fig, ax = new_figure(*figsize)
    labels, sizes, colors = [], [], []
    order = ["red", "yellow", "green", "gold"]
    display = {"red": "At Risk", "yellow": "Developing",
               "green": "Strong", "gold": "Achiever"}
    for z in order:
        if zone_counts.get(z, 0) > 0:
            labels.append(display[z])
            sizes.append(zone_counts[z])
            colors.append(ZONE_COLORS[z])

    if not sizes:
        ax.text(0.5, 0.5, "No data", ha="center", va="center",
                color=CHART_STYLE["text_muted"])
        return fig

    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, colors=colors,
        autopct=lambda pct: f"{pct:.0f}%",
        startangle=90, counterclock=False,
        wedgeprops=dict(width=0.42, edgecolor=CHART_STYLE["fig_bg"],
                        linewidth=2),
        textprops=dict(color=CHART_STYLE["text"], fontsize=10),
    )
    for at in autotexts:
        at.set_color("#0B0A1F")
        at.set_fontweight("bold")

    # Center hole with total count
    ax.text(0, 0, str(sum(sizes)), ha="center", va="center",
            fontsize=22, fontweight="bold",
            color=CHART_STYLE["text"])
    ax.text(0, -0.22, "students", ha="center", va="center",
            fontsize=9, color=CHART_STYLE["text_muted"])
    ax.set_title(title, pad=14)

    add_footer(fig)
    if animate:
        fig._ani = animate_pie_sweep(ax, wedges, fig)
    return fig


# =============================================================
# 7. HEATMAP  (students × subjects, or concepts, animated fade-in)
# =============================================================

def heatmap_chart(matrix: pd.DataFrame,
                  title: str = "Performance Heatmap",
                  cmap: str = "magma",
                  cbar_label: str = "Value",
                  annot: bool = False,
                  animate: bool = True,
                  figsize=(8, 5.5)) -> Figure:
    fig, ax = new_figure(*figsize)

    if matrix.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center",
                color=CHART_STYLE["text_muted"])
        return fig

    im = ax.imshow(matrix.values, aspect="auto", cmap=cmap,
                   vmin=0, vmax=100)

    ax.set_xticks(np.arange(matrix.shape[1]))
    ax.set_xticklabels(matrix.columns, rotation=20, ha="right")
    ax.set_yticks(np.arange(matrix.shape[0]))
    ax.set_yticklabels(matrix.index)

    ax.set_title(title, pad=12)
    cb = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    cb.set_label(cbar_label, color=CHART_STYLE["text"])
    cb.ax.tick_params(colors=CHART_STYLE["text_muted"])

    if annot:
        for i in range(matrix.shape[0]):
            for j in range(matrix.shape[1]):
                v = matrix.values[i, j]
                ax.text(j, i, f"{v:.0f}",
                        ha="center", va="center",
                        color="white" if v < 60 else "#0B0A1F",
                        fontsize=8, fontweight="bold")

    add_footer(fig)
    if animate:
        im.set_clim(100, 100)   # all-dark start
        def update(frame):
            t = (frame + 1) / 20
            t = t * t * (3 - 2 * t)   # smoothstep
            im.set_clim(100, 100 - 100 * t)
            return [im]
        fig._ani = animation.FuncAnimation(
            fig, update, frames=20, interval=25, blit=False, repeat=False)
    return fig


# =============================================================
# 8. RADAR CHART  (student's 4 subjects)
# =============================================================

def radar_chart(values: List[float],
                labels: Optional[List[str]] = None,
                title: str = "Subject Profile",
                max_value: float = 100,
                color: str = GRADIENT_START,
                animate: bool = True,
                figsize=(5.5, 5.5)) -> Figure:
    labels = labels or SUBJECT_SHORT_VALUES()
    N = len(labels)

    fig = Figure(figsize=figsize, dpi=CHART_STYLE["dpi"],
                 facecolor=CHART_STYLE["fig_bg"])
    ax = fig.add_subplot(111, polar=True)
    ax.set_facecolor(CHART_STYLE["axes_bg"])
    ax.tick_params(colors=CHART_STYLE["text_muted"])

    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    vals = list(values) + [values[0]]
    angles_closed = angles + [angles[0]]

    ax.set_xticks(angles)
    ax.set_xticklabels(labels, color=CHART_STYLE["text"], fontsize=10)
    ax.set_ylim(0, max_value)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(["20", "40", "60", "80", "100"],
                       color=CHART_STYLE["text_muted"], fontsize=8)
    ax.grid(color=CHART_STYLE["grid"], alpha=0.6)
    ax.spines["polar"].set_color(CHART_STYLE["spine"])

    line, = ax.plot(angles_closed, vals, color=color, linewidth=2.4)
    fill = ax.fill(angles_closed, vals, color=color, alpha=0.25)

    ax.set_title(title, pad=20, color=CHART_STYLE["text"])

    add_footer(fig)
    if animate:
        def update(frame):
            t = (frame + 1) / 25
            t = 1 - (1 - t) ** 3
            interp = [v * t for v in vals]
            line.set_data(angles_closed, interp)
            for coll in ax.collections:
                coll.remove()
            ax.fill(angles_closed, interp, color=color, alpha=0.25)
            return [line]
        fig._ani = animation.FuncAnimation(
            fig, update, frames=25, interval=25, blit=False, repeat=False)
    return fig


def SUBJECT_SHORT_VALUES():
    return [SUBJECT_SHORT[s] for s in SUBJECTS]


# =============================================================
# 9. BOX PLOT  (marks distribution per subject)
# =============================================================

def subject_boxplot(df: pd.DataFrame,
                    title: str = "Marks Distribution by Subject",
                    animate: bool = True,
                    figsize=(7, 4)) -> Figure:
    fig, ax = new_figure(*figsize)

    if df.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center",
                color=CHART_STYLE["text_muted"])
        return fig

    order = [s for s in SUBJECTS if s in df.columns]
    palette = [SUBJECT_COLORS[s] for s in order]

    bp = ax.boxplot(
        [df[s].dropna().values for s in order],
        labels=order, patch_artist=True,
        medianprops=dict(color="#0B0A1F", linewidth=1.5),
        boxprops=dict(linewidth=1),
        whiskerprops=dict(color=CHART_STYLE["text_muted"]),
        capprops=dict(color=CHART_STYLE["text_muted"]),
        flierprops=dict(marker="o", markersize=4,
                        markerfacecolor=STATUS["red"],
                        markeredgecolor="none", alpha=0.6),
    )
    for patch, color in zip(bp["boxes"], palette):
        patch.set_facecolor(color)
        patch.set_alpha(0.75)

    ax.set_ylabel("Marks")
    ax.set_ylim(0, 105)
    ax.set_title(title, pad=12)

    add_footer(fig)
    if animate:
        # slide boxes in from below
        ys = [0] * len(bp["boxes"])
        for patch in bp["boxes"]:
            patch.set_y(0)
        for med in bp["medians"]:
            med.set_ydata([0, 0])

        def update(frame):
            t = (frame + 1) / 20
            t = 1 - (1 - t) ** 3
            for i, (s, patch) in enumerate(zip(order, bp["boxes"])):
                v = df[s].dropna().values
                if len(v) == 0:
                    continue
                q1, med, q3 = np.percentile(v, [25, 50, 75])
                patch.set_y((q1) * t)
                patch.set_height((q3 - q1) * t)
            return bp["boxes"]
        fig._ani = animation.FuncAnimation(
            fig, update, frames=20, interval=25, blit=False, repeat=False)
    return fig


# =============================================================
# 10. TOPPER / RANKING BAR CHART
# =============================================================

def ranking_bar_chart(names: List[str], values: List[float],
                      title: str = "Top Performers",
                      value_label: str = "%",
                      animate: bool = True,
                      figsize=(7, 5)) -> Figure:
    fig, ax = new_figure(*figsize)
    colors = gradient_colors(len(names))

    bars = ax.barh(names[::-1], values[::-1], color=colors[::-1],
                   edgecolor=CHART_STYLE["spine"], height=0.6)
    ax.set_xlim(0, max(values + [100]) * 1.15)
    ax.set_xlabel(value_label)
    ax.set_title(title, pad=12)

    for bar, v in zip(bars, values[::-1]):
        ax.text(bar.get_width() + 1,
                bar.get_y() + bar.get_height() / 2,
                f"{v:.1f}", va="center", ha="left",
                color=CHART_STYLE["text"], fontsize=9, fontweight="bold")

    add_footer(fig)
    if animate:
        fig._ani = animate_bars(ax, bars, fig)
    return fig


# =============================================================
# 11. ATTENDANCE TREND
# =============================================================

def attendance_trend_chart(df: pd.DataFrame,
                           title: str = "Attendance Trend",
                           animate: bool = True,
                           figsize=(7, 3.5)) -> Figure:
    """
    df: columns [att_date, present_pct]  (one row per date)
    """
    fig, ax = new_figure(*figsize)
    if df.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center",
                color=CHART_STYLE["text_muted"])
        return fig

    ax.plot(df["att_date"], df["present_pct"],
            marker="o", linewidth=2.4, color=GRADIENT_END,
            markerfacecolor=GRADIENT_START, markeredgecolor="white",
            markersize=6)
    ax.set_ylim(0, 105)
    ax.set_ylabel("Present %")
    ax.set_title(title, pad=12)
    ax.tick_params(axis="x", rotation=30, labelsize=8)

    add_footer(fig)
    if animate:
        line = ax.lines[0]
        fig._ani = animate_line(ax, line, fig)
    return fig


# =============================================================
# 12. SCATTER CLUSTERS  (PCA coordinates from clustering)
# =============================================================

def cluster_scatter_chart(df: pd.DataFrame,
                          title: str = "Student Segments",
                          animate: bool = True,
                          figsize=(7, 5)) -> Figure:
    """
    df: columns [pca_x, pca_y, segment, name]
    """
    fig, ax = new_figure(*figsize)
    if df.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center",
                color=CHART_STYLE["text_muted"])
        return fig

    for seg in df["segment"].unique():
        sub = df[df["segment"] == seg]
        color = None
        for name in ("Needs Support", "Developing", "Advanced"):
            if seg == name:
                color = {"Needs Support": "#EF4444",
                         "Developing":    "#F59E0B",
                         "Advanced":      "#10B981"}[name]
                break
        color = color or GRADIENT_START
        ax.scatter(sub["pca_x"], sub["pca_y"],
                   s=140, alpha=0.85, edgecolor="white",
                   linewidth=1.5, color=color, label=seg, zorder=3)
        for _, r in sub.iterrows():
            ax.annotate(r["name"].split()[0],
                        (r["pca_x"], r["pca_y"]),
                        xytext=(5, 5), textcoords="offset points",
                        fontsize=8, color=CHART_STYLE["text_muted"])

    ax.set_xlabel("Component 1")
    ax.set_ylabel("Component 2")
    ax.set_title(title, pad=12)
    ax.legend(loc="best", fontsize=9)
    add_footer(fig)

    if animate:
        for coll in ax.collections:
            coll.set_alpha(0)
        def update(frame):
            t = (frame + 1) / 20
            for coll in ax.collections:
                coll.set_alpha(0.85 * t)
            return ax.collections
        fig._ani = animation.FuncAnimation(
            fig, update, frames=20, interval=25, blit=False, repeat=False)
    return fig


# =============================================================
# 13. GAUGE / PROGRESS RING  (single number)
# =============================================================

def gauge_chart(pct: float, label: str = "Score",
                color: Optional[str] = None,
                max_value: float = 100,
                animate: bool = True,
                figsize=(4.5, 4.5)) -> Figure:
    fig = Figure(figsize=figsize, dpi=CHART_STYLE["dpi"],
                 facecolor=CHART_STYLE["fig_bg"])
    ax = fig.add_subplot(111)
    ax.set_aspect("equal")
    ax.axis("off")

    color = color or zone_color_of(pct)

    # Background ring
    ax.add_patch(Wedge((0, 0), 1.0, 90, -270, width=0.22,
                       facecolor=CHART_STYLE["axes_bg"],
                       edgecolor=CHART_STYLE["spine"], linewidth=1))

    pct = max(0, min(max_value, pct))
    sweep_end = 90 - 360 * (pct / max_value)

    wedge = Wedge((0, 0), 1.0, 90, 90, width=0.22,
                  facecolor=color, edgecolor="none")
    ax.add_patch(wedge)

    ax.set_xlim(-1.15, 1.15)
    ax.set_ylim(-1.15, 1.15)

    txt_val = ax.text(0, 0.05, "0", ha="center", va="center",
                      fontsize=26, fontweight="bold",
                      color=CHART_STYLE["text"])
    ax.text(0, -0.28, label, ha="center", va="center",
            fontsize=10, color=CHART_STYLE["text_muted"])

    add_footer(fig)
    if animate:
        def update(frame):
            t = (frame + 1) / 25
            t = 1 - (1 - t) ** 3
            current = pct * t
            wedge.theta2 = 90 - 360 * (current / max_value)
            txt_val.set_text(f"{current:.1f}")
            return [wedge, txt_val]
        fig._ani = animation.FuncAnimation(
            fig, update, frames=25, interval=25, blit=False, repeat=False)
    else:
        wedge.theta2 = sweep_end
        txt_val.set_text(f"{pct:.1f}")
    return fig


# =============================================================
# 14. TKINTER EMBED HELPER
# =============================================================

def embed_figure(fig: Figure, parent_widget, **pack_kw):
    """
    Embed a matplotlib Figure in a tkinter/CustomTkinter widget.
    Returns the FigureCanvasTkAgg so callers can keep a reference.
    """
    canvas = FigureCanvasTkAgg(fig, master=parent_widget)
    canvas.draw()
    widget = canvas.get_tk_widget()
    widget.configure(bg=CHART_STYLE["fig_bg"], highlightthickness=0)
    widget.pack(**pack_kw)
    return canvas


# =============================================================
# 15. SANITY CHECK  (renders every chart to a PNG)
# =============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  SHRUTHI JHARI — utils/charts.py sanity check")
    print("=" * 60)

    out_dir = os.path.join(_ROOT, "assets", "charts_preview")
    os.makedirs(out_dir, exist_ok=True)

    def save(fig, name, animate=False):
        path = os.path.join(out_dir, name)
        try:
            fig.savefig(path, dpi=110,
                        facecolor=CHART_STYLE["fig_bg"],
                        bbox_inches="tight")
            print(f"   💾  {name}")
        except Exception as e:
            print(f"   ⚠️  {name}: {e}")

    # Dummy data
    averages = {"Maths": 72, "Physics": 68,
                "Chemistry": 75, "Computer Science": 80}
    ia_data = {
        "Maths":            [65, 70, 78],
        "Physics":          [60, 66, 72],
        "Chemistry":        [70, 72, 76],
        "Computer Science": [72, 78, 82],
    }
    zone_counts = {"red": 3, "yellow": 6, "green": 4, "gold": 2}

    hm = pd.DataFrame(
        np.random.randint(30, 95, size=(6, 4)),
        index=[f"Student {i+1}" for i in range(6)],
        columns=SUBJECTS,
    )
    dist = pd.DataFrame(
        np.random.normal(70, 12, size=(40, 4)).clip(0, 100),
        columns=SUBJECTS,
    )

    print("\n📊 Generating sample charts (animated versions render to PNG):")

    save(subject_bar_chart(averages, animate=False),
         "01_subject_bars.png")
    save(ia_trend_chart(ia_data, animate=False),
         "02_ia_trend.png")
    save(zone_donut(zone_counts, animate=False),
         "03_zone_donut.png")
    save(heatmap_chart(hm, animate=False, annot=True),
         "04_heatmap.png")
    save(radar_chart([78, 62, 72, 88], animate=False),
         "05_radar.png")
    save(subject_boxplot(dist, animate=False),
         "06_boxplot.png")
    save(ranking_bar_chart(
            ["Priya", "Sneha", "Divya", "Ananya", "Kiran"],
            [92, 88, 85, 78, 74],
            animate=False),
         "07_ranking.png")
    att_df = pd.DataFrame({
        "att_date": pd.date_range("2025-01-01", periods=12, freq="2D").strftime("%b %d"),
        "present_pct": np.random.randint(70, 100, size=12),
    })
    save(attendance_trend_chart(att_df, animate=False),
         "08_attendance.png")

    cluster_df = pd.DataFrame({
        "name":    ["A", "B", "C", "D", "E", "F"],
        "pca_x":   np.random.randn(6),
        "pca_y":   np.random.randn(6),
        "segment": ["Advanced", "Developing", "Needs Support",
                    "Advanced", "Developing", "Needs Support"],
    })
    save(cluster_scatter_chart(cluster_df, animate=False),
         "09_cluster_scatter.png")

    save(gauge_chart(78, "Mastery", animate=False),
         "10_gauge.png")

    print(f"\n📁 Preview folder: {out_dir}")
    print("\n✅ utils/charts.py OK")
    print("=" * 60)