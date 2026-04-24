from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_optional_user
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse, ChatHistoryOut
from app.services.coach_service import CoachService

router = APIRouter()

# Shared guest user ID for anonymous coach conversations
_GUEST_USER_ID = "guest"


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    AI Coach chat endpoint — async so Gemini call never blocks workers.
    Works for both authenticated users and guests.
    Always returns a reply — never 401 or 500.
    """
    user_id = current_user.id if current_user else _GUEST_USER_ID
    try:
        coach_service = CoachService(db)
        reply, source = await coach_service.chat(user_id, request.message)
        return ChatResponse(reply=reply, source=source)
    except Exception:
        # Never crash the endpoint — always return a safe fallback
        return ChatResponse(reply="Stay active 💪", source="fallback")


@router.get("/history", response_model=list[ChatHistoryOut])
async def get_chat_history(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Return chat history. Guests get an empty list."""
    if current_user is None:
        return []
    try:
        coach_service = CoachService(db)
        return coach_service.get_history(current_user.id, limit)
    except Exception:
        return []
