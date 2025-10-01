"""
P&L models
"""

from datetime import datetime
from datetime import date as Date
from decimal import Decimal
from typing import Optional, Dict, Any, List
from uuid import UUID

from pydantic import BaseModel, Field

from .base import BaseModelWithId


class PnL(BaseModelWithId):
    """P&L model."""
    
    date: Date = Field(..., description="P&L date")
    realized_pnl: Decimal = Field(default=Decimal("0"), description="Realized P&L")
    unrealized_pnl: Decimal = Field(default=Decimal("0"), description="Unrealized P&L")
    total_pnl: Decimal = Field(..., description="Total P&L")
    commission: Decimal = Field(default=Decimal("0"), description="Commission paid")
    net_pnl: Decimal = Field(..., description="Net P&L (after commission)")
    trades_count: int = Field(default=0, description="Number of trades")
    winning_trades: int = Field(default=0, description="Number of winning trades")
    losing_trades: int = Field(default=0, description="Number of losing trades")
    win_rate: Decimal = Field(default=Decimal("0"), description="Win rate")
    avg_win: Decimal = Field(default=Decimal("0"), description="Average win")
    avg_loss: Decimal = Field(default=Decimal("0"), description="Average loss")
    largest_win: Decimal = Field(default=Decimal("0"), description="Largest win")
    largest_loss: Decimal = Field(default=Decimal("0"), description="Largest loss")
    broker: str = Field(..., description="Broker name")
    user_id: Optional[str] = Field(default=None, description="User ID")
    session_id: Optional[str] = Field(default=None, description="Session ID")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="P&L metadata")
    
    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat(),
            Date: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }
    }


class PnLSummary(BaseModel):
    """P&L summary model."""
    
    period: str = Field(..., description="Period (daily, weekly, monthly, yearly)")
    start_date: Date = Field(..., description="Start date")
    end_date: Date = Field(..., description="End date")
    total_pnl: Decimal = Field(..., description="Total P&L")
    realized_pnl: Decimal = Field(..., description="Realized P&L")
    unrealized_pnl: Decimal = Field(..., description="Unrealized P&L")
    commission: Decimal = Field(..., description="Total commission")
    net_pnl: Decimal = Field(..., description="Net P&L")
    trades_count: int = Field(..., description="Total trades")
    winning_trades: int = Field(..., description="Winning trades")
    losing_trades: int = Field(..., description="Losing trades")
    win_rate: Decimal = Field(..., description="Win rate")
    avg_win: Decimal = Field(..., description="Average win")
    avg_loss: Decimal = Field(..., description="Average loss")
    largest_win: Decimal = Field(..., description="Largest win")
    largest_loss: Decimal = Field(..., description="Largest loss")
    max_drawdown: Decimal = Field(..., description="Maximum drawdown")
    sharpe_ratio: Optional[Decimal] = Field(default=None, description="Sharpe ratio")
    sortino_ratio: Optional[Decimal] = Field(default=None, description="Sortino ratio")
    broker: str = Field(..., description="Broker name")
    user_id: Optional[str] = Field(default=None, description="User ID")
    session_id: Optional[str] = Field(default=None, description="Session ID")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Summary creation time")
    
    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat(),
            Date: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }
    }


class PnLFilter(BaseModel):
    """P&L filter parameters."""
    
    start_date: Optional[Date] = Field(default=None, description="Start date")
    end_date: Optional[Date] = Field(default=None, description="End date")
    broker: Optional[str] = Field(default=None, description="Filter by broker")
    user_id: Optional[str] = Field(default=None, description="Filter by user ID")
    session_id: Optional[str] = Field(default=None, description="Filter by session ID")
    min_pnl: Optional[Decimal] = Field(default=None, description="Minimum P&L")
    max_pnl: Optional[Decimal] = Field(default=None, description="Maximum P&L")
    limit: int = Field(default=100, ge=1, le=1000, description="Limit results")
    offset: int = Field(default=0, ge=0, description="Offset results")


class Trade(BaseModel):
    """Trade model."""
    
    trade_id: str = Field(..., description="Trade ID")
    order_id: str = Field(..., description="Order ID")
    symbol: str = Field(..., description="Trading symbol")
    side: str = Field(..., description="Trade side")
    quantity: Decimal = Field(..., description="Trade quantity")
    price: Decimal = Field(..., description="Trade price")
    commission: Decimal = Field(..., description="Commission")
    realized_pnl: Decimal = Field(..., description="Realized P&L")
    timestamp: datetime = Field(..., description="Trade timestamp")
    broker: str = Field(..., description="Broker name")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }
