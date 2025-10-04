"""
FastAPI dependencies
"""

import jwt
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Generator, Optional, Dict, Any
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.models.base import Settings
import structlog

logger = structlog.get_logger(__name__)

security = HTTPBearer(auto_error=False)

@lru_cache()
def get_settings() -> Settings:
    return Settings()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: Settings = Depends(get_settings)
) -> Dict[str, Any]:
    """
    Validate JWT token and return user information.
    
    Args:
        credentials: HTTP Bearer token credentials
        settings: Application settings
        
    Returns:
        User information from JWT payload
        
    Raises:
        HTTPException: If token is invalid, expired, or missing
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Decode and validate JWT token
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
            options={
                "verify_exp": True,  # Verify expiration
                "verify_nbf": True,  # Verify not before
                "verify_aud": True,  # Verify audience
                "verify_iss": True,  # Verify issuer
            }
        )
        
        # Extract user information
        user_id = payload.get("sub", "unknown")
        username = payload.get("username", "unknown")
        roles = payload.get("roles", [])
        
        # Log successful authentication
        logger.info("User authenticated successfully", 
                   user_id=user_id, 
                   username=username,
                   roles=roles)
        
        return {
            "user_id": user_id,
            "username": username,
            "roles": roles,
            "exp": payload.get("exp"),
            "iat": payload.get("iat"),
            "aud": payload.get("aud"),
            "iss": payload.get("iss")
        }
        
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token expired", token=credentials.credentials[:20] + "...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    except jwt.InvalidTokenError as e:
        logger.warning("Invalid JWT token", error=str(e), token=credentials.credentials[:20] + "...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    except Exception as e:
        logger.error("JWT validation error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication error"
        )

def get_risk_guard(request: Request) -> "RiskGuard":
    svc = getattr(request.app.state, "risk_guard", None)
    if svc is None:
        raise HTTPException(status_code=503, detail="RiskGuard not initialized")
    return svc

def get_supervisor(request: Request) -> "Supervisor":
    svc = getattr(request.app.state, "supervisor", None)
    if svc is None:
        raise HTTPException(status_code=503, detail="Supervisor not initialized")
    return svc

def get_queue_service(request: Request) -> "QueueService":
    svc = getattr(request.app.state, "queue_service", None)
    if svc is None:
        raise HTTPException(status_code=503, detail="QueueService not initialized")
    return svc

def get_trade_logger(request: Request) -> "TradeLogger":
    svc = getattr(request.app.state, "trade_logger", None)
    if svc is None:
        raise HTTPException(status_code=503, detail="TradeLogger not initialized")
    return svc