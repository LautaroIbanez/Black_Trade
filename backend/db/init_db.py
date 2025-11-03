"""Database initialization and migration runner."""
import os
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.db.session import engine, init_db
from backend.models.base import Base

# Import all migration modules
import importlib.util
from pathlib import Path

migrations_dir = Path(__file__).parent / "migrations"

def load_migration(name):
    """Load migration module by name."""
    module_path = migrations_dir / f"{name}.py"
    if module_path.exists():
        spec = importlib.util.spec_from_file_location(name, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    return None

# Load migrations
_001_initial_schema = load_migration("001_initial_schema")
_002_strategy_results = load_migration("002_strategy_results")
_003_risk_metrics = load_migration("003_risk_metrics")
_004_journal = load_migration("004_journal")

logger = logging.getLogger(__name__)


def run_migrations():
    """Run all database migrations in order."""
    logger.info("Running database migrations...")
    
    migrations = [
        ("001_initial_schema", _001_initial_schema),
        ("002_strategy_results", _002_strategy_results),
        ("003_risk_metrics", _003_risk_metrics),
        ("004_journal", _004_journal),
    ]
    
    for name, migration_module in migrations:
        try:
            logger.info(f"Running migration: {name}")
            migration_module.upgrade()
            logger.info(f"Migration {name} completed successfully")
        except Exception as e:
            logger.error(f"Error running migration {name}: {e}")
            # Don't raise, just log - migrations may fail if already applied


def initialize_database():
    """Initialize database with schema and migrations."""
    logger.info("Initializing database...")
    
    try:
        # Create all tables from SQLAlchemy models
        logger.info("Creating database tables from models...")
        Base.metadata.create_all(bind=engine)
        logger.info("Tables created successfully")
        
        # Run migrations
        run_migrations()
        
        # Enable TimescaleDB hypertables if available
        try:
            from backend.db.session import enable_timescaledb_hypertable
            enable_timescaledb_hypertable()
            logger.info("TimescaleDB hypertables enabled")
        except Exception as e:
            logger.warning(f"Could not enable TimescaleDB: {e}")
        
        logger.info("Database initialization completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    success = initialize_database()
    sys.exit(0 if success else 1)

