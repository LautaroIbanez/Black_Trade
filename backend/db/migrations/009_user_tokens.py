"""Create user_tokens table to persist access and refresh tokens."""
from sqlalchemy import text
from backend.db.session import engine


def upgrade():
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_tokens (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(100),
                token VARCHAR(512) UNIQUE,
                token_type VARCHAR(20),
                expires_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_user_tokens_user_type ON user_tokens(user_id, token_type)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_user_tokens_token ON user_tokens(token)"))


