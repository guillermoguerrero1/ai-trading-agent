#!/usr/bin/env python3
"""
Direct trade entry script - bypasses API and writes directly to database
"""
import sqlite3
import json
from datetime import datetime
from decimal import Decimal

def add_trade_direct(symbol, side, qty, entry_price, stop_price, target_price, 
                    strategy_id="Manual", setup="Direct-Entry", notes="direct-entry", 
                    entered_at=None):
    """Add trade directly to database."""
    
    # Calculate risk and reward
    risk = abs(entry_price - stop_price)
    rr = abs(target_price - entry_price) / (risk if risk > 0 else 1e-9)
    
    # Create features dict
    features = {
        "root_symbol": "NQ",
        "risk": float(risk),
        "rr": float(rr),
        "atr14": None,
        "body_pct": None,
        "upper_wick_pct": None,
        "lower_wick_pct": None,
        "htf_trend": None,
        "in_session": 1,
        "strategy_id": strategy_id,
        "setup": setup,
        "rule_version": "v1.0",
        "confidence": 0.5,
        "entry_reason": "Direct database entry",
        "exit_plan": "Target or trail"
    }
    
    # Connect to database
    conn = sqlite3.connect('trading_agent.db')
    cursor = conn.cursor()
    
    # Insert trade
    cursor.execute("""
        INSERT INTO trade_logs (
            order_id, created_at, symbol, side, qty, entry_price, stop_price, target_price,
            entered_at, features, notes, outcome, pnl_usd
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        f"direct-{int(datetime.utcnow().timestamp())}",
        datetime.utcnow().isoformat(),
        symbol,
        side,
        qty,
        entry_price,
        stop_price,
        target_price,
        entered_at.isoformat() if entered_at else None,
        json.dumps(features),
        notes,
        None,  # outcome will be set later
        None   # pnl_usd will be calculated later
    ))
    
    conn.commit()
    trade_id = cursor.lastrowid
    conn.close()
    
    print(f"[SUCCESS] Trade added successfully! ID: {trade_id}")
    print(f"   {symbol} {side} {qty} @ {entry_price}")
    print(f"   Stop: {stop_price}, Target: {target_price}")
    print(f"   Risk: {risk}, R/R: {rr:.2f}")
    
    return trade_id

def main():
    print("Direct Trade Entry (NQ Only)")
    print("=" * 40)
    
    # Get trade details
    symbol = input("Symbol [NQZ5]: ").strip() or "NQZ5"
    side = (input("Side (BUY/SELL): ").strip() or "BUY").upper()
    qty = float(input("Quantity [1]: ") or "1")
    entry_price = float(input("Entry Price: "))
    stop_price = float(input("Stop Price: "))
    target_price = float(input("Target Price: "))
    strategy_id = input("Strategy ID [Manual]: ").strip() or "Manual"
    setup = input("Setup [Direct-Entry]: ").strip() or "Direct-Entry"
    notes = input("Notes [direct-entry]: ").strip() or "direct-entry"
    
    # Optional custom entry timestamp for backfilled trades
    custom_timestamp = input("Custom entry timestamp (YYYY-MM-DD HH:MM:SS) [leave blank for now]: ").strip()
    entered_at = None
    if custom_timestamp:
        try:
            entered_at = datetime.strptime(custom_timestamp, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            print("Invalid timestamp format. Using current time.")
            entered_at = None
    
    # Round to NQ ticks (0.25)
    def round_tick(x, tick=0.25):
        return round(round(x / tick) * tick, 2)
    
    entry_price = round_tick(entry_price)
    stop_price = round_tick(stop_price)
    target_price = round_tick(target_price)
    
    print(f"\nTrade Summary:")
    print(f"   Symbol: {symbol}")
    print(f"   Side: {side}")
    print(f"   Quantity: {qty}")
    print(f"   Entry: {entry_price}")
    print(f"   Stop: {stop_price}")
    print(f"   Target: {target_price}")
    
    confirm = input("\nSubmit this trade? (y/N): ").strip().lower()
    if confirm == 'y':
        add_trade_direct(symbol, side, qty, entry_price, stop_price, target_price,
                        strategy_id, setup, notes, entered_at)
    else:
        print("[CANCELLED] Trade cancelled")

if __name__ == "__main__":
    main()
