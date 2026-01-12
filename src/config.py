"""
Application configuration using pydantic-settings.

Supports swappable embedding and LLM providers via environment variables.
Use nested delimiter __ for nested settings, e.g., EMBEDDING__PROVIDER=openai
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class EmbeddingSettings(BaseSettings):
    """Swappable embedding provider configuration."""

    model_config = SettingsConfigDict(env_prefix="EMBEDDING__")

    provider: str = "huggingface"  # huggingface | openai | jina
    model: str = "all-MiniLM-L6-v2"
    dimension: int = 384
    api_key: str = ""  # Required for openai/jina


class LLMSettings(BaseSettings):
    """Swappable LLM provider configuration (for Query phase)."""

    model_config = SettingsConfigDict(env_prefix="LLM__")

    provider: str = "openai"  # openai | ollama | anthropic
    model: str = "gpt-4o-mini"
    api_key: str = ""
    base_url: str = "http://localhost:11434"  # For Ollama


class Settings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App Settings
    log_level: str = "INFO"
    json_logs: bool = False  # Set to True for JSON output in production

    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5433/rag"

    # Nested settings
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
