"""Create kyc_users table to persist verification state."""
from sqlalchemy import text
from backend.db.session import engine


def upgrade():
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS kyc_users (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(100) UNIQUE,
                name VARCHAR(200),
                email VARCHAR(200),
                country VARCHAR(50),
                verified BOOLEAN DEFAULT FALSE,
                verified_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_kyc_user_email ON kyc_users(email)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_kyc_user_verified ON kyc_users(verified)"))


