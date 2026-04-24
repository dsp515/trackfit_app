from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_optional_user
from app.models.user import User
from app.services.pose_service import PoseService

router = APIRouter()

# Singleton pose service (loads MediaPipe model once per process)
_pose_service: PoseService | None = None

# Guard: reject frames larger than ~5 MB base64
_MAX_FRAME_B64_LEN = 7_000_000


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
    current_user: Optional[User] = Depends(get_optional_user),
    pose_service: PoseService = Depends(get_pose_service),
):
    """Process a camera frame: detect pose, calculate angles, count reps."""
    # Reject oversized frames before touching MediaPipe
    if len(req.image_base64) > _MAX_FRAME_B64_LEN:
        return {"error": "Frame too large (max 5 MB)", "reps": 0, "phase": "unknown"}

    try:
        # Use user-scoped session when authenticated, shared session for guests
        session_id = f"{current_user.id}_{req.session_id}" if current_user else f"guest_{req.session_id}"
        return pose_service.process_frame(
            image_base64=req.image_base64,
            exercise_type=req.exercise_type,
            session_id=session_id,
        )
    except Exception as e:
        # Return a safe default so the client's rep counter stays alive
        return {"error": str(e), "reps": 0, "phase": "unknown", "angle": 0}


@router.post("/reset")
def reset_pose_session(
    req: PoseResetRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    pose_service: PoseService = Depends(get_pose_service),
):
    """Reset rep counter for a session."""
    try:
        session_id = f"{current_user.id}_{req.session_id}" if current_user else f"guest_{req.session_id}"
        pose_service.reset_session(session_id)
        return {"status": "reset", "session_id": req.session_id}
    except Exception:
        return {"status": "reset", "session_id": req.session_id}
