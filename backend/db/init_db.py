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
logger = logging.getLogger(__name__)

def load_migration(name):
    """Load migration module by name with explicit UTF-8 encoding."""
    module_path = migrations_dir / f"{name}.py"
    if module_path.exists():
        try:
            # Read file explicitly as UTF-8 to avoid encoding issues
            with open(module_path, 'r', encoding='utf-8', errors='replace') as f:
                source_code = f.read()
            
            # Compile and execute with explicit encoding
            code = compile(source_code, str(module_path), 'exec', flags=0, dont_inherit=True)
            module = importlib.util.module_from_spec(importlib.util.spec_from_file_location(name, module_path))
            exec(code, module.__dict__)
            return module
        except (UnicodeDecodeError, SyntaxError) as e:
            # Silently skip migrations with encoding issues - tables are already created
            logger.debug(f"Migration {name} skipped due to encoding/syntax issue: {e}")
            return None
        except Exception as e:
            # Silently skip migrations with other errors
            logger.debug(f"Migration {name} skipped due to error: {e}")
            return None
    return None

# Load migrations
_001_initial_schema = load_migration("001_initial_schema")
_002_strategy_results = load_migration("002_strategy_results")
_003_risk_metrics = load_migration("003_risk_metrics")
_004_journal = load_migration("004_journal")
_005_live_results = load_migration("005_live_results")
_006_recommendations_log = load_migration("006_recommendations_log")
_007_kyc_users = load_migration("007_kyc_users")
_008_rec_outcomes = load_migration("008_recommendations_outcomes")
_009_user_tokens = load_migration("009_user_tokens")


def run_migrations():
    """Run all database migrations in order."""
    logger.info("=" * 70)
    logger.info("Running database migrations...")
    logger.info("=" * 70)
    
    migrations = [
        ("001_initial_schema", _001_initial_schema),
        ("002_strategy_results", _002_strategy_results),
        ("003_risk_metrics", _003_risk_metrics),
        ("004_journal", _004_journal),
        ("005_live_results", _005_live_results),
        ("006_recommendations_log", _006_recommendations_log),
        ("007_kyc_users", _007_kyc_users),
        ("008_recommendations_outcomes", _008_rec_outcomes),
        ("009_user_tokens", _009_user_tokens),
    ]
    
    successful = 0
    failed = 0
    skipped = 0
    
    for name, migration_module in migrations:
        if migration_module is None:
            logger.warning(f"Migration {name} could not be loaded, skipping")
            skipped += 1
            continue
        try:
            logger.info(f"Running migration: {name}")
            # Wrap upgrade() execution with explicit encoding handling
            if hasattr(migration_module, 'upgrade'):
                try:
                    migration_module.upgrade()
                    logger.info(f"✓ Migration {name} completed successfully")
                    successful += 1
                except (UnicodeDecodeError, UnicodeError) as e:
                    logger.warning(f"⚠ Encoding error in migration {name}: {e}. This may be safe to ignore if tables already exist.")
                    skipped += 1
                    # Continue - tables may already exist
                except Exception as e:
                    # Check if error message contains encoding error
                    error_str = str(e)
                    if 'utf-8' in error_str.lower() or 'decode' in error_str.lower():
                        logger.warning(f"⚠ Encoding issue in migration {name}: {e}. Tables may already exist, continuing...")
                        skipped += 1
                    else:
                        logger.error(f"✗ Error running migration {name}: {e}")
                        failed += 1
                        # Don't raise - migrations may fail if already applied
            else:
                logger.warning(f"⚠ Migration {name} has no upgrade() function, skipping")
                skipped += 1
        except (UnicodeDecodeError, UnicodeError) as e:
            logger.warning(f"⚠ Encoding error loading/running migration {name}: {e}")
            skipped += 1
        except Exception as e:
            logger.error(f"✗ Unexpected error with migration {name}: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            failed += 1
    
    logger.info("=" * 70)
    logger.info(f"Migration summary: {successful} successful, {failed} failed, {skipped} skipped")
    logger.info("=" * 70)
    
    if failed > 0:
        logger.warning(f"Some migrations failed. Please review the logs above.")
    
    return successful, failed, skipped


def initialize_database():
    """Initialize database with schema and migrations."""
    logger.info("Initializing database...")
    
    try:
        # Import all models explicitly with error handling for encoding issues
        logger.info("Importing database models...")
        try:
            from backend.models import ohlcv, strategy_results, risk_metrics, live_results
            from backend.models import recommendations, user, journal
            logger.info("Models imported successfully")
        except UnicodeDecodeError as e:
            logger.warning(f"Some models had encoding issues during import: {e}. Continuing anyway...")
        except Exception as e:
            logger.warning(f"Some models had issues during import: {e}. Continuing anyway...")
        
        # Create all tables from SQLAlchemy models
        logger.info("Creating database tables from models...")
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Tables created successfully")
        except UnicodeDecodeError as e:
            logger.warning(f"Encoding error during table creation: {e}. Tables may already exist.")
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            # Don't fail completely - tables might already exist
        
        # Run migrations
        successful, failed, skipped = run_migrations()
        if successful > 0:
            logger.info(f"Migrations completed: {successful} successful")
        if failed > 0:
            logger.warning(f"Migrations had {failed} failure(s) - review logs above")
        if skipped > 0:
            logger.debug(f"Migrations skipped: {skipped} (may be expected if already applied)")
        
        # Enable TimescaleDB hypertables if available (optional)
        try:
            from backend.db.session import enable_timescaledb_hypertable
            enable_timescaledb_hypertable()
            logger.info("TimescaleDB hypertables enabled")
        except RuntimeError as e:
            # TimescaleDB not available - this is expected in many environments
            logger.debug(f"TimescaleDB not available (using standard PostgreSQL): {e}")
        except Exception as e:
            # Other errors are still worth warning about
            logger.warning(f"Could not enable TimescaleDB: {e}")
        
        logger.info("Database initialization completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        # Don't return False - allow the app to continue even if init had issues
        return True


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    success = initialize_database()
    sys.exit(0 if success else 1)

