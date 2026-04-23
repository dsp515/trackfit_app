import json
import os
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.models.workout_log import WorkoutLog
from app.models.daily_stats import DailyStats
from app.schemas.workout import WorkoutLogCreate


class WorkoutService:
    def __init__(self, db: Session):
        self.db = db
        self.exercise_db: dict = {}
        db_path = os.path.join(os.path.dirname(__file__), "..", "db", "exercise_db.json")
        try:
            with open(db_path) as f:
                self.exercise_db = json.load(f)
        except FileNotFoundError:
            pass

    def search_exercises(self, query: str, limit: int = 20) -> list[dict]:
        query_lower = query.lower()
        results = []
        for key, item in self.exercise_db.items():
            name = item.get("name", "").lower()
            if query_lower in name or query_lower in key:
                results.append({
                    "exercise_key": key,
                    "name": item["name"],
                    "type": item["type"],
                    "calories_per_min": item["calories_per_min"],
                    "muscle_groups": item.get("muscle_groups", []),
                    "equipment": item.get("equipment", "none"),
                    "difficulty": item.get("difficulty", "beginner"),
                })
                if len(results) >= limit:
                    break
        return results

    def log_workout(self, user_id: str, data: WorkoutLogCreate) -> WorkoutLog:
        # If calories_burned not provided, estimate from DB
        calories_burned = data.calories_burned
        if calories_burned == 0 and data.exercise_name.lower().replace(" ", "_") in self.exercise_db:
            ex = self.exercise_db[data.exercise_name.lower().replace(" ", "_")]
            calories_burned = int(ex["calories_per_min"] * data.duration_minutes)

        log = WorkoutLog(
            user_id=user_id,
            exercise_name=data.exercise_name,
            exercise_type=data.exercise_type,
            duration_minutes=data.duration_minutes,
            calories_burned=calories_burned,
            sets=data.sets,
            reps=data.reps,
            weight_kg=data.weight_kg,
            distance_km=data.distance_km,
            notes=data.notes,
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        self._update_daily_stats(user_id)
        return log

    def get_today_workouts(self, user_id: str) -> list[WorkoutLog]:
        today = date.today()
        return (
            self.db.query(WorkoutLog)
            .filter(
                WorkoutLog.user_id == user_id,
                WorkoutLog.logged_at >= datetime(today.year, today.month, today.day),
            )
            .order_by(WorkoutLog.logged_at.desc())
            .all()
        )

    def get_workout_history(self, user_id: str, limit: int = 30) -> list[WorkoutLog]:
        return (
            self.db.query(WorkoutLog)
            .filter(WorkoutLog.user_id == user_id)
            .order_by(WorkoutLog.logged_at.desc())
            .limit(limit)
            .all()
        )

    def _update_daily_stats(self, user_id: str):
        today = date.today()
        workouts = self.get_today_workouts(user_id)
        stat = (
            self.db.query(DailyStats)
            .filter(DailyStats.user_id == user_id, DailyStats.date == today)
            .first()
        )
        if not stat:
            stat = DailyStats(user_id=user_id, date=today)
            self.db.add(stat)

        stat.calories_burned = sum(w.calories_burned for w in workouts)
        stat.workouts_count = len(workouts)
        self.db.commit()
