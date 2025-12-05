"""
Database initialization script
Creates initial admin user and sets up the database
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.db import init_db, check_db_connection, SessionLocal
from app.utils.auth import create_user, create_api_key
from app.logging_config import get_logger

logger = get_logger(__name__)


def init_database():
    """Initialize the database and create tables"""
    logger.info("Initializing database...")
    
    # Check connection
    if not check_db_connection():
        logger.error("Failed to connect to database")
        return False
    
    # Create tables
    try:
        init_db()
        logger.info("Database tables created successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        return False


def create_admin_user(email: str, username: str):
    """Create an admin user and return their API key"""
    db = SessionLocal()
    try:
        # Check if admin already exists
        from app.db import User
        existing_admin = db.query(User).filter(User.is_admin == True).first()
        
        if existing_admin:
            logger.info(f"Admin user already exists: {existing_admin.username}")
            return None
        
        # Create admin user
        admin_user = create_user(db, email, username, is_admin=True)
        logger.info(f"Created admin user: {username}")
        
        # Create API key
        api_key = create_api_key(db, admin_user.id, "Admin API key")
        logger.info(f"Created API key for admin user")
        
        return api_key
        
    except Exception as e:
        logger.error(f"Failed to create admin user: {e}", exc_info=True)
        return None
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Document Validation Service - Database Initialization")
    print("=" * 60)
    print()
    
    # Initialize database
    if not init_database():
        print("❌ Database initialization failed!")
        sys.exit(1)
    
    print("✅ Database initialized successfully")
    print()
    
    # Create admin user
    print("Creating admin user...")
    admin_email = input("Enter admin email (default: admin@example.com): ").strip() or "admin@example.com"
    admin_username = input("Enter admin username (default: admin): ").strip() or "admin"
    
    api_key = create_admin_user(admin_email, admin_username)
    
    if api_key:
        print()
        print("=" * 60)
        print("✅ Admin user created successfully!")
        print("=" * 60)
        print(f"Email: {admin_email}")
        print(f"Username: {admin_username}")
        print(f"API Key: {api_key}")
        print()
        print("⚠️  IMPORTANT: Save this API key securely!")
        print("   You will need it to access admin endpoints.")
        print("=" * 60)
    else:
        print("ℹ️  Admin user already exists or creation skipped")
    
    print()
    print("Database initialization complete!")
