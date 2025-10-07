"""
Order models
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field

from .base import BaseModel as BaseModelWithId


class OrderSide(str, Enum):
    """Order sides."""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    """Order types."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class OrderStatus(str, Enum):
    """Order statuses."""
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class OrderRequest(BaseModel):
    """Order request model."""
    
    symbol: str = Field(..., description="Trading symbol")
    side: OrderSide = Field(..., description="Order side")
    quantity: Decimal = Field(..., gt=0, description="Order quantity")
    order_type: OrderType = Field(..., description="Order type")
    price: Optional[Decimal] = Field(default=None, description="Order price (for limit orders)")
    stop_price: Optional[Decimal] = Field(default=None, description="Stop price (for stop orders)")
    time_in_force: str = Field(default="DAY", description="Time in force")
    client_order_id: Optional[str] = Field(default=None, description="Client order ID")
    entered_at: Optional[datetime] = Field(default=None, description="Custom entry timestamp for backfilled trades")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Order metadata")
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True


class OrderResponse(BaseModel):
    """Order response model."""
    
    order_id: str = Field(..., description="Order ID")
    client_order_id: Optional[str] = Field(default=None, description="Client order ID")
    symbol: str = Field(..., description="Trading symbol")
    side: OrderSide = Field(..., description="Order side")
    quantity: Decimal = Field(..., description="Order quantity")
    filled_quantity: Decimal = Field(default=Decimal("0"), description="Filled quantity")
    order_type: OrderType = Field(..., description="Order type")
    price: Optional[Decimal] = Field(default=None, description="Order price")
    stop_price: Optional[Decimal] = Field(default=None, description="Stop price")
    status: OrderStatus = Field(..., description="Order status")
    time_in_force: str = Field(..., description="Time in force")
    created_at: datetime = Field(..., description="Order creation time")
    updated_at: datetime = Field(..., description="Order update time")
    filled_at: Optional[datetime] = Field(default=None, description="Order fill time")
    cancelled_at: Optional[datetime] = Field(default=None, description="Order cancellation time")
    commission: Optional[Decimal] = Field(default=None, description="Commission")
    broker: str = Field(..., description="Broker name")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Order metadata")
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }


class Order(BaseModelWithId):
    """Order model."""
    
    order_id: str = Field(..., description="Order ID")
    client_order_id: Optional[str] = Field(default=None, description="Client order ID")
    symbol: str = Field(..., description="Trading symbol")
    side: OrderSide = Field(..., description="Order side")
    quantity: Decimal = Field(..., description="Order quantity")
    filled_quantity: Decimal = Field(default=Decimal("0"), description="Filled quantity")
    order_type: OrderType = Field(..., description="Order type")
    price: Optional[Decimal] = Field(default=None, description="Order price")
    stop_price: Optional[Decimal] = Field(default=None, description="Stop price")
    status: OrderStatus = Field(..., description="Order status")
    time_in_force: str = Field(..., description="Time in force")
    filled_at: Optional[datetime] = Field(default=None, description="Order fill time")
    cancelled_at: Optional[datetime] = Field(default=None, description="Order cancellation time")
    commission: Optional[Decimal] = Field(default=None, description="Commission")
    broker: str = Field(..., description="Broker name")
    user_id: Optional[str] = Field(default=None, description="User ID")
    session_id: Optional[str] = Field(default=None, description="Session ID")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Order metadata")
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True


class OrderFilter(BaseModel):
    """Order filter parameters."""
    
    symbols: Optional[list[str]] = Field(default=None, description="Filter by symbols")
    sides: Optional[list[OrderSide]] = Field(default=None, description="Filter by sides")
    statuses: Optional[list[OrderStatus]] = Field(default=None, description="Filter by statuses")
    order_types: Optional[list[OrderType]] = Field(default=None, description="Filter by order types")
    broker: Optional[str] = Field(default=None, description="Filter by broker")
    user_id: Optional[str] = Field(default=None, description="Filter by user ID")
    session_id: Optional[str] = Field(default=None, description="Filter by session ID")
    start_time: Optional[datetime] = Field(default=None, description="Filter by start time")
    end_time: Optional[datetime] = Field(default=None, description="Filter by end time")
    limit: int = Field(default=100, ge=1, le=1000, description="Limit results")
    offset: int = Field(default=0, ge=0, description="Offset results")
