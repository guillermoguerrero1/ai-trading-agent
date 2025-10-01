"""
Account models
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field

from .base import BaseModel as BaseModelWithId


class Account(BaseModel):
    """Account model."""
    
    account_id: str = Field(..., description="Account ID")
    equity: Decimal = Field(..., description="Account equity")
    cash: Decimal = Field(..., description="Available cash")
    buying_power: Decimal = Field(..., description="Buying power")
    margin_used: Decimal = Field(..., description="Margin used")
    margin_available: Decimal = Field(..., description="Margin available")
    day_trading_buying_power: Optional[Decimal] = Field(default=None, description="Day trading buying power")
    overnight_buying_power: Optional[Decimal] = Field(default=None, description="Overnight buying power")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Account timestamp")
    broker: str = Field(..., description="Broker name")
    currency: str = Field(default="USD", description="Account currency")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }


class AccountState(BaseModelWithId):
    """Account state model."""
    
    account_id: str = Field(..., description="Account ID")
    equity: Decimal = Field(..., description="Account equity")
    cash: Decimal = Field(..., description="Available cash")
    buying_power: Decimal = Field(..., description="Buying power")
    margin_used: Decimal = Field(..., description="Margin used")
    margin_available: Decimal = Field(..., description="Margin available")
    day_trading_buying_power: Optional[Decimal] = Field(default=None, description="Day trading buying power")
    overnight_buying_power: Optional[Decimal] = Field(default=None, description="Overnight buying power")
    broker: str = Field(..., description="Broker name")
    currency: str = Field(default="USD", description="Account currency")
    user_id: Optional[str] = Field(default=None, description="User ID")
    session_id: Optional[str] = Field(default=None, description="Session ID")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Account metadata")


class Position(BaseModel):
    """Position model."""
    
    symbol: str = Field(..., description="Trading symbol")
    quantity: Decimal = Field(..., description="Position quantity")
    avg_price: Decimal = Field(..., description="Average price")
    market_price: Decimal = Field(..., description="Current market price")
    market_value: Decimal = Field(..., description="Market value")
    unrealized_pnl: Decimal = Field(..., description="Unrealized P&L")
    realized_pnl: Decimal = Field(default=Decimal("0"), description="Realized P&L")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Position timestamp")
    broker: str = Field(..., description="Broker name")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }


class PositionState(BaseModelWithId):
    """Position state model."""
    
    symbol: str = Field(..., description="Trading symbol")
    quantity: Decimal = Field(..., description="Position quantity")
    avg_price: Decimal = Field(..., description="Average price")
    market_price: Decimal = Field(..., description="Current market price")
    market_value: Decimal = Field(..., description="Market value")
    unrealized_pnl: Decimal = Field(..., description="Unrealized P&L")
    realized_pnl: Decimal = Field(default=Decimal("0"), description="Realized P&L")
    broker: str = Field(..., description="Broker name")
    user_id: Optional[str] = Field(default=None, description="User ID")
    session_id: Optional[str] = Field(default=None, description="Session ID")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Position metadata")


class AccountSummary(BaseModel):
    """Account summary model."""
    
    account_id: str = Field(..., description="Account ID")
    equity: Decimal = Field(..., description="Account equity")
    cash: Decimal = Field(..., description="Available cash")
    buying_power: Decimal = Field(..., description="Buying power")
    margin_used: Decimal = Field(..., description="Margin used")
    margin_available: Decimal = Field(..., description="Margin available")
    total_positions: int = Field(..., description="Total positions")
    total_trades: int = Field(..., description="Total trades")
    daily_trades: int = Field(..., description="Daily trades")
    daily_pnl: Decimal = Field(..., description="Daily P&L")
    total_pnl: Decimal = Field(..., description="Total P&L")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Summary timestamp")
    broker: str = Field(..., description="Broker name")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }
