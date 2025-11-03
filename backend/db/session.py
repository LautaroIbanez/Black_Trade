"""Database session management."""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from contextlib import contextmanager
from typing import Generator

from backend.models.base import Base

# Get database URL from environment
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost:5432/black_trade')

# Create engine
engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,  # Disable pooling for now, can enable later
    echo=os.getenv('DB_ECHO', 'false').lower() == 'true',
    connect_args={
        "connect_timeout": 10,
        "application_name": "black_trade"
    }
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency for FastAPI to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session() -> Session:
    """Get a database session without context manager (for repositories)."""
    return SessionLocal()


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """Context manager for database session."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def check_timescaledb_extension():
    """Check if TimescaleDB extension is available."""
    from sqlalchemy import text
    with db_session() as db:
        result = db.execute(text("SELECT * FROM pg_extension WHERE extname = 'timescaledb'"))
        return result.fetchone() is not None


def enable_timescaledb_hypertable():
    """Enable TimescaleDB hypertable for ohlcv_candles."""
    if not check_timescaledb_extension():
        raise RuntimeError("TimescaleDB extension not found. Install TimescaleDB first.")
    
    from sqlalchemy import text
    with db_session() as db:
        # Check if hypertable already exists
        result = db.execute(
            text("SELECT * FROM _timescaledb_catalog.hypertable WHERE table_name = 'ohlcv_candles'")
        )
        if result.fetchone() is None:
            db.execute(
                text("SELECT create_hypertable('ohlcv_candles', 'timestamp', "
                "chunk_time_interval => INTERVAL '7 days')")
            )
            db.commit()

