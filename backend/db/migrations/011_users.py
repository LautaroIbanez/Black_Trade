"""Create users table for persistent user identity."""
from sqlalchemy import text
from backend.db.session import engine


def upgrade():
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(100) UNIQUE NOT NULL,
                username VARCHAR(200) NOT NULL,
                email VARCHAR(200) UNIQUE,
                role VARCHAR(50) NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)"))
        conn.commit()


def downgrade():
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS users CASCADE"))
        conn.commit()
