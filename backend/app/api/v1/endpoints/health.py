from fastapi import APIRouter
from app.core.config import settings
from app.schemas.health import HealthCheck

router = APIRouter()


@router.get("/health", response_model=HealthCheck)
def get_v1_health() -> HealthCheck:
    """
    V1 API Health Status Check Endpoint.
    """
    return HealthCheck(
        status="ok",
        environment=settings.ENVIRONMENT,
        version=settings.VERSION,
    )
