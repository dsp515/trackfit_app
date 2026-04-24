from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import inspect, text

from app.api.v1.router import api_router
from app.core.database import engine, Base
from app.core.config import settings

# Import all models to ensure they're registered with Base
from app.models import user, profile, food_log, workout_log, hydration_log, daily_stats, chat_history, step_log

Base.metadata.create_all(bind=engine)


def _run_schema_compat_migrations() -> None:
    """Apply lightweight compatibility migrations for existing local databases."""
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "workout_logs" not in table_names:
        return

    workout_columns = {col["name"] for col in inspector.get_columns("workout_logs")}

    statements: list[str] = []
    if "sets_data" not in workout_columns:
        statements.append("ALTER TABLE workout_logs ADD COLUMN sets_data TEXT DEFAULT ''")
    if "form_score" not in workout_columns:
        statements.append("ALTER TABLE workout_logs ADD COLUMN form_score INTEGER DEFAULT 0")

    if not statements:
        return

    with engine.begin() as conn:
        for statement in statements:
            if settings.DATABASE_URL.startswith("sqlite"):
                conn.execute(text(statement))
            else:
                # PostgreSQL path; keep additive and safe for repeated startups.
                conn.execute(text(statement.replace("ADD COLUMN", "ADD COLUMN IF NOT EXISTS", 1)))


try:
    _run_schema_compat_migrations()
except Exception as _mig_err:
    print(f"[startup] Schema migration warning (non-fatal): {_mig_err}")

app = FastAPI(
    title="TrackFit API",
    description="Production-ready fitness tracking API with food logging, workout tracking, hydration, AI coach, daily stats, food recognition, barcode scanning, and step sync.",
    version="1.1.0",
    debug=settings.DEBUG,
)


# ─── Global error safety middleware ──────────────────────────────────────────
# Catches any unhandled exception from ANY route and returns a safe JSON 200
# so the mobile app never receives an unparseable 500 error.
@app.middleware("http")
async def safe_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        print(f"[safe_middleware] Unhandled error on {request.method} {request.url}: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"}
        )


# ─── CORS ─────────────────────────────────────────────────────────────────────
cors_origins = settings.CORS_ORIGINS.split(",") if settings.CORS_ORIGINS != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def root():
    return {"message": "TrackFit API is running", "version": "1.1.0"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/v1/health")
def health_v1():
    """Convenience alias — lets the app confirm /api/v1 routing is working."""
    return {"status": "ok", "version": "1.1.0"}
