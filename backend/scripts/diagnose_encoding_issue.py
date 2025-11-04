#!/usr/bin/env python
"""Direct diagnostic to see raw PostgreSQL server configuration and behavior."""
import psycopg2
import os
import sys

def test_raw_connection():
    """Test raw connection without any options."""
    print("=" * 70)
    print("TEST 1: Conexión RAW sin opciones (lo que PostgreSQL devuelve por defecto)")
    print("=" * 70)
    try:
        # Force UTF-8 in environment
        old_env = os.environ.get('PGCLIENTENCODING')
        os.environ['PGCLIENTENCODING'] = 'UTF8'
        
        # RAW connection - no options at all
        print("\nConectando SIN opciones...")
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='Oasis1693',
            database='black_trade'
        )
        cur = conn.cursor()
        
        print("✓ Conexión establecida")
        
        cur.execute("SHOW server_encoding")
        print(f"  server_encoding: {cur.fetchone()[0]}")
        
        cur.execute("SHOW lc_messages")
        lc_msg = cur.fetchone()[0]
        print(f"  lc_messages: {lc_msg}")
        if '1252' in lc_msg or 'Latin' in lc_msg or 'Spanish' in lc_msg or 'es_' in lc_msg.lower():
            print(f"  ⚠ PROBLEMA: lc_messages está en Latin-1 o español!")
        
        cur.execute("SHOW client_encoding")
        print(f"  client_encoding: {cur.fetchone()[0]}")
        
        # Try a simple query
        print("\nProbando consulta simple...")
        try:
            cur.execute("SELECT 1")
            result = cur.fetchone()
            print(f"  ✓ Query exitosa: {result[0]}")
        except UnicodeDecodeError as e:
            print(f"  ✗ UnicodeDecodeError en query: {e}")
            print(f"     Byte problemático: {e.start if hasattr(e, 'start') else 'desconocido'}")
        
        cur.close()
        conn.close()
        
        # Restore env
        if old_env:
            os.environ['PGCLIENTENCODING'] = old_env
        elif 'PGCLIENTENCODING' in os.environ:
            del os.environ['PGCLIENTENCODING']
        
        return True
    except UnicodeDecodeError as e:
        print(f"\n✗ UnicodeDecodeError durante la conexión misma!")
        print(f"   Byte problemático: {e.start if hasattr(e, 'start') else 'desconocido'}")
        print(f"   Esto significa que el mensaje de bienvenida del servidor tiene acentos")
        return False
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_with_options():
    """Test connection with options."""
    print("\n" + "=" * 70)
    print("TEST 2: Conexión CON opciones (lc_messages=C, client_min_messages=error)")
    print("=" * 70)
    try:
        os.environ['PGCLIENTENCODING'] = 'UTF8'
        
        print("\nConectando CON opciones...")
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='Oasis1693',
            database='black_trade',
            options='-c client_min_messages=error -c lc_messages=C -c client_encoding=UTF8'
        )
        cur = conn.cursor()
        
        print("✓ Conexión establecida")
        
        cur.execute("SHOW lc_messages")
        lc_msg = cur.fetchone()[0]
        print(f"  lc_messages: {lc_msg}")
        
        # Try a query that might trigger notices
        print("\nProbando consulta que podría generar NOTICE...")
        try:
            cur.execute("SELECT COUNT(*) FROM information_schema.tables")
            result = cur.fetchone()
            print(f"  ✓ Query exitosa: {result[0]} tablas")
        except UnicodeDecodeError as e:
            print(f"  ✗ UnicodeDecodeError: {e}")
        
        cur.close()
        conn.close()
        
        return True
    except UnicodeDecodeError as e:
        print(f"\n✗ UnicodeDecodeError incluso CON opciones!")
        print(f"   Esto significa que las opciones no se están aplicando correctamente")
        return False
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ohlcv_query():
    """Test actual OHLCV query that's failing."""
    print("\n" + "=" * 70)
    print("TEST 3: Consulta OHLCV real (la que está fallando en producción)")
    print("=" * 70)
    try:
        os.environ['PGCLIENTENCODING'] = 'UTF8'
        
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='Oasis1693',
            database='black_trade',
            options='-c client_min_messages=error -c lc_messages=C -c client_encoding=UTF8'
        )
        cur = conn.cursor()
        
        print("\nProbando consulta OHLCV...")
        try:
            # This is the actual query from ohlcv_repository
            cur.execute("""
                SELECT timestamp, open, high, low, close, volume
                FROM ohlcv_candles
                WHERE symbol = %s AND timeframe = %s
                ORDER BY timestamp DESC
                LIMIT 10
            """, ('BTCUSDT', '1h'))
            
            rows = cur.fetchall()
            print(f"  ✓ Query exitosa: {len(rows)} filas")
            
            if rows:
                print(f"  Primera fila: {rows[0]}")
        except UnicodeDecodeError as e:
            print(f"  ✗ UnicodeDecodeError en consulta OHLCV: {e}")
            print(f"     Byte problemático: {e.start if hasattr(e, 'start') else 'desconocido'}")
        except Exception as e:
            print(f"  ✗ Error (no Unicode): {e}")
        
        cur.close()
        conn.close()
        
        return True
    except UnicodeDecodeError as e:
        print(f"\n✗ UnicodeDecodeError durante conexión para OHLCV!")
        return False
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_database_defaults():
    """Check what the database defaults are set to."""
    print("\n" + "=" * 70)
    print("TEST 4: Verificando configuración a nivel de BASE DE DATOS")
    print("=" * 70)
    try:
        os.environ['PGCLIENTENCODING'] = 'UTF8'
        
        # Connect to postgres to check black_trade settings
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='Oasis1693',
            database='postgres',
            options='-c client_min_messages=error -c lc_messages=C'
        )
        cur = conn.cursor()
        
        print("\nVerificando configuración de 'black_trade' desde 'postgres'...")
        cur.execute("""
            SELECT 
                datname,
                pg_encoding_to_char(encoding) as encoding,
                datcollate,
                datctype,
                (SELECT setting FROM pg_settings WHERE name = 'lc_messages' LIMIT 1) as default_lc_messages
            FROM pg_database 
            WHERE datname = 'black_trade'
        """)
        db_info = cur.fetchone()
        if db_info:
            print(f"  Base de datos: {db_info[0]}")
            print(f"  Encoding: {db_info[1]}")
            print(f"  Collate: {db_info[2]}")
            print(f"  Ctype: {db_info[3]}")
            print(f"  Default lc_messages: {db_info[4]}")
            
            # Check if database has specific settings
            cur.execute("""
                SELECT 
                    setdatabase,
                    setname,
                    setting
                FROM pg_db_role_setting
                WHERE setdatabase = (SELECT oid FROM pg_database WHERE datname = 'black_trade')
            """)
            db_settings = cur.fetchall()
            if db_settings:
                print("\n  Configuraciones específicas de la base de datos:")
                for db_oid, setting_name, setting_value in db_settings:
                    print(f"    {setting_name}: {setting_value}")
            else:
                print("\n  ⚠ No hay configuraciones específicas para 'black_trade'")
                print("     Esto significa que usa los valores por defecto del servidor")
        
        cur.close()
        conn.close()
        
        return True
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("DIAGNÓSTICO COMPLETO DE CODIFICACIÓN DE POSTGRESQL")
    print("=" * 70)
    
    results = []
    results.append(("Conexión RAW", test_raw_connection()))
    results.append(("Conexión con opciones", test_with_options()))
    results.append(("Consulta OHLCV", test_ohlcv_query()))
    results.append(("Configuración de BD", check_database_defaults()))
    
    print("\n" + "=" * 70)
    print("RESUMEN")
    print("=" * 70)
    for test_name, success in results:
        status = "✓" if success else "✗"
        print(f"{status} {test_name}")
    
    print("\n" + "=" * 70)
    if all(r[1] for r in results):
        print("✓ Todos los tests pasaron - el problema puede estar en otra parte")
    else:
        print("⚠ Algunos tests fallaron - el problema está en la conexión/codificación")
        print("\nSi el TEST 1 (RAW) falla con UnicodeDecodeError:")
        print("  → El servidor está enviando mensajes con acentos en el handshake")
        print("  → SOLUCIÓN: Configurar lc_messages='C' a nivel de base de datos")
        print("\nSi el TEST 1 pasa pero TEST 3 (OHLCV) falla:")
        print("  → Hay datos o mensajes en la consulta que tienen codificación incorrecta")
        print("  → SOLUCIÓN: Verificar los datos almacenados en ohlcv_candles")
    print("=" * 70 + "\n")
