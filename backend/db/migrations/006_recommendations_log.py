"""Create recommendations_log table for human-in-the-loop tracking."""
from sqlalchemy import text
from backend.db.session import engine


def upgrade():
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS recommendations_log (
                id SERIAL PRIMARY KEY,
                status VARCHAR(20) DEFAULT 'suggested',
                user_id VARCHAR(100),
                symbol VARCHAR(50),
                timeframe VARCHAR(20),
                confidence VARCHAR(20),
                risk_level VARCHAR(20),
                payload JSONB,
                checklist JSONB,
                notes VARCHAR(1000),
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_rec_log_status ON recommendations_log(status)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_rec_log_user ON recommendations_log(user_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_rec_log_symbol_tf ON recommendations_log(symbol, timeframe)"))


