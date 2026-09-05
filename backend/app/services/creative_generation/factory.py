from app.core.config import settings
from app.services.creative_generation.base import CreativeGenerationProvider
from app.services.creative_generation.openai_provider import OpenAICreativeGenerationProvider


def get_creative_provider() -> CreativeGenerationProvider:
    """Dependency provider for FastAPI endpoint dependency injection."""
    return OpenAICreativeGenerationProvider()
