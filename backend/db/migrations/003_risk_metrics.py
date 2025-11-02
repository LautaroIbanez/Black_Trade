"""Migration for risk metrics and account tracking tables."""
from sqlalchemy import text
from backend.db.session import engine


def upgrade():
    """Create risk metrics tables."""
    with engine.connect() as conn:
        # Create risk_metrics table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS risk_metrics (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                total_capital DECIMAL(30, 8),
                total_exposure DECIMAL(30, 8),
                exposure_pct DECIMAL(10, 4),
                var_1d_95 DECIMAL(30, 8),
                var_1d_99 DECIMAL(30, 8),
                var_1w_95 DECIMAL(30, 8),
                var_1w_99 DECIMAL(30, 8),
                current_drawdown_pct DECIMAL(10, 4),
                max_drawdown_pct DECIMAL(10, 4),
                unrealized_pnl DECIMAL(30, 8),
                daily_pnl DECIMAL(30, 8)
            )
        """))
        
        # Create index
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_risk_metrics_timestamp ON risk_metrics(timestamp DESC)"))
        
        # Create account_balances table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS account_balances (
                id SERIAL PRIMARY KEY,
                account_id VARCHAR(50) NOT NULL,
                asset VARCHAR(10) NOT NULL,
                free_balance DECIMAL(30, 8),
                locked_balance DECIMAL(30, 8),
                total_balance DECIMAL(30, 8),
                usd_value DECIMAL(30, 8),
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """))
        
        # Create index
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_account_balances_timestamp ON account_balances(timestamp DESC)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_account_balances_account_asset ON account_balances(account_id, asset)"))
        
        # Create positions table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS positions (
                id SERIAL PRIMARY KEY,
                account_id VARCHAR(50) NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                side VARCHAR(10) NOT NULL,
                size DECIMAL(30, 8) NOT NULL,
                entry_price DECIMAL(20, 8) NOT NULL,
                current_price DECIMAL(20, 8),
                unrealized_pnl DECIMAL(30, 8),
                strategy_name VARCHAR(100),
                entry_time TIMESTAMP WITH TIME ZONE NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """))
        
        # Create indexes
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_positions_account ON positions(account_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_positions_updated_at ON positions(updated_at DESC)"))
        
        conn.commit()


def downgrade():
    """Drop risk metrics tables."""
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS positions CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS account_balances CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS risk_metrics CASCADE"))
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
        print("Usage: python 003_risk_metrics.py [upgrade|downgrade]")

