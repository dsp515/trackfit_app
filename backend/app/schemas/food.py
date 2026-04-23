from datetime import datetime

from pydantic import BaseModel


class FoodLogCreate(BaseModel):
    food_key: str | None = None
    name: str
    calories: int
    protein: float = 0
    carbs: float = 0
    fat: float = 0
    fiber: float = 0
    sugar: float = 0
    sodium: int = 0
    amount_g: int
    meal_type: str  # breakfast, lunch, dinner, snacks


class FoodLogOut(BaseModel):
    id: str
    user_id: str
    name: str
    calories: int
    protein: float
    carbs: float
    fat: float
    fiber: float
    sugar: float
    sodium: int
    amount_g: int
    meal_type: str
    logged_at: datetime

    class Config:
        from_attributes = True


class FoodSearchResult(BaseModel):
    food_key: str
    name: str
    calories: int
    protein_g: float
    carbs_g: float
    fats_g: float
    fiber_g: float
    typical_portion_g: int
    is_veg: bool
    category: str


class TodayFoodSummary(BaseModel):
    total_calories: int = 0
    total_protein: float = 0
    total_carbs: float = 0
    total_fat: float = 0
    total_fiber: float = 0
    logs: list[FoodLogOut] = []
    by_meal: dict[str, list[FoodLogOut]] = {}
