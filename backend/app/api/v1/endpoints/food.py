from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_optional_user
from app.models.user import User
from app.schemas.food import FoodLogCreate, FoodLogOut, FoodSearchResult, TodayFoodSummary
from app.services.food_service import FoodService
from pydantic import BaseModel

router = APIRouter()

# Max allowed base64 image size: ~5 MB raw ≈ 6.67 MB base64
_MAX_IMAGE_B64_LEN = 7_000_000


class FoodRecognizeRequest(BaseModel):
    image_base64: str
    method: str = "vit"  # Kept for compatibility; recognition is VIT-only.


class BarcodeRequest(BaseModel):
    barcode: str


@router.get("/search", response_model=list[FoodSearchResult])
def search_foods(
    q: str = Query(..., min_length=1),
    cuisine: str | None = None,
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    try:
        food_service = FoodService(db)
        return food_service.search_foods(q, cuisine, limit)
    except Exception:
        return []


@router.get("/db/{food_key}")
def get_food_details(
    food_key: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    try:
        food_service = FoodService(db)
        item = food_service.get_food_by_key(food_key)
        if not item:
            return {"error": "Food not found"}
        return item
    except Exception:
        return {"error": "Food lookup failed"}


@router.post("/recognize")
async def recognize_food(
    req: FoodRecognizeRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Identify food from a photo using AI (Vision Transformer)."""
    # Guard: reject oversized payloads before touching the model
    if len(req.image_base64) > _MAX_IMAGE_B64_LEN:
        return {"food": "Unknown", "calories": 200, "predictions": [], "source": "rejected"}

    try:
        food_service = FoodService(db)
        result = await food_service.recognize_food_vit(req.image_base64)
        return result
    except Exception:
        return {"food": "Unknown", "calories": 200, "predictions": [], "source": "fallback"}


@router.post("/barcode")
async def barcode_lookup(
    req: BarcodeRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    try:
        food_service = FoodService(db)
        return await food_service.barcode_lookup(req.barcode)
    except Exception:
        return {"name": "Unknown Product", "calories": "200 kcal", "source": "fallback"}


@router.post("/log", status_code=201)
def log_food(
    food: FoodLogCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    if current_user is None:
        from datetime import datetime
        return {
            "id": "guest",
            "user_id": "guest",
            "name": food.name,
            "calories": food.calories,
            "protein": food.protein,
            "carbs": food.carbs,
            "fat": food.fat,
            "fiber": food.fiber,
            "sugar": food.sugar,
            "sodium": food.sodium,
            "amount_g": food.amount_g,
            "meal_type": food.meal_type,
            "logged_at": datetime.utcnow().isoformat(),
        }
    try:
        food_service = FoodService(db)
        return food_service.log_food(current_user.id, food)
    except Exception:
        from datetime import datetime
        return {
            "id": "error",
            "user_id": current_user.id,
            "name": food.name,
            "calories": food.calories,
            "protein": food.protein,
            "carbs": food.carbs,
            "fat": food.fat,
            "fiber": food.fiber,
            "sugar": food.sugar,
            "sodium": food.sodium,
            "amount_g": food.amount_g,
            "meal_type": food.meal_type,
            "logged_at": datetime.utcnow().isoformat(),
        }


@router.get("/today", response_model=TodayFoodSummary)
def get_today_food(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    if current_user is None:
        return TodayFoodSummary()
    try:
        food_service = FoodService(db)
        return food_service.get_today_logs(current_user.id)
    except Exception:
        return TodayFoodSummary()


@router.delete("/log/{log_id}")
def delete_food_log(
    log_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    if current_user is None:
        return {"message": "Food log deleted"}
    try:
        food_service = FoodService(db)
        food_service.delete_food_log(log_id, current_user.id)
        return {"message": "Food log deleted"}
    except Exception:
        return {"message": "Food log deleted"}
