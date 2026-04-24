import json
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.models.step_log import StepLog
from app.models.daily_stats import DailyStats
from app.models.profile import Profile
from app.schemas.steps import StepSyncRequest, StepSyncResponse, TodayStepSummary


class StepsService:
    def __init__(self, db: Session):
        self.db = db

    def sync_steps(self, user_id: str, data: StepSyncRequest) -> StepSyncResponse:
        """Sync step data from device, Google Fit, or Apple Health."""
        sync_date = data.date

        log = (
            self.db.query(StepLog)
            .filter(StepLog.user_id == user_id, StepLog.date == sync_date)
            .first()
        )

        if log:
            # Update if new data has more steps or from a preferred source
            if data.steps > log.steps or data.source in ("google_fit", "apple_health"):
                log.steps = data.steps
                log.distance_m = data.distance_m
                log.calories_burned = data.calories_burned
                log.active_minutes = data.active_minutes
                log.source = data.source
                log.synced_at = datetime.now(timezone.utc)
        else:
            log = StepLog(
                user_id=user_id,
                date=sync_date,
                steps=data.steps,
                distance_m=data.distance_m,
                calories_burned=data.calories_burned,
                active_minutes=data.active_minutes,
                source=data.source,
            )
            self.db.add(log)

        self.db.commit()
        self.db.refresh(log)

        # Update daily_stats
        self._update_daily_stats(user_id, sync_date)

        return StepSyncResponse(
            date=sync_date.isoformat(),
            steps=log.steps,
            distance_km=round(log.distance_m / 1000, 2) if log.distance_m else 0,
            calories_burned=log.calories_burned,
            active_minutes=log.active_minutes,
            source=log.source,
        )

    def get_today_steps(self, user_id: str, target_date: date | None = None) -> TodayStepSummary:
        day = target_date or date.today()
        log = (
            self.db.query(StepLog)
            .filter(StepLog.user_id == user_id, StepLog.date == day)
            .first()
        )
        profile = self.db.query(Profile).filter(Profile.user_id == user_id).first()
        step_goal = profile.daily_step_goal if profile else 8000

        steps = log.steps if log else 0
        distance_km = round(log.distance_m / 1000, 2) if log and log.distance_m else round(steps * 0.0007, 2)
        calories = log.calories_burned if log else int(steps * 0.04)
        active_mins = log.active_minutes if log else 0

        return TodayStepSummary(
            steps=steps,
            step_goal=step_goal,
            percentage=round((steps / step_goal) * 100, 1) if step_goal > 0 else 0,
            distance_km=distance_km,
            calories_burned=calories,
            active_minutes=active_mins,
        )

    def _update_daily_stats(self, user_id: str, target_date: date):
        log = (
            self.db.query(StepLog)
            .filter(StepLog.user_id == user_id, StepLog.date == target_date)
            .first()
        )
        stat = (
            self.db.query(DailyStats)
            .filter(DailyStats.user_id == user_id, DailyStats.date == target_date)
            .first()
        )
        if not stat:
            stat = DailyStats(user_id=user_id, date=target_date)
            self.db.add(stat)

        if log:
            stat.steps = log.steps
        self.db.commit()
