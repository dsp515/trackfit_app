from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.steps import StepSyncRequest, StepSyncResponse, TodayStepSummary
from app.services.steps_service import StepsService

router = APIRouter()


@router.post("/sync", response_model=StepSyncResponse)
def sync_steps(
    data: StepSyncRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    steps_service = StepsService(db)
    return steps_service.sync_steps(current_user.id, data)


@router.get("/today", response_model=TodayStepSummary)
def get_today_steps(
    target_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    steps_service = StepsService(db)
    return steps_service.get_today_steps(current_user.id, target_date)
