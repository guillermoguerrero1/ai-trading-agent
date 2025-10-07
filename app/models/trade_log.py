from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlmodel import SQLModel, Field, JSON
from pydantic import BaseModel

class TradeLog(SQLModel, table=True):
    __tablename__ = "trade_logs"

    id: Optional[int] = Field(default=None, primary_key=True)

    # identity
    order_id: str = Field(index=True)
    symbol: str = Field(index=True)
    side: str  # "BUY" | "SELL"
    qty: float

    # prices
    entry_price: float
    stop_price: Optional[float] = None
    target_price: Optional[float] = None

    # timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    submitted_at: Optional[datetime] = None  # When the order was submitted to the API
    entered_at: Optional[datetime] = None  # Custom entry timestamp for backfilled trades
    exited_at: Optional[datetime] = None

    # outcome
    exit_price: Optional[float] = None
    pnl_usd: Optional[float] = None
    r_multiple: Optional[float] = None
    outcome: Optional[str] = None  # "target", "stop", "manual_exit", "cancelled", "partial", "error"

    # context/features captured at entry time (free-form)
    features: Optional[Dict[str, Any]] = Field(default=None, sa_type=JSON)
    notes: Optional[str] = None
    
    # model tracking
    model_score: Optional[float] = None
    model_version: Optional[str] = None  # e.g., file hash or timestamp


class TradeLogRequest(BaseModel):
    """Trade log request model for creating new trade logs."""
    
    # identity
    order_id: str
    symbol: str
    side: str  # "BUY" | "SELL"
    qty: float
    
    # prices
    entry_price: float
    stop_price: Optional[float] = None
    target_price: Optional[float] = None
    
    # timestamps
    submitted_at: Optional[datetime] = None  # When the order was submitted to the API
    entered_at: Optional[datetime] = None  # Custom entry timestamp for backfilled trades (timezone-aware)
    
    # outcome (optional for new trades)
    exit_price: Optional[float] = None
    pnl_usd: Optional[float] = None
    r_multiple: Optional[float] = None
    outcome: Optional[str] = None
    
    # context/features
    features: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    
    # model tracking
    model_score: Optional[float] = None
    model_version: Optional[str] = None
