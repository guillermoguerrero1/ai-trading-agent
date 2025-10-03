from __future__ import annotations
from datetime import datetime
from typing import Optional, Dict, Any
from sqlmodel import SQLModel, Field, JSON

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
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    entered_at: Optional[datetime] = None
    exited_at: Optional[datetime] = None

    # outcome
    exit_price: Optional[float] = None
    pnl_usd: Optional[float] = None
    r_multiple: Optional[float] = None
    outcome: Optional[str] = None  # "target", "stop", "manual_exit", "cancelled", "partial", "error"

    # context/features captured at entry time (free-form)
    features: Optional[Dict[str, Any]] = Field(default=None, sa_type=JSON)
    notes: Optional[str] = None
