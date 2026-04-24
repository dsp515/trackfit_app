from typing import Optional
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_optional_user
from app.models.user import User
from app.schemas.stats import DailyStatsOut, DailyScoreBreakdown, WeeklyStats
from app.services.stats_service import StatsService

router = APIRouter()

_GUEST_DAILY_SCORE = DailyScoreBreakdown(
    total_score=0,
    nutrition_score=0,
    hydration_score=0,
    activity_score=0,
    workout_score=0,
    streak_bonus=0,
    tips=[],
)

_GUEST_WEEKLY = WeeklyStats(
    avg_calories=0.0,
    avg_protein=0.0,
    avg_steps=0.0,
    avg_water_ml=0.0,
    total_workouts=0,
    best_day=None,
    streak_days=0,
)


@router.get("/daily-score", response_model=DailyScoreBreakdown)
def get_daily_score(
    target_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    if current_user is None:
        return _GUEST_DAILY_SCORE
    try:
        stats_service = StatsService(db)
        return stats_service.calculate_daily_score(current_user.id, target_date)
    except Exception:
        return _GUEST_DAILY_SCORE


@router.get("/weekly", response_model=WeeklyStats)
def get_weekly_stats(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    if current_user is None:
        return _GUEST_WEEKLY
    try:
        stats_service = StatsService(db)
        return stats_service.get_weekly_stats(current_user.id)
    except Exception:
        return _GUEST_WEEKLY


@router.get("/history", response_model=list[DailyStatsOut])
def get_stats_history(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    if current_user is None:
        return []
    try:
        stats_service = StatsService(db)
        return stats_service.get_daily_stats(current_user.id)
    except Exception:
        return []
