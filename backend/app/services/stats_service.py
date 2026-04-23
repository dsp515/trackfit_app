from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.daily_stats import DailyStats
from app.models.profile import Profile
from app.schemas.stats import DailyScoreBreakdown, WeeklyStats


class StatsService:
    def __init__(self, db: Session):
        self.db = db

    def calculate_daily_score(self, user_id: str, target_date: date | None = None) -> DailyScoreBreakdown:
        if target_date is None:
            target_date = date.today()

        stat = (
            self.db.query(DailyStats)
            .filter(DailyStats.user_id == user_id, DailyStats.date == target_date)
            .first()
        )
        profile = self.db.query(Profile).filter(Profile.user_id == user_id).first()

        cal_goal = profile.daily_calorie_goal if profile else 2000
        protein_goal = profile.daily_protein_goal if profile else 120
        water_goal = profile.daily_water_ml_goal if profile else 2500
        step_goal = profile.daily_step_goal if profile else 8000

        calories = stat.calories_consumed if stat else 0
        protein = stat.protein_g if stat else 0
        water = stat.water_ml if stat else 0
        steps = stat.steps if stat else 0
        workouts = stat.workouts_count if stat else 0
        cal_burned = stat.calories_burned if stat else 0

        # Nutrition score (0-30)
        cal_pct = min(calories / cal_goal, 1.0) if cal_goal > 0 else 0
        nutrition_score = 0
        if cal_pct >= 0.7:
            nutrition_score = 25
        elif cal_pct >= 0.5:
            nutrition_score = 15
        elif cal_pct > 0:
            nutrition_score = 5
        if protein >= protein_goal:
            nutrition_score = min(30, nutrition_score + 5)

        # Hydration score (0-25)
        water_pct = min(water / water_goal, 1.0) if water_goal > 0 else 0
        hydration_score = round(water_pct * 25)

        # Activity score (0-25)
        step_pct = min(steps / step_goal, 1.0) if step_goal > 0 else 0
        activity_score = round(step_pct * 25)

        # Workout score (0-20)
        workout_score = min(workouts * 10, 20)

        # Streak bonus (0-10)
        streak = self._get_streak(user_id)
        streak_bonus = min(streak * 2, 10)

        total = min(nutrition_score + hydration_score + activity_score + workout_score + streak_bonus, 100)

        # Generate tips
        tips = []
        if cal_pct < 0.5:
            tips.append("You're eating below 50% of your calorie goal — make sure you're fueling your body properly.")
        if water_pct < 0.5:
            tips.append("Drink more water! You're below 50% of your daily goal.")
        if step_pct < 0.5:
            tips.append("Try to get more steps in — even a short walk helps!")
        if workouts == 0:
            tips.append("No workouts logged today. Even a 15-minute session counts!")
        if streak >= 7:
            tips.append(f"Amazing! You're on a {streak}-day streak. Keep it up!")
        if not tips:
            tips.append("You're doing great! Keep up the consistency.")

        # Save score to daily stats
        if stat:
            stat.daily_score = total
            self.db.commit()

        return DailyScoreBreakdown(
            total_score=total,
            nutrition_score=nutrition_score,
            hydration_score=hydration_score,
            activity_score=activity_score,
            workout_score=workout_score,
            streak_bonus=streak_bonus,
            tips=tips,
        )

    def get_weekly_stats(self, user_id: str) -> WeeklyStats:
        end_date = date.today()
        start_date = end_date - timedelta(days=6)

        stats = (
            self.db.query(DailyStats)
            .filter(
                DailyStats.user_id == user_id,
                DailyStats.date >= start_date,
                DailyStats.date <= end_date,
            )
            .all()
        )

        if not stats:
            return WeeklyStats(
                avg_calories=0, avg_protein=0, avg_steps=0,
                avg_water_ml=0, total_workouts=0, best_day=None, streak_days=0,
            )

        days = len(stats)
        avg_cal = sum(s.calories_consumed for s in stats) / days
        avg_prot = sum(s.protein_g for s in stats) / days
        avg_steps = sum(s.steps for s in stats) / days
        avg_water = sum(s.water_ml for s in stats) / days
        total_workouts = sum(s.workouts_count for s in stats)

        best = max(stats, key=lambda s: s.daily_score)
        best_day = best.date.isoformat()

        streak = self._get_streak(user_id)

        return WeeklyStats(
            avg_calories=round(avg_cal),
            avg_protein=round(avg_prot, 1),
            avg_steps=round(avg_steps),
            avg_water_ml=round(avg_water),
            total_workouts=total_workouts,
            best_day=best_day,
            streak_days=streak,
        )

    def get_daily_stats(self, user_id: str) -> list[DailyStats]:
        return (
            self.db.query(DailyStats)
            .filter(DailyStats.user_id == user_id)
            .order_by(DailyStats.date.desc())
            .limit(30)
            .all()
        )

    def _get_streak(self, user_id: str) -> int:
        streak = 0
        current = date.today()
        while True:
            stat = (
                self.db.query(DailyStats)
                .filter(DailyStats.user_id == user_id, DailyStats.date == current)
                .first()
            )
            if stat and stat.daily_score > 0:
                streak += 1
                current -= timedelta(days=1)
            else:
                break
        return streak
