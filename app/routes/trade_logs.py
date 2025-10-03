from typing import List
from fastapi import APIRouter, Query
from sqlmodel import select, desc
from app.store.db import get_session_factory
from app.models.trade_log import TradeLog

router = APIRouter()

@router.get("/logs/trades", response_model=List[TradeLog])
@router.get("/logs/trades/", response_model=List[TradeLog])
async def list_trade_logs(limit: int = Query(50, ge=1, le=500)) -> List[TradeLog]:
    session_factory = get_session_factory()
    async with session_factory() as s:
        stmt = select(TradeLog).order_by(desc(TradeLog.created_at)).limit(limit)
        result = await s.execute(stmt)
        return list(result.scalars().all())
