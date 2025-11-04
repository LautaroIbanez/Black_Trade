#!/usr/bin/env python
"""Check for PostgreSQL extensions, functions, or triggers that might emit localized messages."""
import psycopg2
import os
import sys

os.environ['PGCLIENTENCODING'] = 'UTF8'

def check_extensions():
    """Check for problematic extensions, functions, or triggers."""
    try:
        print("=" * 60)
        print("VERIFICANDO EXTENSIONES, FUNCIONES Y TRIGGERS")
        print("=" * 60)
        
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='Oasis1693',
            database='black_trade',
            options='-c client_min_messages=error -c lc_messages=C'
        )
        cur = conn.cursor()
        
        # Check extensions
        print("\n1. Extensiones instaladas:")
        cur.execute("""
            SELECT extname, extversion 
            FROM pg_extension 
            ORDER BY extname
        """)
        extensions = cur.fetchall()
        if extensions:
            for extname, extversion in extensions:
                print(f"   - {extname} (versión {extversion})")
        else:
            print("   (ninguna)")
        
        # Check functions that might print messages
        print("\n2. Funciones que podrían emitir mensajes:")
        cur.execute("""
            SELECT 
                p.proname as function_name,
                n.nspname as schema_name
            FROM pg_proc p
            JOIN pg_namespace n ON p.pronamespace = n.oid
            WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
            AND p.prokind = 'f'
            LIMIT 20
        """)
        functions = cur.fetchall()
        if functions:
            print(f"   Encontradas {len(functions)} funciones personalizadas:")
            for func_name, schema_name in functions[:10]:
                print(f"   - {schema_name}.{func_name}")
            if len(functions) > 10:
                print(f"   ... y {len(functions) - 10} más")
            print("   (Estas funciones no deberían ser problemáticas si lc_messages='C')")
        else:
            print("   ✓ No se encontraron funciones personalizadas problemáticas")
        
        # Check triggers
        print("\n3. Triggers activos:")
        cur.execute("""
            SELECT 
                tgname as trigger_name,
                tgrelid::regclass as table_name,
                pg_get_triggerdef(oid) as definition
            FROM pg_trigger
            WHERE tgisinternal = false
            LIMIT 10
        """)
        triggers = cur.fetchall()
        if triggers:
            for trig_name, table_name, definition in triggers:
                print(f"   - {trig_name} en {table_name}")
                # Check if definition contains non-ASCII
                try:
                    definition.encode('ascii')
                except UnicodeEncodeError:
                    print(f"     ⚠ Este trigger contiene caracteres no-ASCII!")
        else:
            print("   (ninguno)")
        
        # Check for rules
        print("\n4. Reglas (rules) activas:")
        cur.execute("""
            SELECT 
                rulename as rule_name,
                ev_class::regclass as table_name
            FROM pg_rewrite
            WHERE ev_class::regclass::text NOT LIKE 'pg_%'
            LIMIT 10
        """)
        rules = cur.fetchall()
        if rules:
            for rule_name, table_name in rules:
                print(f"   - {rule_name} en {table_name}")
        else:
            print("   (ninguna)")
        
        # Check for custom types with non-ASCII
        print("\n5. Tipos personalizados:")
        cur.execute("""
            SELECT typname 
            FROM pg_type t
            JOIN pg_namespace n ON t.typnamespace = n.oid
            WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
            AND t.typtype = 'c'
            LIMIT 10
        """)
        types = cur.fetchall()
        if types:
            for (typname,) in types:
                print(f"   - {typname}")
        else:
            print("   (ninguno)")
        
        cur.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print("✓ Verificación completada")
        print("=" * 60)
        print("\nRecomendación:")
        print("Si encuentras funciones o triggers que emiten mensajes, asegúrate de que:")
        print("1. Usen client_min_messages=error para suprimir NOTICE/WARNING")
        print("2. No contengan caracteres no-ASCII en los mensajes")
        print("3. O usa lc_messages='C' a nivel de sesión (ya configurado)")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = check_extensions()
    sys.exit(0 if success else 1)
