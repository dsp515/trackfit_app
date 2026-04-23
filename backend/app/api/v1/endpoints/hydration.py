from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.hydration import HydrationLogCreate, HydrationLogOut, TodayHydrationSummary
from app.services.hydration_service import HydrationService

router = APIRouter()


@router.post("/log", response_model=HydrationLogOut, status_code=201)
def log_water(
    data: HydrationLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    hydration_service = HydrationService(db)
    return hydration_service.log_water(current_user.id, data)


@router.get("/today", response_model=TodayHydrationSummary)
def get_today_hydration(
    target_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    hydration_service = HydrationService(db)
    return hydration_service.get_today_hydration(current_user.id, target_date)
