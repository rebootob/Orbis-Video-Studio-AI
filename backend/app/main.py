from fastapi import FastAPI
from app.core.config import settings
from app.api.v1.api import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)


@app.get("/health", tags=["health"])
def root_health():
    """
    Top-level application health check.
    """
    return {"status": "ok"}


app.include_router(api_router, prefix=settings.API_V1_STR)
