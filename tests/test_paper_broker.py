"""
Paper broker tests
"""

import pytest
from decimal import Decimal
from datetime import datetime

from app.services.execution.paper import PaperBroker
from app.services.execution.base import OrderRequest, OrderSide, OrderType, OrderStatus


class TestPaperBroker:
    """Test PaperBroker implementation."""
    
    @pytest.fixture
    def broker(self):
        """Create test paper broker."""
        return PaperBroker(initial_capital=Decimal("100000.0"))
    
    @pytest.fixture
    def order_request(self):
        """Create test order request."""
        return OrderRequest(
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=Decimal("100"),
            order_type=OrderType.MARKET,
            client_order_id="test-order-001"
        )
    
    @pytest.mark.asyncio
    async def test_initialization(self, broker):
        """Test broker initialization."""
        assert broker.initial_capital == Decimal("100000.0")
        assert broker.connected is False
        assert broker.account_id == "paper-account-001"
        assert broker.positions == {}
        assert broker.orders == {}
        assert broker.account.equity == Decimal("100000.0")
        assert broker.account.cash == Decimal("100000.0")
        assert broker.account.buying_power == Decimal("100000.0")
    
    @pytest.mark.asyncio
    async def test_connect_disconnect(self, broker):
        """Test broker connection and disconnection."""
        # Test connection
        await broker.connect()
        assert broker.connected is True
        
        # Test disconnection
        await broker.disconnect()
        assert broker.connected is False
    
    @pytest.mark.asyncio
    async def test_place_order_not_connected(self, broker, order_request):
        """Test placing order when not connected."""
        with pytest.raises(Exception, match="Not connected to broker"):
            await broker.place_order(order_request)
    
    @pytest.mark.asyncio
    async def test_place_order_success(self, broker, order_request):
        """Test successful order placement."""
        await broker.connect()
        
        order_response = await broker.place_order(order_request)
        
        assert order_response.order_id is not None
        assert order_response.symbol == "AAPL"
        assert order_response.side == OrderSide.BUY
        assert order_response.quantity == Decimal("100")
        assert order_response.order_type == OrderType.MARKET
        assert order_response.status == OrderStatus.FILLED
        assert order_response.broker == "paper"
        assert order_response.client_order_id == "test-order-001"
        
        # Check that order is stored
        assert order_response.order_id in broker.orders
    
    @pytest.mark.asyncio
    async def test_place_limit_order(self, broker):
        """Test placing limit order."""
        await broker.connect()
        
        order_request = OrderRequest(
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=Decimal("100"),
            order_type=OrderType.LIMIT,
            price=Decimal("150.0")
        )
        
        order_response = await broker.place_order(order_request)
        
        assert order_response.order_type == OrderType.LIMIT
        assert order_response.price == Decimal("150.0")
        assert order_response.status == OrderStatus.FILLED
    
    @pytest.mark.asyncio
    async def test_cancel_order_not_connected(self, broker):
        """Test canceling order when not connected."""
        with pytest.raises(Exception, match="Not connected to broker"):
            await broker.cancel_order("test-order-001")
    
    @pytest.mark.asyncio
    async def test_cancel_order_success(self, broker, order_request):
        """Test successful order cancellation."""
        await broker.connect()
        
        # Place order first
        order_response = await broker.place_order(order_request)
        order_id = order_response.order_id
        
        # Cancel order
        success = await broker.cancel_order(order_id)
        
        assert success is True
        assert broker.orders[order_id].status == OrderStatus.CANCELLED
    
    @pytest.mark.asyncio
    async def test_cancel_nonexistent_order(self, broker):
        """Test canceling nonexistent order."""
        await broker.connect()
        
        success = await broker.cancel_order("nonexistent-order")
        
        assert success is False
    
    @pytest.mark.asyncio
    async def test_cancel_filled_order(self, broker, order_request):
        """Test canceling filled order."""
        await broker.connect()
        
        # Place and wait for order to be filled
        order_response = await broker.place_order(order_request)
        order_id = order_response.order_id
        
        # Try to cancel filled order
        success = await broker.cancel_order(order_id)
        
        assert success is False  # Cannot cancel filled order
    
    @pytest.mark.asyncio
    async def test_get_positions_not_connected(self, broker):
        """Test getting positions when not connected."""
        with pytest.raises(Exception, match="Not connected to broker"):
            await broker.get_positions()
    
    @pytest.mark.asyncio
    async def test_get_positions_after_trade(self, broker, order_request):
        """Test getting positions after trade."""
        await broker.connect()
        
        # Place order to create position
        await broker.place_order(order_request)
        
        positions = await broker.get_positions()
        
        assert len(positions) == 1
        position = positions[0]
        assert position.symbol == "AAPL"
        assert position.quantity == Decimal("100")
        assert position.broker == "paper"
    
    @pytest.mark.asyncio
    async def test_get_account_not_connected(self, broker):
        """Test getting account when not connected."""
        with pytest.raises(Exception, match="Not connected to broker"):
            await broker.get_account()
    
    @pytest.mark.asyncio
    async def test_get_account_after_trade(self, broker, order_request):
        """Test getting account after trade."""
        await broker.connect()
        
        # Place order
        await broker.place_order(order_request)
        
        account = await broker.get_account()
        
        assert account.account_id == "paper-account-001"
        assert account.broker == "paper"
        assert account.equity < Decimal("100000.0")  # Should be less due to commission
        assert account.cash < Decimal("100000.0")  # Should be less due to trade
    
    @pytest.mark.asyncio
    async def test_status_stream_not_connected(self, broker):
        """Test status stream when not connected."""
        with pytest.raises(Exception, match="Not connected to broker"):
            async for update in broker.status_stream():
                break
    
    @pytest.mark.asyncio
    async def test_status_stream_connected(self, broker):
        """Test status stream when connected."""
        await broker.connect()
        
        # Collect a few status updates
        updates = []
        async for update in broker.status_stream():
            updates.append(update)
            if len(updates) >= 2:  # Get 2 updates
                break
        
        assert len(updates) >= 1
        assert all(update.broker == "paper" for update in updates)
    
    @pytest.mark.asyncio
    async def test_position_update_after_buy(self, broker):
        """Test position update after buy order."""
        await broker.connect()
        
        order_request = OrderRequest(
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=Decimal("100"),
            order_type=OrderType.MARKET
        )
        
        await broker.place_order(order_request)
        
        positions = await broker.get_positions()
        assert len(positions) == 1
        
        position = positions[0]
        assert position.symbol == "AAPL"
        assert position.quantity == Decimal("100")
        assert position.avg_price > Decimal("0")
        assert position.market_value > Decimal("0")
    
    @pytest.mark.asyncio
    async def test_position_update_after_sell(self, broker):
        """Test position update after sell order."""
        await broker.connect()
        
        # First buy to create position
        buy_order = OrderRequest(
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=Decimal("200"),
            order_type=OrderType.MARKET
        )
        await broker.place_order(buy_order)
        
        # Then sell half
        sell_order = OrderRequest(
            symbol="AAPL",
            side=OrderSide.SELL,
            quantity=Decimal("100"),
            order_type=OrderType.MARKET
        )
        await broker.place_order(sell_order)
        
        positions = await broker.get_positions()
        assert len(positions) == 1
        
        position = positions[0]
        assert position.symbol == "AAPL"
        assert position.quantity == Decimal("100")  # 200 - 100
    
    @pytest.mark.asyncio
    async def test_market_price_simulation(self, broker):
        """Test market price simulation."""
        await broker.connect()
        
        # Place order to trigger price simulation
        order_request = OrderRequest(
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=Decimal("100"),
            order_type=OrderType.MARKET
        )
        
        await broker.place_order(order_request)
        
        # Check that market price was updated
        assert "AAPL" in broker.market_prices
        assert broker.market_prices["AAPL"] > Decimal("0")
    
    def test_get_status(self, broker):
        """Test broker status."""
        status = broker.get_status()
        
        assert "connected" in status
        assert "account_id" in status
        assert "equity" in status
        assert "cash" in status
        assert "positions_count" in status
        assert "orders_count" in status
        assert "market_prices" in status
    
    @pytest.mark.asyncio
    async def test_commission_calculation(self, broker, order_request):
        """Test commission calculation."""
        await broker.connect()
        
        order_response = await broker.place_order(order_request)
        
        assert order_response.commission is not None
        assert order_response.commission > Decimal("0")
        # Commission should be 0.1% of trade value
        expected_commission = order_response.quantity * order_response.price * Decimal("0.001")
        assert order_response.commission == expected_commission
