from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.hydration_log import HydrationLog
from app.models.daily_stats import DailyStats
from app.models.profile import Profile
from app.schemas.hydration import HydrationLogCreate, TodayHydrationSummary


class HydrationService:
    def __init__(self, db: Session):
        self.db = db

    def log_water(self, user_id: str, data: HydrationLogCreate) -> HydrationLog:
        log_date = data.date or date.today()
        logged_at = datetime.now(timezone.utc).replace(tzinfo=None)
        if data.date is not None:
            # Preserve the user-local day key provided by the client.
            logged_at = datetime.combine(log_date, logged_at.time())

        log = HydrationLog(
            user_id=user_id,
            amount_ml=data.amount_ml,
            logged_at=logged_at,
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        self._update_daily_stats(user_id, log_date)
        return log

    def get_today_hydration(
        self,
        user_id: str,
        target_date: date | None = None,
    ) -> TodayHydrationSummary:
        day = target_date or date.today()
        start_dt = datetime(day.year, day.month, day.day)
        end_dt = start_dt + timedelta(days=1)

        logs = (
            self.db.query(HydrationLog)
            .filter(
                HydrationLog.user_id == user_id,
                HydrationLog.logged_at >= start_dt,
                HydrationLog.logged_at < end_dt,
            )
            .order_by(HydrationLog.logged_at.desc())
            .all()
        )

        total_ml = sum(log.amount_ml for log in logs)
        profile = self.db.query(Profile).filter(Profile.user_id == user_id).first()
        goal_ml = profile.daily_water_ml_goal if profile else 2500

        return TodayHydrationSummary(
            total_ml=total_ml,
            goal_ml=goal_ml,
            percentage=round((total_ml / goal_ml) * 100, 1) if goal_ml > 0 else 0,
            logs=logs,
        )

    def _update_daily_stats(self, user_id: str, target_date: date):
        summary = self.get_today_hydration(user_id, target_date)
        stat = (
            self.db.query(DailyStats)
            .filter(DailyStats.user_id == user_id, DailyStats.date == target_date)
            .first()
        )
        if not stat:
            stat = DailyStats(user_id=user_id, date=target_date)
            self.db.add(stat)

        stat.water_ml = summary.total_ml
        self.db.commit()
