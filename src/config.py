"""
Application configuration using pydantic-settings.

Supports swappable embedding and LLM providers via environment variables.
Use nested delimiter __ for nested settings, e.g., EMBEDDING__PROVIDER=openai
"""

from functools import lru_cache
from enum import Enum

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class TimeoutSettings(BaseSettings):
    """Timeout configuration for external services."""
    
    model_config = SettingsConfigDict(
        env_prefix="TIMEOUT__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    llm_seconds: float = 60.0       # LLM API timeout
    embedding_seconds: float = 30.0  # Embedding API timeout
    db_seconds: float = 10.0         # Database query timeout


class EmbeddingProvider(str, Enum):
    """Supported embedding providers."""
    HUGGINGFACE = "huggingface"
    OPENAI = "openai"
    JINA = "jina"


class EmbeddingSettings(BaseSettings):
    """Swappable embedding provider configuration."""

    model_config = SettingsConfigDict(
        env_prefix="EMBEDDING__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    provider: EmbeddingProvider = EmbeddingProvider.HUGGINGFACE
    model: str = "all-MiniLM-L6-v2"
    dimension: int = 384
    api_key: str = ""  # Required for openai/jina
    
    @field_validator('api_key')
    @classmethod
    def validate_api_key(cls, v, info):
        """Ensure API key is provided for cloud providers."""
        provider = info.data.get('provider')
        if provider in [EmbeddingProvider.OPENAI, EmbeddingProvider.JINA] and not v:
            raise ValueError(f"{provider.value} embedding provider requires a non-empty API key")
        return v



class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    GEMINI = "gemini"


class LLMSettings(BaseSettings):
    """Swappable LLM provider configuration (for Query phase)."""

    model_config = SettingsConfigDict(
        env_prefix="LLM__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    provider: LLMProvider = LLMProvider.OPENAI
    model: str = "gpt-4o-mini"
    api_key: str = ""
    base_url: str = "http://localhost:11434"  # For Ollama
    
    @field_validator('api_key')
    @classmethod
    def validate_api_key(cls, v, info):
        """Ensure API key is provided for cloud LLM providers."""
        provider = info.data.get('provider')
        if provider in [LLMProvider.OPENAI, LLMProvider.GEMINI] and not v:
            raise ValueError(f"{provider.value} LLM provider requires a non-empty API key")
        return v


class OpikSettings(BaseSettings):
    """Opik observability configuration."""
    
    model_config = SettingsConfigDict(
        env_prefix="OPIK_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    api_key: str = ""
    workspace: str = "priya-m"
    project_name: str = "rag-101"


class DBOSSettings(BaseSettings):
    """DBOS configuration."""

    model_config = SettingsConfigDict(
        env_prefix="DBOS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    system_database_url: str = ""
    conductor_key: str = ""
    conductor_url: str = ""


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
    opik: OpikSettings = Field(default_factory=OpikSettings)
    timeout: TimeoutSettings = Field(default_factory=TimeoutSettings)
    dbos: DBOSSettings = Field(default_factory=DBOSSettings)


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
