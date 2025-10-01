from fastapi import APIRouter
from app.deps import get_settings

router = APIRouter()

@router.get("/debug/config")
async def debug_config():
    s = get_settings()
    return {
        "ENVIRONMENT": s.ENVIRONMENT,
        "TZ": s.TZ,
        "BROKER": s.BROKER,
        "DAILY_LOSS_CAP_USD": s.DAILY_LOSS_CAP_USD,
        "MAX_TRADES_PER_DAY": s.MAX_TRADES_PER_DAY,
        "MAX_CONTRACTS": s.MAX_CONTRACTS,
        "SESSION_WINDOWS": s.session_windows_normalized,
    }
