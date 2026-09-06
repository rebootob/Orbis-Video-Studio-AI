from fastapi import APIRouter
from app.api.v1.endpoints import (
    health,
    assets,
    document_extraction,
    story_generation,
    reference_library,
    generation_queue,
    projects,
    shots,
    locks,
    cost_ledger,
    orchestration,
    audio,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(projects.router, tags=["projects"])
api_router.include_router(orchestration.router, tags=["orchestration"])
api_router.include_router(assets.router, tags=["assets"])
api_router.include_router(document_extraction.router, tags=["document-extraction"])
api_router.include_router(story_generation.router, tags=["story-generation"])
api_router.include_router(reference_library.router, tags=["reference-library"])
api_router.include_router(generation_queue.router, tags=["generation-queue"])
api_router.include_router(shots.router, tags=["shots"])
api_router.include_router(locks.router, tags=["locks"])
api_router.include_router(cost_ledger.router, tags=["costs"])
api_router.include_router(audio.router, tags=["audio"])


