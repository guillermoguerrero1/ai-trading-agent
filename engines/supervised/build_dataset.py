import asyncio
from sqlmodel import select
from app.store.db import get_session_factory
from app.models.trade_log import TradeLog
import pandas as pd
import numpy as np
from pathlib import Path
import os
import json
from datetime import timezone

OUT_PATH = "data/processed/trades_dataset.parquet"
EXCLUDE_SEED = os.getenv("EXCLUDE_SEED","1") == "1"
EXCLUDE_BACKFILL = os.getenv("EXCLUDE_BACKFILL","0") == "1"
WEIGHT_BACKFILL = float(os.getenv("WEIGHT_BACKFILL","1.0"))

async def build_dataset(out_path: str = OUT_PATH):
    session_factory = get_session_factory()
    async with session_factory() as s:
        stmt = select(TradeLog)
        result = await s.execute(stmt)
        rows = list(result.scalars().all())
    recs = []
    for r in rows:
        # Parse features JSON to extract is_backfill
        is_backfill = False
        if r.features:
            try:
                features = json.loads(r.features) if isinstance(r.features, str) else r.features
                is_backfill = features.get("is_backfill", False)
            except (json.JSONDecodeError, TypeError):
                is_backfill = False
        
        # Use entered_at if available, fallback to created_at
        # Ensure both timestamps are timezone-aware
        if r.entered_at:
            timestamp = r.entered_at
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
        else:
            timestamp = r.created_at
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
        
        recs.append({
            "ts": timestamp,
            "created_at": r.created_at,
            "entered_at": r.entered_at,
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
            "is_backfill": is_backfill,
        })
    df = pd.DataFrame(recs)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    if df.empty:
        df.to_parquet(out_path, index=False)
        return out_path
    
    # optional: drop synthetic seed rows
    if EXCLUDE_SEED and "notes" in df.columns:
        df = df[~df["notes"].str.contains("seed:true", na=False)]
    
    # optional: drop backfill rows
    if EXCLUDE_BACKFILL:
        df = df[~df["is_backfill"]]
        print(f"Excluded backfill rows, remaining: {len(df)}")
    
    # add weight column: 1.0 for live/paper, WEIGHT_BACKFILL for backfill
    df["weight"] = np.where(df["is_backfill"], WEIGHT_BACKFILL, 1.0)
    
    # sort by timestamp for time-based splits
    df = df.sort_values("ts").reset_index(drop=True)
    
    # label: +1 if r >= +1, -1 if r <= -1, else 0
    df["label"] = np.where(df["r"]>=1, 1, np.where(df["r"]<=-1, -1, 0))
    
    # basic features
    df["risk"] = (df["entry"] - df["stop"]).abs().fillna(0.0)
    df["rr"] = (df["target"] - df["entry"]).abs().fillna(0.0) / df["risk"].replace(0, 1.0)
    
    # print dataset statistics
    print(f"Dataset built: {len(df)} rows")
    print(f"Backfill rows: {df['is_backfill'].sum()}")
    print(f"Live rows: {(~df['is_backfill']).sum()}")
    print(f"Weight backfill: {WEIGHT_BACKFILL}")
    
    df.to_parquet(out_path, index=False)
    return out_path

if __name__ == "__main__":
    print(asyncio.run(build_dataset()))
