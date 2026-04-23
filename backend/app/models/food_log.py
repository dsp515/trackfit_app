import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String

from app.core.database import Base
from app.models.user import GUID


class FoodLog(Base):
    __tablename__ = "food_logs"

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    calories = Column(Integer, nullable=False)
    protein = Column(Float, default=0)
    carbs = Column(Float, default=0)
    fat = Column(Float, default=0)
    fiber = Column(Float, default=0)
    sugar = Column(Float, default=0)
    sodium = Column(Integer, default=0)
    amount_g = Column(Integer, nullable=False)
    meal_type = Column(String, nullable=False)  # breakfast, lunch, dinner, snacks
    logged_at = Column(DateTime, default=datetime.utcnow)
