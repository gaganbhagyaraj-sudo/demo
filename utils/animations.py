# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  utils/animations.py  ·  Non-intrusive animation helpers
# =============================================================

from __future__ import annotations

import os
import sys

# --- make project root importable ---
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import time
from typing import Callable, Optional, Tuple, Any, Union

from config import GRADIENT_START, GRADIENT_END


# =============================================================
# 1. EASING FUNCTIONS
# =============================================================

def ease_linear(t: float) -> float:
    return t


def ease_in(t: float) -> float:
    return t * t


def ease_out(t: float) -> float:
    return 1 - (1 - t) ** 3


def ease_in_out(t: float) -> float:
    return 3 * t * t - 2 * t * t * t


def ease_bounce(t: float) -> float:
    n1, d1 = 7.5625, 2.75
    if t < 1 / d1:
        return n1 * t * t
    elif t < 2 / d1:
        t -= 1.5 / d1
        return n1 * t * t + 0.75
    elif t < 2.5 / d1:
        t -= 2.25 / d1
        return n1 * t * t + 0.9375
    else:
        t -= 2.625 / d1
        return n1 * t * t + 0.984375


EASINGS = {
    "linear":    ease_linear,
    "in":        ease_in,
    "out":       ease_out,
    "in_out":    ease_in_out,
    "bounce":    ease_bounce,
}


# =============================================================
# 2. COLOR HELPERS
# =============================================================

def _hex_to_rgb(h: str) -> Tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb: Tuple[float, float, float]) -> str:
    return "#{:02X}{:02X}{:02X}".format(
        int(max(0, min(255, rgb[0]))),
        int(max(0, min(255, rgb[1]))),
        int(max(0, min(255, rgb[2]))),
    )


def lerp_color(c1: str, c2: str, t: float) -> str:
    """Blend two hex colors by t ∈ [0,1]."""
    t = max(0.0, min(1.0, t))
    a, b = _hex_to_rgb(c1), _hex_to_rgb(c2)
    return _rgb_to_hex((
        a[0] + (b[0] - a[0]) * t,
        a[1] + (b[1] - a[1]) * t,
        a[2] + (b[2] - a[2]) * t,
    ))


# =============================================================
# 3. CORE TWEEN  (frame-by-frame, uses `widget.after`)
# =============================================================

class Tween:
    """
    Cancelable tween.
    Callback receives t ∈ [0,1] each frame.
    Runs at ~60fps until t = 1 or until cancelled.
    """

    def __init__(self, widget, duration_ms: int,
                 on_frame: Callable[[float], None],
                 on_done: Optional[Callable[[], None]] = None,
                 easing: Union[str, Callable[[float], float]] = "in_out",
                 fps: int = 60):
        self.widget = widget
        self.duration_ms = max(1, int(duration_ms))
        self.on_frame = on_frame
        self.on_done = on_done
        self.easing = EASINGS.get(easing, easing) if isinstance(easing, str) else easing
        self.fps = max(1, int(fps))

        self._start = None
        self._after_id = None
        self._cancelled = False

    def start(self):
        self._start = time.perf_counter()
        self._tick()
        return self

    def cancel(self):
        self._cancelled = True
        if self._after_id:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _tick(self):
        if self._cancelled:
            return
        elapsed = (time.perf_counter() - self._start) * 1000.0
        raw = min(1.0, elapsed / self.duration_ms)
        eased = self.easing(raw)
        try:
            self.on_frame(eased)
        except Exception:
            pass

        if raw >= 1.0:
            if self.on_done:
                try:
                    self.on_done()
                except Exception:
                    pass
            return

        interval = int(1000 / self.fps)
        self._after_id = self.widget.after(interval, self._tick)


def tween(widget, duration_ms: int, on_frame, on_done=None,
          easing="in_out", fps=60) -> Tween:
    """Convenience wrapper — create + start a tween."""
    return Tween(widget, duration_ms, on_frame, on_done, easing, fps).start()


# =============================================================
# 4. COUNT-UP NUMBER  (for stat cards)
# =============================================================

def count_up(widget,
             from_value: float,
             to_value: float,
             duration_ms: int = 900,
             fmt: str = "{:.0f}",
             easing: str = "out",
             on_done: Optional[Callable[[], None]] = None) -> Tween:
    """
    Animate a label's text from `from_value` → `to_value`.
    `widget.configure(text=...)` is called every frame.

    Example:
        count_up(stat_label, 0, 92.5, fmt="{:.1f}%")
    """
    def frame(t):
        v = from_value + (to_value - from_value) * t
        try:
            widget.configure(text=fmt.format(v))
        except Exception:
            pass

    return tween(widget, duration_ms, frame, on_done=on_done, easing=easing)


# =============================================================
# 5. COLOR TWEEN  (smooth color transition)
# =============================================================

def color_tween(widget,
                prop: str,
                from_color: str,
                to_color: str,
                duration_ms: int = 600,
                easing: str = "in_out") -> Tween:
    """
    Smoothly transition a hex color property on a widget.
    `prop` is usually 'fg_color' or 'text_color' for CustomTkinter,
    or 'bg' / 'fg' for plain Tkinter widgets.
    """
    def frame(t):
        c = lerp_color(from_color, to_color, t)
        try:
            widget.configure(**{prop: c})
        except Exception:
            pass

    return tween(widget, duration_ms, frame, easing=easing)


def pulse_highlight(widget,
                    prop: str = "fg_color",
                    base: Optional[str] = None,
                    peak: Optional[str] = None,
                    cycles: int = 2,
                    period_ms: int = 300) -> Tween:
    """
    Flash a widget once with a highlight color, then return to base.
    Useful when a value changes (e.g. new alert arrives).
    """
    if base is None:
        try:
            base = widget.cget(prop)
        except Exception:
            base = "#1E293B"
    peak = peak or GRADIENT_END

    total_steps = cycles * 2
    step_ms = period_ms // total_steps

    state = {"i": 0}

    def step():
        if state["i"] >= total_steps:
            try:
                widget.configure(**{prop: base})
            except Exception:
                pass
            return
        from_c = widget.cget(prop) if state["i"] % 2 == 0 else peak
        to_c = peak if state["i"] % 2 == 0 else base
        color_tween(widget, prop, from_c, to_c, step_ms, easing="out")
        state["i"] += 1
        try:
            widget.after(step_ms, step)
        except Exception:
            pass

    step()
    return None


# =============================================================
# 6. DEBOUNCE  (limit rapid calls)
# =============================================================

class Debouncer:
    """
    Wraps a function; when called repeatedly, only the LAST call
    within `wait_ms` actually fires.

    Usage:
        debounced_refresh = Debouncer(widget, 250, refresh_chart)
        entry.bind("<KeyRelease>", lambda e: debounced_refresh.call())
    """

    def __init__(self, widget, wait_ms: int, func: Callable[..., Any]):
        self.widget = widget
        self.wait_ms = max(0, int(wait_ms))
        self.func = func
        self._after_id = None

    def call(self, *args, **kwargs):
        self.cancel()
        try:
            self._after_id = self.widget.after(
                self.wait_ms,
                lambda: self._invoke(*args, **kwargs))
        except Exception:
            self._invoke(*args, **kwargs)

    def _invoke(self, *args, **kwargs):
        self._after_id = None
        try:
            self.func(*args, **kwargs)
        except Exception:
            pass

    def cancel(self):
        if self._after_id:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None


def debounce(widget, wait_ms: int, func: Callable[..., Any]) -> Debouncer:
    return Debouncer(widget, wait_ms, func)


# =============================================================
# 7. THROTTLE  (limit calls to at most once per interval)
# =============================================================

class Throttler:
    def __init__(self, interval_ms: int):
        self.interval_ms = max(0, int(interval_ms))
        self._last = 0.0

    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args, **kwargs):
            now = time.perf_counter() * 1000
            if now - self._last >= self.interval_ms:
                self._last = now
                return func(*args, **kwargs)
        return wrapper


# =============================================================
# 8. DELAY / SCHEDULE
# =============================================================

class Scheduler:
    """
    Simple wrapper around widget.after for scheduling + cancelling.
    """

    def __init__(self, widget):
        self.widget = widget
        self._ids = []

    def after(self, ms: int, func: Callable[[], None]):
        try:
            aid = self.widget.after(ms, func)
            self._ids.append(aid)
            return aid
        except Exception:
            return None

    def cancel_all(self):
        for aid in self._ids:
            try:
                self.widget.after_cancel(aid)
            except Exception:
                pass
        self._ids.clear()


def schedule(widget, ms: int, func) -> Optional[str]:
    try:
        return widget.after(ms, func)
    except Exception:
        return None


def cancel_schedule(widget, after_id: Optional[str]):
    if not after_id:
        return
    try:
        widget.after_cancel(after_id)
    except Exception:
        pass


# =============================================================
# 9. TYPEWRITER EFFECT  (splash hero text)
# =============================================================

def typewriter(label,
               text: str,
               duration_ms: int = 1200,
               cursor: str = "▍",
               show_cursor: bool = True,
               on_done: Optional[Callable[[], None]] = None) -> Tween:
    """
    Reveals text character by character on a label.
    """
    def frame(t):
        n = int(len(text) * t)
        shown = text[:n]
        suffix = cursor if (show_cursor and n < len(text)) else ""
        try:
            label.configure(text=shown + suffix)
        except Exception:
            pass

    def done():
        try:
            label.configure(text=text)
        except Exception:
            pass
        if on_done:
            on_done()

    return tween(label, duration_ms, frame, on_done=done, easing="in_out")


# =============================================================
# 10. STAGGER  (run multiple callbacks one after another)
# =============================================================

def stagger(widget,
            callbacks: list,
            interval_ms: int = 120):
    """
    Fire a list of callbacks one by one with `interval_ms` gaps.
    """
    for i, cb in enumerate(callbacks):
        try:
            widget.after(i * interval_ms, cb)
        except Exception:
            pass


# =============================================================
# 11. SANITY CHECK
# =============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  SHRUTHI JHARI — utils/animations.py sanity check")
    print("=" * 60)

    # --- easing values ---
    print("\n📈 Easing curve samples (t=0.25, 0.5, 0.75):")
    for name, fn in EASINGS.items():
        samples = [f"{fn(t):.3f}" for t in (0.25, 0.5, 0.75)]
        print(f"   {name:<8}  →  {', '.join(samples)}")

    # --- color lerp ---
    print("\n🎨 Color interpolation (purple → gold):")
    for t in (0.0, 0.25, 0.5, 0.75, 1.0):
        c = lerp_color(GRADIENT_START, GRADIENT_END, t)
        print(f"   t={t:.2f}  →  {c}")

    # --- tiny CTk demo (optional — only runs if display available) ---
    print("\n🖥️  Optional live demo (skip if no display)...")
    try:
        import customtkinter as ctk
        ctk.set_appearance_mode("dark")

        root = ctk.CTk()
        root.geometry("520x260")
        root.title("animations.py — demo")
        root.configure(fg_color="#0F172A")

        title = ctk.CTkLabel(root, text="", font=("Segoe UI", 26, "bold"),
                             text_color="#F5F3FF")
        title.pack(pady=(28, 8))

        stat = ctk.CTkLabel(root, text="0", font=("Segoe UI", 32, "bold"),
                            text_color="#F59E0B")
        stat.pack(pady=6)

        note = ctk.CTkLabel(root, text="", font=("Segoe UI", 11),
                            text_color="#94A3B8")
        note.pack(pady=(6, 12))

        box = ctk.CTkFrame(root, width=220, height=44,
                           corner_radius=10, fg_color="#6D28D9")
        box.pack(pady=8)
        box.pack_propagate(False)
        inner = ctk.CTkLabel(box, text="   Value updated   ",
                             text_color="#FFFFFF")
        inner.place(relx=0.5, rely=0.5, anchor="center")

        # 1. Typewriter title
        typewriter(title, "Shruthi Jhari", duration_ms=1100)

        # 2. Count-up stat after title finishes
        root.after(1200, lambda: count_up(stat, 0, 92.5,
                                          duration_ms=900, fmt="{:.1f}%"))

        # 3. Flash highlight on the box
        root.after(2200, lambda: pulse_highlight(box, prop="fg_color",
                                                 base="#6D28D9",
                                                 peak="#F59E0B",
                                                 cycles=2,
                                                 period_ms=360))

        # 4. Debounce demo (info only)
        root.after(2800, lambda: note.configure(
            text="count-up · color tween · pulse · debounce ready"))

        root.mainloop()
    except Exception as e:
        print(f"   (skipped live demo: {e})")

    print("\n✅ utils/animations.py OK")
    print("=" * 60)