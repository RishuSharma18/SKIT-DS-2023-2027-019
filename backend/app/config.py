import os
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "Smart CCTV Parking & Vehicle Safety System"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/cctv_parking"
    )
    ENABLE_SQLITE_FALLBACK: bool = True
    SQLITE_URL: str = f"sqlite:///{BASE_DIR / 'cctv_parking.db'}"

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_CACHE_TTL_SECONDS: int = 3600

    # Business Rules
    MAX_ALLOWED_DURATION_MINUTES: int = int(os.getenv("MAX_ALLOWED_DURATION", "240"))
    OVERSTAY_CHECK_INTERVAL_SECONDS: int = 60
    ENABLE_OVERSTAY_WORKER: bool = True
    AI_API_KEY: str = os.getenv("AI_API_KEY", "dev-key")
    IDEMPOTENCY_WINDOW_SECONDS: int = 10

    # Media / Uploads
    UPLOADS_DIR: Path = BASE_DIR / "uploads"
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024  # 10MB

    # CORS
    CORS_ORIGINS: list[str] = ["*"]

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
