"""
Guardrail limits models
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator


class ViolationSeverity(str, Enum):
    """Violation severity levels."""
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class GuardrailLimits(BaseModel):
    """Guardrail limits configuration."""
    
    # Daily limits
    max_trades_per_day: int = Field(default=50, ge=1, description="Maximum trades per day")
    daily_loss_cap_usd: Decimal = Field(default=Decimal("1000.0"), ge=0, description="Daily loss cap in USD")
    
    # Position limits
    max_contracts: int = Field(default=10, ge=1, description="Maximum contracts per position")
    
    # Session windows (HH:MM format)
    session_windows: List[str] = Field(
        default=["09:30-16:00"], 
        description="Trading session windows in HH:MM-HH:MM format"
    )
    
    # Additional limits
    max_position_size_usd: Decimal = Field(default=Decimal("50000.0"), ge=0, description="Maximum position size in USD")
    max_daily_volume_usd: Decimal = Field(default=Decimal("100000.0"), ge=0, description="Maximum daily volume in USD")
    
    @validator('session_windows')
    def validate_session_windows(cls, v):
        """Validate session window format."""
        for window in v:
            try:
                start_str, end_str = window.split('-')
                from datetime import time
                time.fromisoformat(start_str)
                time.fromisoformat(end_str)
            except (ValueError, IndexError):
                raise ValueError(f"Invalid session window format: {window}. Use HH:MM-HH:MM")
        return v
    
    @validator('daily_loss_cap_usd', 'max_position_size_usd', 'max_daily_volume_usd')
    def validate_positive_decimals(cls, v):
        """Validate positive decimal values."""
        if v < 0:
            raise ValueError('Value must be non-negative')
        return v


class GuardrailViolation(BaseModel):
    """Guardrail violation record."""
    
    violation_id: UUID = Field(default_factory=uuid4, description="Unique violation identifier")
    violation_type: str = Field(..., description="Type of violation")
    severity: ViolationSeverity = Field(..., description="Violation severity")
    message: str = Field(..., description="Human-readable violation message")
    current_value: Any = Field(..., description="Current value that triggered violation")
    limit_value: Any = Field(..., description="Limit value that was exceeded")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Violation timestamp")
    resolved: bool = Field(default=False, description="Whether violation is resolved")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional violation data")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
            Decimal: lambda v: float(v)
        }


class GuardrailStatus(BaseModel):
    """Guardrail status model."""
    
    halted: bool = Field(..., description="Whether trading is halted")
    daily_trades: int = Field(..., description="Daily trades count")
    daily_loss_usd: Decimal = Field(..., description="Daily loss in USD")
    daily_volume_usd: Decimal = Field(..., description="Daily volume in USD")
    violation_count: int = Field(..., description="Total violation count")
    unresolved_violations: int = Field(..., description="Unresolved violation count")
    current_positions: Dict[str, int] = Field(..., description="Current positions")
    session_start_equity: Decimal = Field(..., description="Session start equity")
    current_equity: Decimal = Field(..., description="Current equity")
    equity_change: Decimal = Field(..., description="Equity change from session start")
    limits: GuardrailLimits = Field(..., description="Current limits")
    last_violation: Optional[GuardrailViolation] = Field(default=None, description="Last violation")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Status timestamp")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }


class GuardrailUpdate(BaseModel):
    """Guardrail update request."""
    
    max_trades_per_day: Optional[int] = Field(default=None, ge=1, description="Maximum trades per day")
    daily_loss_cap_usd: Optional[Decimal] = Field(default=None, ge=0, description="Daily loss cap in USD")
    max_contracts: Optional[int] = Field(default=None, ge=1, description="Maximum contracts per position")
    session_windows: Optional[List[str]] = Field(default=None, description="Trading session windows")
    max_position_size_usd: Optional[Decimal] = Field(default=None, ge=0, description="Maximum position size in USD")
    max_daily_volume_usd: Optional[Decimal] = Field(default=None, ge=0, description="Maximum daily volume in USD")
    
    @validator('session_windows')
    def validate_session_windows(cls, v):
        """Validate session window format."""
        if v is not None:
            for window in v:
                try:
                    start_str, end_str = window.split('-')
                    from datetime import time
                    time.fromisoformat(start_str)
                    time.fromisoformat(end_str)
                except (ValueError, IndexError):
                    raise ValueError(f"Invalid session window format: {window}. Use HH:MM-HH:MM")
        return v
    
    @validator('daily_loss_cap_usd', 'max_position_size_usd', 'max_daily_volume_usd')
    def validate_positive_decimals(cls, v):
        """Validate positive decimal values."""
        if v is not None and v < 0:
            raise ValueError('Value must be non-negative')
        return v


class ConfigUpdate(BaseModel):
    """Configuration update request for runtime toggles."""
    
    session_windows: Optional[List[str]] = Field(default=None, description="Trading session windows in HH:MM-HH:MM format")
    ignore_session: Optional[bool] = Field(default=None, description="Bypass session window checks")
    
    @validator('session_windows')
    def validate_session_windows(cls, v):
        """Validate session window format."""
        if v is not None:
            for window in v:
                try:
                    start_str, end_str = window.split('-')
                    from datetime import time
                    time.fromisoformat(start_str)
                    time.fromisoformat(end_str)
                except (ValueError, IndexError):
                    raise ValueError(f"Invalid session window format: {window}. Use HH:MM-HH:MM")
        return v