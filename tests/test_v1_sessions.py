import pytest
from unittest.mock import Mock, patch
import json
from datetime import datetime
from fastapi.testclient import TestClient
from jose import jwt
import time
import os

from app.main import app
from app.db.database import get_db, engine, SessionLocal
from app.api.v1.deps import get_current_user_from_jwt

# Import models to ensure they're available for testing
from app.db import models

# Create an in-memory SQLite database for testing
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


# Create a test client with overrides for dependencies
@pytest.fixture
def test_client():
    """Create a test client with mocked dependencies."""
    # Create in-memory SQLite engine for testing
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    # Create tables in the test database
    models.Base.metadata.create_all(bind=test_engine)
    
    # Create a sessionmaker for the test database
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    
    # Override the database dependency
    def get_test_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = get_test_db
    
    client = TestClient(app)
    
    # Clean up the override after test
    yield client
    
    # Remove the override to avoid affecting other tests
    if get_db in app.dependency_overrides:
        del app.dependency_overrides[get_db]


@pytest.fixture
def valid_jwt_token():
    """Create a valid JWT token for testing."""
    # Create a simple JWT token for the test user
    secret_key = "test_secret"  # Same key should be used during testing
    algorithm = "HS256"
    payload = {
        "sub": "1",  # User ID as string
        "exp": int(time.time()) + 3600,  # 1 hour expiration
        "iat": int(time.time())
    }
    token = jwt.encode(payload, secret_key, algorithm=algorithm)
    
    # Patch the decode_token function to return our payload
    with patch("app.core.security.decode_token") as mock_decode:
        mock_decode.return_value = payload
        yield token


class TestV1SessionEndpoints:
    """Test cases for the new v1 session endpoints."""

    def test_list_user_sessions_unauthorized(self, test_client):
        """Test list user sessions without valid token."""
        response = test_client.get("/v1/me/sessions/")
        assert response.status_code == 401

    def test_get_user_session_unauthorized(self, test_client):
        """Test getting a user session without valid token."""
        response = test_client.get("/v1/me/sessions/test-session")
        assert response.status_code == 401

    def test_list_user_sessions_invalid_params(self, test_client, valid_jwt_token):
        """Test list user sessions with invalid parameters."""
        # Mock the get_current_user_from_jwt dependency
        mock_user = Mock()
        mock_user.id = 1
        mock_user.email = "test@example.com"
        mock_user.username = "testuser"
        mock_user.is_active = True
        
        app.dependency_overrides[get_current_user_from_jwt] = lambda: mock_user

        try:
            # Test limit too low
            response = test_client.get(
                "/v1/me/sessions/?limit=0",
                headers={"Authorization": f"Bearer {valid_jwt_token}"}
            )
            assert response.status_code == 422
            
            # Test limit too high
            response = test_client.get(
                "/v1/me/sessions/?limit=101",
                headers={"Authorization": f"Bearer {valid_jwt_token}"}
            )
            assert response.status_code == 422
            
            # Test negative offset
            response = test_client.get(
                "/v1/me/sessions/?offset=-1",
                headers={"Authorization": f"Bearer {valid_jwt_token}"}
            )
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()

    def test_get_user_session_invalid_session_id(self, test_client, valid_jwt_token):
        """Test getting a user session with an invalid session ID format."""
        # Mock the get_current_user_from_jwt dependency
        mock_user = Mock()
        mock_user.id = 1
        mock_user.email = "test@example.com"
        mock_user.username = "testuser"
        mock_user.is_active = True
        
        app.dependency_overrides[get_current_user_from_jwt] = lambda: mock_user

        try:
            # Try to access a session that doesn't exist
            response = test_client.get(
                "/v1/me/sessions/non-existent-session-id",
                headers={"Authorization": f"Bearer {valid_jwt_token}"}
            )
            # Should return 404 for non-existent session
            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()


# Integration test using the main application database
class TestV1SessionIntegration:
    """Integration tests that work with the existing application."""

    def test_endpoint_accessibility(self, test_client, valid_jwt_token):
        """Test that endpoints are accessible with proper auth."""
        # Mock the get_current_user_from_jwt dependency
        mock_user = Mock()
        mock_user.id = 1
        mock_user.email = "test@example.com"
        mock_user.username = "testuser"
        mock_user.is_active = True
        
        app.dependency_overrides[get_current_user_from_jwt] = lambda: mock_user

        try:
            # Test the list endpoint - should return 200 with empty results
            response = test_client.get(
                "/v1/me/sessions/",
                headers={"Authorization": f"Bearer {valid_jwt_token}"}
            )
            # Even if no sessions exist, it should return 200 with proper structure
            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert "total_count" in data
            assert isinstance(data["items"], list)
            assert isinstance(data["total_count"], int)
            
            # Should have no items when no sessions exist
            assert data["total_count"] == 0
            assert len(data["items"]) == 0
        finally:
            app.dependency_overrides.clear()

    def test_get_session_endpoint_structure(self, test_client, valid_jwt_token):
        """Test the structure of the get session endpoint."""
        # Mock the get_current_user_from_jwt dependency
        mock_user = Mock()
        mock_user.id = 1
        mock_user.email = "test@example.com"
        mock_user.username = "testuser"
        mock_user.is_active = True
        
        app.dependency_overrides[get_current_user_from_jwt] = lambda: mock_user

        try:
            # Test with a non-existent session - should return 404
            response = test_client.get(
                "/v1/me/sessions/definitely-not-exist",
                headers={"Authorization": f"Bearer {valid_jwt_token}"}
            )
            # Should return 404 for non-existent session
            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()


class TestV1SessionWithTestData:
    """Tests that create actual test data in the database."""

    def test_list_user_sessions_with_data(self, test_client, valid_jwt_token):
        """Test listing user sessions when sessions exist in the database."""
        from app.db.models import User, Session
        
        # Get the database session from the test client fixture
        # To do this, we'll create a session directly
        test_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        models.Base.metadata.create_all(bind=test_engine)
        TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

        # Create test data directly in the database
        db = TestSessionLocal()
        
        # Create test user
        test_user = User(
            id=1,
            email="test@example.com",
            username="testuser",
            is_active=True
        )
        db.add(test_user)
        
        # Create a session for the test user
        test_session = Session(
            session_id="test-session-123",
            application_type="Income Certificate",
            user_id=1,
            api_key_id=1,
            summary_json={"applicant_name": "Test User"},
            created_at=datetime.now(),
        )
        db.add(test_session)
        
        # Create a session for a different user
        other_user = User(
            id=2,
            email="other@example.com",
            username="otheruser",
            is_active=True
        )
        db.add(other_user)
        
        other_session = Session(
            session_id="test-session-456",
            application_type="OBC Certificate",
            user_id=2,
            api_key_id=2,
            summary_json={"applicant_name": "Other User"},
            created_at=datetime.now(),
        )
        db.add(other_session)
        
        db.commit()
        
        # Override the database dependency to use our test database with data
        def get_test_db():
            yield db
        
        app.dependency_overrides[get_db] = get_test_db
        
        mock_user = Mock()
        mock_user.id = 1  # This user should only see their own sessions
        mock_user.email = "test@example.com"
        mock_user.username = "testuser"
        mock_user.is_active = True
        
        app.dependency_overrides[get_current_user_from_jwt] = lambda: mock_user

        try:
            response = test_client.get(
                "/v1/me/sessions/",
                headers={"Authorization": f"Bearer {valid_jwt_token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["total_count"] == 1  # Only 1 session belongs to user 1
            assert len(data["items"]) == 1
            assert data["items"][0]["session_id"] == "test-session-123"
            assert data["items"][0]["application_type"] == "Income Certificate"
            assert data["items"][0]["file_count"] >= 0
        finally:
            app.dependency_overrides.clear()
            db.close()

    def test_get_specific_session(self, test_client, valid_jwt_token):
        """Test retrieving a specific session that belongs to the user."""
        from app.db.models import User, Session
        
        # Create test database with data
        test_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        models.Base.metadata.create_all(bind=test_engine)
        TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

        db = TestSessionLocal()
        
        # Create test user and session
        test_user = User(
            id=1,
            email="test@example.com",
            username="testuser", 
            is_active=True
        )
        db.add(test_user)
        
        test_session = Session(
            session_id="test-session-123",
            application_type="Income Certificate",
            user_id=1,
            api_key_id=1,
            summary_json={
                "applicant_name": "Test User",
                "source_documents": [{"document_title": "Test Doc", "filename": "test.pdf"}]
            },
            created_at=datetime.now(),
        )
        db.add(test_session)
        db.commit()
        
        # Override database dependency
        def get_test_db():
            yield db
        
        app.dependency_overrides[get_db] = get_test_db
        
        mock_user = Mock()
        mock_user.id = 1
        mock_user.email = "test@example.com"
        mock_user.username = "testuser"
        mock_user.is_active = True
        
        app.dependency_overrides[get_current_user_from_jwt] = lambda: mock_user

        try:
            response = test_client.get(
                "/v1/me/sessions/test-session-123",
                headers={"Authorization": f"Bearer {valid_jwt_token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == "test-session-123"
            assert data["application_type"] == "Income Certificate"
            assert data["summary"]["applicant_name"] == "Test User"
            assert "bounding_boxes" in data
            assert "citations" in data
            assert "documents" in data
        finally:
            app.dependency_overrides.clear()
            db.close()

    def test_session_access_control(self, test_client, valid_jwt_token):
        """Test that users can't access sessions that don't belong to them."""
        from app.db.models import User, Session
        
        # Create test database with data
        test_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        models.Base.metadata.create_all(bind=test_engine)
        TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

        db = TestSessionLocal()
        
        # Create two users
        user1 = User(id=1, email="user1@example.com", username="user1", is_active=True)
        user2 = User(id=2, email="user2@example.com", username="user2", is_active=True)
        db.add(user1)
        db.add(user2)
        
        # Create session owned by user2
        other_session = Session(
            session_id="user2-session",
            application_type="OBC Certificate",
            user_id=2,
            api_key_id=2,
            summary_json={"applicant_name": "User 2"},
            created_at=datetime.now(),
        )
        db.add(other_session)
        db.commit()
        
        # Override database dependency
        def get_test_db():
            yield db
        
        app.dependency_overrides[get_db] = get_test_db
        
        mock_user = Mock()  # Current user is user 1
        mock_user.id = 1
        mock_user.email = "user1@example.com"
        mock_user.username = "user1"
        mock_user.is_active = True
        
        app.dependency_overrides[get_current_user_from_jwt] = lambda: mock_user

        try:
            # User 1 tries to access user 2's session - should return 404
            response = test_client.get(
                "/v1/me/sessions/user2-session",
                headers={"Authorization": f"Bearer {valid_jwt_token}"}
            )
            
            # Should return 404 to prevent information leakage
            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()
            db.close()