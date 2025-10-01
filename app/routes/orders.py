"""
Order management routes
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from typing import List, Optional
from uuid import UUID

from app.deps import get_settings, get_supervisor
from app.models.base import Settings
from app.models.order import OrderRequest, OrderResponse, OrderFilter
from app.models.event import Event, EventType, EventSeverity
from app.services.supervisor import Supervisor

router = APIRouter(prefix="/v1/orders", tags=["orders"])


@router.post("/", response_model=OrderResponse)
async def create_order(
    order_request: OrderRequest,
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
