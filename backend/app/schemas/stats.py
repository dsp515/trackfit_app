from datetime import date, datetime

from pydantic import BaseModel


class DailyStatsOut(BaseModel):
    id: str
    user_id: str
    date: date
    calories_consumed: int
    calories_burned: int
    protein_g: float
    carbs_g: float
    fat_g: float
    water_ml: int
    steps: int
    workouts_count: int
    daily_score: int

    class Config:
        from_attributes = True


class DailyScoreBreakdown(BaseModel):
    total_score: int
    nutrition_score: int
    hydration_score: int
    activity_score: int
    workout_score: int
    streak_bonus: int
    tips: list[str]


class WeeklyStats(BaseModel):
    avg_calories: float
    avg_protein: float
    avg_steps: float
    avg_water_ml: float
    total_workouts: int
    best_day: str | None
    streak_days: int
