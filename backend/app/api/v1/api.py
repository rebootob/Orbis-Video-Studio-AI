from fastapi import APIRouter
from app.api.v1.endpoints import health, assets, document_extraction, story_generation, reference_library

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(assets.router, tags=["assets"])
api_router.include_router(document_extraction.router, tags=["document-extraction"])
api_router.include_router(story_generation.router, tags=["story-generation"])
api_router.include_router(reference_library.router, tags=["reference-library"])


