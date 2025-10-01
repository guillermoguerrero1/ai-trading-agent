"""
Configuration routes
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.deps import get_settings
from app.models.base import Settings
from app.models.limits import GuardrailLimits, GuardrailUpdate

router = APIRouter(prefix="/v1/config", tags=["config"])


@router.get("/")
async def get_config(settings: Settings = Depends(get_settings)):
    """
    Get current configuration.
    
    Returns:
        Current configuration settings
    """
    return {
        "app": {
            "name": settings.app_name,
            "version": settings.app_version,
            "debug": settings.debug,
            "timezone": settings.timezone,
        },
        "api": {
            "host": settings.api_host,
            "port": settings.api_port,
            "workers": settings.api_workers,
        },
        "trading": {
            "default_broker": settings.default_broker,
            "initial_capital": float(settings.initial_capital),
            "commission_rate": float(settings.commission_rate),
        },
        "guardrails": {
            "max_trades_per_day": settings.max_trades_per_day,
            "daily_loss_cap_usd": float(settings.daily_loss_cap_usd),
            "max_contracts": settings.max_contracts,
            "max_position_size_usd": float(settings.max_position_size_usd),
            "max_daily_volume_usd": float(settings.max_daily_volume_usd),
            "session_windows": settings.session_windows,
        },
        "risk": {
            "check_interval": settings.risk_check_interval,
            "violation_cooldown": settings.violation_cooldown,
            "auto_halt_on_critical": settings.auto_halt_on_critical,
        },
        "logging": {
            "level": settings.log_level,
            "format": settings.log_format,
        },
    }


@router.put("/")
async def update_config(
    config_update: GuardrailUpdate,
    settings: Settings = Depends(get_settings)
):
    """
    Update configuration.
    
    Args:
        config_update: Configuration update request
        
    Returns:
        Updated configuration
    """
    # TODO: Implement configuration persistence
    # For now, just return the update request
    
    updated_config = {
        "max_trades_per_day": config_update.max_trades_per_day or settings.max_trades_per_day,
        "daily_loss_cap_usd": float(config_update.daily_loss_cap_usd or settings.daily_loss_cap_usd),
        "max_contracts": config_update.max_contracts or settings.max_contracts,
        "max_position_size_usd": float(config_update.max_position_size_usd or settings.max_position_size_usd),
        "max_daily_volume_usd": float(config_update.max_daily_volume_usd or settings.max_daily_volume_usd),
        "session_windows": config_update.session_windows or settings.session_windows,
    }
    
    return {
        "message": "Configuration updated successfully",
        "config": updated_config,
    }


@router.get("/guardrails")
async def get_guardrails(settings: Settings = Depends(get_settings)):
    """
    Get current guardrail limits.
    
    Returns:
        Current guardrail limits
    """
    limits = GuardrailLimits(
        max_trades_per_day=settings.max_trades_per_day,
        daily_loss_cap_usd=settings.daily_loss_cap_usd,
        max_contracts=settings.max_contracts,
        max_position_size_usd=settings.max_position_size_usd,
        max_daily_volume_usd=settings.max_daily_volume_usd,
        session_windows=settings.session_windows,
    )
    
    return limits


@router.put("/guardrails")
async def update_guardrails(
    guardrail_update: GuardrailUpdate,
    settings: Settings = Depends(get_settings)
):
    """
    Update guardrail limits.
    
    Args:
        guardrail_update: Guardrail update request
        
    Returns:
        Updated guardrail limits
    """
    # TODO: Implement guardrail persistence and validation
    # For now, just return the update request
    
    updated_limits = GuardrailLimits(
        max_trades_per_day=guardrail_update.max_trades_per_day or settings.max_trades_per_day,
        daily_loss_cap_usd=guardrail_update.daily_loss_cap_usd or settings.daily_loss_cap_usd,
        max_contracts=guardrail_update.max_contracts or settings.max_contracts,
        max_position_size_usd=guardrail_update.max_position_size_usd or settings.max_position_size_usd,
        max_daily_volume_usd=guardrail_update.max_daily_volume_usd or settings.max_daily_volume_usd,
        session_windows=guardrail_update.session_windows or settings.session_windows,
    )
    
    return {
        "message": "Guardrails updated successfully",
        "limits": updated_limits,
    }
