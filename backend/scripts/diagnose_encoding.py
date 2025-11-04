#!/usr/bin/env python
"""Diagnostic script to identify encoding issues in PostgreSQL."""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import logging
logging.basicConfig(level=logging.DEBUG)

# Force UTF-8 encoding
os.environ['PGCLIENTENCODING'] = 'UTF8'

from sqlalchemy import create_engine, text
from backend.db.session import engine

print("=" * 60)
print("PostgreSQL Encoding Diagnostic")
print("=" * 60)

try:
    # Test 1: Direct connection test
    print("\n1. Testing direct connection...")
    conn = engine.connect()
    result = conn.execute(text("SHOW server_encoding"))
    server_enc = result.fetchone()[0]
    print(f"   Server encoding: {server_enc}")
    
    result = conn.execute(text("SHOW client_encoding"))
    client_enc = result.fetchone()[0]
    print(f"   Client encoding: {client_enc}")
    
    result = conn.execute(text("SELECT current_database(), pg_encoding_to_char(encoding) FROM pg_database WHERE datname = current_database()"))
    db_row = result.fetchone()
    print(f"   Database: {db_row[0]}, Encoding: {db_row[1]}")
    
    # Test 2: Try to query ohlcv_candles table
    print("\n2. Testing OHLCV candles query...")
    try:
        result = conn.execute(text("SELECT COUNT(*) FROM ohlcv_candles"))
        count = result.fetchone()[0]
        print(f"   ✓ Table exists, row count: {count}")
    except Exception as e:
        print(f"   ✗ Error querying table: {e}")
        print(f"   Error type: {type(e)}")
    
    # Test 3: Try to get table structure
    print("\n3. Testing table structure query...")
    try:
        result = conn.execute(text("""
            SELECT column_name, data_type, character_set_name 
            FROM information_schema.columns 
            WHERE table_name = 'ohlcv_candles'
            LIMIT 5
        """))
        cols = result.fetchall()
        print(f"   ✓ Retrieved {len(cols)} columns")
        for col in cols:
            print(f"      - {col[0]}: {col[1]}")
    except Exception as e:
        print(f"   ✗ Error getting table structure: {e}")
        print(f"   Error type: {type(e)}")
    
    # Test 4: Try using SQLAlchemy ORM
    print("\n4. Testing SQLAlchemy ORM query...")
    try:
        from backend.models.ohlcv import OHLCVCandle
        from backend.db.session import get_db_session
        from sqlalchemy import and_
        
        db = get_db_session()
        query = db.query(OHLCVCandle).filter(
            and_(
                OHLCVCandle.symbol == 'BTCUSDT',
                OHLCVCandle.timeframe == '1h'
            )
        ).limit(1)
        
        candles = query.all()
        print(f"   ✓ ORM query executed, found {len(candles)} candles")
        if candles:
            print(f"   ✓ First candle timestamp: {candles[0].timestamp}")
        db.close()
    except UnicodeDecodeError as e:
        print(f"   ✗ UnicodeDecodeError: {e}")
        print(f"   Error at position: {e.start if hasattr(e, 'start') else 'unknown'}")
        print(f"   Object causing error: {e.object if hasattr(e, 'object') else 'unknown'}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        print(f"   Error type: {type(e)}")
        import traceback
        traceback.print_exc()
    
    # Test 5: Check for warnings/notices
    print("\n5. Checking PostgreSQL notices...")
    try:
        result = conn.execute(text("""
            SELECT * FROM pg_stat_database WHERE datname = current_database()
        """))
        stats = result.fetchone()
        print(f"   ✓ Database stats retrieved successfully")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    conn.close()
    print("\n" + "=" * 60)
    print("Diagnostic complete")
    print("=" * 60)
    
except Exception as e:
    print(f"\n✗ Fatal error: {e}")
    print(f"Error type: {type(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
