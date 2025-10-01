from fastapi import APIRouter
from pydantic import BaseModel
from app.services.execution.paper import price_bus

router = APIRouter()

class Tick(BaseModel):
    symbol: str
    price: float

@router.post("/tick")
async def post_tick(t: Tick):
    price_bus.publish(t.symbol, t.price)
    return {"ok": True, "symbol": t.symbol, "price": t.price}
