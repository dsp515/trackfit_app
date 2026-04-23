import uuid
from datetime import date, datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String

from app.core.database import Base
from app.models.user import GUID


class StepLog(Base):
    __tablename__ = "step_logs"

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False)
    date = Column(Date, default=date.today, nullable=False)
    steps = Column(Integer, default=0)
    distance_m = Column(Integer, default=0)  # meters
    calories_burned = Column(Integer, default=0)
    active_minutes = Column(Integer, default=0)
    source = Column(String, default="device")  # device, google_fit, apple_health
    synced_at = Column(DateTime, default=datetime.utcnow)
