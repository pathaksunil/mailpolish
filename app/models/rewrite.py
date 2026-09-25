from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ProviderName(str, Enum):
    groqcloud = "groqcloud"


# class RewriteMode(str):
#    pass


# GroqCloud models supported for rewriting (text generation).
# Prompt-guard models are intentionally excluded — they are classifiers,
# not text generators, and will produce empty or nonsensical rewrites.
SUPPORTED_GROQ_MODELS = {
    "openai/gpt-oss-20b",  # default
    "openai/gpt-oss-120b",
    "qwen/qwen3.8-27b",
    "qwen/qwen3.6-27b",
    "groq/compound-mini",
}

# Models that should never be offered in rewrite model selection because
# they serve a different purpose (prompt-injection guard classifiers).
READONLY_MODELS = {
    "meta-llama/llama-prompt-guard-2-86m",
    "meta-llama/llama-prompt-guard-2-22m",
}

ALL_KNOWN_MODELS = SUPPORTED_GROQ_MODELS | READONLY_MODELS

class RewriteRequest(BaseModel):
    """Request body for a rewrite call.

    The Groq API key is no longer required in the request — the API holds
    it server-side (loaded from its own .env / process environment).
    Clients only need to choose a model, mode, and provide the text.
    """
    provider: ProviderName = ProviderName.groqcloud
    model: str = Field(
        default="openai/gpt-oss-20b",
        min_length=3,
        max_length=160,
    )
    mode: str
    max_words: int = Field(default=200, ge=10, le=1000)  # Add this
    instructions: str = Field(default="", max_length=500) # Add this
    output_format: Literal["plain_text", "markdown"] = "plain_text"
    text: str = Field(
        min_length=1,
        max_length=1000,
    )

    @field_validator("model")
    @classmethod
    def validate_model(cls, value: str) -> str:
        if value not in SUPPORTED_GROQ_MODELS:
            raise ValueError(
                "Unsupported GroqCloud model."
            )
        return value

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Text cannot be empty.")
        return cleaned

class RewriteResponse(BaseModel):
    rewritten_text: str = Field(alias="rewrittenText")
    provider: ProviderName
    model: str
