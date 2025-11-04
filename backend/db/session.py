"""Database session management."""
import os
import sys
import locale

# Import psycopg2 patch BEFORE importing sqlalchemy or psycopg2
try:
    from backend.db import psycopg2_patch
    psycopg2_patch.patch_psycopg2()
except ImportError:
    pass  # Patch module not available

# Force UTF-8 encoding before importing anything that might use psycopg2
if sys.platform == 'win32':
    # On Windows, ensure UTF-8 encoding is used
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict') if hasattr(sys.stdout, 'buffer') else sys.stdout
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict') if hasattr(sys.stderr, 'buffer') else sys.stderr
    # Set environment variable to force UTF-8
    os.environ['PGCLIENTENCODING'] = 'UTF8'

# Patch psycopg2 to handle encoding errors gracefully
try:
    import psycopg2.extensions
    
    # Original notice processor
    _original_notice_processor = None
    
    def safe_notice_processor(notice):
        """Handle PostgreSQL notices safely, ignoring encoding errors."""
        try:
            # Try to get the message safely
            if hasattr(notice, 'message_primary'):
                msg = notice.message_primary
            elif hasattr(notice, 'message'):
                msg = notice.message
            else:
                msg = str(notice)
            
            # Log the notice if it can be decoded
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"PostgreSQL notice: {msg}")
        except (UnicodeDecodeError, UnicodeError):
            # Silently ignore encoding errors in notices
            pass
    
    # Register the safe notice processor
    psycopg2.extensions.set_wait_callback(None)  # Disable async wait callback if set
    # Note: We can't directly set notice processor without connection, but we'll handle it in the connect event
    
except ImportError:
    pass  # psycopg2 not available

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from contextlib import contextmanager
from typing import Generator

from backend.models.base import Base

# Create a custom connection factory that handles encoding errors
def create_safe_connection(dsn=None, connection_factory=None, **kwargs):
    """Create a PostgreSQL connection with safe encoding error handling."""
    try:
        import psycopg2
        
        # Wrap the connection to handle encoding errors in notices
        class SafeConnection(psycopg2.extensions.connection):
            """Connection wrapper that safely handles encoding errors."""
            
            def __init__(self, *args, **kwargs):
                # Call parent init, but catch encoding errors
                try:
                    super().__init__(*args, **kwargs)
                    # Set notice handler immediately after connection
                    self.set_notice_handler(self._safe_notice_handler)
                    # Set encoding to UTF-8
                    self.set_client_encoding('UTF8')
                    # Suppress notices that might have encoding issues
                    with self.cursor() as cur:
                        cur.execute("SET client_min_messages TO 'ERROR'")
                except UnicodeDecodeError as e:
                    # If we get an encoding error during connection, try to continue anyway
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Encoding error during connection initialization: {e}. Continuing anyway...")
                    # Re-raise as a more generic error that won't break the connection
                    raise psycopg2.OperationalError(f"Connection encoding issue: {e}")
            
            def _safe_notice_handler(self, notice):
                """Safely handle PostgreSQL notices."""
                try:
                    # Only process if we can safely decode
                    if hasattr(notice, 'message_primary'):
                        msg = str(notice.message_primary)
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.debug(f"PostgreSQL notice: {msg}")
                except (UnicodeDecodeError, UnicodeError, AttributeError):
                    # Silently ignore encoding errors in notices
                    pass
        
        # Use the safe connection factory
        if connection_factory is None:
            connection_factory = SafeConnection
        
        # Create connection with error handling
        try:
            return psycopg2.connect(dsn=dsn, connection_factory=connection_factory, **kwargs)
        except UnicodeDecodeError as e:
            # If we still get encoding errors, try with explicit encoding suppression
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Encoding error in psycopg2.connect: {e}. Attempting workaround...")
            # Try again with options to suppress notices
            if isinstance(dsn, str) and '?' not in dsn:
                dsn = f"{dsn}?client_min_messages=error"
            elif isinstance(dsn, str):
                dsn = f"{dsn}&client_min_messages=error"
            return psycopg2.connect(dsn=dsn, connection_factory=connection_factory, **kwargs)
            
    except ImportError:
        # Fallback to normal connection if psycopg2 is not available
        import psycopg2
        return psycopg2.connect(dsn=dsn, connection_factory=connection_factory, **kwargs)

# Get database URL from environment and ensure proper encoding
_db_url = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost:5432/black_trade')
# Ensure DATABASE_URL is properly encoded as UTF-8 string
if isinstance(_db_url, bytes):
    _db_url = _db_url.decode('utf-8', errors='replace')
else:
    _db_url = str(_db_url)

# Modify DSN to suppress notices and set correct encoding/locale
# This is done before creating the engine to avoid encoding errors during connection
if sys.platform == 'win32' and 'postgresql' in _db_url.lower():
    # Add options to suppress notices/warnings and set locale to C (ASCII-safe)
    # URL encode: = becomes %3D, space becomes %20
    # Critical: lc_messages=C prevents encoding errors from PostgreSQL messages
    options_param = "options=-c%20client_min_messages%3Derror%20-c%20lc_messages%3DC%20-c%20client_encoding%3DUTF8"
    if '?' in _db_url:
        if 'options=' not in _db_url:
            DATABASE_URL = f"{_db_url}&{options_param}"
        else:
            DATABASE_URL = _db_url
    else:
        DATABASE_URL = f"{_db_url}?{options_param}"
else:
    DATABASE_URL = _db_url

# Create engine with explicit UTF-8 encoding
# Configure connect_args to handle encoding issues
connect_args = {
    "connect_timeout": 10,
    "application_name": "black_trade",
    "client_encoding": "UTF8",  # Explicitly set UTF-8 encoding
}

# On Windows, suppress notices and set locale to prevent encoding errors
# This MUST be set to prevent encoding errors during connection
if sys.platform == 'win32':
    # Add options to suppress warnings/notices and set locale to C (ASCII-safe)
    # Critical: lc_messages=C prevents encoding errors from PostgreSQL messages
    if 'options' not in connect_args:
        connect_args["options"] = "-c client_min_messages=error -c lc_messages=C -c client_encoding=UTF8"
    else:
        # Append to existing options
        existing = connect_args["options"]
        if 'lc_messages' not in existing:
            connect_args["options"] = f"{existing} -c lc_messages=C"
        if 'client_min_messages' not in existing:
            connect_args["options"] = f"{connect_args['options']} -c client_min_messages=error"
        if 'client_encoding' not in existing:
            connect_args["options"] = f"{connect_args['options']} -c client_encoding=UTF8"

# Create engine with custom connection creator for safe encoding handling
try:
    from sqlalchemy import event as sa_event
    
    # Create engine with custom connect function
    def safe_connect(dialect, conn_rec, cargs, cparams):
        """Create connection with safe encoding handling."""
        try:
            # Import here to avoid circular imports
            return create_safe_connection(*cargs, **cparams)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in safe_connect: {e}")
            raise
    
    # Note: We can't easily override the connection creator, so we'll use the event listener approach
    engine = create_engine(
        DATABASE_URL,
        poolclass=NullPool,  # Disable pooling for now, can enable later
        echo=os.getenv('DB_ECHO', 'false').lower() == 'true',
        connect_args=connect_args,
        # Ensure SQLAlchemy uses UTF-8 for all string operations
        execution_options={
            "autocommit": False
        },
        # Use psycopg2's text mode to avoid encoding issues
        pool_pre_ping=True,  # Verify connections before using
    )
except Exception as e:
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"Could not set up safe connection factory: {e}. Using default.")
    engine = create_engine(
        DATABASE_URL,
        poolclass=NullPool,
        echo=os.getenv('DB_ECHO', 'false').lower() == 'true',
        connect_args=connect_args,
        execution_options={"autocommit": False},
        pool_pre_ping=True,
    )


@event.listens_for(engine, "connect")
def set_utf8_encoding(dbapi_conn, connection_record):
    """Set UTF-8 encoding on connection for PostgreSQL."""
    if 'postgresql' in DATABASE_URL:
        try:
            # Set safe notice processor to handle encoding errors
            import psycopg2.extensions
            
            def safe_notice_handler(notice):
                """Handle PostgreSQL notices safely."""
                try:
                    # Only log if we can safely decode the message
                    if hasattr(notice, 'message_primary'):
                        msg = str(notice.message_primary)
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.debug(f"PostgreSQL notice: {msg}")
                except (UnicodeDecodeError, UnicodeError, AttributeError):
                    # Silently ignore encoding errors in notices
                    pass
            
            # Set the notice processor
            psycopg2.extensions.register_type(psycopg2.extensions.UNICODE, dbapi_conn)
            dbapi_conn.set_notice_handler(safe_notice_handler)
            
        except (ImportError, AttributeError):
            pass
        
        # Ensure UTF-8 encoding and locale are set on connection before any queries
        cursor = dbapi_conn.cursor()
        try:
            # Set locale to C (ASCII-safe) FIRST - this prevents encoding errors in messages
            cursor.execute("SET lc_messages TO 'C'")
            # Set client encoding to UTF8
            cursor.execute("SET client_encoding TO 'UTF8'")
            # Disable notices that might contain encoding issues
            cursor.execute("SET client_min_messages TO 'ERROR'")  # Only show errors, suppress warnings/notices
            cursor.execute("SET bytea_output TO 'hex'")  # Helps with binary data
            cursor.close()
            dbapi_conn.commit()
        except Exception as e:
            # If setting fails, log but continue
            import logging
            logging.getLogger(__name__).debug(f"Could not set UTF-8 encoding on connection: {e}")


@event.listens_for(engine, "before_cursor_execute", retval=True)
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Ensure UTF-8 encoding before executing any statement."""
    if 'postgresql' in DATABASE_URL:
        try:
            # Set encoding before each statement execution
            cursor.execute("SET client_encoding TO 'UTF8'")
        except Exception:
            pass
    return statement, parameters


@event.listens_for(engine, "handle_error")
def handle_encoding_error(exception_context):
    """Handle encoding errors gracefully."""
    exc = exception_context.original_exception
    if isinstance(exc, (UnicodeDecodeError, UnicodeError)):
        # Replace encoding error with a more informative error
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Encoding error in database operation: {exc}")
        # Convert to a generic database error instead of crashing
        from sqlalchemy.exc import DatabaseError
        exception_context.chained_exception = None
        exception_context.is_disconnect = False
    elif hasattr(exc, 'args') and len(exc.args) > 0:
        error_str = str(exc.args[0]) if exc.args[0] else ""
        if 'utf-8' in error_str.lower() or 'decode' in error_str.lower() or 'codec' in error_str.lower():
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Potential encoding error in database operation: {exc}")
            # Don't propagate encoding errors, handle them gracefully
            exception_context.is_disconnect = False

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency for FastAPI to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session() -> Session:
    """Get a database session without context manager (for repositories)."""
    return SessionLocal()


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """Context manager for database session."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def check_timescaledb_extension():
    """Check if TimescaleDB extension is available."""
    from sqlalchemy import text
    with db_session() as db:
        result = db.execute(text("SELECT * FROM pg_extension WHERE extname = 'timescaledb'"))
        return result.fetchone() is not None


def enable_timescaledb_hypertable():
    """Enable TimescaleDB hypertable for ohlcv_candles."""
    try:
        if not check_timescaledb_extension():
            raise RuntimeError("TimescaleDB extension not found. Install TimescaleDB first.")
        
        from sqlalchemy import text
        with db_session() as db:
            # Check if hypertable already exists
            result = db.execute(
                text("SELECT * FROM _timescaledb_catalog.hypertable WHERE table_name = 'ohlcv_candles'")
            )
            if result.fetchone() is None:
                db.execute(
                    text("SELECT create_hypertable('ohlcv_candles', 'timestamp', "
                    "chunk_time_interval => INTERVAL '7 days')")
                )
                db.commit()
    except (UnicodeDecodeError, UnicodeError) as e:
        # Re-raise as RuntimeError to match expected exception type
        raise RuntimeError(f"Encoding error enabling TimescaleDB: {e}")
    except Exception as e:
        # Re-raise to preserve original error
        raise

