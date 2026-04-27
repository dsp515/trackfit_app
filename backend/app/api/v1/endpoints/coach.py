from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_optional_user
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse, ChatHistoryOut
from app.services.coach_service import CoachService
from app.services.adaptive_coach import generate_adaptive_response, enrich_coach_context

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


# ─── Adaptive Coach endpoint ─────────────────────────────────────────────────

class AdaptiveRequest(BaseModel):
    """Daily health snapshot sent by the app for adaptive coaching."""
    id: Optional[str] = None          # user-supplied id override
    steps: int = 0
    calories: int = 0
    water_ml: int = 0
    protein: float = 0.0
    workouts: int = 0
    sleep_hours: float = 0.0
    weight_kg: Optional[float] = None
    # Optional personalised goals (uses sensible defaults if omitted)
    step_goal: int = 8000
    calorie_goal: int = 2000
    water_goal_ml: int = 2500
    protein_goal_g: float = 120.0


class AdaptiveResponse(BaseModel):
    message: str
    suggestions: list
    trend: str
    score: float
    confidence: float
    signals: list
    source: str


@router.post("/adaptive", response_model=AdaptiveResponse)
async def adaptive_coach(
    request: AdaptiveRequest,
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Adaptive self-learning coaching endpoint.

    The engine keeps a 7-day rolling memory per user and detects trends
    (improving / stable / declining) across steps, water, protein, calories,
    and workouts.  No LLM, no GPU — Render-safe pure Python.

    Always returns a valid response even on error.

    Test payload:
      {"id": "user1", "steps": 2000, "calories": 2500,
       "water_ml": 500, "protein": 30}
    """
    user_id = (
        request.id
        or (current_user.id if current_user else "guest")
    )

    try:
        data: Dict[str, Any] = {
            "steps":          request.steps,
            "calories":       request.calories,
            "water_ml":       request.water_ml,
            "protein":        request.protein,
            "workouts":       request.workouts,
            "sleep_hours":    request.sleep_hours,
            "weight_kg":      request.weight_kg,
            "step_goal":      request.step_goal,
            "calorie_goal":   request.calorie_goal,
            "water_goal_ml":  request.water_goal_ml,
            "protein_goal_g": request.protein_goal_g,
        }

        result = generate_adaptive_response(user_id, data)

        return AdaptiveResponse(
            message=result.message,
            suggestions=result.suggestions,
            trend=result.trend,
            score=result.score,
            confidence=result.confidence,
            signals=result.signals,
            source=result.source,
        )
    except Exception:
        return AdaptiveResponse(
            message="Stay active and hydrated 💪",
            suggestions=["Keep going"],
            trend="stable",
            score=0.5,
            confidence=0.5,
            signals=[],
            source="fallback",
        )


@router.post("/chat-adaptive", response_model=ChatResponse)
async def chat_adaptive(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Enhanced chat that enriches the standard reply with adaptive trend insights.
    Drop-in replacement for /coach/chat that adds trend-awareness.
    """
    user_id = current_user.id if current_user else _GUEST_USER_ID
    try:
        coach_service = CoachService(db)
        reply, source = await coach_service.chat(user_id, request.message)
        enriched = enrich_coach_context(user_id, reply)
        return ChatResponse(reply=enriched, source=f"{source}+adaptive")
    except Exception:
        return ChatResponse(reply="Stay active 💪", source="fallback")
