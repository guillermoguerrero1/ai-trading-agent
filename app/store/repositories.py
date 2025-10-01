"""
Repository layer for data access
"""

from datetime import datetime, date
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func
from sqlmodel import SQLModel

from app.models.event import Event, EventFilter
from app.models.order import Order, OrderFilter
from app.models.pnl import PnL, PnLFilter, PnLSummary
from app.models.limits import GuardrailViolation

import structlog

logger = structlog.get_logger(__name__)


class BaseRepository:
    """Base repository class."""
    
    def __init__(self, session: AsyncSession):
        """
        Initialize repository.
        
        Args:
            session: Database session
        """
        self.session = session


class EventRepository(BaseRepository):
    """Event repository."""
    
    async def create(self, event: Event) -> Event:
        """
        Create an event.
        
        Args:
            event: Event to create
            
        Returns:
            Created event
        """
        self.session.add(event)
        await self.session.commit()
        await self.session.refresh(event)
        
        logger.info("Event created", event_id=str(event.id), event_type=event.event_type)
        return event
    
    async def get_by_id(self, event_id: UUID) -> Optional[Event]:
        """
        Get event by ID.
        
        Args:
            event_id: Event ID
            
        Returns:
            Event or None
        """
        result = await self.session.execute(
            select(Event).where(Event.id == event_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_filter(self, event_filter: EventFilter) -> List[Event]:
        """
        Get events by filter.
        
        Args:
            event_filter: Event filter
            
        Returns:
            List of events
        """
        query = select(Event)
        
        # Apply filters
        if event_filter.event_types:
            query = query.where(Event.event_type.in_(event_filter.event_types))
        
        if event_filter.severities:
            query = query.where(Event.severity.in_(event_filter.severities))
        
        if event_filter.sources:
            query = query.where(Event.source.in_(event_filter.sources))
        
        if event_filter.user_id:
            query = query.where(Event.user_id == event_filter.user_id)
        
        if event_filter.session_id:
            query = query.where(Event.session_id == event_filter.session_id)
        
        if event_filter.correlation_id:
            query = query.where(Event.correlation_id == event_filter.correlation_id)
        
        if event_filter.start_time:
            query = query.where(Event.created_at >= event_filter.start_time)
        
        if event_filter.end_time:
            query = query.where(Event.created_at <= event_filter.end_time)
        
        # Apply ordering and pagination
        query = query.order_by(desc(Event.created_at))
        query = query.offset(event_filter.offset).limit(event_filter.limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_recent(self, limit: int = 100) -> List[Event]:
        """
        Get recent events.
        
        Args:
            limit: Maximum number of events
            
        Returns:
            List of recent events
        """
        query = select(Event).order_by(desc(Event.created_at)).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()


class OrderRepository(BaseRepository):
    """Order repository."""
    
    async def create(self, order: Order) -> Order:
        """
        Create an order.
        
        Args:
            order: Order to create
            
        Returns:
            Created order
        """
        self.session.add(order)
        await self.session.commit()
        await self.session.refresh(order)
        
        logger.info("Order created", order_id=order.order_id, symbol=order.symbol)
        return order
    
    async def get_by_id(self, order_id: str) -> Optional[Order]:
        """
        Get order by ID.
        
        Args:
            order_id: Order ID
            
        Returns:
            Order or None
        """
        result = await self.session.execute(
            select(Order).where(Order.order_id == order_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_filter(self, order_filter: OrderFilter) -> List[Order]:
        """
        Get orders by filter.
        
        Args:
            order_filter: Order filter
            
        Returns:
            List of orders
        """
        query = select(Order)
        
        # Apply filters
        if order_filter.symbols:
            query = query.where(Order.symbol.in_(order_filter.symbols))
        
        if order_filter.statuses:
            query = query.where(Order.status.in_(order_filter.statuses))
        
        if order_filter.sides:
            query = query.where(Order.side.in_(order_filter.sides))
        
        if order_filter.order_types:
            query = query.where(Order.order_type.in_(order_filter.order_types))
        
        if order_filter.broker:
            query = query.where(Order.broker == order_filter.broker)
        
        if order_filter.user_id:
            query = query.where(Order.user_id == order_filter.user_id)
        
        if order_filter.session_id:
            query = query.where(Order.session_id == order_filter.session_id)
        
        if order_filter.start_time:
            query = query.where(Order.created_at >= order_filter.start_time)
        
        if order_filter.end_time:
            query = query.where(Order.created_at <= order_filter.end_time)
        
        # Apply ordering and pagination
        query = query.order_by(desc(Order.created_at))
        query = query.offset(order_filter.offset).limit(order_filter.limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def update(self, order: Order) -> Order:
        """
        Update an order.
        
        Args:
            order: Order to update
            
        Returns:
            Updated order
        """
        order.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(order)
        
        logger.info("Order updated", order_id=order.order_id)
        return order


class PnLRepository(BaseRepository):
    """P&L repository."""
    
    async def create(self, pnl: PnL) -> PnL:
        """
        Create a P&L record.
        
        Args:
            pnl: P&L record to create
            
        Returns:
            Created P&L record
        """
        self.session.add(pnl)
        await self.session.commit()
        await self.session.refresh(pnl)
        
        logger.info("P&L record created", date=pnl.date, total_pnl=float(pnl.total_pnl))
        return pnl
    
    async def get_by_date(self, pnl_date: date) -> Optional[PnL]:
        """
        Get P&L by date.
        
        Args:
            pnl_date: P&L date
            
        Returns:
            P&L record or None
        """
        result = await self.session.execute(
            select(PnL).where(PnL.date == pnl_date)
        )
        return result.scalar_one_or_none()
    
    async def get_by_filter(self, pnl_filter: PnLFilter) -> List[PnL]:
        """
        Get P&L records by filter.
        
        Args:
            pnl_filter: P&L filter
            
        Returns:
            List of P&L records
        """
        query = select(PnL)
        
        # Apply filters
        if pnl_filter.start_date:
            query = query.where(PnL.date >= pnl_filter.start_date)
        
        if pnl_filter.end_date:
            query = query.where(PnL.date <= pnl_filter.end_date)
        
        if pnl_filter.broker:
            query = query.where(PnL.broker == pnl_filter.broker)
        
        if pnl_filter.user_id:
            query = query.where(PnL.user_id == pnl_filter.user_id)
        
        if pnl_filter.session_id:
            query = query.where(PnL.session_id == pnl_filter.session_id)
        
        if pnl_filter.min_pnl is not None:
            query = query.where(PnL.total_pnl >= pnl_filter.min_pnl)
        
        if pnl_filter.max_pnl is not None:
            query = query.where(PnL.total_pnl <= pnl_filter.max_pnl)
        
        # Apply ordering and pagination
        query = query.order_by(desc(PnL.date))
        query = query.offset(pnl_filter.offset).limit(pnl_filter.limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_summary(
        self, 
        period: str, 
        start_date: date, 
        end_date: date
    ) -> Optional[PnLSummary]:
        """
        Get P&L summary for a period.
        
        Args:
            period: Period (daily, weekly, monthly, yearly)
            start_date: Start date
            end_date: End date
            
        Returns:
            P&L summary or None
        """
        # TODO: Implement P&L summary calculation
        # This would involve aggregating P&L records and calculating metrics
        return None


class ViolationRepository(BaseRepository):
    """Guardrail violation repository."""
    
    async def create(self, violation: GuardrailViolation) -> GuardrailViolation:
        """
        Create a violation record.
        
        Args:
            violation: Violation to create
            
        Returns:
            Created violation
        """
        self.session.add(violation)
        await self.session.commit()
        await self.session.refresh(violation)
        
        logger.info("Violation created", violation_id=str(violation.violation_id), type=violation.violation_type)
        return violation
    
    async def get_by_id(self, violation_id: UUID) -> Optional[GuardrailViolation]:
        """
        Get violation by ID.
        
        Args:
            violation_id: Violation ID
            
        Returns:
            Violation or None
        """
        result = await self.session.execute(
            select(GuardrailViolation).where(GuardrailViolation.violation_id == violation_id)
        )
        return result.scalar_one_or_none()
    
    async def get_unresolved(self) -> List[GuardrailViolation]:
        """
        Get unresolved violations.
        
        Returns:
            List of unresolved violations
        """
        query = select(GuardrailViolation).where(GuardrailViolation.resolved == False)
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def mark_resolved(self, violation_id: UUID) -> bool:
        """
        Mark violation as resolved.
        
        Args:
            violation_id: Violation ID
            
        Returns:
            True if updated
        """
        violation = await self.get_by_id(violation_id)
        if not violation:
            return False
        
        violation.resolved = True
        await self.session.commit()
        
        logger.info("Violation marked as resolved", violation_id=str(violation_id))
        return True
