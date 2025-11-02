"""Initial database schema migration."""
from sqlalchemy import text
from backend.db.session import engine, check_timescaledb_extension


def upgrade():
    """Create initial schema."""
    with engine.connect() as conn:
        # Create extension if TimescaleDB is available
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb"))
            conn.commit()
        except Exception as e:
            print(f"Warning: Could not enable TimescaleDB extension: {e}")
            print("Continuing without TimescaleDB (will use regular PostgreSQL)")
        
        # Create tables (SQLAlchemy models will handle this, but we can also do raw SQL)
        # This is a backup/alternative approach
        conn.commit()


def downgrade():
    """Drop schema."""
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS ingestion_metrics CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS ingestion_status CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS ohlcv_candles CASCADE"))
        conn.commit()


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'upgrade':
        upgrade()
        print("Migration applied successfully")
    elif len(sys.argv) > 1 and sys.argv[1] == 'downgrade':
        downgrade()
        print("Migration rolled back successfully")
    else:
        print("Usage: python 001_initial_schema.py [upgrade|downgrade]")

