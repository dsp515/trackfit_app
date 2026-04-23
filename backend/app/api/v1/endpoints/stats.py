from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.stats import DailyStatsOut, DailyScoreBreakdown, WeeklyStats
from app.services.stats_service import StatsService

router = APIRouter()


@router.get("/daily-score", response_model=DailyScoreBreakdown)
def get_daily_score(
    target_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stats_service = StatsService(db)
    return stats_service.calculate_daily_score(current_user.id, target_date)


@router.get("/weekly", response_model=WeeklyStats)
def get_weekly_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stats_service = StatsService(db)
    return stats_service.get_weekly_stats(current_user.id)


@router.get("/history", response_model=list[DailyStatsOut])
def get_stats_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stats_service = StatsService(db)
    return stats_service.get_daily_stats(current_user.id)
