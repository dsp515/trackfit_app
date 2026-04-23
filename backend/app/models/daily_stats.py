import uuid
from datetime import date, datetime

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer

from app.core.database import Base
from app.models.user import GUID


class DailyStats(Base):
    __tablename__ = "daily_stats"

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False)
    date = Column(Date, default=date.today, nullable=False)
    calories_consumed = Column(Integer, default=0)
    calories_burned = Column(Integer, default=0)
    protein_g = Column(Float, default=0)
    carbs_g = Column(Float, default=0)
    fat_g = Column(Float, default=0)
    water_ml = Column(Integer, default=0)
    steps = Column(Integer, default=0)
    workouts_count = Column(Integer, default=0)
    daily_score = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
