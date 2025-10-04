"""
Interactive Brokers (IBKR) adapter with paper-compatible interface
"""

import os
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List, AsyncGenerator, Optional

from .base import (
    IBroker, OrderRequest, OrderResponse, Position, Account, StatusUpdate,
    OrderSide, OrderType, OrderStatus, BrokerError, ConnectionError, AuthenticationError, OrderError
)

import structlog

logger = structlog.get_logger(__name__)


class IBKRAdapter(IBroker):
    """Interactive Brokers adapter with paper-compatible interface."""
    
    def __init__(self, host: str = None, port: int = None, client_id: int = None, account: str = None):
        """
        Initialize IBKR adapter.
        
        Args:
            host: IBKR TWS/Gateway host (defaults to env var)
            port: IBKR TWS/Gateway port (defaults to env var)
            client_id: IBKR client ID (defaults to env var)
            account: IBKR account number (defaults to env var)
        """
        # Environment-gated configuration
        self.enabled = os.getenv("BROKER", "").lower() == "ibkr"
        self.host = host or os.getenv("IBKR_HOST", "127.0.0.1")
        self.port = port or int(os.getenv("IBKR_PORT", "7497"))
        self.client_id = client_id or int(os.getenv("IBKR_CLIENT_ID", "1"))
        self.account = account or os.getenv("IBKR_ACCOUNT")
        
        # Connection state
        self.connected = False
        self.authenticated = False
        self.credentials_provided = bool(self.account)
        
        # Stub state for logging
        self.orders: Dict[str, OrderResponse] = {}
        self.positions: Dict[str, Position] = {}
        self.account_info: Optional[Account] = None
        
        # Status stream
        self._status_queue: asyncio.Queue = asyncio.Queue()
        self._status_task: Optional[asyncio.Task] = None
        
        logger.info("IBKR adapter initialized", 
                   enabled=self.enabled,
                   host=self.host, 
                   port=self.port, 
                   client_id=self.client_id,
                   credentials_provided=self.credentials_provided)
    
    async def connect(self) -> None:
        """Connect to IBKR broker."""
        if not self.enabled:
            logger.warning("IBKR adapter disabled (BROKER != 'ibkr')")
            return
        
        logger.info("Connecting to IBKR broker", host=self.host, port=self.port)
        
        try:
            # Check if credentials are provided
            if not self.credentials_provided:
                logger.warning("IBKR credentials not provided - using stub mode")
                self.connected = True
                self._status_task = asyncio.create_task(self._status_stream_worker())
                return
            
            # TODO: Implement actual IBKR connection
            # - Connect to TWS/Gateway using ib_insync or similar
            # - Authenticate with provided credentials
            # - Set up event handlers for order updates, positions, etc.
            
            # For now, simulate connection
            await asyncio.sleep(0.1)  # Simulate connection delay
            
            self.connected = True
            self.authenticated = True
            
            # Start status stream
            self._status_task = asyncio.create_task(self._status_stream_worker())
            
            logger.info("Connected to IBKR broker successfully")
            
        except Exception as e:
            logger.error("Failed to connect to IBKR broker", error=str(e))
            raise ConnectionError(f"Failed to connect to IBKR: {e}")
    
    async def disconnect(self) -> None:
        """Disconnect from IBKR broker."""
        if not self.connected:
            return
        
        logger.info("Disconnecting from IBKR broker")
        
        self.connected = False
        self.authenticated = False
        
        # Stop status stream
        if self._status_task:
            self._status_task.cancel()
            try:
                await self._status_task
            except asyncio.CancelledError:
                pass
        
        # TODO: Implement actual IBKR disconnection
        # - Disconnect from TWS/Gateway
        # - Clean up event handlers
        
        logger.info("Disconnected from IBKR broker")
    
    async def place_order(self, order_request: OrderRequest) -> OrderResponse:
        """Place an order."""
        if not self.enabled:
            raise BrokerError("IBKR adapter is disabled (BROKER != 'ibkr')")
        
        if not self.connected:
            raise ConnectionError("Not connected to IBKR broker")
        
        logger.info("Placing order via IBKR", order=order_request.dict())
        
        # Generate order ID
        order_id = f"ibkr-{datetime.utcnow().timestamp()}"
        
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
            broker="ibkr",
            metadata=order_request.metadata,
        )
        
        # Store order
        self.orders[order_id] = order_response
        
        if self.credentials_provided:
            # TODO: Implement actual IBKR order placement
            # - Convert order request to IBKR format
            # - Submit order via IBKR API
            # - Handle order confirmation
            
            logger.info("Order submitted to IBKR", order_id=order_id)
            
            # Simulate order processing
            await asyncio.sleep(0.1)
            
            # Send status update
            await self._send_status_update(StatusUpdate(
                update_type="order_submitted",
                data={
                    "order_id": order_id,
                    "symbol": order_request.symbol,
                    "side": order_request.side,
                    "quantity": float(order_request.quantity),
                    "order_type": order_request.order_type,
                },
                broker="ibkr"
            ))
        else:
            # Stub mode - just log the intent
            logger.info("Order intent logged (stub mode - no credentials)", 
                       order_id=order_id,
                       symbol=order_request.symbol,
                       side=order_request.side,
                       quantity=float(order_request.quantity),
                       order_type=order_request.order_type,
                       price=float(order_request.price) if order_request.price else None)
            
            # In stub mode, mark as pending
            order_response.status = OrderStatus.PENDING
        
        return order_response
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        if not self.enabled:
            raise BrokerError("IBKR adapter is disabled (BROKER != 'ibkr')")
        
        if not self.connected:
            raise ConnectionError("Not connected to IBKR broker")
        
        if order_id not in self.orders:
            logger.warning("Order not found for cancellation", order_id=order_id)
            return False
        
        order = self.orders[order_id]
        
        if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
            logger.warning("Cannot cancel order in current status", 
                          order_id=order_id, 
                          status=order.status)
            return False
        
        logger.info("Cancelling order via IBKR", order_id=order_id)
        
        if self.credentials_provided:
            # TODO: Implement actual IBKR order cancellation
            # - Cancel order via IBKR API
            # - Handle cancellation confirmation
            
            # Simulate cancellation
            await asyncio.sleep(0.1)
            
            order.status = OrderStatus.CANCELLED
            order.cancelled_at = datetime.utcnow()
            order.updated_at = datetime.utcnow()
            
            logger.info("Order cancelled via IBKR", order_id=order_id)
            
            # Send status update
            await self._send_status_update(StatusUpdate(
                update_type="order_cancelled",
                data={"order_id": order_id},
                broker="ibkr"
            ))
        else:
            # Stub mode - just log the intent
            logger.info("Order cancellation intent logged (stub mode - no credentials)", 
                       order_id=order_id)
            
            order.status = OrderStatus.CANCELLED
            order.cancelled_at = datetime.utcnow()
            order.updated_at = datetime.utcnow()
        
        return True
    
    async def get_positions(self) -> List[Position]:
        """Get current positions."""
        if not self.enabled:
            raise BrokerError("IBKR adapter is disabled (BROKER != 'ibkr')")
        
        if not self.connected:
            raise ConnectionError("Not connected to IBKR broker")
        
        logger.info("Getting positions from IBKR")
        
        if self.credentials_provided:
            # TODO: Implement actual IBKR position retrieval
            # - Get positions via IBKR API
            # - Convert to Position objects
            # - Return positions list
            
            # For now, return empty list
            positions = []
        else:
            # Stub mode - return empty positions
            logger.info("Position request logged (stub mode - no credentials)")
            positions = []
        
        return positions
    
    async def get_account(self) -> Account:
        """Get account information."""
        if not self.enabled:
            raise BrokerError("IBKR adapter is disabled (BROKER != 'ibkr')")
        
        if not self.connected:
            raise ConnectionError("Not connected to IBKR broker")
        
        logger.info("Getting account from IBKR")
        
        if self.credentials_provided:
            # TODO: Implement actual IBKR account retrieval
            # - Get account info via IBKR API
            # - Convert to Account object
            # - Return account
            
            # For now, return stub account
            if not self.account_info:
                self.account_info = Account(
                    account_id=self.account or "ibkr-account",
                    equity=Decimal("100000.00"),
                    cash=Decimal("100000.00"),
                    buying_power=Decimal("100000.00"),
                    margin_used=Decimal("0.00"),
                    margin_available=Decimal("100000.00"),
                    broker="ibkr"
                )
        else:
            # Stub mode - return empty account info
            logger.info("Account request logged (stub mode - no credentials)")
            if not self.account_info:
                self.account_info = Account(
                    account_id="ibkr-stub-account",
                    equity=Decimal("0.00"),
                    cash=Decimal("0.00"),
                    buying_power=Decimal("0.00"),
                    margin_used=Decimal("0.00"),
                    margin_available=Decimal("0.00"),
                    broker="ibkr"
                )
        
        return self.account_info
    
    async def status_stream(self) -> AsyncGenerator[StatusUpdate, None]:
        """Get status updates stream."""
        if not self.enabled:
            raise BrokerError("IBKR adapter is disabled (BROKER != 'ibkr')")
        
        if not self.connected:
            raise ConnectionError("Not connected to IBKR broker")
        
        logger.info("Starting IBKR status stream")
        
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
                # Send periodic status updates
                await asyncio.sleep(10.0)  # Update every 10 seconds
                
                if self.credentials_provided:
                    # TODO: Implement actual IBKR status updates
                    # - Monitor order status changes
                    # - Track position updates
                    # - Handle account updates
                    
                    # For now, send stub status
                    await self._send_status_update(StatusUpdate(
                        update_type="heartbeat",
                        data={
                            "broker": "ibkr",
                            "connected": self.connected,
                            "authenticated": self.authenticated,
                            "timestamp": datetime.utcnow().isoformat()
                        },
                        broker="ibkr"
                    ))
                else:
                    # Stub mode - send periodic stub updates
                    await self._send_status_update(StatusUpdate(
                        update_type="stub_heartbeat",
                        data={
                            "broker": "ibkr",
                            "mode": "stub",
                            "credentials_provided": False,
                            "timestamp": datetime.utcnow().isoformat()
                        },
                        broker="ibkr"
                    ))
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("IBKR status stream worker error", error=str(e), exc_info=True)
    
    async def _send_status_update(self, status_update: StatusUpdate):
        """Send status update."""
        try:
            await self._status_queue.put(status_update)
        except Exception as e:
            logger.error("Failed to send IBKR status update", error=str(e), exc_info=True)
    
    def get_status(self) -> Dict[str, Any]:
        """Get broker status."""
        return {
            "enabled": self.enabled,
            "connected": self.connected,
            "authenticated": self.authenticated,
            "credentials_provided": self.credentials_provided,
            "broker": "ibkr",
            "host": self.host,
            "port": self.port,
            "client_id": self.client_id,
            "account": self.account,
            "orders_count": len(self.orders),
            "positions_count": len(self.positions),
        }
