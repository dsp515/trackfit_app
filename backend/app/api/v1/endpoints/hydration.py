from typing import Optional
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_optional_user
from app.models.user import User
from app.schemas.hydration import HydrationLogCreate, HydrationLogOut, TodayHydrationSummary
from app.services.hydration_service import HydrationService

router = APIRouter()


@router.post("/log", status_code=201)
def log_water(
    data: HydrationLogCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    if current_user is None:
        from datetime import datetime
        return {
            "id": "guest",
            "user_id": "guest",
            "amount_ml": data.amount_ml,
            "logged_at": datetime.utcnow().isoformat(),
        }
    try:
        hydration_service = HydrationService(db)
        return hydration_service.log_water(current_user.id, data)
    except Exception:
        from datetime import datetime
        return {
            "id": "error",
            "user_id": current_user.id,
            "amount_ml": data.amount_ml,
            "logged_at": datetime.utcnow().isoformat(),
        }


@router.get("/today", response_model=TodayHydrationSummary)
def get_today_hydration(
    target_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    if current_user is None:
        return TodayHydrationSummary()
    try:
        hydration_service = HydrationService(db)
        return hydration_service.get_today_hydration(current_user.id, target_date)
    except Exception:
        return TodayHydrationSummary()
