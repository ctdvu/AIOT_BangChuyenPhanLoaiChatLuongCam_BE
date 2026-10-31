from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    app_name: str = "Orange Sorting API"
    database_url: str = (
        "mysql+pymysql://orange_user:orange_password@127.0.0.1:3306/"
        "orange_sorting?charset=utf8mb4"
    )
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    frontend_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    max_image_size_mb: int = 10
    upload_dir: Path = BACKEND_DIR / "uploads"
    camera_allowed_hosts: list[str] = []
    camera_simulation_enabled: bool = False
    camera_connect_timeout: float = 5.0
    camera_read_timeout: float = 3.0
    camera_frame_max_age: float = 2.0
    camera_pair_max_skew: float = 0.25
    secret_key: str = "orange-sorting-ec2-secret-key-change-in-prod"
    access_token_expire_hours: int = 72
    confidence_gap_threshold: float = 0.20
    allow_unauthenticated_device_in_tests: bool = True

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("frontend_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

