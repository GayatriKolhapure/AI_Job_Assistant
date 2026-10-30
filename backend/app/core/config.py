"""Application configuration loaded from environment variables and .env file."""

from functools import lru_cache
import os
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Application settings
    environment: str = Field(default="development", description="Runtime environment")
    app_name: str = Field(default="Hidani AI Job Assistant", description="Application name")
    max_history_turns: int = Field(default=10, description="Max conversation turns in memory")

    # LLM Configuration
    openai_api_key: str = Field(default="mock", description="OpenAI API key or 'mock'")
    openai_model: str = Field(default="gpt-4o-mini", description="LLM model identifier")
    openai_api_base: str = Field(default="https://api.openai.com/v1", description="OpenAI API base URL")
    llm_timeout_seconds: int = Field(default=30, description="Timeout for LLM API calls in seconds")
    llm_temperature: float = Field(default=0.2, description="LLM generation temperature")

    # Server & Networking
    backend_host: str = Field(default="127.0.0.1", description="Backend bind host")
    backend_port: int = Field(default=8000, description="Backend bind port")
    backend_url: str = Field(default="http://127.0.0.1:8000", description="Backend URL")
    allowed_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000",
        description="Allowed CORS origins comma-separated"
    )

    # Storage paths
    database_url: str = Field(
        default="sqlite:///./data/applications.db",
        description="SQLite database path"
    )
    jobs_data_path: str = Field(
        default="./data/jobs.json",
        description="Path to real jobs JSON dataset"
    )
    upload_dir: str = Field(
        default="./data/uploads",
        description="Temporary directory for uploaded resumes"
    )
    max_upload_size_mb: int = Field(
        default=10,
        description="Maximum resume upload size in megabytes"
    )

    # Matching weights (sum to 1.0)
    weight_skills: float = Field(default=0.50, description="Weight for skills overlap")
    weight_designation: float = Field(default=0.25, description="Weight for title/role similarity")
    weight_experience: float = Field(default=0.15, description="Weight for experience compatibility")
    weight_location: float = Field(default=0.10, description="Weight for location & remote compatibility")

    @property
    def cors_origins(self) -> List[str]:
        """Parse comma-separated origins list."""
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def is_mock_mode(self) -> bool:
        """Check if LLM is running in deterministic offline mock mode."""
        key = (self.openai_api_key or "").strip().lower()
        return not key or key in ("mock", "none", "placeholder", "test", "fake", "")


@lru_cache()
def get_settings() -> Settings:
    """Settings singleton cache."""
    return Settings()

