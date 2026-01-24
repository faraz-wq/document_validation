import pytest
from unittest.mock import Mock, patch
import json
from datetime import datetime, timedelta, timezone
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

    # Create tables
    models.Base.metadata.create_all(bind=test_engine)

    # Create session
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    def override_get_db():
        try:
            db = TestSessionLocal()
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


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
    return token




class TestV1MeLogsEndpoints:
    """Test cases for the /v1/me/logs endpoint."""

    def test_get_user_logs_unauthorized(self, test_client):
        """Test that getting user logs requires authentication."""
        response = test_client.get("/v1/me/logs")
        assert response.status_code == 401
        assert "detail" in response.json()

    def test_get_user_logs_empty(self, test_client, valid_jwt_token):
        """Test getting user logs when user has no logs."""
        # Mock the get_current_user_from_jwt dependency
        mock_user = Mock()
        mock_user.id = 1
        mock_user.email = "test@example.com"
        mock_user.username = "testuser"
        mock_user.is_active = True

        app.dependency_overrides[get_current_user_from_jwt] = lambda: mock_user

        try:
            response = test_client.get(
                "/v1/me/logs",
                headers={"Authorization": f"Bearer {valid_jwt_token}"}
            )
            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert "total_count" in data
            assert data["items"] == []  # Empty list when no logs
            assert data["total_count"] == 0
        finally:
            app.dependency_overrides.clear()

    def test_get_user_logs_success(self, test_client, valid_jwt_token):
        """Test getting user logs successfully."""
        # Mock the get_current_user_from_jwt dependency
        mock_user = Mock()
        mock_user.id = 1
        mock_user.email = "test@example.com"
        mock_user.username = "testuser"
        mock_user.is_active = True

        app.dependency_overrides[get_current_user_from_jwt] = lambda: mock_user

        from app.db import get_db
        # Add some logs to the database using the test DB session
        for db in get_db():
            # Create API key for the user
            api_key = models.ApiKey(
                id=1,
                key_hash="test_key_hash",
                owner_id=1,  # Same user id as in mock
                description="Test API key"
            )
            db.add(api_key)

            # Create some request logs
            request_log1 = models.RequestLog(
                id=1,
                api_key_id=1,
                path="/v1/test",
                method="GET",
                status_code=200,
                processing_ms=100.5,
                client_ip="127.0.0.1",
                user_agent="test-agent"
            )
            db.add(request_log1)

            request_log2 = models.RequestLog(
                id=2,
                api_key_id=1,
                path="/v1/error",
                method="POST",
                status_code=400,
                processing_ms=200.3,
                client_ip="127.0.0.1",
                user_agent="test-agent",
                error_message="Bad request"
            )
            db.add(request_log2)

            db.commit()
            break

        try:
            response = test_client.get(
                "/v1/me/logs",
                headers={"Authorization": f"Bearer {valid_jwt_token}"}
            )
            assert response.status_code == 200

            data = response.json()
            assert "items" in data
            assert "total_count" in data
            # The service should return 2 logs for this user
            assert data["total_count"] >= 2  # Might be more based on other tests
            assert len(data["items"]) >= 2

            # Verify the logs belong to the user's API key
            for log in data["items"]:
                assert log["api_key_id"] == 1  # Belongs to user's key
        finally:
            app.dependency_overrides.clear()
    
    def test_get_user_logs_pagination(self, test_client, valid_jwt_token):
        """Test pagination parameters for user logs."""
        # Mock the get_current_user_from_jwt dependency
        mock_user = Mock()
        mock_user.id = 1
        mock_user.email = "test@example.com"
        mock_user.username = "testuser"
        mock_user.is_active = True

        app.dependency_overrides[get_current_user_from_jwt] = lambda: mock_user

        from app.db import get_db
        # Add some logs to the database using the test DB session
        for db in get_db():
            # Create API key for the user
            api_key = models.ApiKey(
                id=1,
                key_hash="test_key_hash",
                owner_id=1,  # Same user id as in mock
                description="Test API key"
            )
            db.add(api_key)

            # Create some request logs
            for i in range(5):  # Create multiple logs to test pagination
                request_log = models.RequestLog(
                    id=i+1,
                    api_key_id=1,
                    path=f"/v1/test{i}",
                    method="GET",
                    status_code=200,
                    processing_ms=100.0 + i * 10,
                    client_ip="127.0.0.1",
                    user_agent="test-agent"
                )
                db.add(request_log)

            db.commit()
            break

        try:
            # Test limit
            response = test_client.get(
                "/v1/me/logs?limit=2",
                headers={"Authorization": f"Bearer {valid_jwt_token}"}
            )
            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 2
            assert data["total_count"] == 5

            # Test offset
            response = test_client.get(
                "/v1/me/logs?limit=2&offset=2",
                headers={"Authorization": f"Bearer {valid_jwt_token}"}
            )
            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 2
            assert data["total_count"] == 5
        finally:
            app.dependency_overrides.clear()
    
    def test_get_user_logs_errors_only(self, test_client, valid_jwt_token):
        """Test filtering logs by errors_only."""
        # Mock the get_current_user_from_jwt dependency
        mock_user = Mock()
        mock_user.id = 1
        mock_user.email = "test@example.com"
        mock_user.username = "testuser"
        mock_user.is_active = True

        app.dependency_overrides[get_current_user_from_jwt] = lambda: mock_user

        from app.db import get_db
        # Add some logs to the database using the test DB session
        for db in get_db():
            # Create API key for the user
            api_key = models.ApiKey(
                id=1,
                key_hash="test_key_hash",
                owner_id=1,  # Same user id as in mock
                description="Test API key"
            )
            db.add(api_key)

            # Create request logs with both success and error
            success_log = models.RequestLog(
                id=1,
                api_key_id=1,
                path="/v1/test",
                method="GET",
                status_code=200,
                processing_ms=100.5,
                client_ip="127.0.0.1",
                user_agent="test-agent"
            )
            db.add(success_log)

            error_log = models.RequestLog(
                id=2,
                api_key_id=1,
                path="/v1/error",
                method="POST",
                status_code=400,
                processing_ms=200.3,
                client_ip="127.0.0.1",
                user_agent="test-agent",
                error_message="Bad request"
            )
            db.add(error_log)

            db.commit()
            break

        try:
            response = test_client.get(
                "/v1/me/logs?errors_only=true",
                headers={"Authorization": f"Bearer {valid_jwt_token}"}
            )
            assert response.status_code == 200

            data = response.json()
            # Should only return error logs
            for log in data["items"]:
                assert log["status_code"] >= 400
                assert log["error_message"] is not None
        finally:
            app.dependency_overrides.clear()
    
    def test_get_user_logs_min_processing_ms(self, test_client, valid_jwt_token):
        """Test filtering logs by minimum processing time."""
        # Mock the get_current_user_from_jwt dependency
        mock_user = Mock()
        mock_user.id = 1
        mock_user.email = "test@example.com"
        mock_user.username = "testuser"
        mock_user.is_active = True

        app.dependency_overrides[get_current_user_from_jwt] = lambda: mock_user

        from app.db import get_db
        # Add some logs to the database using the test DB session
        for db in get_db():
            # Create API key for the user
            api_key = models.ApiKey(
                id=1,
                key_hash="test_key_hash",
                owner_id=1,  # Same user id as in mock
                description="Test API key"
            )
            db.add(api_key)

            # Create request logs with different processing times
            fast_log = models.RequestLog(
                id=1,
                api_key_id=1,
                path="/v1/fast",
                method="GET",
                status_code=200,
                processing_ms=50.0,  # Fast log
                client_ip="127.0.0.1",
                user_agent="test-agent"
            )
            db.add(fast_log)

            slow_log = models.RequestLog(
                id=2,
                api_key_id=1,
                path="/v1/slow",
                method="GET",
                status_code=200,
                processing_ms=200.0,  # Slow log
                client_ip="127.0.0.1",
                user_agent="test-agent"
            )
            db.add(slow_log)

            db.commit()
            break

        try:
            response = test_client.get(
                "/v1/me/logs?min_processing_ms=150",
                headers={"Authorization": f"Bearer {valid_jwt_token}"}
            )
            assert response.status_code == 200

            data = response.json()
            # Should only return logs with processing time >= 150ms
            for log in data["items"]:
                assert log["processing_ms"] >= 150
        finally:
            app.dependency_overrides.clear()
    
    def test_get_user_logs_path_contains(self, test_client, valid_jwt_token):
        """Test filtering logs by path substring."""
        # Mock the get_current_user_from_jwt dependency
        mock_user = Mock()
        mock_user.id = 1
        mock_user.email = "test@example.com"
        mock_user.username = "testuser"
        mock_user.is_active = True

        app.dependency_overrides[get_current_user_from_jwt] = lambda: mock_user

        from app.db import get_db
        # Add some logs to the database using the test DB session
        for db in get_db():
            # Create API key for the user
            api_key = models.ApiKey(
                id=1,
                key_hash="test_key_hash",
                owner_id=1,  # Same user id as in mock
                description="Test API key"
            )
            db.add(api_key)

            # Create request logs with different paths
            test_log = models.RequestLog(
                id=1,
                api_key_id=1,
                path="/v1/test",
                method="GET",
                status_code=200,
                processing_ms=100.0,
                client_ip="127.0.0.1",
                user_agent="test-agent"
            )
            db.add(test_log)

            other_log = models.RequestLog(
                id=2,
                api_key_id=1,
                path="/v1/other",
                method="GET",
                status_code=200,
                processing_ms=100.0,
                client_ip="127.0.0.1",
                user_agent="test-agent"
            )
            db.add(other_log)

            db.commit()
            break

        try:
            response = test_client.get(
                "/v1/me/logs?path_contains=test",
                headers={"Authorization": f"Bearer {valid_jwt_token}"}
            )
            assert response.status_code == 200

            data = response.json()
            # Should find the logs that contain "test" in the path
            for log in data["items"]:
                assert "test" in log["path"].lower()
        finally:
            app.dependency_overrides.clear()
    
    def test_get_user_logs_multiple_filters(self, test_client, valid_jwt_token):
        """Test combining multiple filters."""
        # Mock the get_current_user_from_jwt dependency
        mock_user = Mock()
        mock_user.id = 1
        mock_user.email = "test@example.com"
        mock_user.username = "testuser"
        mock_user.is_active = True

        app.dependency_overrides[get_current_user_from_jwt] = lambda: mock_user

        from app.db import get_db
        # Add some logs to the database using the test DB session
        for db in get_db():
            # Create API key for the user
            api_key = models.ApiKey(
                id=1,
                key_hash="test_key_hash",
                owner_id=1,  # Same user id as in mock
                description="Test API key"
            )
            db.add(api_key)

            # Create various logs for testing multiple filters
            # Fast success log
            models.RequestLog(
                id=1,
                api_key_id=1,
                path="/v1/fast_success",
                method="GET",
                status_code=200,
                processing_ms=50.0,
                client_ip="127.0.0.1",
                user_agent="test-agent"
            )

            # Slow success log
            models.RequestLog(
                id=2,
                api_key_id=1,
                path="/v1/slow_success",
                method="GET",
                status_code=200,
                processing_ms=200.0,
                client_ip="127.0.0.1",
                user_agent="test-agent"
            )

            # Fast error log
            models.RequestLog(
                id=3,
                api_key_id=1,
                path="/v1/fast_error",
                method="POST",
                status_code=400,
                processing_ms=50.0,
                client_ip="127.0.0.1",
                user_agent="test-agent",
                error_message="Fast error"
            )

            # Slow error log - this one should match both filters
            models.RequestLog(
                id=4,
                api_key_id=1,
                path="/v1/slow_error",
                method="POST",
                status_code=500,
                processing_ms=200.0,
                client_ip="127.0.0.1",
                user_agent="test-agent",
                error_message="Slow error"
            )

            db.commit()
            break

        try:
            response = test_client.get(
                "/v1/me/logs?errors_only=true&min_processing_ms=150",
                headers={"Authorization": f"Bearer {valid_jwt_token}"}
            )
            assert response.status_code == 200

            data = response.json()
            # Should find logs that are errors AND have processing time >= 150ms
            for log in data["items"]:
                assert log["status_code"] >= 400  # errors_only
                assert log["processing_ms"] >= 150  # min_processing_ms
        finally:
            app.dependency_overrides.clear()
    
    def test_user_isolation(self, test_client, valid_jwt_token):
        """Test that users can only see their own logs."""
        # Mock the get_current_user_from_jwt dependency for first user
        main_user = Mock()
        main_user.id = 1
        main_user.email = "test@example.com"
        main_user.username = "testuser"
        main_user.is_active = True

        app.dependency_overrides[get_current_user_from_jwt] = lambda: main_user

        from app.db import get_db
        # Add logs for different users to the database using the test DB session
        for db in get_db():
            # Create API key for the main user
            main_api_key = models.ApiKey(
                id=1,
                key_hash="test_key_hash_main",
                owner_id=1,  # Main user ID
                description="Main user's API key"
            )
            db.add(main_api_key)

            # Create a log for main user
            main_log = models.RequestLog(
                id=1,
                api_key_id=1,
                path="/v1/main",
                method="GET",
                status_code=200,
                processing_ms=100.0,
                client_ip="127.0.0.1",
                user_agent="test-agent"
            )
            db.add(main_log)

            # Create API key for the other user
            other_api_key = models.ApiKey(
                id=2,
                key_hash="test_key_hash_other",
                owner_id=2,  # Other user ID
                description="Other user's API key"
            )
            db.add(other_api_key)

            # Create a log for other user
            other_log = models.RequestLog(
                id=2,
                api_key_id=2,
                path="/v1/other",
                method="GET",
                status_code=200,
                processing_ms=150.0,
                client_ip="127.0.0.1",
                user_agent="test-agent"
            )
            db.add(other_log)

            db.commit()
            break

        try:
            # First user should only see their logs (associated with user ID 1's keys)
            response = test_client.get(
                "/v1/me/logs",
                headers={"Authorization": f"Bearer {valid_jwt_token}"}
            )
            assert response.status_code == 200
            data = response.json()
            # Should only return logs from keys owned by user 1
            for log in data["items"]:
                assert log["api_key_id"] == 1  # Main user's key

            # Now test with second user's mock
            other_user = Mock()
            other_user.id = 2
            other_user.email = "other@example.com"
            other_user.username = "otheruser"
            other_user.is_active = True

            app.dependency_overrides[get_current_user_from_jwt] = lambda: other_user

            response = test_client.get(
                "/v1/me/logs",
                headers={"Authorization": f"Bearer {valid_jwt_token}"}
            )
            assert response.status_code == 200
            data = response.json()
            # Should only return logs from keys owned by user 2
            for log in data["items"]:
                assert log["api_key_id"] == 2  # Other user's key
        finally:
            app.dependency_overrides.clear()
    
    def test_invalid_parameters(self, test_client, valid_jwt_token):
        """Test validation of query parameters."""
        # Mock the get_current_user_from_jwt dependency
        mock_user = Mock()
        mock_user.id = 1
        mock_user.email = "test@example.com"
        mock_user.username = "testuser"
        mock_user.is_active = True

        app.dependency_overrides[get_current_user_from_jwt] = lambda: mock_user

        # No need to add any data for this test, just testing validation
        try:
            # Test invalid limit
            response = test_client.get(
                "/v1/me/logs?limit=0",
                headers={"Authorization": f"Bearer {valid_jwt_token}"}
            )
            assert response.status_code == 422

            # Test invalid limit (too high)
            response = test_client.get(
                "/v1/me/logs?limit=1001",
                headers={"Authorization": f"Bearer {valid_jwt_token}"}
            )
            assert response.status_code == 422

            # Test invalid offset
            response = test_client.get(
                "/v1/me/logs?offset=-1",
                headers={"Authorization": f"Bearer {valid_jwt_token}"}
            )
            assert response.status_code == 422

            # Test invalid min_processing_ms
            response = test_client.get(
                "/v1/me/logs?min_processing_ms=-1",
                headers={"Authorization": f"Bearer {valid_jwt_token}"}
            )
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()


class TestV1MeLogsIntegration:
    """Integration tests for the /v1/me/logs endpoint."""
    
    def test_get_user_logs_full_response_structure(self, test_client, valid_jwt_token):
        """Test that the response has the correct structure."""
        # Mock the get_current_user_from_jwt dependency
        mock_user = Mock()
        mock_user.id = 1
        mock_user.email = "test@example.com"
        mock_user.username = "testuser"
        mock_user.is_active = True

        app.dependency_overrides[get_current_user_from_jwt] = lambda: mock_user

        from app.db import get_db
        # Add a log to the database using the test DB session
        for db in get_db():
            # Create API key for the user
            api_key = models.ApiKey(
                id=1,
                key_hash="test_key_hash",
                owner_id=1,  # Same user id as in mock
                description="Test API key"
            )
            db.add(api_key)

            # Create a request log
            request_log = models.RequestLog(
                id=1,
                api_key_id=1,
                path="/v1/test",
                method="GET",
                status_code=200,
                processing_ms=100.5,
                client_ip="127.0.0.1",
                user_agent="test-agent"
            )
            db.add(request_log)

            db.commit()
            break

        try:
            response = test_client.get(
                "/v1/me/logs",
                headers={"Authorization": f"Bearer {valid_jwt_token}"}
            )
            assert response.status_code == 200

            data = response.json()

            # Check response structure
            assert "items" in data
            assert "total_count" in data
            assert isinstance(data["total_count"], int)
            assert isinstance(data["items"], list)

            # Check that items have the correct structure
            for log in data["items"]:
                assert "id" in log
                assert "api_key_id" in log
                assert "session_id" in log
                assert "method" in log
                assert "path" in log
                assert "status_code" in log
                assert "processing_ms" in log
                assert "timestamp" in log
                assert "client_ip" in log
                assert "user_agent" in log
                assert "error_message" in log

                # Check data types
                assert isinstance(log["id"], int)
                assert log["method"] in ["GET", "POST", "PUT", "DELETE", "PATCH"]
                assert isinstance(log["status_code"], int)
                assert isinstance(log["processing_ms"], (int, float))
                # timestamp should be in ISO format
                assert "T" in log["timestamp"]  # ISO format includes 'T'
        finally:
            app.dependency_overrides.clear()