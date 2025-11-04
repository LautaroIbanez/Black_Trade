#!/usr/bin/env python
"""Check PostgreSQL server lc_messages configuration at database level."""
import psycopg2
import os

os.environ['PGCLIENTENCODING'] = 'UTF8'

# Connect to postgres database
conn = psycopg2.connect(
    host='localhost',
    port=5432,
    user='postgres',
    password='Oasis1693',
    database='postgres',
    options='-c client_min_messages=error -c lc_messages=C'
)
cur = conn.cursor()

print("=" * 70)
print("VERIFICANDO CONFIGURACIÓN DE lc_messages A NIVEL DE SERVIDOR/BD")
print("=" * 70)

# Check server-level settings
print("\n1. Configuración a nivel de SERVIDOR:")
cur.execute("""
    SELECT name, setting, source, context 
    FROM pg_settings 
    WHERE name IN ('lc_messages', 'lc_ctype', 'lc_collate')
    ORDER BY name
""")
for name, setting, source, context in cur.fetchall():
    print(f"   {name}: {setting}")
    print(f"      Fuente: {source}, Contexto: {context}")

# Check database-level settings
print("\n2. Configuración específica de la base de datos 'black_trade':")
cur.execute("""
    SELECT 
        datname,
        pg_encoding_to_char(encoding) as encoding,
        datcollate,
        datctype
    FROM pg_database 
    WHERE datname = 'black_trade'
""")
db_row = cur.fetchone()
if db_row:
    print(f"   Base de datos: {db_row[0]}")
    print(f"   Encoding: {db_row[1]}")
    print(f"   Collate: {db_row[2]}")
    print(f"   Ctype: {db_row[3]}")

# Check if black_trade has database-level settings
print("\n3. Verificando configuraciones específicas de 'black_trade':")
cur.execute("""
    SELECT 
        d.datname,
        s.setconfig
    FROM pg_db_role_setting s
    JOIN pg_database d ON s.setdatabase = d.oid
    WHERE d.datname = 'black_trade'
""")
db_settings = cur.fetchall()
if db_settings:
    print("   Configuraciones encontradas:")
    for datname, setconfig in db_settings:
        for setting in setconfig:
            print(f"     {setting}")
else:
    print("   ⚠ No hay configuraciones específicas para 'black_trade'")
    print("      La base de datos usa los valores por defecto del servidor")

# Try to see what lc_messages is when connecting to black_trade
print("\n4. Probando conexión directa a 'black_trade' (sin opciones):")
cur.close()
conn.close()

conn2 = psycopg2.connect(
    host='localhost',
    port=5432,
    user='postgres',
    password='Oasis1693',
    database='black_trade'
    # NO options here - see what the server sends by default
)
cur2 = conn2.cursor()
cur2.execute("SHOW lc_messages")
lc_msg_default = cur2.fetchone()[0]
print(f"   lc_messages sin opciones: {lc_msg_default}")

if '1252' in lc_msg_default or 'Latin' in lc_msg_default or 'Spanish' in lc_msg_default or 'es_' in lc_msg_default.lower():
    print(f"   ⚠ PROBLEMA: El servidor está usando un locale con acentos!")
    print(f"      Esto causa errores de codificación en el mensaje de bienvenida")
    print(f"\n   SOLUCIÓN: Ejecutar como superusuario en PostgreSQL:")
    print(f"      ALTER DATABASE black_trade SET lc_messages TO 'C';")
else:
    print(f"   ✓ lc_messages está configurado correctamente")

cur2.close()
conn2.close()

print("\n" + "=" * 70)
