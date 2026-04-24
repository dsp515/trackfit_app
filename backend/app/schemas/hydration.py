from datetime import date as date_type, datetime

from pydantic import BaseModel, PositiveInt


class HydrationLogCreate(BaseModel):
    amount_ml: PositiveInt
    date: date_type | None = None


class HydrationLogOut(BaseModel):
    id: str
    user_id: str
    amount_ml: int
    logged_at: datetime

    class Config:
        from_attributes = True


class TodayHydrationSummary(BaseModel):
    total_ml: int = 0
    goal_ml: int = 2500
    percentage: float = 0
    logs: list[HydrationLogOut] = []
