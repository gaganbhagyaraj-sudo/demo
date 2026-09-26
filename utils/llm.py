# =============================================================
#  SHRUTHI JHARI — Cascade of Divine Knowledge
#  utils/llm.py  ·  Hint generation (LLM + offline fallback)
# =============================================================

from __future__ import annotations

import os
import sys

# --- make project root importable ---
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import re
import json
import random
import time
from dataclasses import dataclass, field
from typing import Optional, List, Dict

from config import SUBJECTS


# =============================================================
# 0. CONFIG — set these env vars to enable real LLM calls
# =============================================================

LLM_PROVIDER   = os.getenv("SJ_LLM_PROVIDER", "offline")   # offline | openai | gemini | ollama
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OLLAMA_URL     = os.getenv("OLLAMA_URL", "http://localhost:11434")

LLM_ENABLED = (
    (LLM_PROVIDER == "openai" and OPENAI_API_KEY) or
    (LLM_PROVIDER == "gemini" and GEMINI_API_KEY) or
    (LLM_PROVIDER == "ollama")
)

REQUEST_TIMEOUT = 8   # seconds


# =============================================================
# 1. DATA STRUCTURES
# =============================================================

@dataclass
class Hint:
    level: int              # 1 (nudge), 2 (hint), 3 (full explain)
    text: str
    source: str = "offline"  # "offline" | "openai" | "gemini" | "ollama"

    def to_dict(self) -> dict:
        return {"level": self.level, "text": self.text, "source": self.source}


@dataclass
class HintSet:
    problem: str
    concept: str
    hints: List[Hint] = field(default_factory=list)

    def get(self, level: int) -> Optional[Hint]:
        for h in self.hints:
            if h.level == level:
                return h
        return None

    def levels(self) -> List[int]:
        return [h.level for h in self.hints]


# =============================================================
# 2. INTEREST INJECTION TEMPLATES
# =============================================================

# Rich context lines per interest to spark engagement
INTEREST_CONTEXTS = {
    "Cricket": {
        "maths":   "runs, overs, run rate, strike rate, batting average",
        "physics": "ball trajectory, velocity, spin, momentum",
        "chemistry": "pitch conditions, grass, moisture, weather impact",
        "cs":      "score tracking apps, ball-by-ball analytics, DRS",
        "examples": [
            "A batsman scored 45 runs off 30 balls — what's the strike rate?",
            "If a team scores 240 in 50 overs, what's the run rate?",
            "A bowler took 3 wickets for 24 runs — what's the economy?",
        ],
    },
    "Cooking": {
        "maths":   "recipe scaling, ratios, fractions, portions",
        "physics": "heat transfer, boiling point, pressure cooking",
        "chemistry": "reactions, pH, fermentation, caramelization",
        "cs":      "recipe apps, timers, ingredient databases",
        "examples": [
            "A recipe uses 3/4 cup sugar for 12 cookies. How much for 20?",
            "Water boils at 100°C at sea level. Why lower on a hill?",
            "If 2 cups of flour make 12 rotis, how many for 30?",
        ],
    },
    "Gaming": {
        "maths":   "K/D ratio, XP curves, damage calculation, hit percentage",
        "physics": "projectile motion, gravity, friction, collision",
        "chemistry": "explosions, reactions, materials",
        "cs":      "game engines, pathfinding, AI, physics engines",
        "examples": [
            "You have 12 kills and 4 deaths — what's your K/D ratio?",
            "An arrow is fired at 30° — how high does it go?",
            "If a health bar is 240 and damage is 15 per hit, how many hits?",
        ],
    },
    "Space": {
        "maths":   "orbits, distances, time dilation, escape velocity",
        "physics": "gravity, acceleration, orbits, relativity",
        "chemistry": "rocket fuel, oxygen, vacuum chemistry",
        "cs":      "satellite software, image processing, autonomous nav",
        "examples": [
            "The Moon is 384,400 km away. Light takes how many seconds?",
            "Escape velocity from Earth is 11.2 km/s — why?",
            "If a rocket burns 5 tonnes/sec, how much for a 3-min burn?",
        ],
    },
    "Music": {
        "maths":   "beats, tempo, time signatures, intervals, frequencies",
        "physics": "sound waves, frequency, amplitude, resonance",
        "chemistry": "materials of instruments, acoustics",
        "cs":      "audio processing, DAWs, synthesizers, sampling",
        "examples": [
            "A song is 120 BPM — how many beats in 30 seconds?",
            "A note at 440 Hz — what's its wavelength in air?",
            "If a bar has 4 beats and each beat is 0.5 sec, how long is the bar?",
        ],
    },
    "Football": {
        "maths":   "goals per match, pass accuracy %, possession",
        "physics": "ball swerve, spin, force, kinematics",
        "chemistry": "pitch, weather, ball materials",
        "cs":      "VAR, tracking systems, analytics",
        "examples": [
            "A team passes 480 times and completes 384 — what's the accuracy?",
            "A free kick is taken 25 m from goal at 60° — will it clear the wall?",
            "If a striker scores in 3 of 5 matches, what's the ratio?",
        ],
    },
    "Movies": {
        "maths":   "runtime, box office, ratings, budget ratios",
        "physics": "special effects, stunts, light",
        "chemistry": "props, effects, materials",
        "cs":      "VFX, animation, CGI pipelines",
        "examples": [
            "A movie runs 2h 18m — how many minutes is that?",
            "A film cost $80M and earned $400M — what's the return?",
            "If 24 frames per second, how many frames in a 2-min scene?",
        ],
    },
}


# =============================================================
# 3. OFFLINE HINT GENERATOR  (always available)
# =============================================================

def _extract_numbers(problem: str) -> List[float]:
    """Find all numeric values (incl. fractions like 1/2) in a problem."""
    fracs = re.findall(r"(\d+)\s*/\s*(\d+)", problem)
    for a, b in fracs:
        try:
            problem = problem.replace(f"{a}/{b}", str(float(a) / float(b)))
        except ZeroDivisionError:
            pass
    nums = re.findall(r"-?\d+\.?\d*", problem)
    return [float(n) for n in nums if n not in ("", "-")]


def _detect_op(problem: str) -> str:
    p = problem.lower()
    if " + " in p or "add" in p or "sum" in p or "total" in p:
        return "add"
    if " - " in p or "subtract" in p or "difference" in p:
        return "subtract"
    if " × " in p or " * " in p or "multipl" in p or "times" in p or "product" in p:
        return "multiply"
    if " ÷ " in p or " / " in p or "divid" in p or "ratio" in p:
        return "divide"
    if "percent" in p or "%" in p:
        return "percent"
    if "solve" in p or "x =" in p or "find x" in p:
        return "equation"
    return "unknown"


def _offline_hint_level1(problem: str, concept: str, subject: str) -> str:
    """A gentle nudge — the question you should ask yourself."""
    op = _detect_op(problem)
    nudges = {
        "add":      "Look carefully — what are the parts you're combining? Add them up.",
        "subtract": "You're finding what's left over. Which value comes first?",
        "multiply": "This is about groups of equal size. Multiply the group size by the count.",
        "divide":   "You're splitting into equal parts. Which number is the total?",
        "percent":  "Percent means 'per hundred.' What's the whole thing you're comparing to?",
        "equation": "Get the unknown alone on one side. Do the opposite operation on both sides.",
        "unknown":  f"Read the question slowly. What exactly are they asking you to find about '{concept}'?",
    }
    return f"💡 {nudges.get(op, nudges['unknown'])}"


def _offline_hint_level2(problem: str, concept: str, subject: str) -> str:
    """A concrete hint — the first step."""
    op = _detect_op(problem)
    nums = _extract_numbers(problem)
    num_str = ", ".join(f"{n:g}" for n in nums[:4])

    steps = {
        "add":      f"Step 1: Write the numbers to add ({num_str}). Line them up by place value. Step 2: Start from the rightmost column.",
        "subtract": f"Step 1: Put the larger number on top ({num_str}). Step 2: Subtract column by column, borrowing when needed.",
        "multiply": f"Step 1: Identify the groups and size ({num_str}). Step 2: Multiply them — use the multiplication table or break into smaller parts.",
        "divide":   f"Step 1: Identify total and divisor ({num_str}). Step 2: Ask: how many times does the divisor fit into the total?",
        "percent":  f"Step 1: Convert percent to decimal (÷100). Step 2: Multiply by the whole. Then check if the answer feels reasonable.",
        "equation": f"Step 1: Move all terms with x to one side, constants to the other. Step 2: Divide by the coefficient of x.",
        "unknown":  f"Step 1: Underline the given values ({num_str}). Step 2: Identify the formula related to '{concept}'.",
    }
    return f"🔎 {steps.get(op, steps['unknown'])}"


def _offline_hint_level3(problem: str, concept: str, subject: str) -> str:
    """Full walkthrough — the conceptual explanation with worked example."""
    op = _detect_op(problem)
    nums = _extract_numbers(problem)

    # Try to actually solve simple cases so the explanation is concrete
    solved_text = ""
    try:
        if len(nums) >= 2:
            a, b = nums[0], nums[1]
            if op == "add":
                solved_text = f"For example: {a:g} + {b:g} = {a+b:g}."
            elif op == "subtract":
                solved_text = f"For example: {a:g} − {b:g} = {a-b:g}."
            elif op == "multiply":
                solved_text = f"For example: {a:g} × {b:g} = {a*b:g}."
            elif op == "divide" and b != 0:
                solved_text = f"For example: {a:g} ÷ {b:g} = {a/b:.2f}."
            elif op == "percent" and b != 0:
                solved_text = f"For example: {a:g}% of {b:g} = {a/100*b:.2f}."
    except Exception:
        pass

    base = {
        "add": (
            f"Think of addition as combining two groups. If you have {nums[0]:g} apples "
            f"and someone gives you more, you count them all together. Write the numbers "
            f"one under the other, aligned by place value. Add from right to left."
        ) if nums else "Add the parts together. Line them up by place value.",
        "subtract": (
            f"Subtraction means taking away. Start with the larger number ({nums[0]:g} if applicable), "
            f"and remove the smaller. Borrow from the next column if needed."
        ) if len(nums) >= 2 else "Subtract the smaller from the larger. Borrow when needed.",
        "multiply": (
            "Multiplication is repeated addition. 3 × 4 is the same as 4 + 4 + 4. "
            "For larger numbers, break them into tens and ones and multiply separately, "
            "then add the results."
        ),
        "divide":   "Division splits a total into equal parts. If 12 apples are shared among 4 people, each gets 3. Long division works digit by digit.",
        "percent":  "Percent means 'out of 100'. 25% of 80 is 25/100 × 80. Convert to decimal first, then multiply. Check: is the answer smaller than the whole? Yes, unless > 100%.",
        "equation": "An equation is a balance scale. Whatever you do to one side, do to the other. To solve for x, isolate it. If x has a coefficient, divide both sides by it.",
        "unknown":  f"'{concept}' is best understood by identifying what is known and what is unknown. Look for keywords (total, left over, each, per) that hint at the operation.",
    }

    tail = f" {solved_text}" if solved_text else ""
    return f"📘 {base.get(op, base['unknown'])}{tail}"


def generate_offline_hints(problem: str, concept: str,
                           subject: str = "Maths") -> HintSet:
    """Always-available fallback: 3 template-based hints."""
    hs = HintSet(problem=problem, concept=concept)
    hs.hints = [
        Hint(1, _offline_hint_level1(problem, concept, subject), "offline"),
        Hint(2, _offline_hint_level2(problem, concept, subject), "offline"),
        Hint(3, _offline_hint_level3(problem, concept, subject), "offline"),
    ]
    return hs


# =============================================================
# 4. INTEREST-BASED EXAMPLE GENERATOR (offline)
# =============================================================

def interest_example(concept: str, interest: str,
                     subject: str = "Maths") -> str:
    """
    Generate a personalized example using the student's interest.
    Offline template-based.
    """
    ctx = INTEREST_CONTEXTS.get(interest)
    if not ctx:
        return f"A real-world example using {concept} would help — try thinking of it in terms of something you love."

    example = random.choice(ctx["examples"])
    field_map = {
        "Maths":            ctx.get("maths"),
        "Physics":          ctx.get("physics"),
        "Chemistry":        ctx.get("chemistry"),
        "Computer Science": ctx.get("cs"),
    }
    focus = field_map.get(subject, ctx.get("maths", ""))

    return (
        f"**{interest} × {concept}**\n"
        f"Using {concept}, think about: {focus}.\n"
        f"Try this: {example}"
    )


# =============================================================
# 5. LLM CALLS  (only used when API is configured)
# =============================================================

def _call_openai(prompt: str, model: str = "gpt-4o-mini") -> Optional[str]:
    try:
        import requests
    except ImportError:
        return None

    try:
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type":  "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system",
                     "content": "You are a patient tutor for Grade 7 students. "
                                "Give clear, short, encouraging guidance."},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 220,
                "temperature": 0.6,
            },
            timeout=REQUEST_TIMEOUT,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


def _call_gemini(prompt: str,
                 model: str = "gemini-1.5-flash") -> Optional[str]:
    try:
        import requests
    except ImportError:
        return None

    try:
        url = (f"https://generativelanguage.googleapis.com/v1beta/"
               f"models/{model}:generateContent?key={GEMINI_API_KEY}")
        resp = requests.post(
            url,
            json={
                "contents": [{
                    "parts": [{
                        "text": ("You are a patient tutor for Grade 7 students. "
                                 + prompt)
                    }]
                }],
                "generationConfig": {"maxOutputTokens": 220, "temperature": 0.6},
            },
            timeout=REQUEST_TIMEOUT,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception:
        return None


def _call_ollama(prompt: str,
                 model: str = "llama3.2") -> Optional[str]:
    try:
        import requests
    except ImportError:
        return None

    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": model,
                "prompt": ("You are a patient tutor for Grade 7 students. "
                           + prompt),
                "stream": False,
            },
            timeout=REQUEST_TIMEOUT,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        return data.get("response", "").strip()
    except Exception:
        return None


def _call_llm(prompt: str) -> Optional[str]:
    """Try the configured provider. Returns None if unavailable."""
    if LLM_PROVIDER == "openai" and OPENAI_API_KEY:
        return _call_openai(prompt)
    if LLM_PROVIDER == "gemini" and GEMINI_API_KEY:
        return _call_gemini(prompt)
    if LLM_PROVIDER == "ollama":
        return _call_ollama(prompt)
    return None


# =============================================================
# 6. PUBLIC API
# =============================================================

def generate_hints(problem: str,
                   concept: str,
                   subject: str = "Maths",
                   interest: Optional[str] = None,
                   student_name: Optional[str] = None) -> HintSet:
    """
    Generate a full 3-level hint set for a problem.

    Tries the LLM first (if configured), falls back to offline templates.
    Always returns exactly 3 hints (levels 1, 2, 3).
    """
    # Build LLM prompt
    prompt = (
        f"Student: {student_name or 'a Grade 7 student'}\n"
        f"Subject: {subject}\n"
        f"Concept: {concept}\n"
        f"{('Interest: ' + interest) if interest else ''}\n"
        f"Problem: {problem}\n\n"
        "Return ONLY JSON of the form:\n"
        '{"nudge": "...", "hint": "...", "explain": "..."}\n'
        "- nudge: a 1-sentence question to nudge thinking (no answer)\n"
        "- hint: the first step, still no final answer\n"
        "- explain: a full conceptual explanation with a worked example\n"
        "Keep each under 60 words."
    )

    text = _call_llm(prompt) if LLM_ENABLED else None

    if text:
        try:
            # Try strict JSON first
            m = re.search(r"\{.*\}", text, re.DOTALL)
            if m:
                data = json.loads(m.group(0))
                hs = HintSet(problem=problem, concept=concept)
                hs.hints = [
                    Hint(1, data.get("nudge",   "").strip(), LLM_PROVIDER),
                    Hint(2, data.get("hint",    "").strip(), LLM_PROVIDER),
                    Hint(3, data.get("explain", "").strip(), LLM_PROVIDER),
                ]
                if all(h.text for h in hs.hints):
                    return hs
        except Exception:
            pass

    # Fallback
    return generate_offline_hints(problem, concept, subject)


def get_hint(problem: str, concept: str, level: int,
             subject: str = "Maths",
             interest: Optional[str] = None,
             student_name: Optional[str] = None) -> Hint:
    """
    Get a single hint at the requested level (1, 2, or 3).
    Internally generates the full set (cached in-memory per problem+concept).
    """
    key = (problem, concept, subject, interest or "")
    if key not in _HINT_CACHE:
        _HINT_CACHE[key] = generate_hints(
            problem, concept, subject, interest, student_name)
    hs = _HINT_CACHE[key]
    h = hs.get(level)
    return h or Hint(level, "Hint unavailable.", "offline")


_HINT_CACHE: Dict[tuple, HintSet] = {}


def clear_cache():
    _HINT_CACHE.clear()


def provider_status() -> dict:
    """Info about the active provider — useful for a settings/debug page."""
    return {
        "enabled":     LLM_ENABLED,
        "provider":    LLM_PROVIDER,
        "has_openai":  bool(OPENAI_API_KEY),
        "has_gemini":  bool(GEMINI_API_KEY),
        "ollama_url":  OLLAMA_URL,
        "mode":        ("online" if LLM_ENABLED else "offline (template)"),
    }


# =============================================================
# 7. SANITY CHECK
# =============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  SHRUTHI JHARI — utils/llm.py sanity check")
    print("=" * 60)

    status = provider_status()
    print(f"\n🔌 Provider status:")
    for k, v in status.items():
        print(f"   {k:<12}  :  {v}")

    # ---------- Offline hint generation ----------
    print("\n💡 Offline hints — Fractions problem:")
    problem = "Add 1/2 + 1/3 and write the answer as a fraction."
    hs = generate_offline_hints(problem, "Fractions", "Maths")
    for h in hs.hints:
        print(f"\n   Level {h.level} [{h.source}]")
        print(f"   → {h.text}")

    # ---------- Offline hints — Percentages ----------
    print("\n💡 Offline hints — Percentages problem:")
    problem = "What is 25% of 80?"
    hs = generate_offline_hints(problem, "Percentages", "Maths")
    for h in hs.hints:
        print(f"\n   Level {h.level}")
        print(f"   → {h.text}")

    # ---------- Interest injection ----------
    print("\n🎯 Interest-based example (Cricket × Fractions):")
    print("   " + interest_example("Fractions", "Cricket", "Maths").replace(
        "\n", "\n   "))

    print("\n🎯 Interest-based example (Gaming × Ratios):")
    print("   " + interest_example("Ratios", "Gaming", "Maths").replace(
        "\n", "\n   "))

    # ---------- Public API ----------
    print("\n📞 Public API — single hint (level 2):")
    h = get_hint("What is 3/4 of 20?", "Fractions", level=2,
                 subject="Maths", interest="Cooking")
    print(f"   Level {h.level} [{h.source}]: {h.text}")

    print("\n📞 Public API — cached second call (level 3):")
    h3 = get_hint("What is 3/4 of 20?", "Fractions", level=3,
                  subject="Maths", interest="Cooking")
    print(f"   Level {h3.level} [{h3.source}]: {h3.text}")

    print("\n📞 Public API — unknown concept fallback:")
    h = get_hint("Solve for x: 2x + 3 = 11", "Linear Equations",
                 level=1, subject="Maths", interest="Gaming")
    print(f"   Level {h.level} [{h.source}]: {h.text}")

    print("\n✅ utils/llm.py OK")
    print("=" * 60)