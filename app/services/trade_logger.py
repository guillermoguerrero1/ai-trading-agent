from __future__ import annotations
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.store.db import get_session_factory
from app.models.trade_log import TradeLog

class TradeLogger:
    def __init__(self):
        self.session_factory = get_session_factory()

    async def log_open(
        self,
        *,
        order_id: str,
        symbol: str,
        side: str,
        qty: float,
        entry: float,
        stop: Optional[float],
        target: Optional[float],
        features: Optional[Dict[str, Any]] = None,
        notes: Optional[str] = None,
        model_score: Optional[float] = None,
        model_version: Optional[str] = None,
    ) -> int:
        row = TradeLog(
            order_id=order_id,
            symbol=symbol,
            side=side.upper(),
            qty=qty,
            entry_price=entry,
            stop_price=stop,
            target_price=target,
            entered_at=datetime.utcnow(),
            features=features,
            notes=notes,
            model_score=model_score,
            model_version=model_version,
        )
        async with self.session_factory() as s:
            s.add(row)
            await s.commit()
            await s.refresh(row)
            return row.id

    async def log_close(
        self,
        *,
        order_id: str,
        exit_price: float,
        outcome: str,
    ) -> None:
        async with self.session_factory() as s:
            result = await s.execute(select(TradeLog).where(TradeLog.order_id == order_id))
            row = result.scalar_one_or_none()
            if not row:
                # late attach (minimal)
                row = TradeLog(order_id=order_id, symbol="", side="", qty=0, entry_price=0.0)
                s.add(row)
                await s.commit()
                await s.refresh(row)
            row.exit_price = exit_price
            row.exited_at = datetime.utcnow()
            # PnL & R calc (if stop present)
            if row.side and row.entry_price and exit_price is not None:
                direction = 1 if row.side == "BUY" else -1
                row.pnl_usd = (exit_price - row.entry_price) * direction * row.qty
                if row.stop_price:
                    risk = abs(row.entry_price - row.stop_price)
                    row.r_multiple = (exit_price - row.entry_price) * direction / risk if risk > 0 else None
            row.outcome = outcome
            s.add(row)
            await s.commit()

    async def annotate(self, *, order_id: str, notes: str) -> None:
        async with self.session_factory() as s:
            result = await s.execute(select(TradeLog).where(TradeLog.order_id == order_id))
            row = result.scalar_one_or_none()
            if row:
                row.notes = (row.notes + "\n" if row.notes else "") + notes
                s.add(row)
                await s.commit()
