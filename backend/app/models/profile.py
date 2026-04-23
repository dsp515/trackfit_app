from sqlalchemy import Column, Float, ForeignKey, Integer, String

from app.core.database import Base
from app.models.user import GUID


class Profile(Base):
    __tablename__ = "profiles"

    user_id = Column(GUID(), ForeignKey("users.id"), primary_key=True)
    goal = Column(String, nullable=False)  # lose_weight, build_muscle, stay_fit
    age = Column(Integer)
    gender = Column(String)
    height_cm = Column(Integer)
    weight_kg = Column(Float)
    activity_level = Column(String)  # sedentary, light, moderate, active, very_active
    preferred_cuisine = Column(String, default="indian")
    daily_calorie_goal = Column(Integer, default=2000)
    daily_protein_goal = Column(Integer, default=120)
    daily_carbs_goal = Column(Integer, default=250)
    daily_fat_goal = Column(Integer, default=65)
    daily_water_ml_goal = Column(Integer, default=2500)
    daily_step_goal = Column(Integer, default=8000)
