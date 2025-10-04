import asyncio
from sqlmodel import select
from app.store.db import get_session_factory
from app.models.trade_log import TradeLog
import pandas as pd
import numpy as np
from pathlib import Path
import os

OUT_PATH = "data/processed/trades_dataset.parquet"
EXCLUDE_SEED = os.getenv("EXCLUDE_SEED","1") == "1"

async def build_dataset(out_path: str = OUT_PATH):
    session_factory = get_session_factory()
    async with session_factory() as s:
        stmt = select(TradeLog)
        result = await s.execute(stmt)
        rows = list(result.scalars().all())
    recs = []
    for r in rows:
        recs.append({
            "ts": r.created_at,
            "symbol": r.symbol,
            "side": 1 if (r.side or "").upper()=="BUY" else -1,
            "qty": r.qty or 0,
            "entry": r.entry_price or 0.0,
            "stop": r.stop_price,
            "target": r.target_price,
            "exit": r.exit_price,
            "pnl": r.pnl_usd,
            "r": r.r_multiple,
            "outcome": r.outcome,
            "notes": r.notes or "",
        })
    df = pd.DataFrame(recs)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    if df.empty:
        df.to_parquet(out_path, index=False)
        return out_path
    # optional: drop synthetic seed rows
    if EXCLUDE_SEED and "notes" in df.columns:
        df = df[~df["notes"].str.contains("seed:true", na=False)]
    # label: +1 if r >= +1, -1 if r <= -1, else 0
    df["label"] = np.where(df["r"]>=1, 1, np.where(df["r"]<=-1, -1, 0))
    # basic features
    df["risk"] = (df["entry"] - df["stop"]).abs().fillna(0.0)
    df["rr"] = (df["target"] - df["entry"]).abs().fillna(0.0) / df["risk"].replace(0, 1.0)
    df.to_parquet(out_path, index=False)
    return out_path

if __name__ == "__main__":
    print(asyncio.run(build_dataset()))
