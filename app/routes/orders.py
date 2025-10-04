"""
Order management routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from typing import List, Optional
from uuid import UUID
import hashlib
import os

from app.deps import get_settings, get_supervisor, get_trade_logger, get_current_user
from app.models.base import Settings
from app.models.order import OrderRequest, OrderResponse, OrderFilter
from app.models.event import Event, EventType, EventSeverity
from app.services.supervisor import Supervisor
from agent.infer import allow, score

import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/", response_model=OrderResponse)
async def create_order(
    order_request: OrderRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
    supervisor: Supervisor = Depends(get_supervisor)
):
    """
    Create a new order.
    
    Args:
        order_request: Order request
        settings: Application settings
        supervisor: Supervisor service
        
    Returns:
        Created order response
    """
    try:
        # Check if trading is halted
        if supervisor.is_halted():
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Trading is currently halted"
            )
        
        # Model gate check (optional runtime toggle)
        require_model_gate = bool(getattr(request.app.state, "require_model_gate", False))
        if require_model_gate:
            # Build minimal features from payload (entry/stop/target must exist)
            entry_price = float(order_request.price) if order_request.price else 0.0
            stop_price = float(order_request.stop_price) if order_request.stop_price else entry_price
            target_price = entry_price  # OrderRequest doesn't have target field, use entry as fallback
            
            risk = abs(entry_price - stop_price)
            rr = (abs(target_price - entry_price) / (risk if risk > 0 else 1.0))
            features = {"risk": risk, "rr": rr}
            
            # Get dynamic threshold from app state if available
            dynamic_threshold = getattr(request.app.state, "model_threshold", None)
            if not allow(features, threshold=dynamic_threshold):
                return JSONResponse(
                    status_code=409, 
                    content={
                        "error": "model_gate", 
                        "score": score(features),
                        "threshold": dynamic_threshold
                    }
                )
        
        # Compute model score and version for logging (regardless of gate status)
        model_path = os.getenv("MODEL_PATH", "models/clf.joblib")
        model_version = None
        model_score = None
        
        if os.path.exists(model_path):
            try:
                with open(model_path, "rb") as f:
                    model_version = hashlib.md5(f.read()).hexdigest()
            except Exception:
                model_version = None
        
        # Compute model score if we have features
        if 'features' in locals() and features:
            try:
                model_score = score(features)
            except Exception:
                model_score = None
        
        # Submit order through supervisor
        order_response = await supervisor.submit_order(order_request)
        
        # Log order creation
        await supervisor.log_event(
            Event(
                event_type=EventType.ORDER,
                severity=EventSeverity.LOW,
                message=f"Order created: {order_response.symbol} {order_response.side} {order_response.quantity}",
                data={"order_id": order_response.order_id, "order": order_request.dict()},
                source="order_api"
            )
        )
        
        # Log trade opening as backup (in case broker doesn't have TradeLogger)
        # capture optional features from request body if present
        features = order_request.dict().get("features") if hasattr(order_request, "dict") else None
        try:
            # Access TradeLogger directly from app state
            trade_logger = getattr(request.app.state, "trade_logger", None)
            if trade_logger:
                await trade_logger.log_open(
                    order_id=order_response.order_id,
                    symbol=order_request.symbol,
                    side=order_request.side,
                    qty=float(order_request.quantity),
                    entry=float(order_request.price) if order_request.price else 0.0,
                    stop=float(order_request.stop_price) if order_request.stop_price else None,
                    target=None,  # OrderRequest doesn't have target field
                    features=features,
                    notes="orders.route.open",
                    model_score=model_score,
                    model_version=model_version,
                )
                logger.info("Trade logged successfully from orders route", order_id=order_response.order_id)
            else:
                logger.warning("TradeLogger not available in app state", order_id=order_response.order_id)
        except Exception as e:
            # don't fail the API on logging error
            logger.error("Failed to log trade from orders route", error=str(e), order_id=order_response.order_id)
            pass
        
        return order_response
        
    except HTTPException:
        raise
    except Exception as e:
        # Log error
        await supervisor.log_event(
            Event(
                event_type=EventType.ERROR,
                severity=EventSeverity.HIGH,
                message=f"Order creation error: {str(e)}",
                data={"order": order_request.dict(), "error": str(e)},
                source="order_api"
            )
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Order creation failed: {str(e)}"
        )


@router.get("/", response_model=List[OrderResponse])
async def get_orders(
    symbol: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    supervisor: Supervisor = Depends(get_supervisor)
):
    """
    Get orders with optional filtering.
    
    Args:
        symbol: Filter by symbol
        status: Filter by status
        limit: Maximum number of orders to return
        offset: Number of orders to skip
        supervisor: Supervisor service
        
    Returns:
        List of orders
    """
    try:
        # Create filter
        order_filter = OrderFilter(
            symbols=[symbol] if symbol else None,
            statuses=[status] if status else None,
            limit=limit,
            offset=offset
        )
        
        # Get orders from supervisor
        orders = await supervisor.get_orders(order_filter)
        
        return orders
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve orders: {str(e)}"
        )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    supervisor: Supervisor = Depends(get_supervisor)
):
    """
    Get a specific order by ID.
    
    Args:
        order_id: Order ID
        supervisor: Supervisor service
        
    Returns:
        Order details
    """
    try:
        order = await supervisor.get_order(order_id)
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order {order_id} not found"
            )
        
        return order
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve order: {str(e)}"
        )


@router.delete("/{order_id}")
async def cancel_order(
    order_id: str,
    current_user: dict = Depends(get_current_user),
    supervisor: Supervisor = Depends(get_supervisor)
):
    """
    Cancel an order.
    
    Args:
        order_id: Order ID to cancel
        supervisor: Supervisor service
        
    Returns:
        Cancellation result
    """
    try:
        # Check if trading is halted
        if supervisor.is_halted():
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Trading is currently halted"
            )
        
        # Cancel order through supervisor
        cancellation_result = await supervisor.cancel_order(order_id)
        
        if not cancellation_result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to cancel order: {cancellation_result.reason}"
            )
        
        # Log order cancellation
        await supervisor.log_event(
            Event(
                event_type=EventType.ORDER,
                severity=EventSeverity.LOW,
                message=f"Order cancelled: {order_id}",
                data={"order_id": order_id, "reason": cancellation_result.reason},
                source="order_api"
            )
        )
        
        return {
            "status": "success",
            "message": f"Order {order_id} cancelled successfully",
            "order_id": order_id,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        # Log error
        await supervisor.log_event(
            Event(
                event_type=EventType.ERROR,
                severity=EventSeverity.HIGH,
                message=f"Order cancellation error: {str(e)}",
                data={"order_id": order_id, "error": str(e)},
                source="order_api"
            )
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Order cancellation failed: {str(e)}"
        )


@router.get("/{order_id}/status")
async def get_order_status(
    order_id: str,
    supervisor: Supervisor = Depends(get_supervisor)
):
    """
    Get order status.
    
    Args:
        order_id: Order ID
        supervisor: Supervisor service
        
    Returns:
        Order status information
    """
    try:
        order = await supervisor.get_order(order_id)
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order {order_id} not found"
            )
        
        return {
            "order_id": order_id,
            "status": order.status,
            "filled_quantity": float(order.filled_quantity),
            "remaining_quantity": float(order.quantity - order.filled_quantity),
            "created_at": order.created_at.isoformat(),
            "updated_at": order.updated_at.isoformat(),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve order status: {str(e)}"
        )
