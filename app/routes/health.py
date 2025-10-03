"""
Health check routes
"""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.deps import get_settings
from app.models.base import Settings

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
async def health_check(settings: Settings = Depends(get_settings)):
    """
    Health check endpoint.
    
    Returns:
        Health status information
    """
    return {
        "status": "healthy",
        "service": "ai-trading-agent",
        "version": "0.1.0",
        "environment": settings.ENVIRONMENT,
        "timezone": settings.TZ,
    }


@router.get("/ready")
async def readiness_check():
    """
    Readiness check endpoint.
    
    Returns:
        Readiness status
    """
    # TODO: Add actual readiness checks
    # - Database connectivity
    # - External service dependencies
    # - Required resources
    
    return {
        "status": "ready",
        "checks": {
            "database": "ok",
            "broker": "ok",
            "queue": "ok",
        }
    }


@router.get("/live")
async def liveness_check():
    """
    Liveness check endpoint.
    
    Returns:
        Liveness status
    """
    return {
        "status": "alive",
        "timestamp": "2024-01-01T00:00:00Z",
    }
