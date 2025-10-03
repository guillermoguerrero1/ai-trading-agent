"""
Paper trading broker implementation
"""

import asyncio
import random
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List, AsyncGenerator, Callable, Optional

from .base import (
    IBroker, OrderRequest, OrderResponse, Position, Account, StatusUpdate,
    OrderSide, OrderType, OrderStatus, BrokerError, ConnectionError, AuthenticationError, OrderError
)

import structlog

logger = structlog.get_logger(__name__)


class _PriceBus:
    def __init__(self):
        self.subs: Dict[str, List[Callable[[float], None]]] = defaultdict(list)
        self.last: Dict[str, float] = {}
    
    def subscribe(self, symbol: str, fn: Callable[[float], None]):
        self.subs[symbol].append(fn)
        if symbol in self.last:
            fn(self.last[symbol])
    
    def publish(self, symbol: str, price: float):
        self.last[symbol] = price
        for fn in self.subs[symbol]:
            fn(price)


price_bus = _PriceBus()


class PaperBroker(IBroker):
    """Paper trading broker implementation."""
    
    def __init__(self, initial_capital: Decimal = Decimal("100000.0"), trade_logger: Optional["TradeLogger"] = None):
        """
        Initialize paper broker.
        
        Args:
            initial_capital: Initial capital amount
            trade_logger: Optional TradeLogger instance for logging trades
        """
        self.initial_capital = initial_capital
        self.connected = False
        self.account_id = "paper-account-001"
        self.trade_logger = trade_logger
        
        # Simulated state
        self.positions: Dict[str, Position] = {}
        self.orders: Dict[str, OrderResponse] = {}
        self.account: Account = Account(
            account_id=self.account_id,
            equity=initial_capital,
            cash=initial_capital,
            buying_power=initial_capital,
            margin_used=Decimal("0"),
            margin_available=initial_capital,
            broker="paper"
        )
        
        # Simulated market data
        self.market_prices: Dict[str, Decimal] = {
            "AAPL": Decimal("150.00"),
            "GOOGL": Decimal("2800.00"),
            "MSFT": Decimal("300.00"),
            "TSLA": Decimal("200.00"),
            "AMZN": Decimal("3200.00"),
        }
        
        # Status stream
        self._status_queue: asyncio.Queue = asyncio.Queue()
        self._status_task: asyncio.Task = None
        
    async def connect(self) -> None:
        """Connect to paper broker."""
        if self.connected:
            return
            
        logger.info("Connecting to paper broker")
        
        # Simulate connection delay
        await asyncio.sleep(0.1)
        
        self.connected = True
        
        # Start status stream
        self._status_task = asyncio.create_task(self._status_stream_worker())
        
        logger.info("Connected to paper broker successfully")
    
    async def disconnect(self) -> None:
        """Disconnect from paper broker."""
        if not self.connected:
            return
            
        logger.info("Disconnecting from paper broker")
        
        self.connected = False
        
        # Stop status stream
        if self._status_task:
            self._status_task.cancel()
            try:
                await self._status_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Disconnected from paper broker")
    
    async def place_order(self, order_request: OrderRequest) -> OrderResponse:
        """Place an order."""
        if not self.connected:
            raise ConnectionError("Not connected to broker")
        
        logger.info("Placing order", order=order_request.dict())
        
        # Generate order ID
        order_id = f"paper-{datetime.utcnow().timestamp()}"
        
        # Create order response
        order_response = OrderResponse(
            order_id=order_id,
            client_order_id=order_request.client_order_id,
            symbol=order_request.symbol,
            side=order_request.side,
            quantity=order_request.quantity,
            order_type=order_request.order_type,
            price=order_request.price,
            stop_price=order_request.stop_price,
            status=OrderStatus.SUBMITTED,
            time_in_force=order_request.time_in_force,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            broker="paper",
            metadata=order_request.metadata,
        )
        
        # Store order
        self.orders[order_id] = order_response
        
        # Log trade opening if trade_logger is available
        if self.trade_logger:
            await self.trade_logger.log_open(
                order_id=order_id,
                symbol=order_request.symbol,
                side=order_request.side.value,
                qty=float(order_request.quantity),
                entry=float(order_request.price) if order_request.price else float(self.market_prices.get(order_request.symbol, Decimal("100.00"))),
                stop=float(order_request.stop_price) if order_request.stop_price else None,
                target=None,  # PaperBroker doesn't have explicit target in OrderRequest
                features=order_request.metadata,
                notes="paper.open",
            )
        
        # Simulate order execution
        await self._simulate_order_execution(order_response)
        
        return order_response
    
    async def _simulate_order_execution(self, order_response: OrderResponse):
        """Simulate order execution."""
        # For market orders, execute immediately
        if order_response.order_type == OrderType.MARKET:
            await self._execute_order_immediately(order_response)
        else:
            # For limit/stop orders, subscribe to price updates
            def on_price_update(price: float):
                asyncio.create_task(self._check_order_fill(order_response, Decimal(str(price))))
            
            price_bus.subscribe(order_response.symbol, on_price_update)
            
            # Set order as pending
            order_response.status = OrderStatus.PENDING
            order_response.updated_at = datetime.utcnow()
    
    async def _execute_order_immediately(self, order_response: OrderResponse):
        """Execute market order immediately."""
        # Get current market price
        market_price = self.market_prices.get(order_response.symbol, Decimal("100.00"))
        
        # Simulate execution delay
        await asyncio.sleep(random.uniform(0.1, 0.5))
        
        # Execute order
        await self._fill_order(order_response, market_price)
    
    async def _check_order_fill(self, order_response: OrderResponse, market_price: Decimal):
        """Check if order should be filled based on current price."""
        if order_response.status != OrderStatus.PENDING:
            return  # Order already processed
        
        should_fill = False
        execution_price = market_price
        
        if order_response.order_type == OrderType.LIMIT:
            if order_response.side == OrderSide.BUY and order_response.price >= market_price:
                should_fill = True
                execution_price = market_price
            elif order_response.side == OrderSide.SELL and order_response.price <= market_price:
                should_fill = True
                execution_price = market_price
        elif order_response.order_type == OrderType.STOP:
            if order_response.side == OrderSide.BUY and market_price >= order_response.stop_price:
                should_fill = True
                execution_price = market_price
            elif order_response.side == OrderSide.SELL and market_price <= order_response.stop_price:
                should_fill = True
                execution_price = market_price
        
        if should_fill:
            await self._fill_order(order_response, execution_price)
    
    async def _fill_order(self, order_response: OrderResponse, execution_price: Decimal):
        """Fill an order at the given price."""
        # Update market price
        self.market_prices[order_response.symbol] = execution_price
        
        # Execute order
        order_response.status = OrderStatus.FILLED
        order_response.filled_quantity = order_response.quantity
        order_response.filled_at = datetime.utcnow()
        order_response.updated_at = datetime.utcnow()
        order_response.commission = order_response.quantity * execution_price * Decimal("0.001")  # 0.1% commission
        
        # Update position
        await self._update_position(order_response, execution_price)
        
        # Update account
        await self._update_account(order_response, execution_price)
        
        # Log trade closing if trade_logger is available
        # Note: This logs when the order is filled, which for paper trading is the close
        # In a real scenario with stop/target OCO orders, this would be called when those are hit
        if self.trade_logger:
            # Determine outcome based on order type/metadata
            outcome = "fill"
            if hasattr(order_response, 'metadata') and order_response.metadata:
                if order_response.metadata.get('is_stop'):
                    outcome = "stop"
                elif order_response.metadata.get('is_target'):
                    outcome = "target"
            
            await self.trade_logger.log_close(
                order_id=order_response.order_id,
                exit_price=float(execution_price),
                outcome=outcome,
            )
        
        # Send status update
        await self._send_status_update(StatusUpdate(
            update_type="order_filled",
            data={
                "order_id": order_response.order_id,
                "symbol": order_response.symbol,
                "quantity": float(order_response.quantity),
                "price": float(execution_price),
                "side": order_response.side,
            },
            broker="paper"
        ))
    
    async def _update_position(self, order_response: OrderResponse, execution_price: Decimal):
        """Update position after order execution."""
        symbol = order_response.symbol
        
        if symbol not in self.positions:
            self.positions[symbol] = Position(
                symbol=symbol,
                quantity=Decimal("0"),
                avg_price=Decimal("0"),
                market_price=self.market_prices.get(symbol, Decimal("100.00")),
                market_value=Decimal("0"),
                unrealized_pnl=Decimal("0"),
                realized_pnl=Decimal("0"),
                broker="paper"
            )
        
        position = self.positions[symbol]
        
        # Update position
        if order_response.side == OrderSide.BUY:
            # Add to position
            total_quantity = position.quantity + order_response.quantity
            total_value = (position.quantity * position.avg_price) + (order_response.quantity * execution_price)
            position.avg_price = total_value / total_quantity if total_quantity > 0 else Decimal("0")
            position.quantity = total_quantity
        else:
            # Subtract from position
            position.quantity -= order_response.quantity
            if position.quantity < 0:
                position.quantity = Decimal("0")
        
        # Update market price and value
        position.market_price = self.market_prices.get(symbol, Decimal("100.00"))
        position.market_value = position.quantity * position.market_price
        position.unrealized_pnl = position.market_value - (position.quantity * position.avg_price)
        position.timestamp = datetime.utcnow()
    
    async def _update_account(self, order_response: OrderResponse, execution_price: Decimal):
        """Update account after order execution."""
        # Calculate order value
        order_value = order_response.quantity * execution_price
        
        # Update cash
        if order_response.side == OrderSide.BUY:
            self.account.cash -= order_value + order_response.commission
        else:
            self.account.cash += order_value - order_response.commission
        
        # Update equity
        total_position_value = sum(pos.market_value for pos in self.positions.values())
        self.account.equity = self.account.cash + total_position_value
        
        # Update buying power
        self.account.buying_power = self.account.cash
        self.account.margin_available = self.account.cash
        
        self.account.timestamp = datetime.utcnow()
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        if not self.connected:
            raise ConnectionError("Not connected to broker")
        
        if order_id not in self.orders:
            return False
        
        order = self.orders[order_id]
        
        if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
            return False
        
        # Cancel order
        order.status = OrderStatus.CANCELLED
        order.cancelled_at = datetime.utcnow()
        order.updated_at = datetime.utcnow()
        
        # Log trade closing with manual_exit outcome if trade_logger is available
        if self.trade_logger:
            await self.trade_logger.log_close(
                order_id=order_id,
                exit_price=float(self.market_prices.get(order.symbol, Decimal("100.00"))),
                outcome="cancelled",
            )
        
        # Send status update
        await self._send_status_update(StatusUpdate(
            update_type="order_cancelled",
            data={"order_id": order_id},
            broker="paper"
        ))
        
        return True
    
    async def get_positions(self) -> List[Position]:
        """Get current positions."""
        if not self.connected:
            raise ConnectionError("Not connected to broker")
        
        # Update market prices
        for symbol in self.positions:
            if symbol in self.market_prices:
                self.positions[symbol].market_price = self.market_prices[symbol]
                self.positions[symbol].market_value = self.positions[symbol].quantity * self.market_prices[symbol]
                self.positions[symbol].unrealized_pnl = self.positions[symbol].market_value - (self.positions[symbol].quantity * self.positions[symbol].avg_price)
                self.positions[symbol].timestamp = datetime.utcnow()
        
        return list(self.positions.values())
    
    async def get_account(self) -> Account:
        """Get account information."""
        if not self.connected:
            raise ConnectionError("Not connected to broker")
        
        # Update account with current position values
        total_position_value = sum(pos.market_value for pos in self.positions.values())
        self.account.equity = self.account.cash + total_position_value
        self.account.timestamp = datetime.utcnow()
        
        return self.account
    
    async def status_stream(self) -> AsyncGenerator[StatusUpdate, None]:
        """Get status updates stream."""
        if not self.connected:
            raise ConnectionError("Not connected to broker")
        
        while self.connected:
            try:
                status_update = await asyncio.wait_for(
                    self._status_queue.get(), 
                    timeout=1.0
                )
                yield status_update
            except asyncio.TimeoutError:
                continue
    
    async def _status_stream_worker(self):
        """Status stream worker task."""
        while self.connected:
            try:
                # Send periodic market updates
                await asyncio.sleep(5.0)  # Update every 5 seconds
                
                # Simulate market price changes
                for symbol in self.market_prices:
                    price_change = Decimal(str(random.uniform(-0.01, 0.01)))  # ±1% price change
                    self.market_prices[symbol] = self.market_prices[symbol] * (Decimal("1") + price_change)
                    # Publish price update to price bus
                    price_bus.publish(symbol, float(self.market_prices[symbol]))
                
                # Send market update
                await self._send_status_update(StatusUpdate(
                    update_type="market_update",
                    data={
                        "prices": {symbol: float(price) for symbol, price in self.market_prices.items()},
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    broker="paper"
                ))
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Status stream worker error", error=str(e), exc_info=True)
    
    async def _send_status_update(self, status_update: StatusUpdate):
        """Send status update."""
        try:
            await self._status_queue.put(status_update)
        except Exception as e:
            logger.error("Failed to send status update", error=str(e), exc_info=True)
    
    def get_status(self) -> Dict[str, Any]:
        """Get broker status."""
        return {
            "connected": self.connected,
            "account_id": self.account_id,
            "equity": float(self.account.equity),
            "cash": float(self.account.cash),
            "positions_count": len(self.positions),
            "orders_count": len(self.orders),
            "market_prices": {symbol: float(price) for symbol, price in self.market_prices.items()},
        }
