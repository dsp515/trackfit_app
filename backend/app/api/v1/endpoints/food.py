from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.food import FoodLogCreate, FoodLogOut, FoodSearchResult, TodayFoodSummary
from app.services.food_service import FoodService
from pydantic import BaseModel

router = APIRouter()


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
    current_user: User = Depends(get_current_user),
):
    food_service = FoodService(db)
    return food_service.search_foods(q, cuisine, limit)


@router.get("/db/{food_key}")
def get_food_details(
    food_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    food_service = FoodService(db)
    item = food_service.get_food_by_key(food_key)
    if not item:
        raise HTTPException(status_code=404, detail="Food not found")
    return item


@router.post("/recognize")
def recognize_food(
    req: FoodRecognizeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Identify food from a photo using AI.

    Uses Vision Transformer (VIT) in production.
    """
    food_service = FoodService(db)
    return food_service.recognize_food_vit(req.image_base64)


@router.post("/barcode")
async def barcode_lookup(
    req: BarcodeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    food_service = FoodService(db)
    return await food_service.barcode_lookup(req.barcode)


@router.post("/log", response_model=FoodLogOut, status_code=201)
def log_food(
    food: FoodLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    food_service = FoodService(db)
    return food_service.log_food(current_user.id, food)


@router.get("/today", response_model=TodayFoodSummary)
def get_today_food(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    food_service = FoodService(db)
    return food_service.get_today_logs(current_user.id)


@router.delete("/log/{log_id}")
def delete_food_log(
    log_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    food_service = FoodService(db)
    if not food_service.delete_food_log(log_id, current_user.id):
        raise HTTPException(status_code=404, detail="Food log not found")
    return {"message": "Food log deleted"}
