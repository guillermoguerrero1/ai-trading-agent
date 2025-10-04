"""
AI Trading Agent FastAPI Application
"""

import contextlib
import asyncio
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.deps import get_settings
from app.store.db import create_tables
from app.routes import health, config, signal, orders, pnl, debug, trade_logs, debug_routes, export, model, metrics, broker
try:
    from app.routes import tick  # optional, only if file exists
    HAS_TICK = True
except Exception:
    HAS_TICK = False
from app.services.supervisor import Supervisor
from app.services.risk_guard import RiskGuard
from app.services.queue import QueueService

import structlog
logger = structlog.get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("startup.begin", app="ai-trading-agent")
    
    settings = get_settings()
    
    try:
        await create_tables()
        logger.info("db.init.ok")
        
        # Log current database revision
        try:
            from ops.migrations.get_revision import get_current_revision
            current_revision = get_current_revision(settings.DATABASE_URL)
            logger.info("db.revision", revision=current_revision)
        except Exception as e:
            logger.warning("db.revision.error", error=str(e))
    except Exception as e:
        logger.exception("db.init.error", error=str(e))
        raise

    risk_guard = RiskGuard(settings)
    app.state.risk_guard = risk_guard
    supervisor = Supervisor(risk_guard)
    app.state.supervisor = supervisor
    
    # Update risk guard with supervisor reference for runtime config
    risk_guard.supervisor = supervisor
    queue_service = QueueService()
    app.state.queue_service = queue_service
    
    from app.services.trade_logger import TradeLogger
    trade_logger = TradeLogger()
    app.state.trade_logger = trade_logger
    
    # Initialize brokers based on configuration
    broker_type = os.getenv("BROKER", "").lower()
    
    if broker_type == "ibkr":
        from app.services.execution.ibkr import IBKRAdapter
        ibkr_adapter = IBKRAdapter()
        app.state.ibkr_adapter = ibkr_adapter
        logger.info("IBKR adapter initialized")
    else:
        # Default to paper broker
        from app.services.execution.paper import PaperBroker
        paper_broker = PaperBroker(trade_logger=trade_logger)
        app.state.paper_broker = paper_broker
        logger.info("Paper broker initialized")

    # Log effective settings snapshot
    logger.info(
        "settings.effective",
        env=settings.ENVIRONMENT,
        tz=settings.TZ,
        broker=settings.BROKER,
        daily_loss_cap_usd=settings.DAILY_LOSS_CAP_USD,
        max_trades_per_day=settings.MAX_TRADES_PER_DAY,
        max_contracts=settings.MAX_CONTRACTS,
        session_windows=settings.session_windows_normalized,
    )

    try:
        await supervisor.start()
        await queue_service.start()
        logger.info("startup.ok")
    except Exception as e:
        logger.exception("startup.services.error", error=str(e))
        with contextlib.suppress(Exception):
            await queue_service.stop()
        with contextlib.suppress(Exception):
            await supervisor.stop()
        raise

    yield

    logger.info("shutdown.begin")
    with contextlib.suppress(Exception):
        await queue_service.stop()
    with contextlib.suppress(Exception):
        await supervisor.stop()
    logger.info("shutdown.ok")

def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="AI Trading Agent",
        description="Production-ready AI Trading Agent with FastAPI, Streamlit, and MLflow",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.__dict__.get("cors_origins", ["*"]),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

    # Versioned routers
    app.include_router(health.router, prefix="/v1", tags=["health"])
    app.include_router(config.router, prefix="/v1", tags=["config"])
    app.include_router(signal.router, prefix="/v1", tags=["signal"])
    app.include_router(orders.router, prefix="/v1", tags=["orders"])
    app.include_router(pnl.router,    prefix="/v1", tags=["pnl"])
    app.include_router(debug.router, prefix="/v1", tags=["debug"])
    app.include_router(debug_routes.router, prefix="/v1", tags=["debug"])
    app.include_router(trade_logs.router, prefix="/v1", tags=["logs"])
    app.include_router(export.router, prefix="/v1", tags=["export"])
    app.include_router(model.router, prefix="/v1", tags=["model"])
    app.include_router(metrics.router, prefix="/v1", tags=["metrics"])
    app.include_router(broker.router, prefix="/v1", tags=["broker"])
    if HAS_TICK:
        app.include_router(tick.router, prefix="/v1", tags=["tick"])

    @app.get("/")
    async def root():
        return {"message": "AI Trading Agent API", "version": "0.1.0", "docs": "/docs", "redoc": "/redoc"}

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "ai-trading-agent"}

    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        rid = request.headers.get("x-request-id") or str(id(request))
        request.state.request_id = rid
        logger.bind(request_id=rid)
        response = await call_next(request)
        response.headers["x-request-id"] = rid
        return response

    return app

app = create_app()