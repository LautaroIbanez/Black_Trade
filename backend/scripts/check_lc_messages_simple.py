#!/usr/bin/env python
"""Simple check for lc_messages configuration."""
import psycopg2

try:
    conn = psycopg2.connect('postgresql://postgres:Oasis1693@localhost:5432/black_trade')
    cur = conn.cursor()
    cur.execute("SHOW lc_messages")
    lc_msg = cur.fetchone()[0]
    print(f"lc_messages actual: {lc_msg}")
    
    if lc_msg == 'C':
        print("OK: lc_messages esta configurado correctamente")
    else:
        print(f"WARNING: lc_messages es '{lc_msg}', deberia ser 'C'")
        print("Necesitas reiniciar PostgreSQL o configurar a nivel de servidor")
    
    conn.close()
except UnicodeDecodeError as e:
    print(f"ERROR: UnicodeDecodeError al conectar: {e}")
    print("Esto significa que el servidor aun tiene lc_messages con acentos")
except Exception as e:
    print(f"ERROR: {e}")
