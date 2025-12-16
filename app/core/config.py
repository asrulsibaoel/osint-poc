from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore")

    app_name: str = "Sentiment Analyzer API"
    # If ALLOWED_ORIGINS env is provided, it should be a JSON array.
    # Example: ["http://localhost:8501", "http://127.0.0.1:8501"]
    allowed_origins: List[str] = Field(default_factory=lambda: ["*"])
    
    # Twitter API credentials
    twitter_bearer_token: Optional[str] = None
    
    # Neo4j configuration
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    neo4j_database: str = "neo4j"
    
    # PostgreSQL configuration (for future use)
    database_url: str = "postgresql://postgres:postgres@localhost:5432/osint_db"


settings = Settings()
