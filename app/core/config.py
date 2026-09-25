from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"
    allowed_origins: list[str] = Field(default_factory=lambda: ["https://localhost:3000", "http://localhost:3000"])
    request_timeout_seconds: float = 45
    max_input_chars: int = 8000
    # GroqCloud OpenAI-compatible Chat Completions base URL.
    # The provider appends "/chat/completions" to this base.
    groq_api_base_url: str = "https://api.groq.com/openai/v1"
    # Server-side Groq API key. Loaded from .env (GROQ_API_KEY=...).
    # The .env file is the single source of truth — process env is ignored
    # so a stale GROQ_API_KEY in the user's shell cannot silently override
    # the project's configured key.
    groq_api_key: SecretStr = Field(default=SecretStr(""))
    # Base64-encoded Ed25519 private key. Keep this only in Lambda/Secrets
    # Manager; the desktop application receives only the corresponding public key.
    entitlement_private_key_b64: SecretStr = Field(default=SecretStr(""))
    SUPABASE_URL: str
    SUPABASE_KEY: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
