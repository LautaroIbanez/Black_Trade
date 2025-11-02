"""Migration for strategy results and optimal parameters tables."""
from sqlalchemy import text
from backend.db.session import engine


def upgrade():
    """Create strategy results tables."""
    with engine.connect() as conn:
        # Create backtest_results table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS backtest_results (
                id SERIAL PRIMARY KEY,
                strategy_name VARCHAR(100) NOT NULL,
                dataset_name VARCHAR(100),
                period_start TIMESTAMP WITH TIME ZONE,
                period_end TIMESTAMP WITH TIME ZONE,
                split_type VARCHAR(20),
                parameters JSONB,
                metrics JSONB,
                trades_count INTEGER,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """))
        
        # Create indexes
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_backtest_strategy_name ON backtest_results(strategy_name)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_backtest_dataset_name ON backtest_results(dataset_name)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_backtest_created_at ON backtest_results(created_at DESC)"))
        
        # Create optimal_parameters table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS optimal_parameters (
                id SERIAL PRIMARY KEY,
                strategy_name VARCHAR(100) NOT NULL,
                dataset_name VARCHAR(100),
                validation_period_start TIMESTAMP WITH TIME ZONE,
                validation_period_end TIMESTAMP WITH TIME ZONE,
                parameters JSONB NOT NULL,
                validation_metrics JSONB,
                train_metrics JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """))
        
        # Create indexes
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_optimal_strategy_name ON optimal_parameters(strategy_name)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_optimal_dataset_name ON optimal_parameters(dataset_name)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_optimal_created_at ON optimal_parameters(created_at DESC)"))
        
        conn.commit()


def downgrade():
    """Drop strategy results tables."""
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS optimal_parameters CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS backtest_results CASCADE"))
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
        print("Usage: python 002_strategy_results.py [upgrade|downgrade]")

