"""
Central settings – read from environment / .env file.
All other modules import *only* from here; never read os.environ directly.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict

_KNOWN_INSECURE_SECRETS = {
    "",
    "change_me",
    "change_me_in_production_min_32_chars",
    "change_me_to_a_long_random_string_before_deploy",
    "secret",
    "dev",
}


class Settings(BaseSettings):
    # ── Database ────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql://rc:rc_pass@localhost:5432/residue"

    # ── Redis / Celery ───────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Auth ─────────────────────────────────────────────────────────────────
    # Must be set via environment / .env (min 32 chars in production).
    SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8   # 8 hours

    # ── Feature flags ────────────────────────────────────────────────────────
    # When True the API allows demo endpoints; production must set DEMO_MODE=false.
    DEMO_MODE: bool = False

    # ── Notification channels ────────────────────────────────────────────────
    # Supported: "log" | "twilio_sms" | "twilio_whatsapp"
    NOTIFIER_CHANNEL: str = "log"
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""   # e.g. "+14155238886" for WhatsApp sandbox

    # ── CORS ─────────────────────────────────────────────────────────────────
    # Comma-separated list; tighten before production.
    CORS_ORIGINS: str = "*"

    # ── Scheduler ────────────────────────────────────────────────────────────
    # Standard 5-field cron for Celery beat harvest refresh task.
    HARVEST_REFRESH_CRON: str = "0 2 * * *"

    model_config = SettingsConfigDict(env_file="../.env", env_file_encoding="utf-8")


settings = Settings()


def validate_security_config() -> None:
    """
    Fail closed if SECRET_KEY is missing, a known placeholder, or too short,
    or if CORS_ORIGINS is empty or wildcard ('*') outside DEMO_MODE.
    Called during application startup and token operations.
    """
    key = (settings.SECRET_KEY or "").strip()
    if not key or key in _KNOWN_INSECURE_SECRETS:
        raise RuntimeError(
            "Unsafe SECRET_KEY configuration: set a strong random SECRET_KEY (>= 32 chars) in environment/.env."
        )
    if len(key) < 32:
        raise RuntimeError(
            "Unsafe SECRET_KEY configuration: SECRET_KEY must be at least 32 characters."
        )
    if not settings.DEMO_MODE:
        origins = [o.strip() for o in (settings.CORS_ORIGINS or "").split(",") if o.strip()]
        if not origins or "*" in origins:
            raise RuntimeError(
                "Unsafe CORS_ORIGINS configuration: explicit allowed origins are required when DEMO_MODE=false (wildcard '*' is forbidden)."
            )
