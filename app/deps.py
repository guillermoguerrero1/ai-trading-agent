"""
FastAPI dependencies
"""

from functools import lru_cache
from typing import Generator, Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.models.base import Settings

security = HTTPBearer(auto_error=False)

@lru_cache()
def get_settings() -> Settings:
    return Settings()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return "user-123"

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