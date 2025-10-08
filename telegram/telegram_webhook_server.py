#!/usr/bin/env python3
"""
Standalone Telegram Webhook Server for Testing
Simple FastAPI server to receive and process Telegram webhook messages
"""

import os
import re
import time
import uuid
import asyncio
from datetime import datetime, timezone
from typing import Optional, Tuple

import httpx
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Telegram Webhook Server", version="1.0.0")

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8443339641:AAEODDBahaHiNI5id_Np3yqyBmVinTqha9c")
TELEGRAM_ALLOWED_USER_IDS = {6122478067}  # Your user ID
TICK = 0.25  # NQ tick size

# Models
class TGChat(BaseModel):
    id: int

class TGMessage(BaseModel):
    message_id: int
    date: int
    chat: TGChat
    text: Optional[str] = None

class TGUpdate(BaseModel):
    update_id: int
    message: Optional[TGMessage] = None

# Trade parsing regex
TRADE_RE = re.compile(
    r"""
    ^\s*(?:/trade|trade)?\s*
    (?P<symbol>NQ[A-Z0-9]*)\s+
    (?P<side>buy|sell)\s+
    (?P<qty>\d+)\s*
    (?:@|at)\s*(?P<entry>\d+(?:\.\d+)?)\s*
    (?:stop\s*(?P<stop>\d+(?:\.\d+)?))\s*
    (?:target\s*(?P<target>\d+(?:\.\d+)?))?
    (?:\s+strat[:=](?P<strategy>[A-Za-z0-9_\-\.]+))?
    (?:\s+conf[:=](?P<conf>\d?\.?\d+))?
    \s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)

def round_tick(x: float, tick: float = TICK) -> float:
    """Round to nearest tick then to 2 decimals for JSON cleanliness."""
    return round(round(x / tick) * tick, 2)

def parse_trade(text: str) -> Tuple[dict, list[str]]:
    """
    Parse trade message like:
      trade NQZ5 buy 1 @ 17895 stop 17885 target 17915 strat:ORB conf:0.7
    Returns (payload_dict, warnings[])
    """
    m = TRADE_RE.match(text or "")
    if not m:
        raise ValueError("Could not parse trade. Format: 'trade NQZ5 buy 1 @ 17895 stop 17885 target 17915'")
    
    d = m.groupdict()
    warnings = []
    symbol = d["symbol"].upper()
    side = d["side"].upper()
    qty = int(d["qty"])
    entry = float(d["entry"])
    stop = float(d["stop"])
    target = float(d["target"]) if d.get("target") else None

    # NQ-only validation
    if not symbol.startswith("NQ"):
        raise ValueError("Only NQ symbols are allowed (e.g., NQZ5).")

    entry, stop = round_tick(entry), round_tick(stop)
    if target is not None:
        target = round_tick(target)

    # Compute risk/R:R
    risk = abs(entry - stop)
    if risk <= 0:
        raise ValueError("Stop must be different from entry.")
    rr = abs((target - entry)) / risk if target is not None else None

    # Optional extras
    strat = d.get("strategy") or "Manual"
    try:
        conf = float(d.get("conf")) if d.get("conf") is not None else 0.5
    except:
        conf = 0.5

    payload = {
        "symbol": symbol,
        "side": side,
        "quantity": qty,
        "order_type": "LIMIT",
        "price": entry,
        "stop_price": stop,
        "target_price": target,
        "paper": True,
        "features": {
            "root_symbol": "NQ",
            "risk": risk,
            "rr": rr,
            "in_session": 1,
            "strategy_id": strat,
            "setup": strat,
            "rule_version": "v1.0",
            "confidence": conf,
            "source": "telegram"
        },
        "notes": "telegram-webhook-test"
    }

    return payload, warnings

async def send_telegram_reply(chat_id: int, text: str):
    """Send a reply message to Telegram."""
    if not TELEGRAM_BOT_TOKEN:
        print(f"Would send to chat {chat_id}: {text}")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            await client.post(url, json={"chat_id": chat_id, "text": text})
        except Exception as e:
            print(f"Failed to send Telegram reply: {e}")

async def submit_to_trading_api(payload: dict) -> Tuple[int, str]:
    """Submit trade to the main trading API."""
    print(f"📤 Submitting trade to API: {payload}")
    
    # POST to the trading API
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            response = await client.post(
                "http://localhost:9001/v1/orders",
                headers={
                    "Content-Type": "application/json", 
                    "Idempotency-Key": f"tg-{int(time.time())}-{uuid.uuid4().hex[:6]}"
                },
                json=payload
            )
            print(f"✅ API Response: {response.status_code}")
            return response.status_code, response.text
        except Exception as e:
            print(f"❌ Error submitting to API: {e}")
            return 500, str(e)

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Telegram Webhook Server",
        "version": "1.0.0",
        "endpoints": {
            "webhook": "/webhook",
            "health": "/health",
            "test": "/test"
        }
    }

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.post("/webhook")
async def telegram_webhook(update_raw: dict, request: Request):
    """Main Telegram webhook endpoint."""
    print(f"📨 Received webhook: {update_raw}")
    
    try:
        update = TGUpdate(**update_raw)
    except Exception as e:
        print(f"❌ Invalid webhook payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid Telegram update payload")

    if not update.message or not update.message.text:
        print("ℹ️ No text message, ignoring")
        return {"ok": True}

    chat_id = update.message.chat.id
    from_user_id = None
    
    # Get user ID from the raw payload
    if "from" in update_raw.get("message", {}):
        from_user_id = int(update_raw["message"]["from"]["id"])
    else:
        from_user_id = chat_id

    # Check if user is allowed
    if from_user_id not in TELEGRAM_ALLOWED_USER_IDS:
        print(f"🚫 Unauthorized user: {from_user_id}")
        await send_telegram_reply(chat_id, "❌ Unauthorized user.")
        raise HTTPException(status_code=403, detail="Unauthorized Telegram user")

    text = update.message.text.strip()
    print(f"💬 Processing message from {from_user_id}: {text}")

    try:
        payload, warnings = parse_trade(text)
        print(f"✅ Parsed trade: {payload}")
    except Exception as e:
        print(f"❌ Parse error: {e}")
        await send_telegram_reply(chat_id, f"❌ {e}")
        return {"ok": True}

    # Submit to trading API
    try:
        status_code, response_text = await submit_to_trading_api(payload)
        print(f"📊 API response: {status_code} - {response_text}")
    except Exception as e:
        print(f"❌ API error: {e}")
        await send_telegram_reply(chat_id, f"❌ Error submitting trade: {e}")
        return {"ok": False}

    # Build reply message
    target_txt = f" target {payload['target_price']}" if payload.get("target_price") else ""
    warn_txt = f"\n⚠️ {'; '.join(warnings)}" if warnings else ""
    
    if status_code < 300:
        reply = f"✅ Submitted {payload['symbol']} {payload['side']} {payload['quantity']} @ {payload['price']} stop {payload['stop_price']}{target_txt}{warn_txt}"
    else:
        reply = f"❌ API Error {status_code}: {response_text}{warn_txt}"
    
    await send_telegram_reply(chat_id, reply)
    return {"ok": True}

@app.get("/test")
async def test_endpoint():
    """Test endpoint to verify the server is working."""
    return {
        "message": "Telegram webhook server is running!",
        "bot_token": f"{TELEGRAM_BOT_TOKEN[:10]}..." if TELEGRAM_BOT_TOKEN else "Not set",
        "allowed_users": list(TELEGRAM_ALLOWED_USER_IDS),
        "webhook_url": "https://your-ngrok-url.ngrok.io/webhook"
    }

@app.post("/test-trade")
async def test_trade_parsing():
    """Test endpoint to verify trade parsing works."""
    test_message = "trade NQZ5 buy 1 @ 17895 stop 17885 target 17915"
    try:
        payload, warnings = parse_trade(test_message)
        return {
            "message": "Trade parsing test successful",
            "input": test_message,
            "parsed": payload,
            "warnings": warnings
        }
    except Exception as e:
        return {
            "message": "Trade parsing test failed",
            "input": test_message,
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    
    print("🤖 Starting Telegram Webhook Server...")
    print(f"📱 Bot Token: {TELEGRAM_BOT_TOKEN[:10]}..." if TELEGRAM_BOT_TOKEN else "❌ No bot token set")
    print(f"👤 Allowed Users: {TELEGRAM_ALLOWED_USER_IDS}")
    print("🌐 Webhook URL: https://your-ngrok-url.ngrok.io/webhook")
    print("📋 Test URLs:")
    print("   - Health: http://localhost:8000/health")
    print("   - Test: http://localhost:8000/test")
    print("   - Trade Parse: http://localhost:8000/test-trade")
    print()
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
