from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_optional_user
from app.models.user import User
from app.schemas.workout import WorkoutLogCreate, WorkoutLogOut, ExerciseSearchResult, RepLogRequest
from app.services.workout_service import WorkoutService

router = APIRouter()


def _guest_workout_dict(exercise_name: str, exercise_type: str, duration_minutes: int,
                        calories_burned: int = 0, reps: int = 0, notes: str = "") -> dict:
    """Return a safe workout dict for guest/error responses."""
    return {
        "id": "guest",
        "user_id": "guest",
        "exercise_name": exercise_name,
        "exercise_type": exercise_type or "strength",
        "duration_minutes": duration_minutes,
        "calories_burned": calories_burned,
        "sets": 0,
        "reps": reps,
        "weight_kg": 0.0,
        "distance_km": 0.0,
        "notes": notes,
        "sets_data": "",
        "form_score": 0,
        "logged_at": datetime.utcnow().isoformat(),
    }


@router.get("/exercises/search", response_model=list[ExerciseSearchResult])
def search_exercises(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    try:
        workout_service = WorkoutService(db)
        return workout_service.search_exercises(q, limit)
    except Exception:
        return []


@router.post("/log", status_code=201)
def log_workout(
    data: WorkoutLogCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    if current_user is None:
        return _guest_workout_dict(
            data.exercise_name, data.exercise_type, data.duration_minutes,
            data.calories_burned, data.reps, data.notes,
        )
    try:
        workout_service = WorkoutService(db)
        return workout_service.log_workout(current_user.id, data)
    except Exception:
        return _guest_workout_dict(
            data.exercise_name, data.exercise_type, data.duration_minutes,
            data.calories_burned, data.reps, data.notes,
        )


@router.post("/rep-log", status_code=201)
def log_rep_counting(
    data: RepLogRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Log a rep-counted workout from the camera/accelerometer rep counter."""
    duration = max(1, (data.duration_seconds or 60) // 60)
    if current_user is None:
        return _guest_workout_dict(
            data.exercise_name, data.exercise_type, duration,
            data.calories_burned, data.total_reps,
            f"Rep counter: {data.total_reps} reps",
        )
    try:
        workout_service = WorkoutService(db)
        return workout_service.log_workout(
            current_user.id,
            WorkoutLogCreate(
                exercise_name=data.exercise_name,
                exercise_type=data.exercise_type,
                duration_minutes=duration,
                calories_burned=data.calories_burned,
                sets=0,
                reps=data.total_reps,
                weight_kg=0,
                distance_km=0,
                notes=f"Rep counter: {data.total_reps} reps in {data.duration_seconds}s",
                sets_data=data.sets_data,
                form_score=data.form_score,
            ),
        )
    except Exception:
        return _guest_workout_dict(
            data.exercise_name, data.exercise_type, duration,
            data.calories_burned, data.total_reps,
        )


@router.get("/today", response_model=list[WorkoutLogOut])
def get_today_workouts(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    if current_user is None:
        return []
    try:
        workout_service = WorkoutService(db)
        return workout_service.get_today_workouts(current_user.id)
    except Exception:
        return []


@router.get("/history", response_model=list[WorkoutLogOut])
def get_workout_history(
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    if current_user is None:
        return []
    try:
        workout_service = WorkoutService(db)
        return workout_service.get_workout_history(current_user.id, limit)
    except Exception:
        return []
