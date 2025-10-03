"""
Base models and settings
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Any, Dict
from uuid import UUID, uuid4
from functools import lru_cache

from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    # Core
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Timezone (prefer TZ; accept DEFAULT_TIMEZONE via alias)
    TZ: str = Field("America/Phoenix", alias="DEFAULT_TIMEZONE")

    # DB / API
    DATABASE_URL: str = "sqlite:///./trading_agent.db"
    DATABASE_ECHO: bool = False
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_WORKERS: int = 1

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_DIR: str = "./logs"

    # Broker & Risk (aliases for Cursor-style names)
    BROKER: str = Field("paper", alias="BROKER_TYPE")
    INITIAL_CAPITAL: float = 100000.0
    MAX_CONTRACTS: int = Field(5, alias="MAX_ORDER_SIZE")
    MAX_POSITION_SIZE_USD: float = 50000.0
    MAX_DAILY_VOLUME_USD: float = 100000.0
    DAILY_LOSS_CAP_USD: float = Field(300.0, alias="MAX_DAILY_LOSS")
    MAX_TRADES_PER_DAY: int = Field(5, alias="MAX_DAILY_TRADES")
    POSITION_LIMIT_PCT: float = 0.1
    ENABLE_RISK_MANAGEMENT: bool = True

    # Market data
    DATA_BUFFER_SIZE: int = 1000
    MARKET_DATA_UPDATE_INTERVAL: float = 1.0

    # Sessions: prefer SESSION_WINDOWS; fallback to start/end/days
    SESSION_WINDOWS: Optional[List[str]] = None
    SESSION_PROVIDER: str = "none"  # "cme" for CME provider, "none" for default
    TRADING_START_TIME: Optional[str] = None  # "09:30"
    TRADING_END_TIME: Optional[str] = None    # "16:00"
    TRADING_DAYS: Optional[str] = None        # "0,1,2,3,4"

    @property
    def session_windows_normalized(self) -> List[str]:
        # If SESSION_WINDOWS provided → use it
        if self.SESSION_WINDOWS:
            return self.SESSION_WINDOWS
        
        # Else if SESSION_PROVIDER == "cme" → import and call get_rth_windows
        if self.SESSION_PROVIDER == "cme":
            try:
                from config.providers.cme import get_rth_windows
                return get_rth_windows(self.TZ)
            except Exception as e:
                logging.warning(f"Failed to load CME session windows: {e}. Falling back to default.")
                return ["08:30-15:00"]
        
        # Else if TRADING_START_TIME/END_TIME provided → use that range
        if self.TRADING_START_TIME and self.TRADING_END_TIME:
            return [f"{self.TRADING_START_TIME}-{self.TRADING_END_TIME}"]
        
        # Default to a reasonable RTH window if nothing is set
        return ["08:30-15:00"]
    
    @property
    def session_windows(self) -> List[str]:
        """Alias for session_windows_normalized."""
        return self.session_windows_normalized
    
    @property
    def initial_capital(self) -> float:
        """Alias for INITIAL_CAPITAL."""
        return self.INITIAL_CAPITAL
    
    @property
    def max_trades_per_day(self) -> int:
        """Alias for MAX_TRADES_PER_DAY."""
        return self.MAX_TRADES_PER_DAY
    
    @property
    def daily_loss_cap_usd(self) -> float:
        """Alias for DAILY_LOSS_CAP_USD."""
        return self.DAILY_LOSS_CAP_USD
    
    @property
    def max_contracts(self) -> int:
        """Alias for MAX_CONTRACTS."""
        return self.MAX_CONTRACTS
    
    @property
    def max_position_size_usd(self) -> float:
        """Alias for MAX_POSITION_SIZE_USD."""
        return self.MAX_POSITION_SIZE_USD
    
    @property
    def max_daily_volume_usd(self) -> float:
        """Alias for MAX_DAILY_VOLUME_USD."""
        return self.MAX_DAILY_VOLUME_USD


class BaseModelWithId(BaseModel):
    """Base model with common fields."""
    
    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    
    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
            Decimal: lambda v: float(v)
        }
    }


class PaginationParams(BaseModel):
    """Pagination parameters."""
    
    page: int = Field(default=1, ge=1, description="Page number")
    size: int = Field(default=50, ge=1, le=1000, description="Page size")
    
    @property
    def offset(self) -> int:
        """Calculate offset."""
        return (self.page - 1) * self.size


class PaginatedResponse(BaseModel):
    """Paginated response."""
    
    items: List[Any] = Field(..., description="Items")
    total: int = Field(..., description="Total count")
    page: int = Field(..., description="Current page")
    size: int = Field(..., description="Page size")
    pages: int = Field(..., description="Total pages")
    
    @classmethod
    def create(cls, items: List[Any], total: int, page: int, size: int) -> "PaginatedResponse":
        """Create paginated response."""
        pages = (total + size - 1) // size
        return cls(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages
        )