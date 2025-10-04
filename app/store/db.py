"""
Database configuration and session management
"""

from sqlalchemy import create_engine as sa_create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from app.models.base import Settings

import structlog

logger = structlog.get_logger(__name__)

# Global engine and session factory
_engine = None
_session_factory = None


def create_engine(settings: Settings = None):
    """
    Create database engine.
    
    Args:
        settings: Application settings
        
    Returns:
        Database engine
    """
    global _engine
    
    if settings is None:
        settings = Settings()
    
    if _engine is None:
        database_url = settings.DATABASE_URL
        
        # Convert to async URL if needed
        if database_url.startswith("sqlite:///"):
            database_url = database_url.replace("sqlite:///", "sqlite+aiosqlite:///")
        elif database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
        
        _engine = create_async_engine(
            database_url,
            echo=settings.DATABASE_ECHO,
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
        )
        
        logger.info("Database engine created", url=database_url)
    
    return _engine


def get_session_factory(settings: Settings = None):
    """
    Get session factory.
    
    Args:
        settings: Application settings
        
    Returns:
        Session factory
    """
    global _session_factory
    
    if _session_factory is None:
        engine = create_engine(settings)
        _session_factory = sessionmaker(
            engine, 
            class_=AsyncSession, 
            expire_on_commit=False
        )
        
        logger.info("Session factory created")
    
    return _session_factory


async def get_session(settings: Settings = None):
    """
    Get database session.
    
    Args:
        settings: Application settings
        
    Yields:
        Database session
    """
    session_factory = get_session_factory(settings)
    
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables(settings: Settings = None):
    """
    Create database tables.
    
    Args:
        settings: Application settings
    """
    engine = create_engine(settings)
    
    async with engine.begin() as conn:
        # Import all models to ensure they are registered
        from app.models.event import Event
        from app.models.order import Order
        from app.models.account import AccountState, PositionState
        from app.models.pnl import PnL
        from app.models.limits import GuardrailViolation
        from app.models.trade_log import TradeLog  # noqa
        
        # Drop and recreate all tables (for development)
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)
        
        logger.info("Database tables created successfully")


async def close_engine():
    """Close database engine."""
    global _engine
    
    if _engine:
        await _engine.dispose()
        _engine = None
        logger.info("Database engine closed")
