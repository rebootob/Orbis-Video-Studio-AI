import os
import pytest
from alembic.config import Config
from alembic import command
from app.core.config import settings

# Test migration execution against SQLite or PostgreSQL database URL
def test_alembic_migration_lifecycle(tmp_path):
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    alembic_cfg_path = os.path.join(backend_dir, "alembic.ini")
    
    alembic_cfg = Config(alembic_cfg_path)
    alembic_cfg.set_main_option("script_location", os.path.join(backend_dir, "migrations"))
    
    # Use isolated SQLite file db for migration lifecycle testing
    test_db_path = tmp_path / "test_migration.db"
    sqlite_url = f"sqlite:///{test_db_path}"
    
    # Override settings for migration runner test
    original_uri = settings.SQLALCHEMY_DATABASE_URI_OVERRIDE
    settings.SQLALCHEMY_DATABASE_URI_OVERRIDE = sqlite_url

    try:
        # 1. Upgrade to head (001 -> 002 -> 003)
        command.upgrade(alembic_cfg, "head")

        # 2. Downgrade one revision (003 -> 002)
        command.downgrade(alembic_cfg, "-1")

        # 3. Upgrade to head again (002 -> 003)
        command.upgrade(alembic_cfg, "head")
        
        # 4. Downgrade to base
        command.downgrade(alembic_cfg, "base")
        
        # 5. Upgrade to head again
        command.upgrade(alembic_cfg, "head")
    finally:
        settings.SQLALCHEMY_DATABASE_URI_OVERRIDE = original_uri

