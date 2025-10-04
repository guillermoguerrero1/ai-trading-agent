"""
Utility to get current database revision
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from alembic.config import Config
from alembic import script
from alembic.runtime import migration
from sqlalchemy import create_engine


def get_current_revision(database_url: str = None) -> str:
    """
    Get the current database revision.
    
    Args:
        database_url: Database URL (optional, will use env or config)
        
    Returns:
        Current revision string or "none" if no revisions applied
    """
    try:
        # Get database URL
        if not database_url:
            database_url = os.getenv("DATABASE_URL", "sqlite:///./trading_agent.db")
        
        # Convert to sync URL for Alembic
        sync_url = database_url
        if sync_url.startswith("sqlite+aiosqlite://"):
            sync_url = sync_url.replace("sqlite+aiosqlite://", "sqlite://")
        elif sync_url.startswith("postgresql+asyncpg://"):
            sync_url = sync_url.replace("postgresql+asyncpg://", "postgresql://")
        
        # Create Alembic config
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", sync_url)
        
        # Create engine
        engine = create_engine(sync_url)
        
        # Get script directory
        script_dir = script.ScriptDirectory.from_config(alembic_cfg)
        
        # Get current revision
        with engine.connect() as connection:
            context = migration.MigrationContext.configure(connection)
            current_rev = context.get_current_revision()
            
            if current_rev:
                return current_rev
            else:
                return "none"
                
    except Exception as e:
        return f"error: {str(e)}"


if __name__ == "__main__":
    revision = get_current_revision()
    print(revision)
