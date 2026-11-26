from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://rc:rc_pass@localhost:5432/residue"
    REDIS_URL: str = "redis://localhost:6379/0"
    DEMO_MODE: bool = True
    SECRET_KEY: str = "change_me"

    class Config:
        env_file = "../.env"


settings = Settings()