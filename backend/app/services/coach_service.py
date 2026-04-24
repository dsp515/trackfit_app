import random
from datetime import date, datetime, timedelta
from typing import Optional, Dict, Any
import json
from pathlib import Path

from sqlalchemy.orm import Session
from app.models.chat_history import ChatHistory
from app.models.daily_stats import DailyStats
from app.models.food_log import FoodLog
from app.models.profile import Profile
from app.models.user import User
from app.models.workout_log import WorkoutLog
from app.core.config import settings

# Load food and exercise databases at module level (loaded once)
FOOD_DB_PATH = Path(settings.FOOD_DB_PATH)
EXERCISE_DB_PATH = Path(settings.EXERCISE_DB_PATH)

try:
    with open(FOOD_DB_PATH, "r", encoding="utf-8") as f:
        FOOD_DB = json.load(f)
except FileNotFoundError:
    FOOD_DB = {}

try:
    with open(EXERCISE_DB_PATH, "r", encoding="utf-8") as f:
        EXERCISE_DB = json.load(f)
except FileNotFoundError:
    EXERCISE_DB = {}

# Precompute Indian food keys for quick lookup
INDIAN_FOOD_KEYS = [k for k, v in FOOD_DB.items() if v.get("cuisine_region") == "Indian"]

# ─── Local LLM (optional) ────────────────────────────────────────────────────
# Loads the CoachLLM transformer + tokenizer if model files exist.
# Falls back to rule-based only if not available.

_local_llm = None
_local_tokenizer = None
_local_config = None
_local_device = None

def _try_load_local_llm():
    global _local_llm, _local_tokenizer, _local_config, _local_device
    model_path = Path(settings.COACH_MODEL_PATH)
    tokenizer_path = Path(settings.TOKENIZER_PATH)
    config_path = model_path.parent / "coach_config.json"

    if not model_path.exists() or not tokenizer_path.exists() or not config_path.exists():
        return

    try:
        import torch
        from models.coach_llm import CoachLLM, CoachConfig
        from models.tokenizer import BPETokenizer

        with open(config_path) as f:
            cfg = json.load(f)

        _local_config = CoachConfig(
            vocab_size=cfg["vocab_size"],
            block_size=cfg["block_size"],
            n_embed=cfg["n_embed"],
            n_head=cfg["n_head"],
            n_layer=cfg["n_layer"],
            dropout=cfg.get("dropout", 0.1),
        )
        _local_device = "cuda" if torch.cuda.is_available() else "cpu"
        _local_llm = CoachLLM(_local_config).to(_local_device)
        _local_llm.load_state_dict(torch.load(model_path, map_location=_local_device, weights_only=True))
        _local_llm.eval()

        _local_tokenizer = BPETokenizer(_local_config.vocab_size)
        _local_tokenizer.load(tokenizer_path)
        print("Local Coach LLM loaded successfully")
    except Exception as e:
        print(f"Could not load local LLM: {e}")
        _local_llm = None

_try_load_local_llm()

# ─── Intent Keywords ─────────────────────────────────────────────────────────

INTENT_KEYWORDS = {
    "greeting": ["hi", "hello", "hey", "namaste", "sup", "what's up", "hola"],
    "progress": ["how am i doing", "my progress", "summary", "dashboard", "today's stats", "how did i do", "daily summary"],
    "water": ["water", "hydration", "drink", "thirsty", "pani", "chaas", "coconut water"],
    "protein": ["protein", "how much protein", "protein intake", "protein source"],
    "calories": ["calories", "cal", "how many calories", "kcal", "calorie"],
    "weight_loss": ["lose weight", "fat loss", "cutting", "deficit", "slim", "reduce weight"],
    "muscle_gain": ["build muscle", "gain weight", "bulk", "mass", "gain muscle"],
    "workout": ["workout", "exercise", "training", "gym", "routine", "plan"],
    "home_workout": ["home workout", "no equipment", "bodyweight", "home exercise"],
    "sleep": ["sleep", "recovery", "rest", "fatigue", "tired"],
    "motivation": ["motivate", "encourage", "give up", "can't do", "hard", "bored", "lazy"],
    "bmi": ["bmi", "body mass", "ideal weight", "overweight", "underweight"],
    "cheat": ["cheat meal", "junk food", "pizza", "burger", "fast food"],
    "supplement": ["supplement", "whey", "creatine", "vitamin", "protein powder"],
    "steps": ["steps", "walk", "walking", "10000", "pedometer"],
    "indian_food": ["biryani", "dal", "roti", "paneer", "dosa", "idli", "samosa", "chole", "rajma", "khichdi", "paratha", "upma", "poha", "curd", "ghee"],
    "exercise_form": ["squat", "push-up", "pushup", "pull-up", "pullup", "lunge", "plank", "burpee", "form", "technique", "how to do"],
    "general": [],
}


class CoachService:
    def __init__(self, db: Session):
        self.db = db

    async def chat(
        self,
        user_id: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> tuple[str, str]:
        """Main entry point for the coach (async — uses Gemini AI)."""
        self._save_message(user_id, "user", message)

        intent = self._detect_intent(message)
        user_context = context or self._safe_get_user_context(user_id)

        try:
            response = self._handle_intent(intent, message, user_context, user_id)
            source = "local"

            # Try Gemini AI enhancement (non-blocking)
            if settings.GEMINI_API_KEY:
                try:
                    llm_response = await self._generate_gemini_response(message, user_context)
                    if llm_response:
                        response = llm_response
                        source = "gemini"
                except Exception:
                    pass  # Keep rule-based reply on any Gemini failure

            response = self._format_structured_reply(intent, response, user_context, message)
            self._save_message(user_id, "assistant", response)
            return response, source
        except Exception:
            # Never fail hard for coach chat; provide safe local guidance.
            fallback = self._fallback_reply(message, user_context)
            self._save_message(user_id, "assistant", fallback)
            return fallback, "fallback"

    def get_history(self, user_id: str, limit: int = 50) -> list[ChatHistory]:
        return (
            self.db.query(ChatHistory)
            .filter(ChatHistory.user_id == user_id)
            .order_by(ChatHistory.created_at.desc())
            .limit(limit)
            .all()
        )

    # ─── Internal ────────────────────────────────────────────────────────────

    def _save_message(self, user_id: str, role: str, content: str):
        try:
            msg = ChatHistory(user_id=user_id, role=role, content=content)
            self.db.add(msg)
            self.db.commit()
        except Exception:
            self.db.rollback()

    def _default_context(self) -> dict:
        return {
            "profile": None,
            "user": None,
            "stats": None,
            "food_logs": [],
            "workouts_today": [],
            "workouts_last_3_days": 0,
            "recent_daily_stats": [],
        }

    def _safe_get_user_context(self, user_id: str) -> dict:
        try:
            return self._get_user_context(user_id)
        except Exception:
            return self._default_context()

    def _get_user_context(self, user_id: str) -> dict:
        profile = self.db.query(Profile).filter(Profile.user_id == user_id).first()
        user = self.db.query(User).filter(User.id == user_id).first()
        today = date.today()
        start_of_today = datetime(today.year, today.month, today.day)
        start_of_3_day_window = start_of_today - timedelta(days=2)
        start_of_7_day_window = today - timedelta(days=6)

        stat = (
            self.db.query(DailyStats)
            .filter(DailyStats.user_id == user_id, DailyStats.date == today)
            .first()
        )

        food_logs = (
            self.db.query(FoodLog)
            .filter(
                FoodLog.user_id == user_id,
                FoodLog.logged_at >= start_of_today,
            )
            .all()
        )

        workouts_today = (
            self.db.query(WorkoutLog)
            .filter(
                WorkoutLog.user_id == user_id,
                WorkoutLog.logged_at >= start_of_today,
            )
            .all()
        )

        workouts_last_3_days = (
            self.db.query(WorkoutLog)
            .filter(
                WorkoutLog.user_id == user_id,
                WorkoutLog.logged_at >= start_of_3_day_window,
            )
            .count()
        )

        recent_daily_stats = (
            self.db.query(DailyStats)
            .filter(
                DailyStats.user_id == user_id,
                DailyStats.date >= start_of_7_day_window,
            )
            .order_by(DailyStats.date.desc())
            .all()
        )

        return {
            "profile": profile,
            "user": user,
            "stats": stat,
            "food_logs": food_logs,
            "workouts_today": workouts_today,
            "workouts_last_3_days": workouts_last_3_days,
            "recent_daily_stats": recent_daily_stats,
        }

    def _detect_intent(self, message: str) -> str:
        msg_lower = message.lower()
        for intent, keywords in INTENT_KEYWORDS.items():
            for kw in keywords:
                if kw in msg_lower:
                    return intent
        return "general"

    def _handle_intent(self, intent: str, message: str, context: dict, user_id: str) -> str:
        # Build context from DB if not provided
        if not context:
            context = self._safe_get_user_context(user_id)

        handlers = {
            "greeting": self._greeting,
            "progress": self._progress,
            "water": self._water_advice,
            "protein": self._protein_advice,
            "calories": self._calorie_advice,
            "weight_loss": self._weight_loss_advice,
            "muscle_gain": self._muscle_gain_advice,
            "workout": self._workout_plan,
            "home_workout": self._home_workout_plan,
            "sleep": self._sleep_advice,
            "motivation": self._motivation,
            "bmi": self._bmi_info,
            "cheat": self._cheat_meal_advice,
            "supplement": self._supplement_advice,
            "steps": self._steps_advice,
            "indian_food": self._indian_food_info,
            "exercise_form": self._exercise_form,
        }

        handler = handlers.get(intent, self._general_response)
        return handler(context, message)

    def _format_structured_reply(self, intent: str, base_response: str, context: dict, message: str) -> str:
        response = (base_response or "").strip()
        if not response:
            response = "I am here to help you stay consistent with fitness, food, water, and workouts."

        if "Action now:" in response and "Next check:" in response:
            return response

        action_now, why, next_check = self._build_action_plan(intent, context, message)
        lines = [
            f"Action now: {action_now}",
            f"Why: {why}",
            f"Next check: {next_check}",
            "",
            "Details:",
            response,
        ]

        hydration_nudge = self._build_hydration_nudge(context)
        if hydration_nudge:
            lines.extend(["", f"Hydration nudge: {hydration_nudge}"])

        risk_watch = self._build_risk_watch(context, message)
        if risk_watch:
            lines.append(f"Risk watch: {risk_watch}")

        return "\n".join(lines).strip()

    def _build_action_plan(self, intent: str, context: dict, message: str) -> tuple[str, str, str]:
        profile = context.get("profile")
        stats = context.get("stats")

        steps = int((stats.steps if stats else 0) or 0)
        step_goal = int((profile.daily_step_goal if profile else 8000) or 8000)
        water = int((stats.water_ml if stats else 0) or 0)
        water_goal = int((profile.daily_water_ml_goal if profile else 2500) or 2500)
        calories = int((stats.calories_consumed if stats else 0) or 0)
        calorie_goal = int((profile.daily_calorie_goal if profile else 2000) or 2000)
        protein = int(round((stats.protein_g if stats else 0) or 0))
        protein_goal = int((profile.daily_protein_goal if profile else 120) or 120)

        remaining_water = max(0, water_goal - water)
        remaining_steps = max(0, step_goal - steps)
        remaining_calories = max(0, calorie_goal - calories)
        remaining_protein = max(0, protein_goal - protein)

        if intent == "water":
            if remaining_water == 0:
                return (
                    "Sip 200ml water in the next 2 hours to maintain hydration.",
                    "Even after hitting your goal, spaced hydration keeps energy and focus stable.",
                    "Log your next drink after 2 hours.",
                )
            drink_now = min(400, max(250, int(round(min(remaining_water, 600) / 50) * 50)))
            return (
                f"Drink {drink_now}ml water now.",
                f"You are {remaining_water}ml away from today's hydration target.",
                "Re-check hydration in 90 minutes and log the next intake.",
            )

        if intent == "steps":
            if remaining_steps == 0:
                return (
                    "Do a light 10-minute walk after your next meal.",
                    "Bonus movement improves blood sugar control and recovery.",
                    "Check your step total tonight before bed.",
                )
            return (
                "Take a 20-minute brisk walk now.",
                f"That can cover a large chunk of your remaining {remaining_steps:,} steps.",
                "Open TrackFit again in 60 minutes to see progress.",
            )

        if intent in {"protein", "calories", "weight_loss", "muscle_gain", "indian_food"}:
            if remaining_protein > 0:
                return (
                    f"Add a protein-rich meal/snack with ~{min(35, max(20, remaining_protein))}g protein.",
                    f"You still need about {remaining_protein}g protein to stay on track.",
                    "Check macros after your next meal.",
                )
            if remaining_calories > 0:
                return (
                    "Pick a balanced meal with lean protein and fiber.",
                    f"You still have {remaining_calories} kcal available today.",
                    "Review calories after the next meal entry.",
                )

        message_lower = message.lower()
        if intent == "sleep" or any(k in message_lower for k in ["tired", "fatigue", "sleep", "exhausted"]):
            return (
                "Use a recovery day plan: mobility + easy walk + early bedtime.",
                "Recovery improves consistency and reduces injury risk.",
                "Review energy levels tomorrow morning before intense training.",
            )

        # Default: choose the biggest gap among hydration, steps, and protein.
        ratios = {
            "hydration": (water / water_goal) if water_goal > 0 else 1,
            "steps": (steps / step_goal) if step_goal > 0 else 1,
            "protein": (protein / protein_goal) if protein_goal > 0 else 1,
        }
        weakest = min(ratios, key=ratios.get)

        if weakest == "hydration" and remaining_water > 0:
            drink_now = min(400, max(250, int(round(min(remaining_water, 600) / 50) * 50)))
            return (
                f"Drink {drink_now}ml water now.",
                "Hydration has the biggest gap in today's progress.",
                "Check water progress in 90 minutes.",
            )
        if weakest == "steps" and remaining_steps > 0:
            return (
                "Take a 15-20 minute walk.",
                "Movement is currently the biggest gap toward your daily goals.",
                "Check step progress after your walk.",
            )
        if remaining_protein > 0:
            return (
                "Add one protein-focused meal in your next eating window.",
                "Protein is behind target and affects recovery.",
                "Review protein intake after next meal log.",
            )

        return (
            "Keep your current routine and log the next meal or workout.",
            "Your core metrics are mostly on track today.",
            "Check back in 2-3 hours for the next adjustment.",
        )

    def _build_hydration_nudge(self, context: dict) -> Optional[str]:
        profile = context.get("profile")
        stats = context.get("stats")
        water = int((stats.water_ml if stats else 0) or 0)
        goal = int((profile.daily_water_ml_goal if profile else 2500) or 2500)

        hour = datetime.now().hour
        target_ratio = 0.0
        if hour >= 18:
            target_ratio = 0.75
        elif hour >= 12:
            target_ratio = 0.40
        elif hour >= 9:
            target_ratio = 0.25

        if target_ratio == 0.0:
            return None

        expected_by_now = int(goal * target_ratio)
        if water >= expected_by_now:
            return None

        deficit = expected_by_now - water
        drink_now = min(400, max(250, int(round(deficit / 50) * 50)))
        return (
            f"You are {deficit}ml behind the {int(target_ratio * 100)}% hydration checkpoint. "
            f"Drink {drink_now}ml now."
        )

    def _build_risk_watch(self, context: dict, message: str) -> Optional[str]:
        workouts_last_3_days = int(context.get("workouts_last_3_days") or 0)
        if workouts_last_3_days == 0:
            return "No workouts logged in the last 3 days. Do a 15-minute recovery workout today to restart momentum."

        recent_daily_stats = context.get("recent_daily_stats") or []
        if recent_daily_stats:
            last_3_days = recent_daily_stats[:3]
            avg_steps = sum(int((day.steps or 0)) for day in last_3_days) / len(last_3_days)
            if avg_steps < 3000:
                return "3-day average steps are below 3000. Add one fixed 20-minute walk block to your schedule."

        lower_message = message.lower()
        if any(token in lower_message for token in ["tired", "fatigue", "sleep", "exhausted"]):
            return "Recovery signal detected. Prioritize 7-8 hours of sleep and keep tomorrow's session light to moderate."

        return None

    def _fallback_reply(self, message: str, context: dict) -> str:
        action_now, why, next_check = self._build_action_plan("general", context, message)
        lines = [
            f"Action now: {action_now}",
            f"Why: {why}",
            f"Next check: {next_check}",
            "",
            "Details:",
            "I could not use advanced AI for this response, so I switched to TrackFit safe mode.",
            "Keep logging water, steps, meals, and workouts to improve personalization.",
        ]

        hydration_nudge = self._build_hydration_nudge(context)
        if hydration_nudge:
            lines.extend(["", f"Hydration nudge: {hydration_nudge}"])

        risk_watch = self._build_risk_watch(context, message)
        if risk_watch:
            lines.append(f"Risk watch: {risk_watch}")

        return "\n".join(lines)

    # ─── Handlers ────────────────────────────────────────────────────────────

    def _greeting(self, context: dict, message: str = "") -> str:
        name = "friend"
        if context.get("user"):
            name = context["user"].name.split()[0]
        greetings = [
            f"Namaste {name}! How can I help you today? Ask about workouts, nutrition, water, or your daily progress.",
            f"Hey {name}! Ready to crush your fitness goals? What do you need help with?",
            f"Hello {name}! Your TrackFit coach is here. What would you like to know?",
        ]
        return random.choice(greetings)

    def _progress(self, context: dict, message: str = "") -> str:
        profile = context.get("profile")
        stats = context.get("stats")
        workouts = context.get("workouts_today", [])
        food_logs = context.get("food_logs", [])

        steps = stats.steps if stats else 0
        step_goal = profile.daily_step_goal if profile else 8000
        water = stats.water_ml if stats else 0
        water_goal = profile.daily_water_ml_goal if profile else 2500
        calories = stats.calories_consumed if stats else 0
        cal_goal = profile.daily_calorie_goal if profile else 2000
        protein = stats.protein_g if stats else 0
        protein_goal = profile.daily_protein_goal if profile else 150
        workout_count = len(workouts)

        step_pct = round((steps / step_goal) * 100) if step_goal > 0 else 0
        water_pct = round((water / water_goal) * 100) if water_goal > 0 else 0
        cal_pct = round((calories / cal_goal) * 100) if cal_goal > 0 else 0
        protein_pct = round((protein / protein_goal) * 100) if protein_goal > 0 else 0

        lines = ["Here's your summary for today:"]
        lines.append(f"  Steps: {steps:,}/{step_goal:,} ({step_pct}%)")
        lines.append(f"  Water: {water}/{water_goal}ml ({water_pct}%)")
        lines.append(f"  Calories: {calories}/{cal_goal} kcal ({cal_pct}%)")
        lines.append(f"  Protein: {round(protein)}/{protein_goal}g ({protein_pct}%)")
        lines.append(f"  Workouts: {workout_count} sessions")

        # Personalized tips
        if steps < step_goal * 0.6:
            lines.append("Tip: A 15-min walk adds ~2000 steps. Try after dinner!")
        if water < water_goal * 0.5:
            lines.append("Drink a glass of water now — you're behind on hydration.")
        if calories < cal_goal * 0.5 and cal_pct > 0:
            lines.append("You still have calories left for a healthy meal or snack.")
        if protein < protein_goal * 0.5:
            lines.append("Boost protein: have paneer, dal, or eggs next meal.")

        return "\n".join(lines)

    def _water_advice(self, context: dict, message: str = "") -> str:
        profile = context.get("profile")
        stats = context.get("stats")
        water = stats.water_ml if stats else 0
        goal = profile.daily_water_ml_goal if profile else 2500
        remaining = max(0, goal - water)

        if remaining <= 0:
            return "Great job! You've reached your water goal. Stay hydrated!"

        return (
            f"You've had {water}ml today. You need {remaining}ml more to hit your {goal}ml goal.\n"
            "Indian options that count: Chaas (25 kcal/250ml), Nimbu Pani, Coconut Water, or plain water.\n"
            f"At your current pace, try drinking {round(remaining/4)}ml every 2 hours."
        )

    def _protein_advice(self, context: dict, message: str = "") -> str:
        profile = context.get("profile")
        stats = context.get("stats")
        eaten = round(stats.protein_g) if stats else 0
        goal = profile.daily_protein_goal if profile else 150
        weight = profile.weight_kg if profile else 70

        if eaten >= goal:
            return "Excellent! You've hit your protein goal. Keep it up!"

        needed = goal - eaten
        return (
            f"You've had {eaten}g protein today. You need about {needed}g more.\n"
            f"For your weight ({weight}kg), target {round(weight*1.6)}-{round(weight*2.2)}g/day.\n"
            "Top Indian sources:\n"
            "  Paneer: 18g per 100g\n"
            "  Chicken breast: 31g per 100g\n"
            "  Dal (cooked): 9g per cup\n"
            "  Eggs: 6g each\n"
            "  Soy chunks: 52g per 100g (dried)\n"
            "  Greek yogurt: 10g per 100g"
        )

    def _calorie_advice(self, context: dict, message: str = "") -> str:
        profile = context.get("profile")
        stats = context.get("stats")
        eaten = stats.calories_consumed if stats else 0
        goal = profile.daily_calorie_goal if profile else 2000
        remaining = max(0, goal - eaten)

        return (
            f"You've consumed {eaten} kcal today. You have {remaining} kcal remaining.\n"
            "For a balanced Indian meal: 1 roti (120 kcal) + 1 cup dal (116 kcal) + sabzi (100 kcal) + curd (60 kcal) = ~400 kcal.\n"
            "Avoid fried snacks like samosa (260 kcal each) and pakora (200 kcal per serving)."
        )

    def _weight_loss_advice(self, context: dict, message: str = "") -> str:
        profile = context.get("profile")
        weight = profile.weight_kg if profile else 70
        cal_goal = profile.daily_calorie_goal if profile else 1600

        return (
            "For sustainable fat loss:\n"
            f"  Create a 300-500 kcal daily deficit (your goal: {cal_goal} kcal/day)\n"
            f"  Eat {round(weight*1.6)}-{round(weight*2.2)}g protein per day\n"
            "  Strength train 3x/week + walk 8,000+ steps/day\n"
            "  Avoid fried foods, maida, sugary drinks\n"
            "  Best Indian choices: dal, sabzi, roti (portion control), chaas, salad\n"
            "  Aim to lose 0.5-1% body weight per week\n"
            "  Track everything — what gets measured gets managed"
        )

    def _muscle_gain_advice(self, context: dict, message: str = "") -> str:
        profile = context.get("profile")
        weight = profile.weight_kg if profile else 70
        cal_goal = profile.daily_calorie_goal if profile else 2400

        return (
            "For muscle building:\n"
            f"  Eat 200-400 kcal above maintenance (your goal: {cal_goal} kcal/day)\n"
            f"  Protein: {round(weight*1.6)}-{round(weight*2.2)}g per day\n"
            "  Progressive overload: increase weight or reps each week\n"
            "  Sleep 7-9 hours for recovery\n"
            "  Best Indian protein sources: paneer, chicken, eggs, dal, rajma, curd\n"
            "  Post-workout: whey shake or 200g paneer bhurji\n"
            "  Aim to gain 0.25-0.5 kg per week"
        )

    def _workout_plan(self, context: dict, message: str = "") -> str:
        profile = context.get("profile")
        goal = profile.goal if profile else "stay_fit"
        msg_lower = message.lower()

        if "full body" in msg_lower:
            return self._full_body_workout(goal)
        elif "upper" in msg_lower:
            return self._upper_body_workout()
        elif "lower" in msg_lower:
            return self._lower_body_workout()
        elif "cardio" in msg_lower:
            return (
                "Cardio options (30 min each, 3-4x/week):\n"
                "  Brisk walking: ~200 kcal\n"
                "  Jogging: ~350 kcal\n"
                "  Cycling: ~300 kcal\n"
                "  Swimming: ~400 kcal\n"
                "  HIIT (20 min): ~350 kcal\n"
                "  Surya Namaskar (12 rounds): ~250 kcal"
            )
        else:
            if goal == "lose_weight":
                return (
                    "Fat loss plan (4x/week):\n"
                    "  Day 1: Full body strength (squats, push-ups, rows, planks)\n"
                    "  Day 2: Cardio (30 min brisk walk or run)\n"
                    "  Day 3: Full body strength\n"
                    "  Day 4: Cardio + 10 min HIIT\n"
                    "  Daily: 8,000+ steps, slight calorie deficit\n"
                    "Want a full body or upper/lower split?"
                )
            elif goal == "build_muscle":
                return (
                    "Muscle building plan (4x/week):\n"
                    "  Day 1: Upper (bench, rows, OHP, pull-ups)\n"
                    "  Day 2: Lower (squat, deadlift, lunges, calves)\n"
                    "  Day 3: Rest\n"
                    "  Day 4: Upper\n"
                    "  Day 5: Lower\n"
                    "  Progressive overload each week. Eat in surplus."
                )
            else:
                return (
                    "Balanced plan (3-4x/week):\n"
                    "  3x full body strength (squats, push-ups, rows, core)\n"
                    "  2x cardio (walk, run, cycle)\n"
                    "  Daily: 8,000+ steps\n"
                    "  Flexibility: yoga or stretching 2x/week"
                )

    def _home_workout_plan(self, context: dict, message: str = "") -> str:
        return (
            "Home workout (no equipment, ~45 min):\n"
            "  Warm-up: 5 min jumping jacks + arm circles\n"
            "  Surya Namaskar: 12 rounds\n"
            "  Circuit (3 rounds, 30 sec rest between exercises):\n"
            "    Push-ups: 15 reps\n"
            "    Bodyweight squats: 20 reps\n"
            "    Lunges: 12 each leg\n"
            "    Burpees: 10 reps\n"
            "    Plank: 45 sec\n"
            "    Mountain climbers: 30 sec\n"
            "  Cool-down: 5 min stretching\n"
            "  Burns ~300-400 kcal. Do 4x/week."
        )

    def _sleep_advice(self, context: dict, message: str = "") -> str:
        return (
            "Sleep is crucial for recovery. Aim for 7-9 hours nightly.\n"
            "Tips:\n"
            "  No screens 1 hour before bed\n"
            "  Keep room cool and dark\n"
            "  Warm haldi doodh (turmeric milk) aids sleep and recovery\n"
            "  Consistent sleep schedule — even on weekends\n"
            "  No caffeine after 2 PM\n"
            "  Light dinner 2-3 hours before sleep"
        )

    def _motivation(self, context: dict, message: str = "") -> str:
        stats = context.get("stats")
        steps = stats.steps if stats else 0
        name = "friend"
        if context.get("user"):
            name = context["user"].name.split()[0]

        quotes = [
            f"{name}, every champion was once a beginner who refused to give up. You've taken {steps:,} steps today — that's progress!",
            "Consistency beats intensity. A 10-minute walk beats a skipped workout every time.",
            "The pain you feel today is the strength you'll feel tomorrow. Keep pushing!",
            f"You're building a lifestyle, {name}, not chasing a quick fix. One day at a time.",
            "Ek kadam aur — one more step. You've got this!",
            "Your body is a temple. Nourish it with good food and movement.",
            "The only bad workout is the one that didn't happen.",
        ]
        return random.choice(quotes)

    def _bmi_info(self, context: dict, message: str = "") -> str:
        profile = context.get("profile")
        weight = profile.weight_kg if profile else None
        height = profile.height_cm if profile else None

        if weight and height:
            height_m = height / 100
            bmi = round(weight / (height_m ** 2), 1)
            category = "underweight" if bmi < 18.5 else "normal" if bmi < 25 else "overweight" if bmi < 30 else "obese"
            return (
                f"Your BMI: {bmi} ({category}).\n"
                f"Weight: {weight} kg, Height: {height} cm.\n"
                "BMI is a rough guide — muscle mass and body composition matter more.\n"
                "Focus on how you feel, perform, and look rather than just the number."
            )
        return "Update your profile with height and weight to get BMI insights!"

    def _cheat_meal_advice(self, context: dict, message: str = "") -> str:
        return (
            "Cheat meals are fine once a week — they help with adherence!\n"
            "Tips to minimize damage:\n"
            "  Have a protein-rich meal before to reduce overeating\n"
            "  Choose one indulgence, not everything\n"
            "  Go for a walk after the meal\n"
            "  Get back on track the next meal — don't let one cheat become a cheat week\n"
            "Pizza slice: ~280 kcal. Samosa: ~260 kcal. Balance with lighter meals around it."
        )

    def _supplement_advice(self, context: dict, message: str = "") -> str:
        return (
            "Supplement basics:\n"
            "  Creatine monohydrate (5g/day) — safe, effective for strength\n"
            "  Whey protein — convenient way to hit protein goals\n"
            "  Vitamin D3 — many Indians are deficient; 1000-2000 IU/day\n"
            "  Omega-3 (fish oil) — anti-inflammatory, heart health\n"
            "  Iron — especially for vegetarian women\n"
            "Always consult a doctor before starting supplements.\n"
            "Whole food first — supplements only fill gaps."
        )

    def _steps_advice(self, context: dict, message: str = "") -> str:
        profile = context.get("profile")
        stats = context.get("stats")
        steps = stats.steps if stats else 0
        goal = profile.daily_step_goal if profile else 8000
        remaining = max(0, goal - steps)

        if steps >= goal:
            return (
                f"You've hit your step goal with {steps:,} steps — well done!\n"
                "Walking burns ~50-70 kcal per 1000 steps.\n"
                "Keep moving for bonus health benefits!"
            )
        return (
            f"You've taken {steps:,} steps. You need {remaining:,} more to hit {goal:,}.\n"
            "A 20-min brisk walk adds ~2000-2500 steps.\n"
            "Try a post-dinner walk — it also helps digestion!\n"
            "Park further away, take stairs, or pace while on calls."
        )

    def _indian_food_info(self, context: dict, message: str = "") -> str:
        msg_lower = message.lower()

        # Check message against food DB
        for key, item in FOOD_DB.items():
            name_lower = item.get("name", "").lower()
            aliases = [a.lower() for a in item.get("common_aliases", [])]

            if key in msg_lower or name_lower in msg_lower or any(a in msg_lower for a in aliases):
                calories = item.get("calories", "N/A")
                protein = item.get("protein_g", "N/A")
                carbs = item.get("carbs_g", "N/A")
                fat = item.get("fats_g", "N/A")
                fiber = item.get("fiber_g", "N/A")
                portion = item.get("typical_portion_g", 100)
                is_veg = item.get("is_veg", True)

                tip = self._food_tip(key)
                veg_label = "Veg" if is_veg else "Non-Veg"

                return (
                    f"{item['name']} ({veg_label}):\n"
                    f"  Calories: {calories} kcal per {portion}g\n"
                    f"  Protein: {protein}g\n"
                    f"  Carbs: {carbs}g\n"
                    f"  Fat: {fat}g\n"
                    f"  Fiber: {fiber}g\n"
                    f"  Tip: {tip}"
                )

        return (
            "I have nutrition info for 4500+ Indian and global foods. "
            "Try asking about specific foods like 'paneer', 'dal', 'roti', 'biryani', 'idli', etc."
        )

    def _food_tip(self, food_key: str) -> str:
        tips = {
            "paneer": "Great for muscle building. Opt for grilled paneer tikka or bhurji instead of deep-fried paneer pakora.",
            "dal": "Rich in fiber and plant protein. Pair with rice for complete amino acids. Moong dal is easiest to digest.",
            "roti": "Whole wheat roti is a healthy complex carb. Limit butter/ghee to 1 tsp per roti.",
            "biryani": "Often high in calories from ghee and rice. Enjoy as a treat, add raita for probiotics.",
            "samosa": "High in refined carbs and fat (~260 kcal each). Fine as an occasional snack.",
            "dosa": "Fermented batter is good for gut health. Plain dosa is healthier than masala dosa.",
            "idli": "Steamed and low fat — one of the healthiest Indian breakfasts. Pair with sambar for protein.",
            "chole": "Chickpeas are high in protein (9g/cup) and fiber. Avoid excess oil in preparation.",
            "rajma": "Kidney beans are excellent protein + fiber. Best paired with brown rice.",
            "paratha": "Can be high calorie with ghee. Use less oil and stuff with paneer or dal for protein.",
            "poha": "Light and easy to digest. Add peanuts and vegetables for a balanced meal.",
            "upma": "Moderate GI. Add vegetables and nuts for fiber and protein.",
            "curd": "Probiotic benefits. Raita with meals aids digestion. Choose plain curd over sweetened.",
            "ghee": "900 kcal per 100g. Use sparingly — 1 tsp (5g) = 45 kcal. Good for high-heat cooking.",
            "mango": "60 kcal per 100g. High in sugar — limit to 1 small mango/day. Great source of vitamin A.",
            "banana": "89 kcal per 100g. Excellent pre-workout energy. Contains potassium for muscle function.",
        }
        return tips.get(food_key, "Enjoy in moderation as part of a balanced diet.")

    def _exercise_form(self, context: dict, message: str = "") -> str:
        msg_lower = message.lower()

        if "squat" in msg_lower:
            return (
                "Squat form:\n"
                "  Feet shoulder-width, toes slightly out\n"
                "  Chest up, back straight, core braced\n"
                "  Sit back as if into a chair, knees over ankles\n"
                "  Go to 90° or parallel, drive through heels\n"
                "  Start: 3x12 bodyweight squats\n"
                "  Common mistake: knees caving inward — push them out"
            )
        elif "push" in msg_lower:
            return (
                "Push-up form:\n"
                "  Hands slightly wider than shoulders\n"
                "  Body straight from head to heels (tight core)\n"
                "  Lower chest until elbows at 45° angle\n"
                "  Push up explosively, fully extend arms\n"
                "  Beginners: start on knees. Progress: 3x10, then 3x15, then full push-ups\n"
                "  Common mistake: sagging hips — squeeze glutes"
            )
        elif "pull" in msg_lower:
            return (
                "Pull-up form:\n"
                "  Grip slightly wider than shoulders, overhand\n"
                "  Engage core, avoid swinging\n"
                "  Pull until chin over bar, lower slowly (3 sec)\n"
                "  Can't do one? Use resistance bands or do negatives\n"
                "  Progress: 3x3, then 3x5, then 3x8"
            )
        elif "lunge" in msg_lower:
            return (
                "Lunge form:\n"
                "  Step forward, lower back knee toward floor\n"
                "  Front knee stays over ankle (don't push past toes)\n"
                "  Torso upright, core engaged\n"
                "  Push through front heel to return\n"
                "  Progress: 3x12 each leg, add dumbbells when ready"
            )
        elif "plank" in msg_lower:
            return (
                "Plank form:\n"
                "  Forearms on floor, elbows under shoulders\n"
                "  Body straight — no sagging or piking\n"
                "  Squeeze glutes and core, breathe steadily\n"
                "  Progress: 30s → 45s → 60s → 90s\n"
                "  Side plank: targets obliques"
            )
        elif "burpee" in msg_lower:
            return (
                "Burpee form:\n"
                "  Stand → squat down → hands on floor\n"
                "  Jump feet back to plank → push-up (optional)\n"
                "  Jump feet forward → explosive jump up\n"
                "  Land softly, immediately go into next rep\n"
                "  Start: 3x8. Burns ~10 kcal/min — great for fat loss"
            )
        else:
            return (
                "I can help with form for: squats, push-ups, pull-ups, lunges, planks, burpees.\n"
                "Just ask 'How to do a squat?' or 'Push-up form'"
            )

    # ─── Workout Templates ──────────────────────────────────────────────────

    def _full_body_workout(self, goal: str) -> str:
        return (
            "Full body workout (3x/week, ~50 min):\n"
            "  Barbell squat: 4x8-12\n"
            "  Bench press: 4x8-12\n"
            "  Bent-over row: 4x8-12\n"
            "  Overhead press: 3x10\n"
            "  Romanian deadlift: 3x10\n"
            "  Plank: 3x60 sec\n"
            "  Rest 90 sec between sets.\n"
            "  Warm-up: 5 min light cardio + dynamic stretches"
        )

    def _upper_body_workout(self) -> str:
        return (
            "Upper body workout (2x/week, ~45 min):\n"
            "  Bench press: 4x8-12\n"
            "  Bent-over row: 4x10\n"
            "  Overhead press: 3x10\n"
            "  Pull-ups (or lat pulldown): 3xmax\n"
            "  Bicep curls: 3x12\n"
            "  Tricep dips: 3x12\n"
            "  Face pulls: 3x15\n"
            "  Rest 60-90 sec between sets"
        )

    def _lower_body_workout(self) -> str:
        return (
            "Lower body workout (2x/week, ~45 min):\n"
            "  Barbell squat: 4x8-12\n"
            "  Romanian deadlift: 4x10\n"
            "  Leg press: 3x12-15\n"
            "  Walking lunges: 3x12 each leg\n"
            "  Leg curls: 3x12\n"
            "  Calf raises: 4x15\n"
            "  Rest 90 sec between sets"
        )

    def _general_response(self, context: dict, message: str = "") -> str:
        name = "friend"
        if context.get("user"):
            name = context["user"].name.split()[0]

        return (
            f"Hi {name}! I'm your TrackFit coach. I can help with:\n"
            "  Daily progress & stats\n"
            "  Calorie & macro advice\n"
            "  Indian food nutrition info (4500+ foods)\n"
            "  Workout suggestions (home & gym)\n"
            "  Exercise form tips\n"
            "  Water intake & protein tips\n"
            "  Meal ideas (breakfast, lunch, dinner, snacks)\n"
            "  Sleep, supplements & motivation\n"
            "Just ask me anything!"
        )

    # ─── Optional LLM ───────────────────────────────────────────────────────

    async def _generate_gemini_response(self, message: str, context: dict) -> Optional[str]:
        """Generate a reply using Gemini 1.5 Flash via async HTTP (non-blocking)."""

        # 1. Try local CoachLLM transformer first (if loaded)
        if _local_llm and _local_tokenizer:
            try:
                import torch
                profile = context.get("profile")
                stats = context.get("stats")
                prompt = (
                    f"User profile: goal={profile.goal if profile else 'general'}, "
                    f"weight={profile.weight_kg if profile else 'unknown'}kg\n"
                    f"Today: calories={stats.calories_consumed if stats else 0}, "
                    f"water={stats.water_ml if stats else 0}ml, "
                    f"steps={stats.steps if stats else 0}\n"
                    f"User asks: {message}\n"
                    f"Coach responds:"
                )
                tokens = _local_tokenizer.encode(prompt)
                idx = torch.tensor([tokens], dtype=torch.long, device=_local_device)
                with torch.no_grad():
                    output = _local_llm.generate(
                        idx, max_new_tokens=100, temperature=0.7, top_k=40
                    )
                text = _local_tokenizer.decode(output[0].tolist())
                if "coach responds:" in text.lower():
                    local_reply = text.lower().split("coach responds:")[-1].strip()
                    if len(local_reply) > 10:
                        return local_reply
            except Exception:
                pass

        # 2. Gemini 1.5 Flash via REST (async, non-blocking)
        if not settings.GEMINI_API_KEY:
            return None

        try:
            import httpx
            profile = context.get("profile")
            stats = context.get("stats")

            system_text = (
                "You are TrackFit AI Coach — a friendly, concise fitness and nutrition assistant "
                "specializing in Indian food and healthy lifestyle.\n"
                f"User goal: {profile.goal if profile else 'general fitness'}\n"
                f"Weight: {profile.weight_kg if profile else 'unknown'} kg\n"
                f"Today — Calories consumed: {stats.calories_consumed if stats else 0}, "
                f"Water: {stats.water_ml if stats else 0} ml, "
                f"Steps: {stats.steps if stats else 0}\n"
                "Reply in under 150 words. Use bullet points. "
                "Reference Indian foods (dal, roti, paneer, etc.) where relevant. "
                "Always end with one actionable tip."
            )

            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
            )
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": f"{system_text}\n\nUser: {message}"}
                        ]
                    }
                ],
                "generationConfig": {
                    "maxOutputTokens": 300,
                    "temperature": 0.7,
                },
                "safetySettings": [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                ],
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)

            if resp.status_code != 200:
                return None

            data = resp.json()
            candidates = data.get("candidates") or []
            if not candidates:
                return None

            parts = candidates[0].get("content", {}).get("parts") or []
            if not parts:
                return None

            text = parts[0].get("text", "").strip()
            return text if len(text) > 5 else None

        except Exception:
            return None

    # Keep old name as alias so any external callers aren't broken
    def _generate_llm_response(self, message: str, context: dict) -> Optional[str]:
        """Deprecated: use _generate_gemini_response (async). Kept for backward compat."""
        return None

