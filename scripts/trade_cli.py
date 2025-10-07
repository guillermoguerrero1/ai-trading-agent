#!/usr/bin/env python3
import json, os, sys, time, uuid, argparse
import requests

API = os.getenv("API", "http://localhost:9001")

def round_tick(x, tick=0.25):
    return round(round(x / tick) * tick, 2)

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Interactive CLI for NQ trade entry")
    parser.add_argument("--entered-at", type=str, help="Custom entry timestamp (ISO format, e.g., '2025-09-12T13:45:00Z')")
    parser.add_argument("--backfill", action="store_true", help="Mark as backfilled trade")
    args = parser.parse_args()
    
    # Interactive input
    sym = input("Symbol [NQZ5]: ").strip() or "NQZ5"
    side = (input("Side (BUY/SELL): ").strip() or "BUY").upper()
    qty  = int(input("Qty [1]: ") or "1")
    entry = float(input("Entry: "))
    stop  = float(input("Stop: "))
    target= float(input("Target: "))
    paper = (input("Paper? [y]/n: ").strip().lower() or "y") == "y"

    entry, stop, target = map(round_tick, (entry, stop, target))
    risk = abs(entry - stop)
    rr   = abs(target - entry) / (risk if risk > 0 else 1e-9)

    # Build payload
    payload = {
        "symbol": sym, "side": side, "quantity": qty,
        "order_type": "LIMIT", "price": entry, "stop_price": stop, "target_price": target,
        "paper": paper,
        "features": {
            "root_symbol": "NQ", "risk": risk, "rr": rr,
            "in_session": 1, "strategy_id": "Manual", "setup": "Manual-Entry",
            "rule_version": "v1.0", "confidence": 0.5
        },
        "notes": "cli-entry"
    }
    
    # Add entered_at if provided
    if args.entered_at:
        payload["entered_at"] = args.entered_at
        print(f"Using custom entered_at: {args.entered_at}")
    
    # Add backfill flag if specified
    if args.backfill:
        payload["features"]["is_backfill"] = True
        print("Marking as backfilled trade")
    
    # Display payload for verification
    print(f"\nPayload to submit:")
    print(json.dumps(payload, indent=2))
    
    key = f"cli-{int(time.time())}-{uuid.uuid4().hex[:6]}"
    r = requests.post(f"{API}/v1/orders",
                      headers={"Content-Type":"application/json","Idempotency-Key":key},
                      data=json.dumps(payload), timeout=8)
    print(f"\nResponse: {r.status_code} {r.text}")

if __name__ == "__main__":
    sys.exit(main())
