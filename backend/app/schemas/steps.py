from datetime import date
from typing import Literal

from pydantic import BaseModel, NonNegativeInt


class StepSyncRequest(BaseModel):
    date: date
    steps: NonNegativeInt
    distance_m: NonNegativeInt = 0
    calories_burned: NonNegativeInt = 0
    active_minutes: NonNegativeInt = 0
    source: Literal[
        "device",
        "google_fit",
        "apple_health",
        "health_connect",
        "hardware",
        "accelerometer",
        "cached",
    ] = "device"


class StepSyncResponse(BaseModel):
    date: str
    steps: int
    distance_km: float
    calories_burned: int
    active_minutes: int
    source: str


class TodayStepSummary(BaseModel):
    steps: int = 0
    step_goal: int = 8000
    percentage: float = 0
    distance_km: float = 0
    calories_burned: int = 0
    active_minutes: int = 0
