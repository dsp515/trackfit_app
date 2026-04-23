from pydantic import BaseModel


class ProfileCreate(BaseModel):
    goal: str  # lose_weight, build_muscle, stay_fit
    age: int
    gender: str
    height_cm: int
    weight_kg: float
    activity_level: str  # sedentary, light, moderate, active, very_active
    preferred_cuisine: str = "indian"


class ProfileUpdate(BaseModel):
    goal: str | None = None
    age: int | None = None
    gender: str | None = None
    height_cm: int | None = None
    weight_kg: float | None = None
    activity_level: str | None = None
    preferred_cuisine: str | None = None
    daily_calorie_goal: int | None = None
    daily_protein_goal: int | None = None
    daily_carbs_goal: int | None = None
    daily_fat_goal: int | None = None
    daily_water_ml_goal: int | None = None
    daily_step_goal: int | None = None


class ProfileOut(BaseModel):
    user_id: str
    goal: str
    age: int | None
    gender: str | None
    height_cm: int | None
    weight_kg: float | None
    activity_level: str | None
    preferred_cuisine: str | None
    daily_calorie_goal: int | None
    daily_protein_goal: int | None
    daily_carbs_goal: int | None
    daily_fat_goal: int | None
    daily_water_ml_goal: int | None
    daily_step_goal: int | None

    class Config:
        from_attributes = True
