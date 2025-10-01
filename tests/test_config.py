"""
Configuration tests
"""

import pytest
from decimal import Decimal

from app.models.base import Settings
from app.models.limits import GuardrailLimits, GuardrailUpdate
from app.deps import get_settings


def _reload_settings(monkeypatch, envs: dict):
    get_settings.cache_clear()
    for k, v in envs.items():
        if v is None:
            monkeypatch.delenv(k, raising=False)
        else:
            monkeypatch.setenv(k, str(v))
    return get_settings()


def test_settings_aliases_work(monkeypatch):
    s = _reload_settings(monkeypatch, {
        "BROKER_TYPE": "paper",
        "MAX_DAILY_TRADES": "9",
        "MAX_ORDER_SIZE": "3",
        "MAX_DAILY_LOSS": "250",
    })
    assert s.BROKER == "paper"
    assert s.MAX_TRADES_PER_DAY == 9
    assert s.MAX_CONTRACTS == 3
    assert s.DAILY_LOSS_CAP_USD == 250.0


def test_session_windows_fallback(monkeypatch):
    s = _reload_settings(monkeypatch, {
        "SESSION_WINDOWS": None,
        "TRADING_START_TIME": "09:30",
        "TRADING_END_TIME": "16:00",
    })
    assert s.session_windows_normalized == ["09:30-16:00"]


class TestSettings:
    """Test Settings model."""
    
    def test_default_settings(self):
        """Test default settings values."""
        settings = Settings()
        
        assert settings.app_name == "AI Trading Agent"
        assert settings.app_version == "0.1.0"
        assert settings.debug is False
        assert settings.timezone == "America/Phoenix"
        assert settings.api_host == "0.0.0.0"
        assert settings.api_port == 8000
        assert settings.database_url == "sqlite:///./trading_agent.db"
        assert settings.log_level == "INFO"
        assert settings.default_broker == "paper"
        assert settings.initial_capital == Decimal("100000.0")
        assert settings.max_trades_per_day == 50
        assert settings.daily_loss_cap_usd == Decimal("1000.0")
    
    def test_settings_validation(self):
        """Test settings validation."""
        # Test valid timezone
        settings = Settings(timezone="America/New_York")
        assert settings.timezone == "America/New_York"
        
        # Test invalid timezone
        with pytest.raises(ValueError, match="Invalid timezone"):
            Settings(timezone="Invalid/Timezone")
        
        # Test negative decimal values
        with pytest.raises(ValueError, match="Value must be non-negative"):
            Settings(daily_loss_cap_usd=Decimal("-100.0"))
        
        with pytest.raises(ValueError, match="Value must be non-negative"):
            Settings(initial_capital=Decimal("-1000.0"))


class TestGuardrailLimits:
    """Test GuardrailLimits model."""
    
    def test_default_limits(self):
        """Test default guardrail limits."""
        limits = GuardrailLimits()
        
        assert limits.max_trades_per_day == 50
        assert limits.daily_loss_cap_usd == Decimal("1000.0")
        assert limits.max_contracts == 10
        assert limits.session_windows == ["09:30-16:00"]
        assert limits.max_position_size_usd == Decimal("50000.0")
        assert limits.max_daily_volume_usd == Decimal("100000.0")
    
    def test_session_windows_validation(self):
        """Test session windows validation."""
        # Test valid session windows
        limits = GuardrailLimits(session_windows=["09:30-16:00", "20:00-22:00"])
        assert limits.session_windows == ["09:30-16:00", "20:00-22:00"]
        
        # Test invalid session window format
        with pytest.raises(ValueError, match="Invalid session window format"):
            GuardrailLimits(session_windows=["09:30-16:00", "invalid"])
        
        with pytest.raises(ValueError, match="Invalid session window format"):
            GuardrailLimits(session_windows=["09:30"])
    
    def test_positive_decimals_validation(self):
        """Test positive decimal validation."""
        # Test valid positive values
        limits = GuardrailLimits(
            daily_loss_cap_usd=Decimal("500.0"),
            max_position_size_usd=Decimal("25000.0"),
            max_daily_volume_usd=Decimal("50000.0")
        )
        assert limits.daily_loss_cap_usd == Decimal("500.0")
        
        # Test negative values
        with pytest.raises(ValueError, match="Value must be non-negative"):
            GuardrailLimits(daily_loss_cap_usd=Decimal("-100.0"))
        
        with pytest.raises(ValueError, match="Value must be non-negative"):
            GuardrailLimits(max_position_size_usd=Decimal("-1000.0"))


class TestGuardrailUpdate:
    """Test GuardrailUpdate model."""
    
    def test_partial_update(self):
        """Test partial guardrail update."""
        update = GuardrailUpdate(
            max_trades_per_day=25,
            daily_loss_cap_usd=Decimal("500.0")
        )
        
        assert update.max_trades_per_day == 25
        assert update.daily_loss_cap_usd == Decimal("500.0")
        assert update.max_contracts is None
        assert update.session_windows is None
    
    def test_validation(self):
        """Test guardrail update validation."""
        # Test valid update
        update = GuardrailUpdate(
            session_windows=["09:30-16:00", "20:00-22:00"],
            daily_loss_cap_usd=Decimal("750.0")
        )
        assert update.session_windows == ["09:30-16:00", "20:00-22:00"]
        
        # Test invalid session windows
        with pytest.raises(ValueError, match="Invalid session window format"):
            GuardrailUpdate(session_windows=["invalid"])
        
        # Test negative values
        with pytest.raises(ValueError, match="Value must be non-negative"):
            GuardrailUpdate(daily_loss_cap_usd=Decimal("-100.0"))


class TestConfigurationIntegration:
    """Test configuration integration."""
    
    def test_settings_to_guardrails(self):
        """Test converting settings to guardrails."""
        settings = Settings(
            max_trades_per_day=30,
            daily_loss_cap_usd=Decimal("750.0"),
            max_contracts=15,
            max_position_size_usd=Decimal("30000.0"),
            max_daily_volume_usd=Decimal("60000.0"),
            session_windows=["08:00-17:00"]
        )
        
        limits = GuardrailLimits(
            max_trades_per_day=settings.max_trades_per_day,
            daily_loss_cap_usd=settings.daily_loss_cap_usd,
            max_contracts=settings.max_contracts,
            max_position_size_usd=settings.max_position_size_usd,
            max_daily_volume_usd=settings.max_daily_volume_usd,
            session_windows=settings.session_windows,
        )
        
        assert limits.max_trades_per_day == 30
        assert limits.daily_loss_cap_usd == Decimal("750.0")
        assert limits.max_contracts == 15
        assert limits.max_position_size_usd == Decimal("30000.0")
        assert limits.max_daily_volume_usd == Decimal("60000.0")
        assert limits.session_windows == ["08:00-17:00"]
    
    def test_guardrail_update_application(self):
        """Test applying guardrail updates."""
        original_limits = GuardrailLimits(
            max_trades_per_day=50,
            daily_loss_cap_usd=Decimal("1000.0"),
            max_contracts=10,
            session_windows=["09:30-16:00"]
        )
        
        update = GuardrailUpdate(
            max_trades_per_day=25,
            daily_loss_cap_usd=Decimal("500.0")
        )
        
        # Apply update
        updated_limits = GuardrailLimits(
            max_trades_per_day=update.max_trades_per_day or original_limits.max_trades_per_day,
            daily_loss_cap_usd=update.daily_loss_cap_usd or original_limits.daily_loss_cap_usd,
            max_contracts=update.max_contracts or original_limits.max_contracts,
            max_position_size_usd=update.max_position_size_usd or original_limits.max_position_size_usd,
            max_daily_volume_usd=update.max_daily_volume_usd or original_limits.max_daily_volume_usd,
            session_windows=update.session_windows or original_limits.session_windows,
        )
        
        assert updated_limits.max_trades_per_day == 25
        assert updated_limits.daily_loss_cap_usd == Decimal("500.0")
        assert updated_limits.max_contracts == 10  # Unchanged
        assert updated_limits.session_windows == ["09:30-16:00"]  # Unchanged
