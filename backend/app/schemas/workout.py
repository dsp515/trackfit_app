from datetime import datetime

from pydantic import BaseModel


class WorkoutLogCreate(BaseModel):
    exercise_name: str
    exercise_type: str = "strength"  # cardio, strength, flexibility, sports
    duration_minutes: int
    calories_burned: int = 0
    sets: int = 0
    reps: int = 0
    weight_kg: float = 0
    distance_km: float = 0
    notes: str = ""
    sets_data: str = ""  # JSON: [{"set": 1, "reps": 12, "weight": 40}, ...]
    form_score: int = 0


class WorkoutLogOut(BaseModel):
    id: str
    user_id: str
    exercise_name: str
    exercise_type: str
    duration_minutes: int
    calories_burned: int
    sets: int
    reps: int
    weight_kg: float
    distance_km: float
    notes: str
    sets_data: str
    form_score: int
    logged_at: datetime

    class Config:
        from_attributes = True


class ExerciseSearchResult(BaseModel):
    exercise_key: str
    name: str
    type: str
    calories_per_min: float
    muscle_groups: list[str]
    equipment: str
    difficulty: str


class RepLogRequest(BaseModel):
    exercise_name: str
    exercise_type: str = "strength"
    total_reps: int
    sets_data: str = ""  # JSON array of set details
    duration_seconds: int = 0
    form_score: int = 0
    calories_burned: int = 0
