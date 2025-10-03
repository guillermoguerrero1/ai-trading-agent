"""
Signal processing routes
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from app.deps import get_settings, get_risk_guard, get_supervisor
from app.models.base import Settings
from app.models.event import Event, EventType, EventSeverity
from app.models.order import OrderRequest, OrderSide, OrderType
from app.services.risk_guard import RiskGuard
from app.services.supervisor import Supervisor

router = APIRouter(prefix="/signal", tags=["signal"])


class SignalRequest:
    """Signal request model."""
    
    def __init__(
        self,
        signal_type: str,
        symbol: str,
        quantity: float,
        price: float = None,
        confidence: float = 1.0,
        metadata: dict = None
    ):
        self.signal_type = signal_type
        self.symbol = symbol
        self.quantity = quantity
        self.price = price
        self.confidence = confidence
        self.metadata = metadata or {}


@router.post("/")
async def process_signal(
    signal_data: dict,
    settings: Settings = Depends(get_settings),
    risk_guard: RiskGuard = Depends(get_risk_guard),
    supervisor: Supervisor = Depends(get_supervisor)
):
    """
    Process trading signal.
    
    Args:
        signal_data: Signal data
        settings: Application settings
        risk_guard: Risk guard service
        supervisor: Supervisor service
        
    Returns:
        Signal processing result
    """
    try:
        # Parse signal data
        signal = SignalRequest(
            signal_type=signal_data.get("signal_type"),
            symbol=signal_data.get("symbol"),
            quantity=signal_data.get("quantity"),
            price=signal_data.get("price"),
            confidence=signal_data.get("confidence", 1.0),
            metadata=signal_data.get("metadata", {})
        )
        
        # Validate signal
        if not signal.signal_type or not signal.symbol or not signal.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required signal fields"
            )
        
        # Check if trading is halted
        if supervisor.is_halted():
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Trading is currently halted"
            )
        
        # Risk check
        risk_check = await risk_guard.check_signal(signal)
        if not risk_check.allowed:
            # Log violation
            await supervisor.log_event(
                Event(
                    event_type=EventType.RISK,
                    severity=EventSeverity.HIGH,
                    message=f"Signal rejected: {risk_check.reason}",
                    data={"signal": signal_data, "violation": risk_check.violation},
                    source="risk_guard"
                )
            )
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Signal rejected: {risk_check.reason}"
            )
        
        # Convert signal to order
        order_side = OrderSide.BUY if signal.signal_type.upper() == "BUY" else OrderSide.SELL
        order_type = OrderType.MARKET if signal.price is None else OrderType.LIMIT
        
        order_request = OrderRequest(
            symbol=signal.symbol,
            side=order_side,
            quantity=signal.quantity,
            order_type=order_type,
            price=signal.price,
            metadata={
                "signal_confidence": signal.confidence,
                "signal_metadata": signal.metadata,
                "signal_source": "api"
            }
        )
        
        # Submit order
        order_response = await supervisor.submit_order(order_request)
        
        # Log successful signal processing
        await supervisor.log_event(
            Event(
                event_type=EventType.ORDER,
                severity=EventSeverity.LOW,
                message=f"Signal processed successfully: {signal.symbol} {signal.signal_type} {signal.quantity}",
                data={"signal": signal_data, "order_id": order_response.order_id},
                source="signal_processor"
            )
        )
        
        return {
            "status": "success",
            "message": "Signal processed successfully",
            "order_id": order_response.order_id,
            "signal": signal_data,
            "risk_check": risk_check.dict() if hasattr(risk_check, 'dict') else None,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        # Log error
        await supervisor.log_event(
            Event(
                event_type=EventType.ERROR,
                severity=EventSeverity.HIGH,
                message=f"Signal processing error: {str(e)}",
                data={"signal": signal_data, "error": str(e)},
                source="signal_processor"
            )
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Signal processing failed: {str(e)}"
        )


@router.get("/status")
async def get_signal_status(supervisor: Supervisor = Depends(get_supervisor)):
    """
    Get signal processing status.
    
    Returns:
        Signal processing status
    """
    return {
        "status": "active" if not supervisor.is_halted() else "halted",
        "trading_halted": supervisor.is_halted(),
        "daily_signals": 0,  # TODO: Implement signal counting
        "last_signal": None,  # TODO: Implement last signal tracking
    }
