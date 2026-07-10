from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = Field(default="development", alias="ENVIRONMENT")
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    model_dir: str = Field(default="models", alias="MODEL_DIR")
    api_key: str | None = Field(default=None, alias="API_KEY")
    api_key_required: bool = Field(default=False, alias="API_KEY_REQUIRED")
    rate_limit_per_minute: int = Field(default=60, alias="RATE_LIMIT_PER_MINUTE")
    static_dir: str = Field(default="static", alias="STATIC_DIR")
    cors_origins: str = Field(default="http://localhost:3000,http://127.0.0.1:3000", alias="CORS_ORIGINS")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def model_dir_path(self) -> Path:
        return Path(self.model_dir).resolve()


settings = Settings()
