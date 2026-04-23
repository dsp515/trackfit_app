from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse, ChatHistoryOut
from app.services.coach_service import CoachService

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    coach_service = CoachService(db)
    reply, source = coach_service.chat(current_user.id, request.message)
    return ChatResponse(reply=reply, source=source)


@router.get("/history", response_model=list[ChatHistoryOut])
def get_chat_history(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    coach_service = CoachService(db)
    return coach_service.get_history(current_user.id, limit)
