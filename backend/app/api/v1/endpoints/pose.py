from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.pose_service import PoseService

router = APIRouter()

# Singleton pose service (loads MediaPipe model once)
_pose_service: PoseService | None = None


def get_pose_service() -> PoseService:
    global _pose_service
    if _pose_service is None:
        _pose_service = PoseService()
    return _pose_service


class PoseDetectRequest(BaseModel):
    image_base64: str
    exercise_type: str = "pushup"
    session_id: str = "default"


class PoseResetRequest(BaseModel):
    session_id: str = "default"


@router.post("/detect")
def detect_pose(
    req: PoseDetectRequest,
    current_user: User = Depends(get_current_user),
    pose_service: PoseService = Depends(get_pose_service),
):
    """Process a camera frame: detect pose, calculate angles, count reps.
    
    The rep counting uses the same state machine as Pushup_counter.py:
      angle > up_angle  ->  phase = UP
      angle < down_angle and was UP  ->  phase = DOWN  
      angle > up_angle and was DOWN  ->  REP COUNTED, reset
    """
    session_id = f"{current_user.id}_{req.session_id}"
    return pose_service.process_frame(
        image_base64=req.image_base64,
        exercise_type=req.exercise_type,
        session_id=session_id,
    )


@router.post("/reset")
def reset_pose_session(
    req: PoseResetRequest,
    current_user: User = Depends(get_current_user),
    pose_service: PoseService = Depends(get_pose_service),
):
    """Reset rep counter for a session."""
    session_id = f"{current_user.id}_{req.session_id}"
    pose_service.reset_session(session_id)
    return {"status": "reset", "session_id": req.session_id}
