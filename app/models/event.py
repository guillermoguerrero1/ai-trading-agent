"""
Event models
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from .base import BaseModel as BaseModelWithId


class EventType(str, Enum):
    """Event types."""
    SYSTEM = "SYSTEM"
    ORDER = "ORDER"
    TRADE = "TRADE"
    POSITION = "POSITION"
    ACCOUNT = "ACCOUNT"
    RISK = "RISK"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


class EventSeverity(str, Enum):
    """Event severity levels."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Event(BaseModelWithId):
    """Event model."""
    
    event_type: EventType = Field(..., description="Event type")
    severity: EventSeverity = Field(..., description="Event severity")
    message: str = Field(..., description="Event message")
    data: Dict[str, Any] = Field(default_factory=dict, description="Event data")
    source: str = Field(..., description="Event source")
    user_id: Optional[str] = Field(default=None, description="User ID")
    session_id: Optional[str] = Field(default=None, description="Session ID")
    correlation_id: Optional[str] = Field(default=None, description="Correlation ID")
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True


class EventFilter(BaseModel):
    """Event filter parameters."""
    
    event_types: Optional[list[EventType]] = Field(default=None, description="Filter by event types")
    severities: Optional[list[EventSeverity]] = Field(default=None, description="Filter by severities")
    sources: Optional[list[str]] = Field(default=None, description="Filter by sources")
    user_id: Optional[str] = Field(default=None, description="Filter by user ID")
    session_id: Optional[str] = Field(default=None, description="Filter by session ID")
    correlation_id: Optional[str] = Field(default=None, description="Filter by correlation ID")
    start_time: Optional[datetime] = Field(default=None, description="Filter by start time")
    end_time: Optional[datetime] = Field(default=None, description="Filter by end time")
    limit: int = Field(default=100, ge=1, le=1000, description="Limit results")
    offset: int = Field(default=0, ge=0, description="Offset results")
