"""
Base broker protocol and models
"""

from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, Any, Optional, AsyncGenerator
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


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
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Order metadata")
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_encoders = {
            Decimal: lambda v: float(v)
        }


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


class StatusUpdate(BaseModel):
    """Status update model."""
    
    update_type: str = Field(..., description="Type of update")
    data: Dict[str, Any] = Field(..., description="Update data")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Update timestamp")
    broker: str = Field(..., description="Broker name")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }


class BrokerError(Exception):
    """Base broker error."""
    pass


class ConnectionError(BrokerError):
    """Broker connection error."""
    pass


class AuthenticationError(BrokerError):
    """Broker authentication error."""
    pass


class OrderError(BrokerError):
    """Order-related error."""
    pass


class IBroker(ABC):
    """Broker interface protocol."""
    
    @abstractmethod
    async def connect(self) -> None:
        """Connect to broker."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from broker."""
        pass
    
    @abstractmethod
    async def place_order(self, order_request: OrderRequest) -> OrderResponse:
        """Place an order."""
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        pass
    
    @abstractmethod
    async def get_positions(self) -> list[Position]:
        """Get current positions."""
        pass
    
    @abstractmethod
    async def get_account(self) -> Account:
        """Get account information."""
        pass
    
    @abstractmethod
    async def status_stream(self) -> AsyncGenerator[StatusUpdate, None]:
        """Get status updates stream."""
        pass
