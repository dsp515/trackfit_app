from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings
import warnings

BASE_DIR = Path(__file__).parent.parent

_INSECURE_DEFAULT_SECRET = "trackfit-ultra-secret-key-change-in-production-2024"


class Settings(BaseSettings):
    ENVIRONMENT: str = "production"
    DEBUG: bool = False

    DATABASE_URL: str = "sqlite:///./trackfit.db"
    JWT_SECRET: str = _INSECURE_DEFAULT_SECRET
    OPENROUTER_API_KEY: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    ALGORITHM: str = "HS256"

    # CORS
    CORS_ORIGINS: str = "*"

    # Rate limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60

    # Paths
    FOOD_DB_PATH: str = str(BASE_DIR / "db" / "food_db.json")
    EXERCISE_DB_PATH: str = str(BASE_DIR / "db" / "exercise_db.json")
    FOOD_MODEL_PATH: str = str(BASE_DIR / "models" / "food_model.pt")
    FOOD_CLASSES_PATH: str = str(BASE_DIR / "models" / "food_classes.json")
    COACH_MODEL_PATH: str = str(BASE_DIR / "data" / "coach_model.pt")
    TOKENIZER_PATH: str = str(BASE_DIR / "data" / "tokenizer.json")

    # External APIs
    API_NINJAS_KEY: str = ""  # https://api-ninjas.com/api/nutrition (free tier)
    HF_TOKEN: str = ""  # Optional HuggingFace token

    # Logging
    LOG_LEVEL: str = "INFO"

    @field_validator("JWT_SECRET")
    @classmethod
    def warn_insecure_secret(cls, v: str) -> str:
        if v == _INSECURE_DEFAULT_SECRET:
            warnings.warn(
                "JWT_SECRET is using the insecure default value. "
                "Set a strong random value in your .env file before production.",
                stacklevel=2,
            )
        return v

    class Config:
        env_file = ".env"


settings = Settings()
