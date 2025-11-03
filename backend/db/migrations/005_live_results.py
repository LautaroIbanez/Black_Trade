"""Migration for live_recommendations table."""
from sqlalchemy import text
from backend.db.session import engine


def upgrade():
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS live_recommendations (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(50) NOT NULL,
                timeframe VARCHAR(20) NOT NULL,
                payload JSONB NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_live_rec_symbol_tf_time ON live_recommendations(symbol, timeframe, created_at DESC)"))


