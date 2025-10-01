"""
Risk management tests
"""

import pytest
from decimal import Decimal
from datetime import datetime, time
from unittest.mock import Mock

from app.services.risk_guard import RiskGuard, RiskCheckResult
from app.models.base import Settings
from app.models.limits import GuardrailLimits, GuardrailViolation, ViolationSeverity


class TestRiskGuard:
    """Test RiskGuard service."""
    
    @pytest.fixture
    def settings(self):
        """Create test settings."""
        return Settings(
            max_trades_per_day=5,
            daily_loss_cap_usd=Decimal("300.0"),
            max_contracts=10,
            max_position_size_usd=Decimal("50000.0"),
            max_daily_volume_usd=Decimal("100000.0"),
            session_windows=["09:30-16:00", "20:00-22:00"]
        )
    
    @pytest.fixture
    def risk_guard(self, settings):
        """Create test risk guard."""
        return RiskGuard(settings)
    
    @pytest.fixture
    def mock_signal(self):
        """Create mock signal."""
        signal = Mock()
        signal.signal_type = "BUY"
        signal.symbol = "AAPL"
        signal.quantity = 100
        signal.price = Decimal("150.0")
        signal.confidence = 0.8
        signal.metadata = {}
        return signal
    
    def test_initialization(self, risk_guard, settings):
        """Test risk guard initialization."""
        assert risk_guard.settings == settings
        assert risk_guard.daily_trades == 0
        assert risk_guard.daily_loss == Decimal("0")
        assert risk_guard.daily_volume == Decimal("0")
        assert risk_guard.current_positions == {}
        assert risk_guard.violations == []
        assert risk_guard.session_start_equity == settings.initial_capital
        assert risk_guard.current_equity == settings.initial_capital
    
    @pytest.mark.asyncio
    async def test_check_signal_allowed(self, risk_guard, mock_signal):
        """Test signal check when allowed."""
        result = await risk_guard.check_signal(mock_signal)
        
        assert result.allowed is True
        assert result.reason == "Signal approved"
        assert result.violation is None
    
    @pytest.mark.asyncio
    async def test_check_signal_daily_trade_limit(self, risk_guard, mock_signal):
        """Test signal check when daily trade limit exceeded."""
        # Set daily trades to limit
        risk_guard.daily_trades = 5
        
        result = await risk_guard.check_signal(mock_signal)
        
        assert result.allowed is False
        assert "Daily trade limit exceeded" in result.reason
        assert result.violation is not None
        assert result.violation.violation_type == "max_trades_per_day"
        assert result.violation.severity == ViolationSeverity.ERROR
    
    @pytest.mark.asyncio
    async def test_check_signal_daily_loss_cap(self, risk_guard, mock_signal):
        """Test signal check when daily loss cap exceeded."""
        # Set daily loss to cap
        risk_guard.daily_loss = Decimal("-300.0")
        
        result = await risk_guard.check_signal(mock_signal)
        
        assert result.allowed is False
        assert "Daily loss cap exceeded" in result.reason
        assert result.violation is not None
        assert result.violation.violation_type == "daily_loss_cap"
        assert result.violation.severity == ViolationSeverity.CRITICAL
    
    @pytest.mark.asyncio
    async def test_check_signal_position_size_limit(self, risk_guard):
        """Test signal check when position size limit exceeded."""
        # Create signal with large position
        mock_signal = Mock()
        mock_signal.signal_type = "BUY"
        mock_signal.symbol = "AAPL"
        mock_signal.quantity = 1000  # Large quantity
        mock_signal.price = Decimal("200.0")  # High price
        mock_signal.confidence = 0.8
        mock_signal.metadata = {}
        
        result = await risk_guard.check_signal(mock_signal)
        
        assert result.allowed is False
        assert "Position size limit exceeded" in result.reason
        assert result.violation is not None
        assert result.violation.violation_type == "max_position_size"
        assert result.violation.severity == ViolationSeverity.ERROR
    
    @pytest.mark.asyncio
    async def test_check_signal_daily_volume_limit(self, risk_guard):
        """Test signal check when daily volume limit exceeded."""
        # Set daily volume close to limit
        risk_guard.daily_volume = Decimal("95000.0")
        
        # Create signal that would exceed volume limit
        mock_signal = Mock()
        mock_signal.signal_type = "BUY"
        mock_signal.symbol = "AAPL"
        mock_signal.quantity = 1000
        mock_signal.price = Decimal("100.0")
        mock_signal.confidence = 0.8
        mock_signal.metadata = {}
        
        result = await risk_guard.check_signal(mock_signal)
        
        assert result.allowed is False
        assert "Daily volume limit exceeded" in result.reason
        assert result.violation is not None
        assert result.violation.violation_type == "max_daily_volume"
        assert result.violation.severity == ViolationSeverity.ERROR
    
    def test_is_trading_session(self, risk_guard):
        """Test trading session check."""
        # Mock current time to be within session
        with pytest.MonkeyPatch().context() as m:
            m.setattr(datetime, 'now', lambda: datetime(2024, 1, 1, 10, 0, 0))  # 10:00 AM
            assert risk_guard._is_trading_session() is True
        
        # Mock current time to be outside session
        with pytest.MonkeyPatch().context() as m:
            m.setattr(datetime, 'now', lambda: datetime(2024, 1, 1, 18, 0, 0))  # 6:00 PM
            assert risk_guard._is_trading_session() is False
    
    @pytest.mark.asyncio
    async def test_record_trade(self, risk_guard):
        """Test trade recording."""
        trade_data = {
            "quantity": 100,
            "price": 150.0,
            "realized_pnl": 50.0,
            "equity_change": 50.0
        }
        
        await risk_guard.record_trade(trade_data)
        
        assert risk_guard.daily_trades == 1
        assert risk_guard.daily_volume == Decimal("15000.0")  # 100 * 150
        assert risk_guard.daily_loss == Decimal("50.0")
        assert risk_guard.current_equity == Decimal("100050.0")  # 100000 + 50
    
    @pytest.mark.asyncio
    async def test_record_violation(self, risk_guard):
        """Test violation recording."""
        violation = GuardrailViolation(
            violation_type="max_trades_per_day",
            severity=ViolationSeverity.ERROR,
            message="Daily trade limit exceeded",
            current_value=6,
            limit_value=5
        )
        
        await risk_guard.record_violation(violation)
        
        assert len(risk_guard.violations) == 1
        assert risk_guard.violations[0] == violation
    
    def test_get_status(self, risk_guard):
        """Test status retrieval."""
        status = risk_guard.get_status()
        
        assert "limits" in status
        assert "daily_trades" in status
        assert "daily_loss" in status
        assert "daily_volume" in status
        assert "current_positions" in status
        assert "violation_count" in status
        assert "unresolved_violations" in status
        assert "session_start_equity" in status
        assert "current_equity" in status
        assert "equity_change" in status
        assert "trading_session" in status
    
    def test_is_halted_no_violations(self, risk_guard):
        """Test halt status with no violations."""
        assert risk_guard.is_halted() is False
    
    def test_is_halted_critical_violation(self, risk_guard):
        """Test halt status with critical violation."""
        violation = GuardrailViolation(
            violation_type="daily_loss_cap",
            severity=ViolationSeverity.CRITICAL,
            message="Daily loss cap exceeded",
            current_value=-500.0,
            limit_value=-300.0
        )
        
        risk_guard.violations.append(violation)
        
        assert risk_guard.is_halted() is True
    
    def test_is_halted_resolved_violation(self, risk_guard):
        """Test halt status with resolved violation."""
        violation = GuardrailViolation(
            violation_type="daily_loss_cap",
            severity=ViolationSeverity.CRITICAL,
            message="Daily loss cap exceeded",
            current_value=-500.0,
            limit_value=-300.0,
            resolved=True
        )
        
        risk_guard.violations.append(violation)
        
        assert risk_guard.is_halted() is False
    
    @pytest.mark.asyncio
    async def test_update_limits(self, risk_guard):
        """Test limits update."""
        new_limits = GuardrailLimits(
            max_trades_per_day=10,
            daily_loss_cap_usd=Decimal("500.0"),
            max_contracts=20,
            session_windows=["08:00-17:00"]
        )
        
        await risk_guard.update_limits(new_limits)
        
        assert risk_guard.limits == new_limits
        assert risk_guard.limits.max_trades_per_day == 10
        assert risk_guard.limits.daily_loss_cap_usd == Decimal("500.0")


class TestRiskCheckResult:
    """Test RiskCheckResult dataclass."""
    
    def test_allowed_result(self):
        """Test allowed result."""
        result = RiskCheckResult(allowed=True, reason="Signal approved")
        
        assert result.allowed is True
        assert result.reason == "Signal approved"
        assert result.violation is None
    
    def test_rejected_result(self):
        """Test rejected result."""
        violation = GuardrailViolation(
            violation_type="max_trades_per_day",
            severity=ViolationSeverity.ERROR,
            message="Daily trade limit exceeded",
            current_value=6,
            limit_value=5
        )
        
        result = RiskCheckResult(
            allowed=False,
            reason="Daily trade limit exceeded",
            violation=violation
        )
        
        assert result.allowed is False
        assert result.reason == "Daily trade limit exceeded"
        assert result.violation == violation
