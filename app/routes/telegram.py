from __future__ import annotations
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional, Tuple
import os, time, uuid, re, math, httpx
from datetime import datetime, timezone
from app.models.base import Settings

router = APIRouter(prefix="/v1/hooks", tags=["integrations", "telegram"])

TICK = 0.25  # NQ tick

class TGChat(BaseModel):
    id: int

class TGMessage(BaseModel):
    message_id: int
    date: int
    chat: TGChat
    text: Optional[str] = None
    from_: Optional[dict] = None

class TGUpdate(BaseModel):
    update_id: int
    message: Optional[TGMessage] = None

def round_tick(x: float, tick: float = TICK) -> float:
    # Round to nearest tick then to 2 decimals for JSON cleanliness
    return round(round(x / tick) * tick, 2)

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
    (?:\s+at[:=](?P<entered_at>[\dT:\-Z]+))?
    \s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)

def parse_trade(text: str) -> Tuple[dict, list[str]]:
    """
    Parse message like:
      trade NQZ5 buy 1 @ 17895 stop 17885 target 17915 strat:ORB conf:0.7 at:2025-09-14T14:30:00Z
    Returns (payload_dict, warnings[])
    """
    m = TRADE_RE.match(text or "")
    if not m:
        raise ValueError("Could not parse trade. Format: 'trade NQZ5 buy 1 @ 17895 stop 17885 target 17915 strat:ORB conf:0.7 at:2025-09-14T14:30:00Z'")
    d = m.groupdict()
    warnings = []
    symbol = d["symbol"].upper()
    side = d["side"].upper()
    qty = int(d["qty"])
    entry = float(d["entry"])
    stop = float(d["stop"])
    target = float(d["target"]) if d.get("target") else None

    # NQ-only guard here too
    if not symbol.startswith("NQ"):
        raise ValueError("Only NQ symbols are allowed (e.g., NQZ5).")

    entry, stop = round_tick(entry), round_tick(stop)
    if target is not None:
        target = round_tick(target)

    # Compute features risk/rr
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

    entered_at_str = d.get("entered_at")
    entered_at = None
    if entered_at_str:
        try:
            entered_at = datetime.fromisoformat(entered_at_str.replace("Z","+00:00"))
        except Exception:
            warnings.append("Invalid entered_at; ignoring.")
            entered_at = None

    features = {
        "root_symbol": "NQ",
        "risk": risk,
        "rr": rr,
        "in_session": 1,
        "strategy_id": strat,
        "setup": strat,
        "rule_version": "v1.0",
        "confidence": conf,
        "source": "telegram"
    }
    payload = {
        "symbol": symbol,
        "side": side,
        "qty": qty,
        "entry": entry,
        "stop": stop,
        "target": target,
        "paper": True,  # keep paper by default
        "features": features,
        "notes": "telegram-entry"
    }
    if entered_at:
        now = datetime.now(timezone.utc)
        if entered_at > now:
            warnings.append("entered_at is in the future; ignoring.")
        else:
            payload["entered_at"] = entered_at.isoformat()

    return payload, warnings

async def send_telegram_reply(settings: Settings, chat_id: int, text: str):
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    async with httpx.AsyncClient(timeout=8) as client:
        await client.post(url, json={"chat_id": chat_id, "text": text})

@router.post("/telegram")
async def telegram_webhook(update_raw: dict, request: Request):
    settings = Settings()
    if not settings.TELEGRAM_ENABLE:
        raise HTTPException(status_code=404, detail="Telegram integration disabled")

    # Parse Telegram update
    try:
        update = TGUpdate(**update_raw)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Telegram update payload")

    if not update.message or not update.message.text:
        return {"ok": True}  # ignore non-text

    chat_id = update.message.chat.id
    # Telegram sends "from" user separately; in this minimal model we accept any chat.id present.
    from_user_id = None
    if update_raw.get("message", {}).get("from"):
        from_user_id = int(update_raw["message"]["from"]["id"])
    else:
        # some clients: try chat.id
        from_user_id = chat_id

    # Whitelist check
    allowed = settings.telegram_allowed_ids
    if allowed and from_user_id not in allowed:
        await send_telegram_reply(settings, chat_id, "❌ Unauthorized user.")
        raise HTTPException(status_code=403, detail="Unauthorized Telegram user")

    text = update.message.text.strip()
    try:
        payload, warns = parse_trade(text)
    except Exception as e:
        await send_telegram_reply(settings, chat_id, f"❌ {e}")
        return {"ok": True}

    # Post to /v1/orders
    key = f"tg-{int(time.time())}-{uuid.uuid4().hex[:6]}"
    # Construct orders URL - try to use url_for first, fallback to string construction
    try:
        orders_url = str(request.url_for("create_order"))
    except:
        # Fallback: construct URL manually
        base_url = str(request.base_url).rstrip('/')
        orders_url = f"{base_url}/v1/orders"

    async with httpx.AsyncClient(timeout=8) as client:
        try:
            r = await client.post(
                orders_url,
                headers={"Content-Type":"application/json", "Idempotency-Key": key},
                json=payload
            )
            ok = r.status_code < 300
            body = r.json() if ok else r.text
        except Exception as e:
            await send_telegram_reply(settings, chat_id, f"❌ Error posting order: {e}")
            return {"ok": False}

    # Build reply
    target_txt = f" target {payload['target']}" if payload.get("target") is not None else ""
    warn_txt = f"\n⚠️ {'; '.join(warns)}" if warns else ""
    if r.status_code < 300:
        await send_telegram_reply(
            settings, chat_id,
            f"✅ Submitted {payload['symbol']} {payload['side']} {payload['qty']} @ {payload['entry']} stop {payload['stop']}{target_txt}\nIdempotency-Key: {key}{warn_txt}"
        )
    else:
        await send_telegram_reply(settings, chat_id, f"❌ API {r.status_code}: {body}{warn_txt}")

    return {"ok": True}
