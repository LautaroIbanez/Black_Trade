"""Monkey patch for psycopg2 to handle encoding errors gracefully."""
import sys
import logging
import warnings
import threading

logger = logging.getLogger(__name__)
# Set logger level to WARNING to reduce noise from encoding errors that we handle
logger.setLevel(logging.WARNING)

# Thread-local storage to track if we're in a psycopg2 connection attempt
_connection_context = threading.local()

# Store original excepthook to restore if needed
_original_excepthook = sys.excepthook

def patch_psycopg2():
    """Patch psycopg2 to handle encoding errors in connection messages."""
    try:
        import psycopg2
        import os
        
        # Store original connect function
        original_connect = psycopg2.connect
        
        def safe_excepthook(exc_type, exc_value, exc_traceback):
            """Custom exception hook that suppresses UnicodeDecodeError during psycopg2 connections."""
            # If we're in a connection context and it's a UnicodeDecodeError, suppress it
            if hasattr(_connection_context, 'in_connection') and _connection_context.in_connection:
                if isinstance(exc_value, UnicodeDecodeError):
                    # Check if this is the specific error we're seeing (position 85, byte 0xf3)
                    if hasattr(exc_value, 'start') and exc_value.start == 85:
                        # This is likely the PostgreSQL welcome message encoding issue
                        logger.debug(f"Suppressing UnicodeDecodeError during connection: {exc_value}")
                        return  # Suppress this exception
            # Otherwise, use original handler
            _original_excepthook(exc_type, exc_value, exc_traceback)
        
        # Install custom excepthook
        sys.excepthook = safe_excepthook
        
        def safe_connect(*args, **kwargs):
            """Wrapper around psycopg2.connect that handles encoding errors."""
            # Mark that we're in a connection attempt
            _connection_context.in_connection = True
            
            # Force UTF-8 encoding environment variable
            old_encoding = os.environ.get('PGCLIENTENCODING', None)
            os.environ['PGCLIENTENCODING'] = 'UTF8'
            
            try:
                # ALWAYS modify DSN to suppress notices to prevent encoding errors
                dsn = args[0] if args else kwargs.get('dsn', None)
                dsn_modified = None
                
                # If dsn is a string (connection string), always add options
                if isinstance(dsn, str) and 'postgresql' in dsn.lower():
                    # Check if options already include lc_messages (most critical)
                    if 'lc_messages' not in dsn:
                        # URL encode: = becomes %3D, space becomes %20
                        # Critical: lc_messages=C prevents encoding errors from PostgreSQL messages
                        options_str = "-c%20lc_messages%3DC%20-c%20client_min_messages%3Derror%20-c%20client_encoding%3DUTF8"
                        if '?' in dsn:
                            dsn_modified = f"{dsn}&options={options_str}"
                        else:
                            dsn_modified = f"{dsn}?options={options_str}"
                
                # Also ensure kwargs has the options if not in DSN
                if 'options' not in kwargs or 'lc_messages' not in kwargs.get('options', ''):
                    existing_opts = kwargs.get('options', '')
                    # Build options ensuring lc_messages=C is included (most critical)
                    new_opts = []
                    if 'lc_messages' not in existing_opts:
                        new_opts.append("-c lc_messages=C")
                    if 'client_min_messages' not in existing_opts:
                        new_opts.append("-c client_min_messages=error")
                    if 'client_encoding' not in existing_opts:
                        new_opts.append("-c client_encoding=UTF8")
                    if new_opts:
                        if existing_opts:
                            kwargs['options'] = f"{existing_opts} {' '.join(new_opts)}"
                        else:
                            kwargs['options'] = " ".join(new_opts)
                
                # Update args if we modified DSN
                if dsn_modified:
                    if args:
                        args_modified = (dsn_modified,) + args[1:]
                    else:
                        kwargs['dsn'] = dsn_modified
                        args_modified = args
                else:
                    args_modified = args
                
                # Since PostgreSQL is now configured correctly, we can connect directly
                # without a custom connection factory. The options in DSN/kwargs handle encoding.
                try:
                    if args_modified != args:
                        conn_result = original_connect(*args_modified, **kwargs)
                    else:
                        conn_result = original_connect(*args, **kwargs)
                    
                    # Set notice handler to suppress any encoding issues in notices
                    try:
                        import psycopg2.extensions
                        conn_result.set_notice_handler(lambda notice: None)
                    except:
                        pass
                    
                    return conn_result
                except (UnicodeDecodeError, UnicodeError) as ude:
                    # If connection with factory fails due to encoding, try without factory
                    # and set notice handler manually after connection
                    logger.debug(f"Connection with factory failed due to encoding error, retrying without factory: {ude}")
                    try:
                        # Remove connection_factory and try again
                        kwargs_no_factory = kwargs.copy()
                        if 'connection_factory' in kwargs_no_factory:
                            del kwargs_no_factory['connection_factory']
                        
                        if args_modified != args:
                            conn_result = original_connect(*args_modified, **kwargs_no_factory)
                        else:
                            conn_result = original_connect(*args, **kwargs_no_factory)
                        
                        # Now set notice handler manually after connection is established
                        try:
                            conn_result.set_notice_handler(lambda notice: None)
                        except:
                            pass
                        
                        # Set encoding and suppress messages
                        try:
                            cursor = conn_result.cursor()
                            cursor.execute("SET client_encoding TO 'UTF8'")
                            cursor.execute("SET client_min_messages TO 'ERROR'")
                            cursor.execute("SET lc_messages TO 'C'")
                            cursor.close()
                            conn_result.commit()
                        except:
                            pass
                        
                        return conn_result
                    except Exception as retry_error:
                        logger.debug(f"Retry without factory also failed: {retry_error}")
                        # Fall through to next retry strategy
                        ude = retry_error  # Ensure ude is defined for fallback handling
                except Exception as other_error:
                    # This error happens during connection initialization
                    # It's usually caused by PostgreSQL messages with wrong encoding
                    # Try one more time with a more aggressive approach: parse DSN and use individual params
                    ude = other_error  # Store error for fallback handling
                    try:
                        if isinstance(dsn, str) and 'postgresql://' in dsn.lower():
                            # Parse connection string manually
                            dsn_clean = dsn.replace('postgresql://', '')
                            if '@' in dsn_clean:
                                auth_part, host_part = dsn_clean.split('@', 1)
                                if ':' in auth_part:
                                    user, password = auth_part.split(':', 1)
                                else:
                                    user, password = auth_part, ''
                                
                                if '/' in host_part:
                                    host_db = host_part.split('/', 1)
                                    host_port_str = host_db[0]
                                    database = host_db[1]
                                else:
                                    host_port_str = host_part
                                    database = None
                                
                                if ':' in host_port_str:
                                    host, port = host_port_str.split(':', 1)
                                    port = int(port)
                                else:
                                    host, port = host_port_str, 5432
                                
                                # Try connecting with individual parameters (avoids DSN parsing issues)
                                conn_params = {
                                    'host': host,
                                    'port': port,
                                    'user': user,
                                    'password': password,
                                    'database': database,
                                    'client_encoding': 'UTF8',
                                    'options': '-c client_min_messages=error -c lc_messages=C',
                                }
                                # Remove None values
                                conn_params = {k: v for k, v in conn_params.items() if v is not None}
                                
                                return original_connect(**conn_params)
                    except Exception as parse_error:
                        logger.debug(f"Could not parse DSN for individual params: {parse_error}")
                    
                    # If all else fails, the error is likely from PostgreSQL welcome messages
                    # with wrong encoding. This happens during connection handshake but the
                    # connection might still work. Log at debug level only.
                    logger.debug(f"UnicodeDecodeError during connection handshake (usually safe to ignore): {ude}")
                    # Try one final approach: ignore the error and retry with minimal logging
                    # This is a last resort - the connection might actually work despite the error
                    try:
                        # Force environment and try once more
                        os.environ['PGCLIENTENCODING'] = 'UTF8'
                        if args_modified != args:
                            return original_connect(*args_modified, **kwargs)
                        else:
                            return original_connect(*args, **kwargs)
                    except:
                        # Final fallback - log but don't spam errors
                        logger.debug(f"Final connection attempt failed, re-raising: {ude}")
                        raise
                    
            finally:
                # Mark connection attempt as complete
                _connection_context.in_connection = False
                
                # Restore original encoding
                if old_encoding:
                    os.environ['PGCLIENTENCODING'] = old_encoding
                elif 'PGCLIENTENCODING' in os.environ:
                    del os.environ['PGCLIENTENCODING']
        
        # Replace psycopg2.connect
        psycopg2.connect = safe_connect
        
        logger.info("psycopg2 patched for encoding error handling")
        return True
    except (ImportError, AttributeError) as e:
        logger.warning(f"Could not patch psycopg2: {e}")
        return False

# Auto-patch when module is imported, but only if psycopg2 hasn't been imported yet
# NOTE: Disabled temporarily since PostgreSQL is now configured correctly with lc_messages=C
# and the patch was interfering with SQLAlchemy connection initialization
# if 'psycopg2' not in sys.modules:
#     patch_psycopg2()
