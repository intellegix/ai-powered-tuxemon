# Backend Configuration for AI-Powered Tuxemon
# Austin Kidwell | Intellegix | Mobile-First Pokemon-Style Game

from typing import Optional
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuration settings for the AI-Powered Tuxemon backend."""

    # Application
    app_name: str = "AI-Powered Tuxemon Backend"
    app_version: str = "1.0.0"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False

    # Database
    database_url: str = Field(
        default="postgresql://tuxemon:tuxemon@localhost:5432/tuxemon",
        description="PostgreSQL connection URL"
    )

    # Vector Database (Qdrant)
    qdrant_url: str = Field(
        default="http://localhost:6333",
        description="Qdrant vector database URL"
    )
    qdrant_api_key: Optional[str] = None

    # Redis Cache
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for caching"
    )

    # Authentication
    jwt_secret_key: str = Field(
        default="your-super-secret-jwt-key-change-this-in-production",
        description="Secret key for JWT token generation"
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # AI Configuration
    claude_api_key: Optional[str] = Field(
        default=None,
        description="Anthropic Claude API key"
    )
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key for fallback"
    )

    # Local LLM Configuration
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Ollama API base URL"
    )
    local_llm_model: str = Field(
        default="mistral:7b",
        description="Local LLM model name (mistral:7b or phi3:mini)"
    )
    local_llm_enabled: bool = True

    # AI Settings
    ai_enabled: bool = True
    ai_cache_ttl: int = 3600  # Cache AI responses for 1 hour
    ai_timeout_seconds: int = 5  # Max time for AI response
    ai_fallback_enabled: bool = True

    # Cost Control
    max_claude_requests_per_day: int = 1000
    max_cost_per_day_usd: float = 50.0

    # Game Settings
    max_players_per_session: int = 100
    world_save_interval_seconds: int = 300  # 5 minutes
    combat_timeout_seconds: int = 60

    # Monitoring
    log_level: str = "INFO"
    sentry_dsn: Optional[str] = None
    enable_metrics: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()