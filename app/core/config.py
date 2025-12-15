from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    app_name: str = "Sentiment Analyzer API"
    # If ALLOWED_ORIGINS env is provided, it should be a JSON array.
    # Example: ["http://localhost:8501", "http://127.0.0.1:8501"]
    allowed_origins: List[str] = Field(default_factory=lambda: ["*"])


settings = Settings()
