"""
Database configuration and session management
Provides SQLAlchemy engine, session factory, and dependency injection for FastAPI
"""

import os
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from app.logging_config import get_logger

logger = get_logger(__name__)

# Database URL from environment variable or construct from components
DATABASE_URL = os.getenv("DATABASE_URL")

# If DATABASE_URL is not set, construct it from individual components
if not DATABASE_URL:
    db_user = os.getenv("DB_USER", "postgres")
    db_password = os.getenv("DB_PASSWORD", "postgres")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "postgres")
    
    # Construct the DATABASE_URL
    # Construct the DATABASE_URL
    # Check for Google Cloud SQL connection name (common in Cloud Run)
    instance_connection_name = os.getenv("INSTANCE_CONNECTION_NAME")
    
    if instance_connection_name:
        # Use Unix Socket for Cloud SQL
        # The socket path is typically /cloudsql/<INSTANCE_CONNECTION_NAME>
        socket_path = f"/cloudsql/{instance_connection_name}"
        DATABASE_URL = f"postgresql://{db_user}:{db_password}@/{db_name}?host={socket_path}"
        logger.info(f"Using Cloud SQL Unix Socket: {socket_path}")
    else:
        # Use TCP connection
        DATABASE_URL = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        logger.info(f"Using TCP Connection: {db_host}:{db_port}")

# Create SQLAlchemy engine with proper connection pooling
# Determine if we're in production or development
is_production = os.getenv("ENV") == "production"

# Configure pool settings based on environment
if is_production:
    # Production settings - larger pool for handling concurrent requests
    pool_size = int(os.getenv("DB_POOL_SIZE", "20"))
    max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "30"))
    pool_timeout = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    pool_recycle = int(os.getenv("DB_POOL_RECYCLE", "3600"))  # 1 hour
else:
    # Development settings - smaller pool but still use pooling
    pool_size = int(os.getenv("DB_POOL_SIZE", "5"))
    max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    pool_timeout = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    pool_recycle = int(os.getenv("DB_POOL_RECYCLE", "1800"))  # 30 minutes

logger.info(f"Configuring database pool: size={pool_size}, max_overflow={max_overflow}, timeout={pool_timeout}s")

engine = create_engine(
    DATABASE_URL,
    pool_size=pool_size,
    max_overflow=max_overflow,
    pool_timeout=pool_timeout,
    pool_recycle=pool_recycle,
    pool_pre_ping=True,  # Verify connections before use
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",  # Set SQL_ECHO=true to see SQL queries
    # Additional connection parameters for better performance
    connect_args={
        "connect_timeout": 10,
        "application_name": "document-validation-service"
    }
)

# Create session factory with optimized settings
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False  # Don't expire objects when session commits (better performance)
)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI endpoints to get a database session.
    
    Usage:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize the database by creating all tables.
    This should be called on application startup.
    
    Note: In production, use Alembic migrations instead.
    """
    from app.db.models import Base
    
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}", exc_info=True)
        raise


def check_db_connection() -> bool:
    """
    Check if the database connection is working.
    Returns True if connection is successful, False otherwise.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}", exc_info=True)
        return False


def get_db_context():
    """
    Context manager for database sessions with proper error handling.
    
    Usage:
        with get_db_context() as db:
            db.add(item)
            # Commit happens automatically
    """
    from contextlib import contextmanager
    
    @contextmanager
    def _context():
        db = SessionLocal()
        try:
            yield db
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Database error in context manager: {e}", exc_info=True)
            raise
        finally:
            db.close()
    
    return _context()


def get_pool_stats() -> dict:
    """
    Get connection pool statistics for monitoring.
    Returns dictionary with pool metrics.
    """
    try:
        if hasattr(engine, 'pool'):
            pool = engine.pool
            return {
                'pool_size': pool.size(),
                'checked_out_connections': pool.checkedout(),
                'overflow_connections': pool.overflow(),
                'total_connections': pool.size() + pool.overflow(),
                'status': 'healthy'
            }
        return {'status': 'no_pool_info'}
    except Exception as e:
        logger.error(f"Error getting pool stats: {e}")
        return {'status': 'error', 'error': str(e)}
