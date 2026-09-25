from app.core.config import Settings
from app.models.rewrite import ProviderName
from app.providers.base import RewriteProvider
from app.providers.groq import GroqProvider


def get_provider(provider: ProviderName, settings: Settings) -> RewriteProvider:
    if provider == ProviderName.groqcloud:
        return GroqProvider(settings)
    raise ValueError(f"Unsupported provider: {provider}")
