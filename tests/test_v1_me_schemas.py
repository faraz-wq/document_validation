"""
Test for the new JWT-based schema management endpoints
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app
from app.schemas.schema_models import SchemaDefinition, FieldConfig, FieldType


def test_new_me_schemas_routes_exist():
    """Test that the new /v1/me/schemas routes are available"""
    # This test checks if our routes are registered by trying to access them with a mock

    client = TestClient(app)

    # Test list user schemas (should return 401 without auth)
    response = client.get("/v1/me/schemas")
    assert response.status_code == 401  # Unauthorized since no JWT token provided

    # Test create schema (should return 401 without auth)
    response = client.post("/v1/me/schemas", json={})
    assert response.status_code == 401  # Unauthorized since no JWT token provided


def test_list_user_schemas_success():
    """Test successful listing of user schemas"""
    from app.api.v1.deps import get_current_user_from_jwt

    client = TestClient(app)

    # Mock current user
    mock_user = MagicMock()
    mock_user.id = 123

    # Mock the get_current_user_from_jwt dependency
    app.dependency_overrides[get_current_user_from_jwt] = lambda: mock_user

    try:
        # Mock schema registry
        mock_schema = SchemaDefinition(
            schema_id="test_schema",
            schema_name="Test Schema",
            description="A test schema",
            fields=[FieldConfig(name="name", type=FieldType.string, description="A name field")],
            created_by="123"
        )

        with patch('app.api.v1.me_schemas.schema_registry') as mock_registry:
            mock_registry.list_user_schemas.return_value = [mock_schema]

            with patch('app.api.v1.me_schemas._get_schema_with_updated_at') as mock_get_timestamps:
                mock_get_timestamps.return_value = (None, None)  # No timestamps for this test

                response = client.get("/v1/me/schemas")

                assert response.status_code == 200
                data = response.json()
                assert "items" in data
                assert len(data["items"]) == 1
                assert data["items"][0]["schema_id"] == "test_schema"
                assert data["items"][0]["schema_name"] == "Test Schema"
                assert data["items"][0]["created_by"] == 123  # Should be converted to int
    finally:
        # Remove the override to avoid affecting other tests
        app.dependency_overrides.pop(get_current_user_from_jwt, None)


def test_get_user_schema_success():
    """Test successful retrieval of a specific user schema"""
    from app.api.v1.deps import get_current_user_from_jwt

    client = TestClient(app)

    # Mock current user
    mock_user = MagicMock()
    mock_user.id = 123

    # Mock the get_current_user_from_jwt dependency
    app.dependency_overrides[get_current_user_from_jwt] = lambda: mock_user

    try:
        # Mock schema
        mock_schema = SchemaDefinition(
            schema_id="test_schema",
            schema_name="Test Schema",
            description="A test schema",
            fields=[FieldConfig(name="name", type=FieldType.string, description="A name field")],
            created_by="123"
        )

        with patch('app.api.v1.me_schemas.schema_registry') as mock_registry:
            mock_registry.get_schema.return_value = mock_schema

            with patch('app.api.v1.me_schemas._get_schema_with_updated_at') as mock_get_timestamps:
                mock_get_timestamps.return_value = (None, None)  # No timestamps for this test

                response = client.get("/v1/me/schemas/test_schema")

                assert response.status_code == 200
                data = response.json()
                assert data["schema_id"] == "test_schema"
                assert data["schema_name"] == "Test Schema"
                assert data["created_by"] == 123  # Should be converted to int
    finally:
        # Remove the override to avoid affecting other tests
        app.dependency_overrides.pop(get_current_user_from_jwt, None)


def test_create_user_schema_success():
    """Test successful creation of a user schema"""
    from app.api.v1.deps import get_current_user_from_jwt

    client = TestClient(app)

    # Mock current user
    mock_user = MagicMock()
    mock_user.id = 123

    # Mock the get_current_user_from_jwt dependency
    app.dependency_overrides[get_current_user_from_jwt] = lambda: mock_user

    try:
        schema_data = {
            "schema_id": "new_schema",
            "schema_name": "New Schema",
            "description": "A new schema",
            "fields": [
                {
                    "name": "name",
                    "type": "string",
                    "description": "A name field",
                    "required": True
                }
            ]
        }

        with patch('app.api.v1.me_schemas.schema_registry') as mock_registry:
            mock_registry.register_schema.return_value = True

            response = client.post("/v1/me/schemas", json=schema_data)

            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Schema created successfully"
            assert data["schema_id"] == "new_schema"
    finally:
        # Remove the override to avoid affecting other tests
        app.dependency_overrides.pop(get_current_user_from_jwt, None)


def test_update_user_schema_success():
    """Test successful update of a user schema"""
    from app.api.v1.deps import get_current_user_from_jwt

    client = TestClient(app)

    # Mock current user
    mock_user = MagicMock()
    mock_user.id = 123

    # Mock the get_current_user_from_jwt dependency
    app.dependency_overrides[get_current_user_from_jwt] = lambda: mock_user

    try:
        update_data = {"schema_name": "Updated Schema Name"}

        with patch('app.api.v1.me_schemas.schema_registry') as mock_registry:
            mock_registry.update_schema.return_value = True

            response = client.put("/v1/me/schemas/test_schema", json=update_data)

            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "updated"
    finally:
        # Remove the override to avoid affecting other tests
        app.dependency_overrides.pop(get_current_user_from_jwt, None)


def test_delete_user_schema_success():
    """Test successful deletion of a user schema"""
    from app.api.v1.deps import get_current_user_from_jwt

    client = TestClient(app)

    # Mock current user
    mock_user = MagicMock()
    mock_user.id = 123

    # Mock the get_current_user_from_jwt dependency
    app.dependency_overrides[get_current_user_from_jwt] = lambda: mock_user

    try:
        with patch('app.api.v1.me_schemas.schema_registry') as mock_registry:
            mock_registry.delete_schema.return_value = True

            response = client.delete("/v1/me/schemas/test_schema")

            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "deleted"
    finally:
        # Remove the override to avoid affecting other tests
        app.dependency_overrides.pop(get_current_user_from_jwt, None)