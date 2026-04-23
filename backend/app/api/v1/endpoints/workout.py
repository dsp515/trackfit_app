from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.workout import WorkoutLogCreate, WorkoutLogOut, ExerciseSearchResult, RepLogRequest
from app.services.workout_service import WorkoutService

router = APIRouter()


@router.get("/exercises/search", response_model=list[ExerciseSearchResult])
def search_exercises(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workout_service = WorkoutService(db)
    return workout_service.search_exercises(q, limit)


@router.post("/log", response_model=WorkoutLogOut, status_code=201)
def log_workout(
    data: WorkoutLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workout_service = WorkoutService(db)
    return workout_service.log_workout(current_user.id, data)


@router.post("/rep-log", response_model=WorkoutLogOut, status_code=201)
def log_rep_counting(
    data: RepLogRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Log a rep-counted workout from the camera/accelerometer rep counter."""
    workout_service = WorkoutService(db)
    duration = max(1, data.duration_seconds // 60)
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


@router.get("/today", response_model=list[WorkoutLogOut])
def get_today_workouts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workout_service = WorkoutService(db)
    return workout_service.get_today_workouts(current_user.id)


@router.get("/history", response_model=list[WorkoutLogOut])
def get_workout_history(
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workout_service = WorkoutService(db)
    return workout_service.get_workout_history(current_user.id, limit)
