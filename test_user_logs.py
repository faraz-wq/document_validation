"""
Test script to verify the user logs functionality
"""

import os
import sys
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.models import Base, User, ApiKey, RequestLog
from app.services.user_logs import get_user_logs, UserLogFilters

# Add the project root to the path so imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_user_logs_service():
    # Use SQLite for testing
    DATABASE_URL = "sqlite:///./test_user_logs.db"
    engine = create_engine(DATABASE_URL, echo=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Create a test user and API key
    db = SessionLocal()

    try:
        # Create a test user
        user = User(
            email="testuser@example.com",
            username="testuser",
            is_active=True,
            is_admin=False
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Create a test API key for the user
        api_key = ApiKey(
            key_hash="test_hash_12345",
            owner_id=user.id,
            description="Test API key"
        )
        db.add(api_key)
        db.commit()
        db.refresh(api_key)

        # Create some test request logs
        log1 = RequestLog(
            api_key_id=api_key.id,
            path="/v1/test",
            method="GET",
            status_code=200,
            processing_ms=100.5,
            client_ip="127.0.0.1",
            user_agent="test-agent"
        )
        db.add(log1)

        log2 = RequestLog(
            api_key_id=api_key.id,
            path="/v1/test-error",
            method="POST",
            status_code=400,
            processing_ms=200.3,
            client_ip="127.0.0.1",
            user_agent="test-agent",
            error_message="Bad request"
        )
        db.add(log2)

        db.commit()

        print(f"Created user: {user.id}")
        print(f"Created API key: {api_key.id}")
        print(f"Created logs: {log1.id}, {log2.id}")

        # Test the service function
        filters = UserLogFilters()
        result = get_user_logs(db, user.id, filters)

        print(f"Total logs for user: {result.total_count}")
        print(f"Returned logs: {len(result.items)}")

        for log in result.items:
            print(f"  - {log.method} {log.path} - {log.status_code} - {log.processing_ms}ms")

        # Test with filters
        filters.errors_only = True
        result_errors = get_user_logs(db, user.id, filters)

        print(f"\nFiltered logs (errors only): {result_errors.total_count}")
        for log in result_errors.items:
            print(f"  - {log.method} {log.path} - {log.status_code} - {log.processing_ms}ms (Error: {log.error_message})")

        # Clean up - delete the test data
        db.delete(log1)
        db.delete(log2)
        db.delete(api_key)
        db.delete(user)
        db.commit()

        print("\nTest completed successfully!")

    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_user_logs_service()