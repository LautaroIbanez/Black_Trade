#!/usr/bin/env python
"""Fix PostgreSQL encoding configuration to resolve UTF-8 issues."""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Force UTF-8 encoding
os.environ['PGCLIENTENCODING'] = 'UTF8'

def fix_postgresql_encoding():
    """Configure PostgreSQL to use UTF-8 and suppress problematic messages."""
    try:
        # Try to connect using psycopg2 directly first
        import psycopg2
        from psycopg2 import sql
        
        # Get database URL from environment
        db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:Oasis1693@localhost:5432/black_trade')
        
        logger.info("Connecting to PostgreSQL...")
        logger.info("This may show encoding errors initially, but we'll fix them.")
        
        # Parse connection string
        # Format: postgresql://user:password@host:port/database
        if db_url.startswith('postgresql://'):
            parts = db_url.replace('postgresql://', '').split('@')
            if len(parts) == 2:
                user_pass = parts[0].split(':')
                host_db = parts[1].split('/')
                if len(host_db) == 2:
                    host_port = host_db[0].split(':')
                    host = host_port[0]
                    port = int(host_port[1]) if len(host_port) > 1 else 5432
                    user = user_pass[0]
                    password = user_pass[1] if len(user_pass) > 1 else ''
                    database = host_db[1]
                    
                    # Try to connect to postgres database first (to configure the database)
                    try:
                        logger.info(f"Connecting to 'postgres' database to configure settings...")
                        conn = psycopg2.connect(
                            host=host,
                            port=port,
                            user=user,
                            password=password,
                            database='postgres',
                            client_encoding='UTF8',
                            connect_timeout=10
                        )
                        conn.set_client_encoding('UTF8')
                        conn.autocommit = True
                        cur = conn.cursor()
                        
                        # Configure PostgreSQL settings
                        logger.info("Configuring PostgreSQL settings...")
                        
                        # 1. Set client_min_messages to ERROR for the database
                        try:
                            cur.execute(f"ALTER DATABASE {database} SET client_min_messages = 'error'")
                            logger.info(f"✓ Set client_min_messages to ERROR for database '{database}'")
                        except Exception as e:
                            logger.warning(f"Could not set client_min_messages for database: {e}")
                        
                        # 2. Set default encoding to UTF8
                        try:
                            cur.execute(f"ALTER DATABASE {database} SET client_encoding = 'UTF8'")
                            logger.info(f"✓ Set client_encoding to UTF8 for database '{database}'")
                        except Exception as e:
                            logger.warning(f"Could not set client_encoding for database: {e}")
                        
                        # 3. Set server locale to UTF8 (if possible)
                        try:
                            # Check current locale
                            cur.execute("SHOW lc_messages")
                            current_locale = cur.fetchone()[0]
                            logger.info(f"Current lc_messages: {current_locale}")
                            
                            # Try to set to C locale (which is ASCII-safe) or en_US.UTF-8
                            try:
                                cur.execute("SET lc_messages = 'C'")
                                logger.info("✓ Set lc_messages to 'C' (ASCII-safe)")
                            except:
                                try:
                                    cur.execute("SET lc_messages = 'en_US.UTF-8'")
                                    logger.info("✓ Set lc_messages to 'en_US.UTF-8'")
                                except:
                                    logger.warning("Could not change lc_messages")
                        except Exception as e:
                            logger.warning(f"Could not configure locale: {e}")
                        
                        cur.close()
                        conn.close()
                        logger.info("Configuration applied to 'postgres' database")
                        
                    except Exception as e:
                        logger.error(f"Error connecting to 'postgres' database: {e}")
                        logger.info("Trying to connect directly to target database...")
                    
                    # Now connect to the target database and configure session settings
                    try:
                        logger.info(f"Connecting to target database '{database}'...")
                        conn = psycopg2.connect(
                            host=host,
                            port=port,
                            user=user,
                            password=password,
                            database=database,
                            client_encoding='UTF8',
                            connect_timeout=10,
                            options='-c client_min_messages=error'
                        )
                        conn.set_client_encoding('UTF8')
                        conn.autocommit = True
                        cur = conn.cursor()
                        
                        # Set session-level settings
                        logger.info("Configuring session-level settings...")
                        
                        try:
                            cur.execute("SET client_min_messages TO 'error'")
                            logger.info("✓ Set session client_min_messages to ERROR")
                        except Exception as e:
                            logger.warning(f"Could not set client_min_messages: {e}")
                        
                        try:
                            cur.execute("SET client_encoding TO 'UTF8'")
                            logger.info("✓ Set session client_encoding to UTF8")
                        except Exception as e:
                            logger.warning(f"Could not set client_encoding: {e}")
                        
                        try:
                            cur.execute("SET lc_messages TO 'C'")
                            logger.info("✓ Set session lc_messages to 'C'")
                        except:
                            try:
                                cur.execute("SET lc_messages TO 'en_US.UTF-8'")
                                logger.info("✓ Set session lc_messages to 'en_US.UTF-8'")
                            except:
                                logger.warning("Could not set lc_messages")
                        
                        # Test a simple query
                        logger.info("Testing database connection...")
                        cur.execute("SELECT 1 as test")
                        result = cur.fetchone()
                        logger.info(f"✓ Test query successful: {result[0]}")
                        
                        # Check encoding
                        cur.execute("SHOW server_encoding")
                        server_enc = cur.fetchone()[0]
                        logger.info(f"✓ Server encoding: {server_enc}")
                        
                        cur.execute("SHOW client_encoding")
                        client_enc = cur.fetchone()[0]
                        logger.info(f"✓ Client encoding: {client_enc}")
                        
                        cur.close()
                        conn.close()
                        logger.info("\n" + "="*60)
                        logger.info("✓ PostgreSQL configuration completed successfully!")
                        logger.info("="*60)
                        logger.info("\nNext steps:")
                        logger.info("1. Restart your backend application")
                        logger.info("2. The encoding errors should now be resolved")
                        return True
                        
                    except Exception as e:
                        logger.error(f"Error configuring target database: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                        return False
                else:
                    logger.error("Invalid DATABASE_URL format: missing database name")
                    return False
            else:
                logger.error("Invalid DATABASE_URL format: missing user/password")
                return False
        else:
            logger.error(f"Unsupported database URL format: {db_url}")
            return False
            
    except ImportError:
        logger.error("psycopg2 is not installed. Please install it first: pip install psycopg2-binary")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    logger.info("="*60)
    logger.info("PostgreSQL Encoding Configuration Fix")
    logger.info("="*60)
    logger.info("")
    
    success = fix_postgresql_encoding()
    
    if success:
        logger.info("\n✓ Configuration completed successfully!")
        sys.exit(0)
    else:
        logger.error("\n✗ Configuration failed. Please check the errors above.")
        sys.exit(1)
