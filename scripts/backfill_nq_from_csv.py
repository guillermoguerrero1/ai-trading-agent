#!/usr/bin/env python3
"""
NQ Backfill Script - Generate NQ-only bracket trades from 1-minute candles CSV

This script processes 1-minute NQ futures data and generates breakout trades
using a lookback-based strategy with stop loss and take profit targets.
"""

from __future__ import annotations
import asyncio
import pandas as pd
from datetime import timedelta
from pathlib import Path
from app.store.db import get_session_factory
from app.models.trade_log import TradeLog
import structlog

logger = structlog.get_logger(__name__)

# Configuration
CSV_PATH = "data/raw/nq_1m.csv"   # Replace with your real file
ROOT = "NQ"
TICK = 0.25

def breakout_trades(df: pd.DataFrame, lookback=15, rr_target=2.0, risk_ticks=8.0, max_horizon=30):
    """
    Generate breakout trades from 1-minute candles data.
    
    Args:
        df: DataFrame with OHLCV data
        lookback: Number of periods to look back for breakout levels
        rr_target: Risk-reward ratio target
        risk_ticks: Risk in ticks
        max_horizon: Maximum bars to hold position
        
    Returns:
        List of trade dictionaries
    """
    df = df.copy().reset_index(drop=True)
    highs = df["high"].rolling(lookback).max()
    lows = df["low"].rolling(lookback).min()
    out = []
    
    logger.info("Processing breakout trades", 
                total_rows=len(df), 
                lookback=lookback, 
                rr_target=rr_target,
                risk_ticks=risk_ticks)
    
    for i in range(lookback, len(df)-1):
        row, nxt = df.iloc[i], df.iloc[i+1]
        
        # Determine breakout signal
        signal = None
        if row["close"] > highs.iloc[i-1]:
            signal = "BUY"
        elif row["close"] < lows.iloc[i-1]:
            signal = "SELL"
        
        if not signal:
            continue
            
        # Calculate entry and risk levels
        entry = float(nxt["open"])
        risk = risk_ticks * TICK
        
        if signal == "BUY":
            stop = entry - risk
            target = entry + rr_target * risk
        else:  # SELL
            stop = entry + risk
            target = entry - rr_target * risk
        
        # Simulate trade execution over next max_horizon bars
        seg = df.iloc[i+1:i+1+max_horizon]
        exit_px, outcome = None, None
        
        for _, b in seg.iterrows():
            hi, lo = float(b["high"]), float(b["low"])
            
            # Check if target or stop was hit
            if signal == "BUY":
                hit_tgt = hi >= target
                hit_stp = lo <= stop
            else:  # SELL
                hit_tgt = lo <= target
                hit_stp = hi >= stop
            
            # Determine exit conditions
            if hit_tgt and not hit_stp:
                exit_px, outcome = target, "target"
                break
            elif hit_stp and not hit_tgt:
                exit_px, outcome = stop, "stop"
                break
            elif hit_tgt and hit_stp:
                # Both hit in same bar - stop takes precedence
                exit_px, outcome = stop, "stop"
                break
        
        # Handle timeout case
        if exit_px is None:
            last = seg.iloc[-1] if len(seg) else nxt
            exit_px, outcome = float(last["close"]), "timeout"
        
        # Calculate P&L and risk metrics
        direction = 1 if signal == "BUY" else -1
        pnl = (exit_px - entry) * direction * 1  # 1 contract
        r = ((exit_px - entry) * direction) / (abs(entry - stop) or 1e-9)
        
        # Create features for ML
        feats = {
            "root_symbol": ROOT,
            "risk": abs(entry - stop),
            "rr": abs(target - entry) / (abs(entry - stop) or 1e-9),
            "in_session": 1,
            "lookback": lookback,
            "risk_ticks": risk_ticks,
            "max_horizon": max_horizon
        }
        
        trade = {
            "ts": pd.to_datetime(nxt["ts"], utc=True).to_pydatetime(),
            "symbol": str(nxt["symbol"]),
            "side": signal,
            "qty": 1,
            "entry": entry,
            "stop": stop,
            "target": target,
            "exit": exit_px,
            "pnl": pnl,
            "r": r,
            "outcome": outcome,
            "features": feats
        }
        
        out.append(trade)
    
    logger.info("Breakout trades generated", 
                total_trades=len(out),
                buy_trades=len([t for t in out if t["side"] == "BUY"]),
                sell_trades=len([t for t in out if t["side"] == "SELL"]),
                target_hits=len([t for t in out if t["outcome"] == "target"]),
                stop_hits=len([t for t in out if t["outcome"] == "stop"]),
                timeouts=len([t for t in out if t["outcome"] == "timeout"]))
    
    return out

async def main():
    """Main function to process CSV and create trades."""
    p = Path(CSV_PATH)
    if not p.exists():
        logger.error("CSV file not found", path=str(p))
        print(f"CSV not found: {p}")
        return 1
    
    logger.info("Loading NQ data", path=str(p))
    
    # Load and validate CSV
    try:
        df = pd.read_csv(p)
    except Exception as e:
        logger.error("Failed to load CSV", error=str(e))
        print(f"Failed to load CSV: {e}")
        return 1
    
    # Validate required columns
    need = {"ts", "open", "high", "low", "close", "volume", "symbol", "timeframe"}
    if not need.issubset(df.columns):
        missing = need - set(df.columns)
        logger.error("CSV missing required columns", missing=list(missing))
        print(f"CSV missing columns. Need: {need}, Missing: {missing}")
        return 1
    
    logger.info("CSV loaded successfully", 
                rows=len(df), 
                columns=list(df.columns),
                date_range=(df["ts"].min(), df["ts"].max()))
    
    # Generate trades
    try:
        trades = breakout_trades(df)
    except Exception as e:
        logger.error("Failed to generate trades", error=str(e))
        print(f"Failed to generate trades: {e}")
        return 1
    
    if not trades:
        logger.warning("No trades generated")
        print("No trades generated from the data")
        return 0
    
    # Save trades to database
    logger.info("Saving trades to database", count=len(trades))
    print(f"Creating {len(trades)} trades...")
    
    try:
        session_factory = get_session_factory()
        async with session_factory() as s:
            for i, t in enumerate(trades):
                row = TradeLog(
                    order_id=f"BACKFILL-NQ-{i:06d}",
                    symbol=t["symbol"],
                    side=t["side"],
                    qty=t["qty"],
                    entry_price=t["entry"],
                    stop_price=t["stop"],
                    target_price=t["target"],
                    exit_price=t["exit"],
                    created_at=t["ts"],
                    entered_at=t["ts"],
                    exited_at=t["ts"] + timedelta(minutes=1),
                    pnl_usd=t["pnl"],
                    r_multiple=t["r"],
                    outcome=t["outcome"],
                    features=t["features"],
                    notes="seed:nq_csv"
                )
                s.add(row)
            
            await s.commit()
            logger.info("Trades saved successfully", count=len(trades))
            
    except Exception as e:
        logger.error("Failed to save trades to database", error=str(e))
        print(f"Failed to save trades: {e}")
        return 1
    
    # Print summary statistics
    total_pnl = sum(t["pnl"] for t in trades)
    win_rate = len([t for t in trades if t["pnl"] > 0]) / len(trades) if trades else 0
    avg_r = sum(t["r"] for t in trades) / len(trades) if trades else 0
    
    print(f"\n[SUCCESS] NQ Backfill Complete!")
    print(f"   Total trades: {len(trades)}")
    print(f"   Total P&L: ${total_pnl:.2f}")
    print(f"   Win rate: {win_rate:.2%}")
    print(f"   Avg R-multiple: {avg_r:.2f}")
    print(f"   Target hits: {len([t for t in trades if t['outcome'] == 'target'])}")
    print(f"   Stop hits: {len([t for t in trades if t['outcome'] == 'stop'])}")
    print(f"   Timeouts: {len([t for t in trades if t['outcome'] == 'timeout'])}")
    
    return 0

if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
