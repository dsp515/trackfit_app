from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, food, workout, hydration, coach, stats, steps, pose

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(food.router, prefix="/food", tags=["food"])
api_router.include_router(workout.router, prefix="/workout", tags=["workout"])
api_router.include_router(hydration.router, prefix="/hydration", tags=["hydration"])
api_router.include_router(coach.router, prefix="/coach", tags=["coach"])
api_router.include_router(stats.router, prefix="/stats", tags=["stats"])
api_router.include_router(steps.router, prefix="/steps", tags=["steps"])
api_router.include_router(pose.router, prefix="/pose", tags=["pose"])
