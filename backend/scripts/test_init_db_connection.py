#!/usr/bin/env python
"""Test the exact connection flow that init_db uses."""
import os
import sys
from pathlib import Path

# Add project root to path (same as init_db)
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load .env file if it exists
env_file = project_root / '.env'
if env_file.exists():
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

# Force UTF-8 encoding (same as session.py)
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict') if hasattr(sys.stdout, 'buffer') else sys.stdout
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict') if hasattr(sys.stderr, 'buffer') else sys.stderr
    os.environ['PGCLIENTENCODING'] = 'UTF8'

# Import psycopg2 patch (same as session.py)
print("1. Importando patch de psycopg2...")
try:
    from backend.db import psycopg2_patch
    psycopg2_patch.patch_psycopg2()
    print("   ✓ Patch importado")
except ImportError as e:
    print(f"   ⚠ Patch no disponible: {e}")

# Now import session (same as init_db)
print("\n2. Importando backend.db.session...")
try:
    from backend.db.session import engine, init_db
    from backend.models.base import Base
    print("   ✓ Session importado")
except Exception as e:
    print(f"   ✗ Error importando session: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test creating tables (same as init_db)
print("\n3. Probando Base.metadata.create_all()...")
try:
    # This is the exact call that init_db makes
    Base.metadata.create_all(bind=engine)
    print("   ✓ create_all() completado sin errores")
except UnicodeDecodeError as e:
    print(f"   ✗ UnicodeDecodeError durante create_all(): {e}")
    print(f"      Byte problemático: {e.start if hasattr(e, 'start') else 'desconocido'}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"   ⚠ Error durante create_all() (no Unicode): {e}")
    import traceback
    traceback.print_exc()

# Test a simple query through SQLAlchemy
print("\n4. Probando consulta a través de SQLAlchemy...")
try:
    from backend.db.session import get_db
    db = next(get_db())
    
    # Test query
    from sqlalchemy import text
    result = db.execute(text("SELECT 1 as test"))
    row = result.fetchone()
    print(f"   ✓ Query SQLAlchemy exitosa: {row[0]}")
    
    # Test OHLCV table exists
    result = db.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'ohlcv_candles'"))
    count = result.fetchone()[0]
    print(f"   ✓ Tabla ohlcv_candles existe: {count > 0}")
    
    db.close()
except UnicodeDecodeError as e:
    print(f"   ✗ UnicodeDecodeError en consulta SQLAlchemy: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"   ⚠ Error en consulta SQLAlchemy: {e}")
    import traceback
    traceback.print_exc()

# Check engine connection args
print("\n5. Verificando configuración del engine...")
try:
    print(f"   Engine URL: {engine.url}")
    if hasattr(engine.url, 'query'):
        print(f"   URL query params: {engine.url.query}")
    
    # Check if we can see connect_args
    if hasattr(engine, 'connect'):
        print(f"   Engine tiene método connect")
        
        # Try to inspect the actual connection
        from sqlalchemy import text
        with engine.connect() as conn:
            result = conn.execute(text("SHOW lc_messages"))
            lc_msg = result.fetchone()[0]
            print(f"   ✓ lc_messages en conexión del engine: {lc_msg}")
            
            result = conn.execute(text("SHOW client_encoding"))
            client_enc = result.fetchone()[0]
            print(f"   ✓ client_encoding en conexión del engine: {client_enc}")
            
            result = conn.execute(text("SHOW server_encoding"))
            server_enc = result.fetchone()[0]
            print(f"   ✓ server_encoding: {server_enc}")
except Exception as e:
    print(f"   ⚠ Error verificando engine: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("RESUMEN")
print("=" * 70)
print("Si viste UnicodeDecodeError en los pasos 3 o 4:")
print("  → El problema está en cómo SQLAlchemy crea las conexiones")
print("  → Las opciones de lc_messages=C no se están aplicando correctamente")
print("  → Necesitas verificar que el engine use las opciones correctas")
print("=" * 70)
