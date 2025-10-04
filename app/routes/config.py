"""
Configuration routes
"""

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional, List

from app.deps import get_settings, get_supervisor, get_current_user
from app.models.base import Settings
from app.models.limits import GuardrailLimits, GuardrailUpdate, ConfigUpdate
from app.services.supervisor import Supervisor

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/")
async def get_config(
    request: Request,
    settings: Settings = Depends(get_settings),
    supervisor: Supervisor = Depends(get_supervisor)
):
    """
    Get current configuration including effective session windows and runtime toggles.
    
    Returns:
        Current configuration settings with effective values
    """
    try:
        # Get effective session windows and ignore_session from supervisor
        effective_session_windows = supervisor.get_effective_session_windows(settings)
        effective_ignore_session = supervisor.get_effective_ignore_session()
    except Exception as e:
        return {"error": f"Supervisor error: {str(e)}", "type": type(e).__name__}
    
    return {
        "session_windows": {
            "configured": settings.session_windows_normalized,
            "effective": effective_session_windows,
            "runtime_override": supervisor.runtime_session_windows,
        },
        "ignore_session": {
            "effective": effective_ignore_session,
            "runtime_override": supervisor.runtime_ignore_session,
        },
        "require_model_gate": {
            "effective": bool(getattr(request.app.state, "require_model_gate", False)),
        },
        "broker": settings.BROKER,
        "timezone": settings.TZ,
        "session_provider": settings.SESSION_PROVIDER,
    }


@router.put("/")
async def update_config(
    config_update: ConfigUpdate,
    request: Request,
    current_user: dict = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
    supervisor: Supervisor = Depends(get_supervisor)
):
    """
    Update runtime configuration for session windows and bypass flags.
    
    Args:
        config_update: Configuration update request with session_windows and ignore_session
        
    Returns:
        Updated configuration status
    """
    try:
        # Update supervisor runtime configuration
        await supervisor.update_runtime_config(
            session_windows=config_update.session_windows,
            ignore_session=config_update.ignore_session
        )
        
        # Update model gate toggle if provided
        if config_update.require_model_gate is not None:
            request.app.state.require_model_gate = bool(config_update.require_model_gate)
        
        # Get effective values after update
        effective_session_windows = supervisor.get_effective_session_windows(settings)
        effective_ignore_session = supervisor.get_effective_ignore_session()
        effective_model_gate = bool(getattr(request.app.state, "require_model_gate", False))
        
        return {
            "message": "Runtime configuration updated successfully",
            "session_windows": {
                "configured": settings.session_windows_normalized,
                "effective": effective_session_windows,
                "runtime_override": supervisor.runtime_session_windows,
            },
            "ignore_session": {
                "effective": effective_ignore_session,
                "runtime_override": supervisor.runtime_ignore_session,
            },
            "require_model_gate": {
                "effective": effective_model_gate,
            },
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Configuration update failed: {str(e)}")


