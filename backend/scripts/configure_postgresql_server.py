#!/usr/bin/env python
"""Configure PostgreSQL server lc_messages to 'C' to prevent encoding errors."""
import os
import shutil
from pathlib import Path

def find_postgresql_conf():
    """Find postgresql.conf file."""
    # Common locations
    search_paths = [
        Path("C:/Program Files/PostgreSQL/18/data/postgresql.conf"),
        Path("C:/Program Files/PostgreSQL/17/data/postgresql.conf"),
        Path("C:/Program Files/PostgreSQL/16/data/postgresql.conf"),
        Path("C:/Program Files/PostgreSQL/15/data/postgresql.conf"),
    ]
    
    for path in search_paths:
        if path.exists():
            return path
    
    # Try to find in Program Files
    pg_dir = Path("C:/Program Files/PostgreSQL")
    if pg_dir.exists():
        for version_dir in sorted(pg_dir.iterdir(), reverse=True):
            conf_file = version_dir / "data" / "postgresql.conf"
            if conf_file.exists():
                return conf_file
    
    return None

def configure_lc_messages(conf_path):
    """Configure lc_messages in postgresql.conf."""
    print(f"Leyendo archivo: {conf_path}")
    
    # Create backup
    backup_path = conf_path.with_suffix('.conf.backup')
    if not backup_path.exists():
        print(f"Creando backup: {backup_path}")
        shutil.copy2(conf_path, backup_path)
    else:
        print(f"Backup ya existe: {backup_path}")
    
    # Read current configuration
    with open(conf_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find and modify lc_messages
    modified = False
    lc_messages_found = False
    
    for i, line in enumerate(lines):
        # Look for lc_messages setting (commented or not)
        if 'lc_messages' in line.lower() and not line.strip().startswith('#'):
            lc_messages_found = True
            # Check current value
            if '=' in line:
                current_value = line.split('=')[1].strip().strip("'\"")
                if current_value.upper() != 'C':
                    print(f"Valor actual de lc_messages: {current_value}")
                    print(f"Modificando a 'C'...")
                    lines[i] = "lc_messages = 'C'\n"
                    modified = True
                else:
                    print(f"lc_messages ya esta configurado como 'C'")
                    return True
            break
    
    # If not found, add it
    if not lc_messages_found:
        print("lc_messages no encontrado, agregando configuracion...")
        # Find a good place to add it (after locale settings or at end of locale section)
        insert_index = len(lines)
        for i, line in enumerate(lines):
            if 'locale' in line.lower() and '=' in line:
                # Insert after this line
                insert_index = i + 1
                # Find end of locale section (next non-commented line not about locale)
                for j in range(i + 1, len(lines)):
                    if lines[j].strip() and not lines[j].strip().startswith('#'):
                        if 'locale' not in lines[j].lower():
                            insert_index = j
                            break
                    insert_index = j + 1
                break
        
        lines.insert(insert_index, "lc_messages = 'C'\n")
        modified = True
    
    # Write modified configuration
    if modified:
        print(f"Guardando configuracion modificada...")
        with open(conf_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        print(f"Configuracion guardada exitosamente!")
        print(f"\nIMPORTANTE: Necesitas reiniciar PostgreSQL para que los cambios surtan efecto.")
        print(f"Ejecuta: .\\backend\\scripts\\restart_postgres.ps1 (como administrador)")
        return True
    else:
        print("No se requieren cambios.")
        return False

if __name__ == "__main__":
    print("=" * 70)
    print("Configurando lc_messages a nivel de servidor PostgreSQL")
    print("=" * 70)
    print()
    
    conf_path = find_postgresql_conf()
    
    if not conf_path:
        print("ERROR: No se encontro el archivo postgresql.conf")
        print("Por favor, verifica que PostgreSQL este instalado correctamente.")
        exit(1)
    
    print(f"Archivo encontrado: {conf_path}")
    print()
    
    try:
        if configure_lc_messages(conf_path):
            print()
            print("=" * 70)
            print("Configuracion completada!")
            print("=" * 70)
            print()
            print("PR proximo paso: Reinicia PostgreSQL como administrador")
            print("Ejecuta: .\\backend\\scripts\\restart_postgres.ps1")
        else:
            print()
            print("=" * 70)
            print("La configuracion ya esta correcta")
            print("=" * 70)
    except PermissionError:
        print()
        print("ERROR: No tienes permisos para modificar el archivo.")
        print("Ejecuta este script como administrador o modifica el archivo manualmente:")
        print(f"  {conf_path}")
        print()
        print("Agrega o modifica esta linea:")
        print("  lc_messages = 'C'")
        exit(1)
    except Exception as e:
        print()
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
