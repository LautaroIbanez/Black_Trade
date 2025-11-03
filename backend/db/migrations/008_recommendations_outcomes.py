"""Add outcomes fields to recommendations_log for hit ratio metrics."""
from sqlalchemy import text
from backend.db.session import engine


def upgrade():
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE recommendations_log ADD COLUMN IF NOT EXISTS outcome VARCHAR(20)"))
        conn.execute(text("ALTER TABLE recommendations_log ADD COLUMN IF NOT EXISTS realized_pnl NUMERIC(20,8)"))
        conn.execute(text("ALTER TABLE recommendations_log ADD COLUMN IF NOT EXISTS decided_at TIMESTAMPTZ"))


