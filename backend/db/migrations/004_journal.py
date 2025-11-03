"""Migration for journal entries table."""
from sqlalchemy import text
from backend.db.session import engine


def upgrade():
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS journal_entries (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                type VARCHAR(50),
                order_id VARCHAR(100),
                user VARCHAR(100) DEFAULT 'system',
                details JSONB
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_journal_timestamp ON journal_entries(timestamp DESC)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_journal_type ON journal_entries(type)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_journal_order ON journal_entries(order_id)"))


