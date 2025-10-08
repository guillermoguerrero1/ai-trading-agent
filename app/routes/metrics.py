"""
Prometheus metrics routes
"""

from fastapi import APIRouter, Response, Depends
from fastapi.responses import PlainTextResponse

from app.services.metrics import get_metrics_service
from app.models.base import Settings
from app.deps import get_settings

router = APIRouter(prefix="/metrics", tags=["metrics"])

@router.get("/prom")
async def get_prometheus_metrics(
    response: Response,
    settings: Settings = Depends(get_settings)
):
    """
    Get metrics in Prometheus format.
    
    Returns:
        Prometheus-formatted metrics
    """
    metrics_service = get_metrics_service()
    
    # Update environment in version metric
    metrics_service.process_version.labels(
        version='0.1.0',
        environment=settings.ENVIRONMENT
    ).set(1)
    
    # Get metrics
    metrics_data = metrics_service.get_metrics()
    
    # Set content type for Prometheus
    response.headers["Content-Type"] = "text/plain; version=0.0.4; charset=utf-8"
    
    return PlainTextResponse(
        content=metrics_data,
        media_type="text/plain; version=0.0.4; charset=utf-8"
    )

@router.get("/debug")
async def get_metrics_debug():
    """
    Get metrics in debug format (JSON).
    
    Returns:
        Metrics debug information
    """
    metrics_service = get_metrics_service()
    return metrics_service.get_metrics_dict()
