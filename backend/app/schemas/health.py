from pydantic import BaseModel


class HealthCheck(BaseModel):
    status: str = "ok"
    environment: str = "development"
    version: str = "0.1.0"
