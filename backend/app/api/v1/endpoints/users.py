from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.profile import Profile
from app.schemas.user import UserOut
from app.schemas.profile import ProfileCreate, ProfileOut, ProfileUpdate

router = APIRouter()


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/profile", response_model=ProfileOut)
def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.post("/profile", response_model=ProfileOut, status_code=201)
def create_profile(
    data: ProfileCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Profile already exists. Use PUT to update.")

    # Calculate daily goals based on profile data
    goals = _calculate_goals(data)

    profile = Profile(
        user_id=current_user.id,
        goal=data.goal,
        age=data.age,
        gender=data.gender,
        height_cm=data.height_cm,
        weight_kg=data.weight_kg,
        activity_level=data.activity_level,
        preferred_cuisine=data.preferred_cuisine,
        **goals,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.put("/profile", response_model=ProfileOut)
def update_profile(
    data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(profile, key, value)

    # Recalculate goals if relevant fields changed
    recalc_fields = {"goal", "age", "gender", "height_cm", "weight_kg", "activity_level"}
    if recalc_fields & set(update_data.keys()):
        from app.schemas.profile import ProfileCreate
        profile_data = ProfileCreate(
            goal=profile.goal,
            age=profile.age or 25,
            gender=profile.gender or "male",
            height_cm=profile.height_cm or 170,
            weight_kg=profile.weight_kg or 70,
            activity_level=profile.activity_level or "moderate",
            preferred_cuisine=profile.preferred_cuisine or "indian",
        )
        goals = _calculate_goals(profile_data)
        for key, value in goals.items():
            setattr(profile, key, value)

    db.commit()
    db.refresh(profile)
    return profile


def _calculate_goals(data: ProfileCreate) -> dict:
    """Calculate daily nutritional and activity goals based on profile data."""
    # Mifflin-B Jeor equation for BMR
    if data.gender == "male":
        bmr = 10 * data.weight_kg + 6.25 * data.height_cm - 5 * data.age + 5
    else:
        bmr = 10 * data.weight_kg + 6.25 * data.height_cm - 5 * data.age - 161

    # Activity multiplier
    activity_multipliers = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "very_active": 1.9,
    }
    multiplier = activity_multipliers.get(data.activity_level, 1.55)
    tdee = bmr * multiplier

    # Adjust for goals
    if data.goal == "lose_weight":
        calorie_goal = int(tdee - 400)
    elif data.goal == "build_muscle":
        calorie_goal = int(tdee + 300)
    else:
        calorie_goal = int(tdee)

    # Macros (grams)
    protein_goal = int(data.weight_kg * 1.8)
    fat_goal = int(calorie_goal * 0.25 / 9)
    carbs_goal = int((calorie_goal - protein_goal * 4 - fat_goal * 9) / 4)

    return {
        "daily_calorie_goal": calorie_goal,
        "daily_protein_goal": protein_goal,
        "daily_carbs_goal": carbs_goal,
        "daily_fat_goal": fat_goal,
        "daily_water_ml_goal": 2500,
        "daily_step_goal": 8000,
    }
