from fastapi import APIRouter, Response, Query
from sqlmodel import select, desc
from app.store.db import get_session_factory
from app.models.trade_log import TradeLog
import csv, io

router = APIRouter()

@router.get("/export/trades.csv")
async def export_trades_csv(limit: int = Query(10000, ge=1, le=100000)):
    session_factory = get_session_factory()
    async with session_factory() as s:
        stmt = select(TradeLog).order_by(desc(TradeLog.created_at)).limit(limit)
        result = await s.execute(stmt)
        rows = list(result.scalars().all())
    
    if not rows:
        return Response(status_code=204)
    
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["created_at","symbol","side","qty","entry_price","stop_price","target_price","exit_price","pnl_usd","r_multiple","outcome","notes"])
    for r in rows:
        w.writerow([r.created_at, r.symbol, r.side, r.qty, r.entry_price, r.stop_price, r.target_price, r.exit_price, r.pnl_usd, r.r_multiple, r.outcome, (r.notes or "").replace("\n"," ")])
    return Response(content=buf.getvalue(), media_type="text/csv")
