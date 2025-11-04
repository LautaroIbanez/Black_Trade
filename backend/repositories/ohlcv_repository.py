"""Repository for OHLCV candle data."""
from typing import List, Dict, Optional
from datetime import datetime
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from sqlalchemy.dialects.postgresql import insert

from backend.models.ohlcv import OHLCVCandle
from backend.db.session import get_db_session


class OHLCVRepository:
    """Repository for OHLCV data operations."""
    
    def save_candle(self, candle: Dict, db: Session = None) -> bool:
        """Save a single candle (upsert based on unique constraint)."""
        should_close = db is None
        if db is None:
            db = get_db_session()
        
        try:
            stmt = insert(OHLCVCandle).values(**candle)
            stmt = stmt.on_conflict_do_update(
                index_elements=['symbol', 'timeframe', 'timestamp'],
                set_={
                    'open': stmt.excluded.open,
                    'high': stmt.excluded.high,
                    'low': stmt.excluded.low,
                    'close': stmt.excluded.close,
                    'volume': stmt.excluded.volume,
                    'quote_volume': stmt.excluded.quote_volume,
                    'trades': stmt.excluded.trades,
                    'taker_buy_base': stmt.excluded.taker_buy_base,
                    'taker_buy_quote': stmt.excluded.taker_buy_quote,
                    'close_time': stmt.excluded.close_time,
                    'updated_at': datetime.utcnow(),
                }
            )
            db.execute(stmt)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise
        finally:
            if should_close:
                db.close()
    
    def save_batch(self, candles: List[Dict], db: Session = None) -> int:
        """Save multiple candles in a batch (upsert)."""
        if not candles:
            return 0
        
        should_close = db is None
        if db is None:
            db = get_db_session()
        
        try:
            # Prepare data for bulk insert
            values = []
            for candle in candles:
                values.append({
                    'symbol': candle['symbol'],
                    'timeframe': candle['timeframe'],
                    'timestamp': candle['timestamp'],
                    'open': candle['open'],
                    'high': candle['high'],
                    'low': candle['low'],
                    'close': candle['close'],
                    'volume': candle['volume'],
                    'quote_volume': candle.get('quote_volume'),
                    'trades': candle.get('trades'),
                    'taker_buy_base': candle.get('taker_buy_base'),
                    'taker_buy_quote': candle.get('taker_buy_quote'),
                    'close_time': candle.get('close_time'),
                })
            
            stmt = insert(OHLCVCandle).values(values)
            stmt = stmt.on_conflict_do_update(
                index_elements=['symbol', 'timeframe', 'timestamp'],
                set_={
                    'open': stmt.excluded.open,
                    'high': stmt.excluded.high,
                    'low': stmt.excluded.low,
                    'close': stmt.excluded.close,
                    'volume': stmt.excluded.volume,
                    'quote_volume': stmt.excluded.quote_volume,
                    'trades': stmt.excluded.trades,
                    'taker_buy_base': stmt.excluded.taker_buy_base,
                    'taker_buy_quote': stmt.excluded.taker_buy_quote,
                    'close_time': stmt.excluded.close_time,
                    'updated_at': datetime.utcnow(),
                }
            )
            result = db.execute(stmt)
            db.commit()
            return len(candles)
        except Exception as e:
            db.rollback()
            raise
        finally:
            if should_close:
                db.close()
    
    def get_latest(self, symbol: str, timeframe: str, db: Session = None) -> Optional[Dict]:
        """Get the latest candle for a symbol/timeframe."""
        should_close = db is None
        if db is None:
            db = get_db_session()
        
        try:
            try:
                candle = db.query(OHLCVCandle).filter(
                    and_(
                        OHLCVCandle.symbol == symbol,
                        OHLCVCandle.timeframe == timeframe
                    )
                ).order_by(desc(OHLCVCandle.timestamp)).first()
                
                if not candle:
                    return None
                
                try:
                    candle_dict = candle.to_dict()
                    # Ensure all string values are properly encoded
                    safe_dict = {}
                    for k, v in candle_dict.items():
                        if isinstance(v, str):
                            try:
                                safe_dict[k] = v.encode('utf-8', errors='replace').decode('utf-8')
                            except (UnicodeEncodeError, UnicodeDecodeError):
                                safe_dict[k] = str(v).encode('utf-8', errors='replace').decode('utf-8')
                        else:
                            safe_dict[k] = v
                    return safe_dict
                except (UnicodeDecodeError, UnicodeError) as e:
                    import logging
                    logging.getLogger(__name__).warning(f"Encoding error in get_latest to_dict: {e}")
                    return None
            except (UnicodeDecodeError, UnicodeError) as e:
                import logging
                logging.getLogger(__name__).error(f"Encoding error in get_latest query: {e}")
                return None
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error in get_latest: {e}")
            return None
        finally:
            if should_close:
                db.close()
    
    def get_range(self, symbol: str, timeframe: str, start: int, end: int, 
                  db: Session = None) -> List[Dict]:
        """Get candles in a timestamp range."""
        should_close = db is None
        if db is None:
            db = get_db_session()
        
        try:
            candles = db.query(OHLCVCandle).filter(
                and_(
                    OHLCVCandle.symbol == symbol,
                    OHLCVCandle.timeframe == timeframe,
                    OHLCVCandle.timestamp >= start,
                    OHLCVCandle.timestamp <= end
                )
            ).order_by(OHLCVCandle.timestamp).all()
            
            return [candle.to_dict() for candle in candles]
        finally:
            if should_close:
                db.close()
    
    def to_dataframe(self, symbol: str, timeframe: str, limit: int = None,
                     start_timestamp: int = None, end_timestamp: int = None,
                     db: Session = None) -> pd.DataFrame:
        """Convert OHLCV data to pandas DataFrame."""
        should_close = db is None
        if db is None:
            db = get_db_session()
        
        try:
            # Wrap database operations to handle encoding errors
            try:
                query = db.query(OHLCVCandle).filter(
                    and_(
                        OHLCVCandle.symbol == symbol,
                        OHLCVCandle.timeframe == timeframe
                    )
                )
                
                if start_timestamp:
                    query = query.filter(OHLCVCandle.timestamp >= start_timestamp)
                if end_timestamp:
                    query = query.filter(OHLCVCandle.timestamp <= end_timestamp)
                
                query = query.order_by(desc(OHLCVCandle.timestamp))
                
                if limit:
                    query = query.limit(limit)
                
                candles = query.all()
                
                if not candles:
                    # Return empty DataFrame with expected columns
                    return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                
                # Convert to list of dicts with encoding error handling
                data = []
                for candle in reversed(candles):  # Reverse to get chronological order
                    try:
                        candle_dict = candle.to_dict()
                        # Ensure all string values are properly encoded
                        safe_dict = {}
                        for k, v in candle_dict.items():
                            if isinstance(v, str):
                                try:
                                    # Try to ensure UTF-8 encoding
                                    safe_dict[k] = v.encode('utf-8', errors='replace').decode('utf-8')
                                except (UnicodeEncodeError, UnicodeDecodeError):
                                    safe_dict[k] = str(v).encode('utf-8', errors='replace').decode('utf-8')
                            else:
                                safe_dict[k] = v
                        data.append(safe_dict)
                    except (UnicodeDecodeError, UnicodeError) as e:
                        # Skip problematic candles
                        import logging
                        logging.getLogger(__name__).warning(f"Encoding error converting candle to dict: {e}")
                        continue
                
                if not data:
                    return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                
                df = pd.DataFrame(data)
                
                # Ensure timestamp column exists and is int (milliseconds)
                # Keep timestamp as int in milliseconds for consistency
                if 'timestamp' in df.columns:
                    # Convert to int if it's not already
                    df['timestamp'] = df['timestamp'].astype('Int64', errors='ignore')
                    # Fill any NaN values (shouldn't happen, but be safe)
                    df['timestamp'] = df['timestamp'].fillna(0).astype(int)
                elif 'datetime' in df.columns:
                    # If only datetime column exists, convert to timestamp in ms
                    df['timestamp'] = pd.to_datetime(df['datetime'], errors='coerce')
                    df['timestamp'] = (df['timestamp'].astype('int64') / 1_000_000).fillna(0).astype(int)
                
                # Select and order columns
                required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                available_cols = [col for col in required_cols if col in df.columns]
                df = df[available_cols]
                
                return df
            except (UnicodeDecodeError, UnicodeError) as e:
                # Return empty DataFrame on encoding errors
                import logging
                logging.getLogger(__name__).error(f"Encoding error in query: {e}")
                return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error in to_dataframe: {e}")
            return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        finally:
            if should_close:
                db.close()
    
    def count(self, symbol: str, timeframe: str, db: Session = None) -> int:
        """Count candles for a symbol/timeframe."""
        should_close = db is None
        if db is None:
            db = get_db_session()
        
        try:
            try:
                count = db.query(OHLCVCandle).filter(
                    and_(
                        OHLCVCandle.symbol == symbol,
                        OHLCVCandle.timeframe == timeframe
                    )
                ).count()
                return count
            except (UnicodeDecodeError, UnicodeError) as e:
                import logging
                logging.getLogger(__name__).error(f"Encoding error in count query: {e}")
                return 0
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error in count: {e}")
            return 0
        finally:
            if should_close:
                db.close()


