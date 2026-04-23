import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer

from app.core.database import Base
from app.models.user import GUID


class HydrationLog(Base):
    __tablename__ = "hydration_logs"

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False)
    amount_ml = Column(Integer, nullable=False)
    logged_at = Column(DateTime, default=datetime.utcnow)
