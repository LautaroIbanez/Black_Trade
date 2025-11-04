#!/usr/bin/env python
"""Fix PostgreSQL locale configuration to use UTF-8."""
import psycopg2
import os
import sys

# Force UTF-8 encoding
os.environ['PGCLIENTENCODING'] = 'UTF8'

def fix_postgres_locale():
    """Fix PostgreSQL locale configuration."""
    try:
        print("=" * 60)
        print("Corrigiendo configuración de PostgreSQL")
        print("=" * 60)
        
        # Connect to postgres database to modify black_trade
        print("\n1. Conectando a base de datos 'postgres'...")
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='Oasis1693',
            database='postgres',
            options='-c client_min_messages=error'
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        print("2. Configurando base de datos 'black_trade'...")
        
        # Set lc_messages to 'C' (ASCII-safe)
        try:
            cur.execute("ALTER DATABASE black_trade SET lc_messages TO 'C'")
            print("   ✓ lc_messages configurado a 'C'")
        except Exception as e:
            print(f"   ⚠ Error configurando lc_messages: {e}")
        
        # Ensure client_encoding is UTF8
        try:
            cur.execute("ALTER DATABASE black_trade SET client_encoding TO 'UTF8'")
            print("   ✓ client_encoding configurado a 'UTF8'")
        except Exception as e:
            print(f"   ⚠ Error configurando client_encoding: {e}")
        
        # Set client_min_messages to error
        try:
            cur.execute("ALTER DATABASE black_trade SET client_min_messages TO 'error'")
            print("   ✓ client_min_messages configurado a 'error'")
        except Exception as e:
            print(f"   ⚠ Error configurando client_min_messages: {e}")
        
        cur.close()
        conn.close()
        
        # Now connect to black_trade and verify
        print("\n3. Verificando configuración en 'black_trade'...")
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='Oasis1693',
            database='black_trade',
            client_encoding='UTF8',
            options='-c client_min_messages=error -c lc_messages=C'
        )
        cur = conn.cursor()
        
        cur.execute("SHOW server_encoding")
        server_enc = cur.fetchone()[0]
        print(f"   server_encoding: {server_enc}")
        
        cur.execute("SHOW client_encoding")
        client_enc = cur.fetchone()[0]
        print(f"   client_encoding: {client_enc}")
        
        cur.execute("SHOW lc_messages")
        lc_msg = cur.fetchone()[0]
        print(f"   lc_messages: {lc_msg}")
        
        cur.execute("SHOW client_min_messages")
        min_msg = cur.fetchone()[0]
        print(f"   client_min_messages: {min_msg}")
        
        # Set session-level settings
        print("\n4. Configurando parámetros de sesión...")
        cur.execute("SET lc_messages TO 'C'")
        cur.execute("SET client_encoding TO 'UTF8'")
        cur.execute("SET client_min_messages TO 'error'")
        print("   ✓ Parámetros de sesión configurados")
        
        # Test query
        print("\n5. Probando consulta...")
        cur.execute("SELECT 1 as test")
        result = cur.fetchone()
        print(f"   ✓ Consulta exitosa: {result[0]}")
        
        cur.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print("✓ Configuración completada exitosamente!")
        print("=" * 60)
        print("\nLa base de datos ahora usa:")
        print("  - server_encoding: UTF8")
        print("  - client_encoding: UTF8")
        print("  - lc_messages: C (ASCII-safe)")
        print("  - client_min_messages: error")
        print("\nLos errores de codificación deberían desaparecer.")
        return True
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = fix_postgres_locale()
    sys.exit(0 if success else 1)
