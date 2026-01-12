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
    DATABASE_URL = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    logger.info(f"Constructed DATABASE_URL from components: {db_user}@{db_host}:{db_port}/{db_name}")

# Create SQLAlchemy engine
# For development, we use NullPool to avoid connection issues with Docker restarts
# In production, you'd want to use a proper connection pool
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    poolclass=NullPool if os.getenv("ENV") == "development" else None,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",  # Set SQL_ECHO=true to see SQL queries
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


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
