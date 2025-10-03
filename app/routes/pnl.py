"""
P&L routes
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from typing import List, Optional
from datetime import date, datetime

from app.deps import get_settings, get_supervisor
from app.models.base import Settings
from app.models.pnl import PnL, PnLSummary, PnLFilter
from app.services.supervisor import Supervisor

router = APIRouter(prefix="/pnl", tags=["pnl"])


@router.get("/daily")
async def get_daily_pnl(
    date: Optional[date] = None,
    supervisor: Supervisor = Depends(get_supervisor)
):
    """
    Get daily P&L.
    
    Args:
        date: Specific date (defaults to today)
        supervisor: Supervisor service
        
    Returns:
        Daily P&L information
    """
    try:
        if date is None:
            date = datetime.now().date()
        
        # Get daily P&L from supervisor
        daily_pnl = await supervisor.get_daily_pnl(date)
        
        if not daily_pnl:
            return {
                "date": date.isoformat(),
                "realized_pnl": 0.0,
                "unrealized_pnl": 0.0,
                "total_pnl": 0.0,
                "commission": 0.0,
                "net_pnl": 0.0,
                "trades_count": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "message": "No P&L data for this date"
            }
        
        return {
            "date": daily_pnl.date.isoformat(),
            "realized_pnl": float(daily_pnl.realized_pnl),
            "unrealized_pnl": float(daily_pnl.unrealized_pnl),
            "total_pnl": float(daily_pnl.total_pnl),
            "commission": float(daily_pnl.commission),
            "net_pnl": float(daily_pnl.net_pnl),
            "trades_count": daily_pnl.trades_count,
            "winning_trades": daily_pnl.winning_trades,
            "losing_trades": daily_pnl.losing_trades,
            "win_rate": float(daily_pnl.win_rate),
            "avg_win": float(daily_pnl.avg_win),
            "avg_loss": float(daily_pnl.avg_loss),
            "largest_win": float(daily_pnl.largest_win),
            "largest_loss": float(daily_pnl.largest_loss),
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve daily P&L: {str(e)}"
        )


@router.get("/summary")
async def get_pnl_summary(
    period: str = "daily",
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    supervisor: Supervisor = Depends(get_supervisor)
):
    """
    Get P&L summary for a period.
    
    Args:
        period: Period (daily, weekly, monthly, yearly)
        start_date: Start date
        end_date: End date
        supervisor: Supervisor service
        
    Returns:
        P&L summary
    """
    try:
        if start_date is None:
            start_date = datetime.now().date()
        if end_date is None:
            end_date = datetime.now().date()
        
        # Get P&L summary from supervisor
        pnl_summary = await supervisor.get_pnl_summary(period, start_date, end_date)
        
        if not pnl_summary:
            return {
                "period": period,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "total_pnl": 0.0,
                "realized_pnl": 0.0,
                "unrealized_pnl": 0.0,
                "commission": 0.0,
                "net_pnl": 0.0,
                "trades_count": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "message": "No P&L data for this period"
            }
        
        return {
            "period": pnl_summary.period,
            "start_date": pnl_summary.start_date.isoformat(),
            "end_date": pnl_summary.end_date.isoformat(),
            "total_pnl": float(pnl_summary.total_pnl),
            "realized_pnl": float(pnl_summary.realized_pnl),
            "unrealized_pnl": float(pnl_summary.unrealized_pnl),
            "commission": float(pnl_summary.commission),
            "net_pnl": float(pnl_summary.net_pnl),
            "trades_count": pnl_summary.trades_count,
            "winning_trades": pnl_summary.winning_trades,
            "losing_trades": pnl_summary.losing_trades,
            "win_rate": float(pnl_summary.win_rate),
            "avg_win": float(pnl_summary.avg_win),
            "avg_loss": float(pnl_summary.avg_loss),
            "largest_win": float(pnl_summary.largest_win),
            "largest_loss": float(pnl_summary.largest_loss),
            "max_drawdown": float(pnl_summary.max_drawdown),
            "sharpe_ratio": float(pnl_summary.sharpe_ratio) if pnl_summary.sharpe_ratio else None,
            "sortino_ratio": float(pnl_summary.sortino_ratio) if pnl_summary.sortino_ratio else None,
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve P&L summary: {str(e)}"
        )


@router.get("/history")
async def get_pnl_history(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 100,
    offset: int = 0,
    supervisor: Supervisor = Depends(get_supervisor)
):
    """
    Get P&L history.
    
    Args:
        start_date: Start date
        end_date: End date
        limit: Maximum number of records
        offset: Number of records to skip
        supervisor: Supervisor service
        
    Returns:
        P&L history
    """
    try:
        if start_date is None:
            start_date = datetime.now().date()
        if end_date is None:
            end_date = datetime.now().date()
        
        # Create filter
        pnl_filter = PnLFilter(
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )
        
        # Get P&L history from supervisor
        pnl_history = await supervisor.get_pnl_history(pnl_filter)
        
        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            "records": [
                {
                    "date": pnl.date.isoformat(),
                    "realized_pnl": float(pnl.realized_pnl),
                    "unrealized_pnl": float(pnl.unrealized_pnl),
                    "total_pnl": float(pnl.total_pnl),
                    "commission": float(pnl.commission),
                    "net_pnl": float(pnl.net_pnl),
                    "trades_count": pnl.trades_count,
                    "win_rate": float(pnl.win_rate),
                }
                for pnl in pnl_history
            ],
            "total_records": len(pnl_history),
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve P&L history: {str(e)}"
        )


@router.get("/positions")
async def get_positions(supervisor: Supervisor = Depends(get_supervisor)):
    """
    Get current positions.
    
    Args:
        supervisor: Supervisor service
        
    Returns:
        Current positions
    """
    try:
        # Get positions from supervisor
        positions = await supervisor.get_positions()
        
        return {
            "positions": [
                {
                    "symbol": pos.symbol,
                    "quantity": float(pos.quantity),
                    "avg_price": float(pos.avg_price),
                    "market_price": float(pos.market_price),
                    "market_value": float(pos.market_value),
                    "unrealized_pnl": float(pos.unrealized_pnl),
                    "realized_pnl": float(pos.realized_pnl),
                }
                for pos in positions
            ],
            "total_positions": len(positions),
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve positions: {str(e)}"
        )
