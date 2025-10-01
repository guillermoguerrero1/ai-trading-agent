"""
Risk guard service for managing trading guardrails
"""

from datetime import datetime, time
from decimal import Decimal
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from app.models.base import Settings
from app.models.limits import GuardrailLimits, GuardrailViolation, ViolationSeverity
from app.models.event import Event, EventType, EventSeverity

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class RiskCheckResult:
    """Risk check result."""
    allowed: bool
    reason: str
    violation: Optional[GuardrailViolation] = None


class RiskGuard:
    """Risk guard service for enforcing trading limits."""
    
    def __init__(self, settings: Settings):
        """
        Initialize risk guard.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.limits = GuardrailLimits(
            max_trades_per_day=settings.max_trades_per_day,
            daily_loss_cap_usd=settings.daily_loss_cap_usd,
            max_contracts=settings.max_contracts,
            max_position_size_usd=settings.max_position_size_usd,
            max_daily_volume_usd=settings.max_daily_volume_usd,
            session_windows=settings.session_windows,
        )
        
        # Runtime state
        self.daily_trades = 0
        self.daily_loss = Decimal("0")
        self.daily_volume = Decimal("0")
        self.current_positions: Dict[str, int] = {}
        self.violations: List[GuardrailViolation] = []
        self.session_start_equity = settings.initial_capital
        self.current_equity = settings.initial_capital
        
        # Reset daily counters at midnight
        self._last_reset_date = datetime.now().date()
        
    async def check_signal(self, signal) -> RiskCheckResult:
        """
        Check if a signal is allowed.
        
        Args:
            signal: Signal to check
            
        Returns:
            Risk check result
        """
        try:
            # Reset daily counters if needed
            await self._reset_daily_counters_if_needed()
            
            # Check if trading is allowed during current time
            if not self._is_trading_session():
                return RiskCheckResult(
                    allowed=False,
                    reason="Trading not allowed outside session windows",
                    violation=GuardrailViolation(
                        violation_type="session_window",
                        severity=ViolationSeverity.WARNING,
                        message="Trading attempted outside allowed session windows",
                        current_value=datetime.now().time().strftime("%H:%M"),
                        limit_value=self.limits.session_windows,
                    )
                )
            
            # Check daily trade limit
            if self.daily_trades >= self.limits.max_trades_per_day:
                return RiskCheckResult(
                    allowed=False,
                    reason="Daily trade limit exceeded",
                    violation=GuardrailViolation(
                        violation_type="max_trades_per_day",
                        severity=ViolationSeverity.ERROR,
                        message=f"Daily trade limit of {self.limits.max_trades_per_day} exceeded",
                        current_value=self.daily_trades,
                        limit_value=self.limits.max_trades_per_day,
                    )
                )
            
            # Check daily loss cap
            if abs(self.daily_loss) >= self.limits.daily_loss_cap_usd:
                return RiskCheckResult(
                    allowed=False,
                    reason="Daily loss cap exceeded",
                    violation=GuardrailViolation(
                        violation_type="daily_loss_cap",
                        severity=ViolationSeverity.CRITICAL,
                        message=f"Daily loss cap of ${self.limits.daily_loss_cap_usd} exceeded",
                        current_value=float(self.daily_loss),
                        limit_value=float(self.limits.daily_loss_cap_usd),
                    )
                )
            
            # Check position size limit
            estimated_value = signal.quantity * (signal.price or 0)
            if estimated_value > self.limits.max_position_size_usd:
                return RiskCheckResult(
                    allowed=False,
                    reason="Position size limit exceeded",
                    violation=GuardrailViolation(
                        violation_type="max_position_size",
                        severity=ViolationSeverity.ERROR,
                        message=f"Position size limit of ${self.limits.max_position_size_usd} exceeded",
                        current_value=float(estimated_value),
                        limit_value=float(self.limits.max_position_size_usd),
                    )
                )
            
            # Check daily volume limit
            if self.daily_volume + estimated_value > self.limits.max_daily_volume_usd:
                return RiskCheckResult(
                    allowed=False,
                    reason="Daily volume limit exceeded",
                    violation=GuardrailViolation(
                        violation_type="max_daily_volume",
                        severity=ViolationSeverity.ERROR,
                        message=f"Daily volume limit of ${self.limits.max_daily_volume_usd} exceeded",
                        current_value=float(self.daily_volume + estimated_value),
                        limit_value=float(self.limits.max_daily_volume_usd),
                    )
                )
            
            return RiskCheckResult(allowed=True, reason="Signal approved")
            
        except Exception as e:
            logger.error("Risk check failed", error=str(e), exc_info=True)
            return RiskCheckResult(
                allowed=False,
                reason=f"Risk check error: {str(e)}"
            )
    
    async def check_order(self, order) -> RiskCheckResult:
        """
        Check if an order is allowed.
        
        Args:
            order: Order to check
            
        Returns:
            Risk check result
        """
        # For now, use the same logic as signal check
        return await self.check_signal(order)
    
    def _is_trading_session(self) -> bool:
        """
        Check if current time is within trading session windows.
        
        Returns:
            True if trading is allowed
        """
        current_time = datetime.now().time()
        
        for window in self.limits.session_windows:
            try:
                start_str, end_str = window.split('-')
                start_time = time.fromisoformat(start_str)
                end_time = time.fromisoformat(end_str)
                
                if start_time <= current_time <= end_time:
                    return True
            except (ValueError, IndexError):
                logger.warning("Invalid session window format", window=window)
                continue
        
        return False
    
    async def _reset_daily_counters_if_needed(self):
        """Reset daily counters if a new day has started."""
        current_date = datetime.now().date()
        
        if current_date > self._last_reset_date:
            logger.info("Resetting daily counters", date=current_date.isoformat())
            
            self.daily_trades = 0
            self.daily_loss = Decimal("0")
            self.daily_volume = Decimal("0")
            self._last_reset_date = current_date
            
            # Reset session start equity to current equity
            self.session_start_equity = self.current_equity
    
    async def record_trade(self, trade_data: Dict[str, Any]):
        """
        Record a completed trade.
        
        Args:
            trade_data: Trade data
        """
        try:
            # Increment daily trade count
            self.daily_trades += 1
            
            # Update daily volume
            trade_value = trade_data.get("quantity", 0) * trade_data.get("price", 0)
            self.daily_volume += Decimal(str(trade_value))
            
            # Update daily loss (if realized P&L is available)
            if "realized_pnl" in trade_data:
                self.daily_loss += Decimal(str(trade_data["realized_pnl"]))
            
            # Update current equity
            if "equity_change" in trade_data:
                self.current_equity += Decimal(str(trade_data["equity_change"]))
            
            logger.info(
                "Trade recorded",
                daily_trades=self.daily_trades,
                daily_volume=float(self.daily_volume),
                daily_loss=float(self.daily_loss),
            )
            
        except Exception as e:
            logger.error("Failed to record trade", error=str(e), exc_info=True)
    
    async def record_violation(self, violation: GuardrailViolation):
        """
        Record a guardrail violation.
        
        Args:
            violation: Violation to record
        """
        self.violations.append(violation)
        
        logger.warning(
            "Guardrail violation recorded",
            violation_type=violation.violation_type,
            severity=violation.severity,
            message=violation.message,
        )
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current risk guard status.
        
        Returns:
            Risk guard status
        """
        return {
            "limits": self.limits.dict(),
            "daily_trades": self.daily_trades,
            "daily_loss": float(self.daily_loss),
            "daily_volume": float(self.daily_volume),
            "current_positions": self.current_positions,
            "violation_count": len(self.violations),
            "unresolved_violations": len([v for v in self.violations if not v.resolved]),
            "session_start_equity": float(self.session_start_equity),
            "current_equity": float(self.current_equity),
            "equity_change": float(self.current_equity - self.session_start_equity),
            "trading_session": self._is_trading_session(),
        }
    
    def is_halted(self) -> bool:
        """
        Check if trading is halted due to violations.
        
        Returns:
            True if trading is halted
        """
        # Check for critical violations
        critical_violations = [
            v for v in self.violations 
            if v.severity == ViolationSeverity.CRITICAL and not v.resolved
        ]
        
        return len(critical_violations) > 0
    
    async def update_limits(self, new_limits: GuardrailLimits):
        """
        Update guardrail limits.
        
        Args:
            new_limits: New limits to apply
        """
        logger.info("Updating guardrail limits", limits=new_limits.dict())
        
        self.limits = new_limits
        
        # Log the change
        logger.info("Guardrail limits updated successfully")
