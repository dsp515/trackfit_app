"""
adaptive_coach.py — Self-learning Adaptive Coach Engine
========================================================
• No LLM / no GPU required — pure Python, Render-safe
• In-memory per-user history (last 7 sessions)
• Multi-signal trend analysis (steps, water, calories, protein, workouts)
• Compound scoring (0-100) that improves with history depth
• Always returns a safe response — never raises
• Integrates with existing coach_service.py via generate_adaptive_response()

Architecture:
  UserMemory (ring-buffer, 7 days)
    └─► TrendAnalyzer  → trend signals per metric
          └─► RuleEngine   → weighted suggestion set
                └─► ResponseComposer → final coach message
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Deque, Dict, List, Optional, Tuple

# ─── Thread-safe user memory store ───────────────────────────────────────────
_MEMORY_LOCK = threading.Lock()
_USER_MEMORY: Dict[str, Deque[Dict[str, Any]]] = {}

MEMORY_WINDOW = 7          # days of history to keep
MIN_HISTORY_FOR_TREND = 3  # minimum snapshots before trend analysis fires


# ─── Data structures ─────────────────────────────────────────────────────────

@dataclass
class UserSnapshot:
    """One day's worth of health data submitted by the client."""
    user_id: str
    timestamp: float = field(default_factory=time.time)
    steps: int = 0
    calories: int = 0
    water_ml: int = 0
    protein_g: float = 0.0
    workouts: int = 0
    sleep_hours: float = 0.0
    weight_kg: Optional[float] = None
    # Optional profile targets (used for ratio scoring)
    step_goal: int = 8000
    calorie_goal: int = 2000
    water_goal_ml: int = 2500
    protein_goal_g: float = 120.0

    @classmethod
    def from_dict(cls, user_id: str, data: Dict[str, Any]) -> "UserSnapshot":
        return cls(
            user_id=user_id,
            steps=int(data.get("steps", 0)),
            calories=int(data.get("calories", 0)),
            water_ml=int(data.get("water_ml", 0)),
            protein_g=float(data.get("protein", 0)),
            workouts=int(data.get("workouts", 0)),
            sleep_hours=float(data.get("sleep_hours", 0)),
            weight_kg=data.get("weight_kg"),
            step_goal=int(data.get("step_goal", 8000)),
            calorie_goal=int(data.get("calorie_goal", 2000)),
            water_goal_ml=int(data.get("water_goal_ml", 2500)),
            protein_goal_g=float(data.get("protein_goal_g", 120)),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "timestamp": self.timestamp,
            "steps": self.steps,
            "calories": self.calories,
            "water_ml": self.water_ml,
            "protein_g": self.protein_g,
            "workouts": self.workouts,
            "sleep_hours": self.sleep_hours,
            "weight_kg": self.weight_kg,
            "step_goal": self.step_goal,
            "calorie_goal": self.calorie_goal,
            "water_goal_ml": self.water_goal_ml,
            "protein_goal_g": self.protein_goal_g,
        }


@dataclass
class TrendSignal:
    metric: str
    direction: str  # "improving" | "declining" | "stable"
    pct_change: float
    current: float
    average: float
    goal: float
    completion_pct: float


@dataclass
class CoachResponse:
    message: str
    suggestions: List[str]
    trend: str              # overall trend label
    score: float            # 0-1 composite daily score
    confidence: float       # 0-1 based on history depth
    signals: List[Dict[str, Any]]
    source: str = "adaptive"


# ─── Memory management ───────────────────────────────────────────────────────

def update_memory(user_id: str, snapshot: UserSnapshot) -> None:
    """Append a snapshot to the user's ring buffer (thread-safe)."""
    with _MEMORY_LOCK:
        if user_id not in _USER_MEMORY:
            _USER_MEMORY[user_id] = deque(maxlen=MEMORY_WINDOW)
        _USER_MEMORY[user_id].append(snapshot.to_dict())


def get_memory(user_id: str) -> List[Dict[str, Any]]:
    """Return a copy of the user's history (oldest → newest)."""
    with _MEMORY_LOCK:
        return list(_USER_MEMORY.get(user_id, []))


def clear_memory(user_id: str) -> None:
    """Reset a user's memory (e.g. on account deletion)."""
    with _MEMORY_LOCK:
        _USER_MEMORY.pop(user_id, None)


# ─── Trend analysis ──────────────────────────────────────────────────────────

def _trend_direction(values: List[float], sensitivity: float = 0.08) -> Tuple[str, float]:
    """
    Compare the latest value against the rolling average.
    Returns (direction, pct_change).
    sensitivity: fraction above/below average to count as improving/declining.
    """
    if not values:
        return "stable", 0.0
    avg = sum(values[:-1]) / max(len(values) - 1, 1) if len(values) > 1 else values[0]
    latest = values[-1]
    if avg == 0:
        return ("improving" if latest > 0 else "stable"), 0.0
    pct = (latest - avg) / avg
    if pct > sensitivity:
        return "improving", round(pct * 100, 1)
    elif pct < -sensitivity:
        return "declining", round(pct * 100, 1)
    return "stable", round(pct * 100, 1)


def analyze_trends(history: List[Dict[str, Any]]) -> List[TrendSignal]:
    """
    Produce a TrendSignal for each tracked metric.
    Returns empty list if history is too shallow.
    """
    if len(history) < MIN_HISTORY_FOR_TREND:
        return []

    def _extract(key: str) -> List[float]:
        return [float(h.get(key, 0) or 0) for h in history]

    metrics = [
        ("steps",    "step_goal",        "steps"),
        ("water_ml", "water_goal_ml",    "water_ml"),
        ("protein_g","protein_goal_g",   "protein_g"),
        ("calories", "calorie_goal",     "calories"),
        ("workouts", None,               "workouts"),
    ]

    signals: List[TrendSignal] = []
    for value_key, goal_key, label in metrics:
        values = _extract(value_key)
        goals  = _extract(goal_key) if goal_key else []
        goal   = goals[-1] if goals else 0.0

        direction, pct_change = _trend_direction(values)
        avg = sum(values[:-1]) / max(len(values) - 1, 1) if len(values) > 1 else values[-1]
        current = values[-1]
        completion = round((current / goal * 100), 1) if goal > 0 else 0.0

        signals.append(TrendSignal(
            metric=label,
            direction=direction,
            pct_change=pct_change,
            current=current,
            average=avg,
            goal=goal,
            completion_pct=completion,
        ))

    return signals


def overall_trend(signals: List[TrendSignal]) -> str:
    """Roll up individual signals into one label."""
    if not signals:
        return "stable"
    counts = {"improving": 0, "declining": 0, "stable": 0}
    for s in signals:
        counts[s.direction] += 1
    if counts["improving"] >= 3:
        return "improving"
    if counts["declining"] >= 3:
        return "declining"
    if counts["improving"] > counts["declining"]:
        return "slightly_improving"
    if counts["declining"] > counts["improving"]:
        return "slightly_declining"
    return "stable"


# ─── Daily score ─────────────────────────────────────────────────────────────

def compute_score(snapshot: UserSnapshot) -> float:
    """
    Composite 0-1 score based on goal completion for today's snapshot.
    Weights: steps 30%, water 25%, protein 25%, workouts 20%.
    """
    def _ratio(val: float, goal: float) -> float:
        if goal <= 0:
            return 0.5
        return min(1.0, val / goal)

    step_r    = _ratio(snapshot.steps,    snapshot.step_goal)
    water_r   = _ratio(snapshot.water_ml, snapshot.water_goal_ml)
    protein_r = _ratio(snapshot.protein_g, snapshot.protein_goal_g)
    workout_r = min(1.0, snapshot.workouts / 1.0)  # 1 session = full score

    score = (step_r * 0.30 + water_r * 0.25 + protein_r * 0.25 + workout_r * 0.20)
    return round(score, 3)


# ─── Rule engine ─────────────────────────────────────────────────────────────

def _build_suggestions(
    snapshot: UserSnapshot,
    signals: List[TrendSignal],
    history_len: int,
) -> List[str]:
    """
    Produce an ordered list of actionable suggestions.
    Priority: declining metrics > under-goal metrics > trend bonuses.
    """
    sug: List[str] = []

    sig_map = {s.metric: s for s in signals}

    # ── Declining trend warnings ──────────────────────────────────────────────
    if sig_map.get("steps", TrendSignal("","stable",0,0,0,0,0)).direction == "declining":
        sug.append("📉 Your step count has been dropping. Aim for a 15-min walk today to reverse the trend.")

    if sig_map.get("water_ml", TrendSignal("","stable",0,0,0,0,0)).direction == "declining":
        sug.append("📉 Hydration has been declining. Set an hourly water reminder.")

    if sig_map.get("protein_g", TrendSignal("","stable",0,0,0,0,0)).direction == "declining":
        sug.append("📉 Protein intake is trending down. Add a high-protein meal (eggs, paneer, dal).")

    # ── Today's under-goal nudges ─────────────────────────────────────────────
    step_remaining = max(0, snapshot.step_goal - snapshot.steps)
    if step_remaining > 2000:
        sug.append(f"🚶 You need {step_remaining:,} more steps. A 20-min brisk walk covers ~2,000 steps.")
    elif step_remaining > 0:
        sug.append(f"🏃 Only {step_remaining:,} steps left to hit your daily goal — you're almost there!")

    water_remaining = max(0, snapshot.water_goal_ml - snapshot.water_ml)
    if water_remaining > 800:
        sug.append(f"💧 Drink {water_remaining}ml more water. Sip 300ml every 2 hours to catch up.")
    elif water_remaining > 0:
        sug.append(f"💧 {water_remaining}ml water left — drink a glass now to hit your goal.")

    protein_remaining = max(0, snapshot.protein_goal_g - snapshot.protein_g)
    if protein_remaining > 30:
        sug.append(f"💪 You still need {protein_remaining:.0f}g protein. Add paneer, chicken, or a whey shake.")
    elif protein_remaining > 0:
        sug.append(f"💪 Just {protein_remaining:.0f}g protein left — a cup of Greek yogurt would do it.")

    if snapshot.workouts == 0:
        sug.append("🏋️ No workouts logged today. Even 20 min of bodyweight training counts!")

    # ── Improving trend encouragement ─────────────────────────────────────────
    if history_len >= MIN_HISTORY_FOR_TREND:
        improving = [s for s in signals if s.direction == "improving"]
        if len(improving) >= 2:
            sug.append("🔥 You're on a roll! Multiple metrics are improving — keep the momentum.")

    # ── All-clear ────────────────────────────────────────────────────────────
    if not sug:
        sug.append("✅ You're doing great across all metrics today!")

    return sug[:5]  # cap at 5 suggestions max


# ─── Confidence ──────────────────────────────────────────────────────────────

def _confidence(history_len: int) -> float:
    """Higher confidence with more history (caps at 0.95)."""
    return min(0.95, 0.5 + (history_len / MEMORY_WINDOW) * 0.45)


# ─── Primary public API ──────────────────────────────────────────────────────

def generate_adaptive_response(
    user_id: str,
    data: Dict[str, Any],
) -> CoachResponse:
    """
    Main entry point.
    1. Parses incoming data into a UserSnapshot.
    2. Stores snapshot in memory.
    3. Analyzes trend from history.
    4. Generates personalized coaching response.
    5. NEVER raises — always returns a safe CoachResponse.
    """
    try:
        snapshot = UserSnapshot.from_dict(user_id, data)
        update_memory(user_id, snapshot)
        history = get_memory(user_id)

        signals  = analyze_trends(history)
        trend    = overall_trend(signals)
        score    = compute_score(snapshot)
        conf     = _confidence(len(history))
        sug      = _build_suggestions(snapshot, signals, len(history))

        # Build headline message
        trend_phrase = {
            "improving":          "You're on an improving streak",
            "slightly_improving": "Things are getting better",
            "stable":             "You're holding steady",
            "slightly_declining": "Slight dip detected — let's correct it",
            "declining":          "Your stats have been dropping",
        }.get(trend, "Keep going")

        headline = f"{trend_phrase} 🎯 — {sug[0]}" if sug else f"{trend_phrase}. Keep logging!"

        return CoachResponse(
            message=headline,
            suggestions=sug,
            trend=trend,
            score=score,
            confidence=conf,
            signals=[
                {
                    "metric":         s.metric,
                    "direction":      s.direction,
                    "pct_change":     s.pct_change,
                    "current":        s.current,
                    "goal":           s.goal,
                    "completion_pct": s.completion_pct,
                }
                for s in signals
            ],
            source="adaptive",
        )

    except Exception as exc:
        # Hard fallback — must never propagate
        print(f"[adaptive_coach] Error for {user_id}: {exc}")
        return CoachResponse(
            message="Stay active and hydrated 💪 Keep logging your daily data!",
            suggestions=["Stay active", "Drink water", "Track your meals"],
            trend="stable",
            score=0.5,
            confidence=0.5,
            signals=[],
            source="fallback",
        )


# ─── Convenience: integrate with existing coach pipeline ─────────────────────

def enrich_coach_context(user_id: str, existing_response: str) -> str:
    """
    Prepend a short adaptive nudge to the existing CoachService response.
    Used when you want the rule-based coach AND adaptive trends together.
    """
    try:
        history = get_memory(user_id)
        if len(history) < MIN_HISTORY_FOR_TREND:
            return existing_response
        signals = analyze_trends(history)
        trend   = overall_trend(signals)

        declining = [s for s in signals if s.direction == "declining"]
        if declining:
            metric_names = ", ".join(s.metric.replace("_", " ") for s in declining[:2])
            nudge = f"⚠️ Adaptive insight: {metric_names} trending down this week. Focus here today.\n\n"
            return nudge + existing_response
        elif trend in ("improving", "slightly_improving"):
            return f"📈 Adaptive insight: Your metrics are improving this week — great consistency!\n\n{existing_response}"
        return existing_response
    except Exception:
        return existing_response
