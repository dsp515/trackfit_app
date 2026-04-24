import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text

from app.core.database import Base
from app.models.user import GUID


class WorkoutLog(Base):
    __tablename__ = "workout_logs"

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False)
    exercise_name = Column(String, nullable=False)
    exercise_type = Column(String, nullable=False)  # cardio, strength, flexibility, sports
    duration_minutes = Column(Integer, nullable=False)
    calories_burned = Column(Integer, default=0)
    sets = Column(Integer, default=0)
    reps = Column(Integer, default=0)
    weight_kg = Column(Float, default=0)
    distance_km = Column(Float, default=0)
    notes = Column(String, default="")
    sets_data = Column(Text, default="")  # JSON array: [{"set": 1, "reps": 12, "weight": 40}, ...]
    form_score = Column(Integer, default=0)  # 0-100 from rep counter
    logged_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
