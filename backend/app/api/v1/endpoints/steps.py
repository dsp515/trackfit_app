from typing import Optional
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_optional_user
from app.models.user import User
from app.schemas.steps import StepSyncRequest, StepSyncResponse, TodayStepSummary
from app.services.steps_service import StepsService

router = APIRouter()


@router.post("/sync", response_model=StepSyncResponse)
def sync_steps(
    data: StepSyncRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    if current_user is None:
        # Guest: acknowledge silently so frontend step counter keeps running
        return StepSyncResponse(
            date=str(data.date),
            steps=data.steps,
            distance_km=round(data.distance_m / 1000, 2) if data.distance_m else 0.0,
            calories_burned=data.calories_burned or 0,
            active_minutes=data.active_minutes or 0,
            source=data.source or "accelerometer",
        )
    try:
        steps_service = StepsService(db)
        return steps_service.sync_steps(current_user.id, data)
    except Exception:
        return StepSyncResponse(
            date=str(data.date),
            steps=data.steps,
            distance_km=round(data.distance_m / 1000, 2) if data.distance_m else 0.0,
            calories_burned=data.calories_burned or 0,
            active_minutes=data.active_minutes or 0,
            source=data.source or "accelerometer",
        )


@router.get("/today", response_model=TodayStepSummary)
def get_today_steps(
    target_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    if current_user is None:
        return TodayStepSummary()
    try:
        steps_service = StepsService(db)
        return steps_service.get_today_steps(current_user.id, target_date)
    except Exception:
        return TodayStepSummary()
