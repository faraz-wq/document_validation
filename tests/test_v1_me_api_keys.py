import pytest
from unittest.mock import Mock, patch
import json
from datetime import datetime
from fastapi.testclient import TestClient
from jose import jwt
import time

from app.main import app
from app.db.database import get_db
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


class TestV1MeApiKeysEndpoints:
    """Test cases for the new v1 me/api-keys endpoints."""

    def test_list_user_api_keys_unauthorized(self, test_client):
        """Test listing user API keys without valid token."""
        response = test_client.get("/v1/me/api-keys/")
        assert response.status_code == 401

    def test_create_user_api_key_unauthorized(self, test_client):
        """Test creating a user API key without valid token."""
        response = test_client.post("/v1/me/api-keys/", json={"description": "Test key"})
        assert response.status_code == 401

    def test_revoke_user_api_key_unauthorized(self, test_client):
        """Test revoking a user API key without valid token."""
        response = test_client.delete("/v1/me/api-keys/1")
        assert response.status_code == 401


class TestV1MeApiKeysIntegration:
    """Integration tests for the user API keys functionality."""

    def test_list_user_api_keys_empty(self, test_client, valid_jwt_token):
        """Test listing user API keys when no keys exist."""
        # Mock the get_current_user_from_jwt dependency
        mock_user = Mock()
        mock_user.id = 1
        mock_user.email = "test@example.com"
        mock_user.username = "testuser"
        mock_user.is_active = True
        
        app.dependency_overrides[get_current_user_from_jwt] = lambda: mock_user

        try:
            response = test_client.get(
                "/v1/me/api-keys/",
                headers={"Authorization": f"Bearer {valid_jwt_token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert isinstance(data["items"], list)
            assert len(data["items"]) == 0
        finally:
            app.dependency_overrides.clear()

    def test_create_user_api_key(self, test_client, valid_jwt_token):
        """Test creating a new user API key."""
        # Mock the get_current_user_from_jwt dependency
        mock_user = Mock()
        mock_user.id = 1
        mock_user.email = "test@example.com"
        mock_user.username = "testuser"
        mock_user.is_active = True
        
        app.dependency_overrides[get_current_user_from_jwt] = lambda: mock_user

        try:
            response = test_client.post(
                "/v1/me/api-keys/",
                json={"description": "Test API key for testing"},
                headers={"Authorization": f"Bearer {valid_jwt_token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "api_key" in data
            assert "id" in data
            assert "message" in data
            assert data["message"] == "API key created"
            assert data["api_key"].startswith("dv_")  # API keys start with dv_
            assert isinstance(data["id"], int)
        finally:
            app.dependency_overrides.clear()

    def test_create_user_api_key_without_description(self, test_client, valid_jwt_token):
        """Test creating a new user API key without providing a description."""
        # Mock the get_current_user_from_jwt dependency
        mock_user = Mock()
        mock_user.id = 1
        mock_user.email = "test@example.com"
        mock_user.username = "testuser"
        mock_user.is_active = True
        
        app.dependency_overrides[get_current_user_from_jwt] = lambda: mock_user

        try:
            response = test_client.post(
                "/v1/me/api-keys/",
                json={},  # No description provided
                headers={"Authorization": f"Bearer {valid_jwt_token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "api_key" in data
            assert "id" in data
            assert "message" in data
            assert data["message"] == "API key created"
        finally:
            app.dependency_overrides.clear()

    def test_list_user_api_keys_with_data(self, test_client, valid_jwt_token):
        """Test listing user API keys when keys exist."""
        from app.db.models import User, ApiKey
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool
        
        # Create test database with data
        test_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        models.Base.metadata.create_all(bind=test_engine)
        TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

        db = TestSessionLocal()
        
        # Create test user
        test_user = User(
            id=1,
            email="test@example.com",
            username="testuser",
            is_active=True
        )
        db.add(test_user)
        
        # Create API key for the test user
        api_key = ApiKey(
            id=1,
            key_hash="test_hash_123",
            owner_id=1,
            description="Test key",
            revoked=False,
            total_requests=5,
            total_errors=0,
            total_documents=2
        )
        db.add(api_key)
        
        # Create another API key for the same user
        api_key2 = ApiKey(
            id=2,
            key_hash="test_hash_456",
            owner_id=1,
            description="Another test key",
            revoked=False,
            total_requests=3,
            total_errors=1,
            total_documents=1
        )
        db.add(api_key2)
        
        # Create API key for different user (should not appear for user 1)
        other_user = User(
            id=2,
            email="other@example.com",
            username="otheruser",
            is_active=True
        )
        db.add(other_user)
        
        other_key = ApiKey(
            id=3,
            key_hash="test_hash_789",
            owner_id=2,
            description="Other user key",
            revoked=False,
            total_requests=0,
            total_errors=0,
            total_documents=0
        )
        db.add(other_key)
        
        db.commit()
        
        # Override database dependency
        def get_test_db():
            yield db
        
        app.dependency_overrides[get_db] = get_test_db
        
        mock_user = Mock()
        mock_user.id = 1  # Should only see their own keys
        mock_user.email = "test@example.com"
        mock_user.username = "testuser"
        mock_user.is_active = True
        
        app.dependency_overrides[get_current_user_from_jwt] = lambda: mock_user

        try:
            response = test_client.get(
                "/v1/me/api-keys/",
                headers={"Authorization": f"Bearer {valid_jwt_token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert isinstance(data["items"], list)
            
            # Should only return keys for user 1 (2 keys)
            assert len(data["items"]) == 2
            
            # Check that both keys are present and have correct properties
            key_ids = [item["id"] for item in data["items"]]
            assert 1 in key_ids
            assert 2 in key_ids
            assert 3 not in key_ids  # Key owned by other user should not appear
            
            # Check structure of returned items
            for item in data["items"]:
                assert "id" in item
                assert "description" in item
                assert "created_at" in item
                assert "revoked" in item
                assert "total_requests" in item
                assert "total_errors" in item
                assert "total_documents" in item
        finally:
            app.dependency_overrides.clear()
            db.close()

    def test_revoke_user_api_key_success(self, test_client, valid_jwt_token):
        """Test successfully revoking a user's API key."""
        from app.db.models import User, ApiKey
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool
        
        # Create test database with data
        test_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        models.Base.metadata.create_all(bind=test_engine)
        TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

        db = TestSessionLocal()
        
        # Create test user
        test_user = User(
            id=1,
            email="test@example.com",
            username="testuser",
            is_active=True
        )
        db.add(test_user)
        
        # Create API key for the test user
        api_key = ApiKey(
            id=5,
            key_hash="test_hash_123",
            owner_id=1,
            description="Test key to revoke",
            revoked=False,
            total_requests=5,
            total_errors=0,
            total_documents=2
        )
        db.add(api_key)
        
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
            response = test_client.delete(
                "/v1/me/api-keys/5",
                headers={"Authorization": f"Bearer {valid_jwt_token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            assert data["message"] == "API key revoked"
        finally:
            app.dependency_overrides.clear()
            db.close()

    def test_revoke_user_api_key_not_found(self, test_client, valid_jwt_token):
        """Test revoking an API key that doesn't exist or doesn't belong to the user."""
        from app.db.models import User
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool
        
        # Create test database with data
        test_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        models.Base.metadata.create_all(bind=test_engine)
        TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

        db = TestSessionLocal()
        
        # Create test user
        test_user = User(
            id=1,
            email="test@example.com",
            username="testuser",
            is_active=True
        )
        db.add(test_user)
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
            # Try to revoke key 99 which doesn't exist
            response = test_client.delete(
                "/v1/me/api-keys/99",
                headers={"Authorization": f"Bearer {valid_jwt_token}"}
            )
            
            # Should return 404 for non-existent key
            assert response.status_code == 404
            data = response.json()
            assert "detail" in data
            
            # Also test trying to revoke a key that belongs to another user
            # by setting up a scenario where the key exists but belongs to different user
        finally:
            app.dependency_overrides.clear()
            db.close()

    def test_revoke_user_api_key_access_control(self, test_client, valid_jwt_token):
        """Test that users can't revoke API keys that don't belong to them."""
        from app.db.models import User, ApiKey
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool
        
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
        user1 = User(
            id=1,
            email="user1@example.com",
            username="user1",
            is_active=True
        )
        user2 = User(
            id=2,
            email="user2@example.com",
            username="user2",
            is_active=True
        )
        db.add(user1)
        db.add(user2)
        
        # Create API key for user2 (user 1 should not be able to revoke this)
        api_key = ApiKey(
            id=10,
            key_hash="test_hash_123",
            owner_id=2,  # Owned by user 2
            description="User 2's key",
            revoked=False,
            total_requests=0,
            total_errors=0,
            total_documents=0
        )
        db.add(api_key)
        
        db.commit()
        
        # Override database dependency
        def get_test_db():
            yield db
        
        app.dependency_overrides[get_db] = get_test_db
        
        mock_user = Mock()  # Current user is user 1 (trying to revoke user 2's key)
        mock_user.id = 1
        mock_user.email = "user1@example.com"
        mock_user.username = "user1"
        mock_user.is_active = True
        
        app.dependency_overrides[get_current_user_from_jwt] = lambda: mock_user

        try:
            # User 1 tries to revoke user 2's API key - should return 404
            response = test_client.delete(
                "/v1/me/api-keys/10",
                headers={"Authorization": f"Bearer {valid_jwt_token}"}
            )
            
            # Should return 404 because the key doesn't belong to the user
            assert response.status_code == 404
            data = response.json()
            assert "detail" in data
            assert "not found" in data["detail"] or "not owned" in data["detail"]
        finally:
            app.dependency_overrides.clear()
            db.close()