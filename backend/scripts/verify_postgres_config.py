#!/usr/bin/env python
"""Verify PostgreSQL server configuration."""
import psycopg2
import os
import sys

os.environ['PGCLIENTENCODING'] = 'UTF8'

def verify_config():
    """Verify PostgreSQL configuration."""
    try:
        print("=" * 60)
        print("VERIFICACIÓN DE CONFIGURACIÓN DE POSTGRESQL")
        print("=" * 60)
        
        # Connect with minimal options to see raw server config
        print("\n1. Conectando sin opciones para ver configuración del SERVIDOR...")
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='Oasis1693',
            database='black_trade'
        )
        cur = conn.cursor()
        
        cur.execute("SHOW server_encoding")
        server_enc = cur.fetchone()[0]
        print(f"   server_encoding: {server_enc}")
        if server_enc.upper() != 'UTF8':
            print(f"   ⚠ PROBLEMA: server_encoding debe ser UTF8, es {server_enc}")
        else:
            print("   ✓ server_encoding es UTF8")
        
        cur.execute("SHOW lc_messages")
        lc_msg = cur.fetchone()[0]
        print(f"   lc_messages: {lc_msg}")
        
        # Check if it's problematic
        problematic = False
        if '1252' in lc_msg or 'Latin' in lc_msg or 'Spanish' in lc_msg or 'es_' in lc_msg.lower():
            print(f"   ⚠ PROBLEMA CRÍTICO: lc_messages está en Latin-1 o español!")
            print(f"      Esto causa errores de codificación. Debe ser 'C' o 'en_US.UTF-8'")
            problematic = True
        else:
            print("   ✓ lc_messages está configurado correctamente")
        
        cur.execute("SHOW client_encoding")
        client_enc = cur.fetchone()[0]
        print(f"   client_encoding: {client_enc}")
        
        # Check database-level settings
        print("\n2. Verificando configuración a nivel de BASE DE DATOS:")
        cur.execute("""
            SELECT name, setting, source 
            FROM pg_settings 
            WHERE name IN ('lc_messages', 'server_encoding', 'client_encoding')
            ORDER BY name
        """)
        settings = cur.fetchall()
        for name, value, source in settings:
            source_desc = {
                'default': 'por defecto',
                'configuration file': 'archivo de configuración',
                'database': 'base de datos',
                'user': 'usuario',
                'session': 'sesión'
            }.get(source, source)
            print(f"   {name}: {value} (fuente: {source_desc})")
        
        # Check database-specific settings
        print("\n3. Verificando configuración específica de 'black_trade':")
        cur.execute("""
            SELECT 
                datname,
                pg_encoding_to_char(encoding) as encoding,
                datcollate,
                datctype
            FROM pg_database 
            WHERE datname = 'black_trade'
        """)
        db_info = cur.fetchone()
        if db_info:
            print(f"   Base de datos: {db_info[0]}")
            print(f"   Encoding: {db_info[1]}")
            print(f"   Collate: {db_info[2]}")
            print(f"   Ctype: {db_info[3]}")
        
        cur.close()
        conn.close()
        
        # Now test with options
        print("\n4. Probando conexión con opciones de corrección...")
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='Oasis1693',
            database='black_trade',
            options='-c client_min_messages=error -c lc_messages=C -c client_encoding=UTF8'
        )
        cur = conn.cursor()
        
        cur.execute("SHOW lc_messages")
        lc_msg_with_opts = cur.fetchone()[0]
        print(f"   lc_messages con opciones: {lc_msg_with_opts}")
        
        # Test query
        cur.execute("SELECT 1 as test")
        result = cur.fetchone()
        print(f"   ✓ Consulta de prueba exitosa: {result[0]}")
        
        cur.close()
        conn.close()
        
        print("\n" + "=" * 60)
        if problematic:
            print("⚠ CONCLUSIÓN: Hay problemas de configuración que deben corregirse")
            print("\nAcción requerida:")
            print("1. Ejecuta: python backend/scripts/fix_postgres_locale.py")
            print("2. O configura PostgreSQL directamente:")
            print("   ALTER DATABASE black_trade SET lc_messages TO 'C';")
        else:
            print("✓ Configuración correcta")
        print("=" * 60)
        
        return not problematic
        
    except Exception as e:
        print(f"\n✗ Error verificando configuración: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = verify_config()
    sys.exit(0 if success else 1)
