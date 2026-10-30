"""Health check endpoint router."""

from fastapi import APIRouter, Depends
from backend.app.core.config import get_settings, Settings
from backend.app.schemas.application import get_utc_now_iso

router = APIRouter(tags=["Health"])


@router.get("/health")
@router.get("/api/health")
def check_health(settings: Settings = Depends(get_settings)):
    """Application health and runtime diagnostic information."""
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "environment": settings.environment,
        "mock_mode": settings.is_mock_mode,
        "version": "1.0.0",
        "timestamp": get_utc_now_iso(),
    }

