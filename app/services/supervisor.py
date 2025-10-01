"""
Supervisor service for monitoring and controlling trading operations
"""

import asyncio
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from app.models.base import Settings
from app.models.event import Event, EventType, EventSeverity
from app.models.order import OrderRequest, OrderResponse, OrderFilter
from app.models.pnl import PnL, PnLSummary, PnLFilter
from app.models.account import Account, Position
from app.services.risk_guard import RiskGuard

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class CancellationResult:
    """Order cancellation result."""
    success: bool
    reason: str


class Supervisor:
    """Supervisor service for monitoring trading operations."""
    
    def __init__(self, risk_guard: RiskGuard):
        """
        Initialize supervisor.
        
        Args:
            risk_guard: Risk guard service
        """
        self.risk_guard = risk_guard
        self.halted = False
        self.events: List[Event] = []
        self.orders: Dict[str, OrderResponse] = {}
        self.positions: Dict[str, Position] = {}
        self.account: Optional[Account] = None
        self.daily_pnl: Dict[date, PnL] = {}
        
        # Event storage (in production, this would be a database)
        self.max_events = 1000
        
    async def start(self):
        """Start the supervisor service."""
        logger.info("Starting supervisor service")
        
        # Initialize account
        self.account = Account(
            account_id="supervisor-account",
            equity=Decimal("100000.0"),
            cash=Decimal("100000.0"),
            buying_power=Decimal("100000.0"),
            margin_used=Decimal("0"),
            margin_available=Decimal("100000.0"),
            broker="supervisor",
        )
        
        # Log startup event
        await self.log_event(
            Event(
                event_type=EventType.SYSTEM,
                severity=EventSeverity.INFO,
                message="Supervisor service started",
                data={"timestamp": datetime.utcnow().isoformat()},
                source="supervisor"
            )
        )
        
        logger.info("Supervisor service started successfully")
    
    async def stop(self):
        """Stop the supervisor service."""
        logger.info("Stopping supervisor service")
        
        # Log shutdown event
        await self.log_event(
            Event(
                event_type=EventType.SYSTEM,
                severity=EventSeverity.INFO,
                message="Supervisor service stopped",
                data={"timestamp": datetime.utcnow().isoformat()},
                source="supervisor"
            )
        )
        
        logger.info("Supervisor service stopped")
    
    async def log_event(self, event: Event):
        """
        Log an event.
        
        Args:
            event: Event to log
        """
        self.events.append(event)
        
        # Keep only the most recent events
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]
        
        logger.info(
            "Event logged",
            event_type=event.event_type,
            severity=event.severity,
            message=event.message,
            source=event.source
        )
    
    async def submit_order(self, order_request: OrderRequest) -> OrderResponse:
        """
        Submit an order for execution.
        
        Args:
            order_request: Order request
            
        Returns:
            Order response
        """
        try:
            # Check if trading is halted
            if self.is_halted():
                raise Exception("Trading is currently halted")
            
            # Risk check
            risk_check = await self.risk_guard.check_order(order_request)
            if not risk_check.allowed:
                if risk_check.violation:
                    await self.risk_guard.record_violation(risk_check.violation)
                raise Exception(f"Order rejected: {risk_check.reason}")
            
            # Create order response (simulated)
            order_id = f"order-{datetime.utcnow().timestamp()}"
            
            order_response = OrderResponse(
                order_id=order_id,
                client_order_id=order_request.client_order_id,
                symbol=order_request.symbol,
                side=order_request.side,
                quantity=order_request.quantity,
                filled_quantity=Decimal("0"),
                order_type=order_request.order_type,
                price=order_request.price,
                stop_price=order_request.stop_price,
                status="SUBMITTED",
                time_in_force=order_request.time_in_force,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                broker="supervisor",
                metadata=order_request.metadata,
            )
            
            # Store order
            self.orders[order_id] = order_response
            
            # Log order submission
            await self.log_event(
                Event(
                    event_type=EventType.ORDER,
                    severity=EventSeverity.LOW,
                    message=f"Order submitted: {order_response.symbol} {order_response.side} {order_response.quantity}",
                    data={"order_id": order_id, "order": order_request.dict()},
                    source="supervisor"
                )
            )
            
            # Simulate order execution (in production, this would be handled by broker)
            await self._simulate_order_execution(order_response)
            
            return order_response
            
        except Exception as e:
            logger.error("Order submission failed", error=str(e), exc_info=True)
            raise
    
    async def _simulate_order_execution(self, order_response: OrderResponse):
        """
        Simulate order execution.
        
        Args:
            order_response: Order to execute
        """
        # Simulate execution delay
        await asyncio.sleep(0.1)
        
        # Update order status
        order_response.status = "FILLED"
        order_response.filled_quantity = order_response.quantity
        order_response.filled_at = datetime.utcnow()
        order_response.updated_at = datetime.utcnow()
        
        # Update position
        await self._update_position(order_response)
        
        # Record trade
        await self.risk_guard.record_trade({
            "symbol": order_response.symbol,
            "quantity": float(order_response.quantity),
            "price": float(order_response.price or 0),
            "side": order_response.side,
        })
        
        # Log execution
        await self.log_event(
            Event(
                event_type=EventType.TRADE,
                severity=EventSeverity.LOW,
                message=f"Order executed: {order_response.symbol} {order_response.side} {order_response.quantity}",
                data={"order_id": order_response.order_id, "filled_quantity": float(order_response.filled_quantity)},
                source="supervisor"
            )
        )
    
    async def _update_position(self, order_response: OrderResponse):
        """
        Update position after order execution.
        
        Args:
            order_response: Executed order
        """
        symbol = order_response.symbol
        
        if symbol not in self.positions:
            self.positions[symbol] = Position(
                symbol=symbol,
                quantity=Decimal("0"),
                avg_price=Decimal("0"),
                market_price=Decimal("100.0"),  # Simulated market price
                market_value=Decimal("0"),
                unrealized_pnl=Decimal("0"),
                realized_pnl=Decimal("0"),
                broker="supervisor",
            )
        
        position = self.positions[symbol]
        
        # Update position based on order
        if order_response.side == "BUY":
            # Add to position
            total_quantity = position.quantity + order_response.quantity
            total_value = (position.quantity * position.avg_price) + (order_response.quantity * (order_response.price or Decimal("100.0")))
            position.avg_price = total_value / total_quantity if total_quantity > 0 else Decimal("0")
            position.quantity = total_quantity
        else:
            # Subtract from position
            position.quantity -= order_response.quantity
            if position.quantity < 0:
                position.quantity = Decimal("0")
        
        # Update market value and P&L
        position.market_value = position.quantity * position.market_price
        position.unrealized_pnl = position.market_value - (position.quantity * position.avg_price)
    
    async def cancel_order(self, order_id: str) -> CancellationResult:
        """
        Cancel an order.
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            Cancellation result
        """
        try:
            if order_id not in self.orders:
                return CancellationResult(
                    success=False,
                    reason=f"Order {order_id} not found"
                )
            
            order = self.orders[order_id]
            
            if order.status in ["FILLED", "CANCELLED", "REJECTED"]:
                return CancellationResult(
                    success=False,
                    reason=f"Order {order_id} cannot be cancelled (status: {order.status})"
                )
            
            # Update order status
            order.status = "CANCELLED"
            order.cancelled_at = datetime.utcnow()
            order.updated_at = datetime.utcnow()
            
            # Log cancellation
            await self.log_event(
                Event(
                    event_type=EventType.ORDER,
                    severity=EventSeverity.LOW,
                    message=f"Order cancelled: {order_id}",
                    data={"order_id": order_id},
                    source="supervisor"
                )
            )
            
            return CancellationResult(success=True, reason="Order cancelled successfully")
            
        except Exception as e:
            logger.error("Order cancellation failed", order_id=order_id, error=str(e), exc_info=True)
            return CancellationResult(success=False, reason=f"Cancellation failed: {str(e)}")
    
    async def get_order(self, order_id: str) -> Optional[OrderResponse]:
        """
        Get order by ID.
        
        Args:
            order_id: Order ID
            
        Returns:
            Order response or None
        """
        return self.orders.get(order_id)
    
    async def get_orders(self, order_filter: OrderFilter) -> List[OrderResponse]:
        """
        Get orders with filtering.
        
        Args:
            order_filter: Order filter
            
        Returns:
            List of orders
        """
        orders = list(self.orders.values())
        
        # Apply filters
        if order_filter.symbols:
            orders = [o for o in orders if o.symbol in order_filter.symbols]
        
        if order_filter.statuses:
            orders = [o for o in orders if o.status in order_filter.statuses]
        
        if order_filter.sides:
            orders = [o for o in orders if o.side in order_filter.sides]
        
        if order_filter.order_types:
            orders = [o for o in orders if o.order_type in order_filter.order_types]
        
        # Apply pagination
        start = order_filter.offset
        end = start + order_filter.limit
        orders = orders[start:end]
        
        return orders
    
    async def get_positions(self) -> List[Position]:
        """
        Get current positions.
        
        Returns:
            List of positions
        """
        return list(self.positions.values())
    
    async def get_account(self) -> Optional[Account]:
        """
        Get current account information.
        
        Returns:
            Account information
        """
        return self.account
    
    async def get_daily_pnl(self, pnl_date: date) -> Optional[PnL]:
        """
        Get daily P&L for a specific date.
        
        Args:
            pnl_date: Date to get P&L for
            
        Returns:
            Daily P&L or None
        """
        return self.daily_pnl.get(pnl_date)
    
    async def get_pnl_summary(self, period: str, start_date: date, end_date: date) -> Optional[PnLSummary]:
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
        return None
    
    async def get_pnl_history(self, pnl_filter: PnLFilter) -> List[PnL]:
        """
        Get P&L history.
        
        Args:
            pnl_filter: P&L filter
            
        Returns:
            List of P&L records
        """
        # TODO: Implement P&L history retrieval
        return []
    
    def is_halted(self) -> bool:
        """
        Check if trading is halted.
        
        Returns:
            True if trading is halted
        """
        return self.halted or self.risk_guard.is_halted()
    
    async def halt_trading(self, reason: str):
        """
        Halt trading.
        
        Args:
            reason: Reason for halting
        """
        self.halted = True
        
        await self.log_event(
            Event(
                event_type=EventType.SYSTEM,
                severity=EventSeverity.HIGH,
                message=f"Trading halted: {reason}",
                data={"reason": reason, "timestamp": datetime.utcnow().isoformat()},
                source="supervisor"
            )
        )
        
        logger.warning("Trading halted", reason=reason)
    
    async def resume_trading(self):
        """Resume trading."""
        self.halted = False
        
        await self.log_event(
            Event(
                event_type=EventType.SYSTEM,
                severity=EventSeverity.INFO,
                message="Trading resumed",
                data={"timestamp": datetime.utcnow().isoformat()},
                source="supervisor"
            )
        )
        
        logger.info("Trading resumed")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get supervisor status.
        
        Returns:
            Supervisor status
        """
        return {
            "halted": self.is_halted(),
            "total_orders": len(self.orders),
            "total_positions": len(self.positions),
            "total_events": len(self.events),
            "account_equity": float(self.account.equity) if self.account else 0.0,
            "risk_guard_status": self.risk_guard.get_status(),
        }
