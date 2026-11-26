"""
Central settings – read from environment / .env file.
All other modules import *only* from here; never read os.environ directly.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Database ────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql://rc:rc_pass@localhost:5432/residue"

    # ── Redis / Celery ───────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Auth ─────────────────────────────────────────────────────────────────
    SECRET_KEY: str = "change_me_in_production_min_32_chars"
    # HS256 is fine for internal demo; switch to RS256 for multi-service prod
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8   # 8 hours

    # ── Feature flags ────────────────────────────────────────────────────────
    # When True the API reads seed JSON instead of calling ML/economics modules
    DEMO_MODE: bool = True

    # ── Notification channels ────────────────────────────────────────────────
    # Supported: "log" | "twilio_sms" | "twilio_whatsapp"
    NOTIFIER_CHANNEL: str = "log"
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""   # e.g. "+14155238886" for WhatsApp sandbox

    # ── CORS ─────────────────────────────────────────────────────────────────
    # Comma-separated list; "*" for open demo, tighten before production
    CORS_ORIGINS: str = "*"

    class Config:
        env_file = "../.env"
        env_file_encoding = "utf-8"


settings = Settings()
