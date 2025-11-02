"""Script to migrate CSV data to PostgreSQL database."""
import os
import sys
import logging
from pathlib import Path
import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.db.session import init_db, enable_timescaledb_hypertable
from backend.repositories.ohlcv_repository import OHLCVRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_csv_file(csv_path: Path, repo: OHLCVRepository) -> int:
    """Migrate a single CSV file to database."""
    try:
        # Parse filename: {SYMBOL}_{TIMEFRAME}.csv
        filename = csv_path.stem
        parts = filename.split('_')
        
        if len(parts) < 2:
            logger.warning(f"Invalid filename format: {filename}")
            return 0
        
        timeframe = parts[-1]  # Last part is timeframe
        symbol = '_'.join(parts[:-1]).upper()  # Everything else is symbol
        
        logger.info(f"Migrating {symbol} {timeframe} from {csv_path}")
        
        # Read CSV
        df = pd.read_csv(csv_path)
        
        if df.empty:
            logger.warning(f"Empty CSV: {csv_path}")
            return 0
        
        # Ensure required columns
        required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            logger.warning(f"Missing columns in {csv_path}: {missing_cols}")
            return 0
        
        # Convert to list of dicts
        candles = []
        for _, row in df.iterrows():
            candle = {
                'symbol': symbol,
                'timeframe': timeframe,
                'timestamp': int(row['timestamp']),
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': float(row['volume']),
            }
            
            # Optional fields
            if 'quote_volume' in df.columns:
                candle['quote_volume'] = float(row['quote_volume'])
            if 'trades' in df.columns:
                candle['trades'] = int(row['trades'])
            if 'taker_buy_base' in df.columns:
                candle['taker_buy_base'] = float(row['taker_buy_base'])
            if 'taker_buy_quote' in df.columns:
                candle['taker_buy_quote'] = float(row['taker_buy_quote'])
            if 'close_time' in df.columns:
                candle['close_time'] = int(row['close_time'])
            
            candles.append(candle)
        
        # Save in batches
        batch_size = 1000
        total_saved = 0
        
        for i in range(0, len(candles), batch_size):
            batch = candles[i:i+batch_size]
            saved = repo.save_batch(batch)
            total_saved += saved
        
        logger.info(f"Migrated {total_saved} candles for {symbol} {timeframe}")
        return total_saved
        
    except Exception as e:
        logger.error(f"Error migrating {csv_path}: {e}")
        return 0


def main():
    """Main migration function."""
    data_dir = Path("data/ohlcv")
    
    if not data_dir.exists():
        logger.error(f"Data directory not found: {data_dir}")
        return
    
    # Initialize database
    logger.info("Initializing database...")
    init_db()
    
    # Enable TimescaleDB if available
    try:
        enable_timescaledb_hypertable()
        logger.info("TimescaleDB hypertable enabled")
    except Exception as e:
        logger.warning(f"Could not enable TimescaleDB: {e}")
    
    # Find all CSV files
    csv_files = list(data_dir.glob("*.csv"))
    
    if not csv_files:
        logger.warning("No CSV files found")
        return
    
    logger.info(f"Found {len(csv_files)} CSV files to migrate")
    
    # Initialize repository
    repo = OHLCVRepository()
    
    # Migrate each file
    total_migrated = 0
    for csv_file in csv_files:
        count = migrate_csv_file(csv_file, repo)
        total_migrated += count
    
    logger.info(f"Migration complete: {total_migrated} total candles migrated")


if __name__ == '__main__':
    main()

