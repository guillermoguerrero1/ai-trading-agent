"""
Broker-specific routes for different execution adapters
"""

from fastapi import APIRouter, Request, HTTPException
from typing import Dict, Any
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/broker", tags=["broker"])

@router.get("/ibkr/health")
async def ibkr_health(request: Request) -> Dict[str, Any]:
    """
    Get IBKR broker health status.
    
    Returns:
        IBKR broker health information
    """
    try:
        # Check if IBKR adapter is available in app state
        if not hasattr(request.app.state, 'ibkr_adapter'):
            return {
                "status": "disabled",
                "message": "IBKR adapter not initialized",
                "broker": "ibkr",
                "enabled": False,
                "connected": False,
                "authenticated": False,
                "credentials_provided": False
            }
        
        ibkr_adapter = request.app.state.ibkr_adapter
        
        # Get status from adapter
        status = ibkr_adapter.get_status()
        
        # Determine overall health
        if status["enabled"]:
            if status["connected"]:
                if status["authenticated"]:
                    health_status = "healthy"
                    message = "IBKR broker is connected and authenticated"
                else:
                    health_status = "warning"
                    message = "IBKR broker is connected but not authenticated"
            else:
                health_status = "error"
                message = "IBKR broker is not connected"
        else:
            health_status = "disabled"
            message = "IBKR broker is disabled (BROKER != 'ibkr')"
        
        return {
            "status": health_status,
            "message": message,
            "broker": "ibkr",
            **status
        }
        
    except Exception as e:
        logger.error("IBKR health check failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"IBKR health check failed: {str(e)}"
        )

@router.get("/paper/health")
async def paper_health(request: Request) -> Dict[str, Any]:
    """
    Get Paper broker health status.
    
    Returns:
        Paper broker health information
    """
    try:
        # Check if paper broker is available in app state
        if not hasattr(request.app.state, 'paper_broker'):
            return {
                "status": "disabled",
                "message": "Paper broker not initialized",
                "broker": "paper",
                "connected": False
            }
        
        paper_broker = request.app.state.paper_broker
        
        # Get status from broker
        status = paper_broker.get_status()
        
        # Determine overall health
        if status.get("connected", False):
            health_status = "healthy"
            message = "Paper broker is connected and ready"
        else:
            health_status = "error"
            message = "Paper broker is not connected"
        
        return {
            "status": health_status,
            "message": message,
            "broker": "paper",
            **status
        }
        
    except Exception as e:
        logger.error("Paper broker health check failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Paper broker health check failed: {str(e)}"
        )

@router.get("/health")
async def broker_health(request: Request) -> Dict[str, Any]:
    """
    Get overall broker health status.
    
    Returns:
        Overall broker health information
    """
    try:
        brokers = {}
        
        # Check IBKR broker
        try:
            ibkr_health = await ibkr_health(request)
            brokers["ibkr"] = ibkr_health
        except Exception as e:
            brokers["ibkr"] = {
                "status": "error",
                "message": f"IBKR health check failed: {str(e)}",
                "broker": "ibkr"
            }
        
        # Check Paper broker
        try:
            paper_health = await paper_health(request)
            brokers["paper"] = paper_health
        except Exception as e:
            brokers["paper"] = {
                "status": "error",
                "message": f"Paper broker health check failed: {str(e)}",
                "broker": "paper"
            }
        
        # Determine overall status
        enabled_brokers = [name for name, health in brokers.items() 
                          if health.get("enabled", True) and health.get("status") == "healthy"]
        
        if enabled_brokers:
            overall_status = "healthy"
            message = f"Brokers healthy: {', '.join(enabled_brokers)}"
        else:
            overall_status = "warning"
            message = "No healthy brokers available"
        
        return {
            "status": overall_status,
            "message": message,
            "brokers": brokers
        }
        
    except Exception as e:
        logger.error("Broker health check failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Broker health check failed: {str(e)}"
        )
