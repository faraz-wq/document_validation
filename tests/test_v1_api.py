import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import UploadFile
from io import BytesIO
import json

from app.main import app
from app.schemas.schema_models import SchemaDefinition, FieldConfig, FieldType


class TestV1SchemasAPI:
    """Test cases for the v1 schema API endpoints"""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create a TestClient with authentication mocked
        self.client = TestClient(app)

    def test_create_schema_success(self):
        """Test successful schema creation"""
        # Valid schema data
        schema_data = {
            "schema_id": "test_schema",
            "schema_name": "Test Schema",
            "description": "A test schema",
            "fields": [
                {
                    "name": "name",
                    "type": "string",
                    "description": "A name field",
                    "required": True
                }
            ],
            "created_by": "test_user"
        }
        
        with patch('app.core.schema_registry.schema_registry') as mock_registry:
            mock_registry.register_schema.return_value = True
            
            response = self.client.post(
                "/v1/schemas", 
                json=schema_data,
                headers={"X-API-Key": "valid_api_key_123456"}
            )
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["message"] == "Schema created successfully"
            assert response_data["schema_id"] == "test_schema"

    def test_create_schema_no_api_key(self):
        """Test schema creation without API key"""
        schema_data = {
            "schema_id": "test_schema",
            "schema_name": "Test Schema",
            "description": "A test schema",
            "fields": [
                {
                    "name": "name",
                    "type": "string",
                    "description": "A name field"
                }
            ],
            "created_by": "test_user"
        }
        
        response = self.client.post("/v1/schemas", json=schema_data)
        assert response.status_code == 401  # Unauthorized

    def test_create_schema_duplicate_id(self):
        """Test creating a schema with duplicate ID"""
        schema_data = {
            "schema_id": "existing_schema",
            "schema_name": "Existing Schema",
            "description": "An existing schema",
            "fields": [
                {
                    "name": "name",
                    "type": "string",
                    "description": "A name field"
                }
            ],
            "created_by": "test_user"
        }
        
        with patch('app.core.schema_registry.schema_registry') as mock_registry:
            mock_registry.register_schema.return_value = False  # Simulate duplicate ID
            
            response = self.client.post(
                "/v1/schemas", 
                json=schema_data,
                headers={"X-API-Key": "valid_api_key_123456"}
            )
            
            assert response.status_code == 400  # Bad Request
            assert "Failed to register schema" in response.json()["detail"]

    @pytest.mark.parametrize("missing_field", ["schema_id", "schema_name", "fields"])
    def test_create_schema_missing_required_field(self, missing_field):
        """Test schema creation with missing required fields"""
        schema_data = {
            "schema_id": "test_schema",
            "schema_name": "Test Schema",
            "description": "A test schema",
            "fields": [
                {
                    "name": "name",
                    "type": "string",
                    "description": "A name field"
                }
            ],
            "created_by": "test_user"
        }
        
        # Remove the required field
        del schema_data[missing_field]
        
        response = self.client.post(
            "/v1/schemas", 
            json=schema_data,
            headers={"X-API-Key": "valid_api_key_123456"}
        )
        
        # Should return 422 for validation error
        assert response.status_code == 422

    def test_create_schema_with_validation_pattern(self):
        """Test schema creation with validation patterns"""
        schema_data = {
            "schema_id": "pattern_schema",
            "schema_name": "Pattern Schema",
            "description": "A schema with validation patterns",
            "fields": [
                {
                    "name": "email_field",
                    "type": "email",
                    "description": "An email field",
                    "validation_pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
                }
            ],
            "created_by": "test_user"
        }
        
        with patch('app.core.schema_registry.schema_registry') as mock_registry:
            mock_registry.register_schema.return_value = True
            
            response = self.client.post(
                "/v1/schemas", 
                json=schema_data,
                headers={"X-API-Key": "valid_api_key_123456"}
            )
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["message"] == "Schema created successfully"

    def test_get_schema_success(self):
        """Test getting a specific schema"""
        schema_def = SchemaDefinition(
            schema_id="test_schema",
            schema_name="Test Schema",
            description="A test schema",
            fields=[FieldConfig(name="name", type=FieldType.string, description="A name field")],
            created_by="test_user"
        )
        
        with patch('app.core.schema_registry.schema_registry') as mock_registry:
            mock_registry.get_schema.return_value = schema_def
            
            response = self.client.get(
                "/v1/schemas/test_schema",
                headers={"X-API-Key": "valid_api_key_123456"}
            )
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["schema_id"] == "test_schema"
            assert response_data["schema_name"] == "Test Schema"

    def test_get_schema_not_found(self):
        """Test getting a non-existent schema"""
        with patch('app.core.schema_registry.schema_registry') as mock_registry:
            mock_registry.get_schema.return_value = None  # Schema not found
            
            response = self.client.get(
                "/v1/schemas/nonexistent_schema",
                headers={"X-API-Key": "valid_api_key_123456"}
            )
            
            assert response.status_code == 404
            assert "Schema not found or access denied" in response.json()["detail"]

    def test_get_schema_no_api_key(self):
        """Test getting a schema without API key"""
        response = self.client.get("/v1/schemas/test_schema")
        assert response.status_code == 401  # Unauthorized

    def test_list_schemas_success(self):
        """Test listing schemas for a user"""
        schema_def = SchemaDefinition(
            schema_id="test_schema",
            schema_name="Test Schema",
            description="A test schema",
            fields=[FieldConfig(name="name", type=FieldType.string, description="A name field")],
            created_by="test_user"
        )
        
        with patch('app.core.schema_registry.schema_registry') as mock_registry:
            mock_registry.list_user_schemas.return_value = [schema_def]
            
            response = self.client.get(
                "/v1/schemas",
                headers={"X-API-Key": "valid_api_key_123456"}
            )
            
            assert response.status_code == 200
            response_data = response.json()
            assert "schemas" in response_data
            assert len(response_data["schemas"]) == 1

    def test_list_schemas_no_api_key(self):
        """Test listing schemas without API key"""
        response = self.client.get("/v1/schemas")
        assert response.status_code == 401  # Unauthorized

    def test_update_schema_success(self):
        """Test updating an existing schema"""
        updates = {
            "schema_name": "Updated Schema Name",
            "description": "Updated description"
        }
        
        with patch('app.core.schema_registry.schema_registry') as mock_registry:
            mock_registry.update_schema.return_value = True
            
            response = self.client.put(
                "/v1/schemas/test_schema", 
                json=updates,
                headers={"X-API-Key": "valid_api_key_123456"}
            )
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["message"] == "Schema updated successfully"

    def test_update_schema_not_found(self):
        """Test updating a non-existent schema"""
        updates = {
            "schema_name": "Updated Schema Name",
            "description": "Updated description"
        }
        
        with patch('app.core.schema_registry.schema_registry') as mock_registry:
            mock_registry.update_schema.return_value = False  # Schema not found or access denied
            
            response = self.client.put(
                "/v1/schemas/nonexistent_schema", 
                json=updates,
                headers={"X-API-Key": "valid_api_key_123456"}
            )
            
            assert response.status_code == 403  # Forbidden
            assert "Access denied or schema not found" in response.json()["detail"]

    def test_update_schema_no_api_key(self):
        """Test updating a schema without API key"""
        updates = {
            "schema_name": "Updated Schema Name",
            "description": "Updated description"
        }
        
        response = self.client.put("/v1/schemas/test_schema", json=updates)
        assert response.status_code == 401  # Unauthorized

    def test_delete_schema_success(self):
        """Test deleting a schema"""
        with patch('app.core.schema_registry.schema_registry') as mock_registry:
            mock_registry.delete_schema.return_value = True
            
            response = self.client.delete(
                "/v1/schemas/test_schema",
                headers={"X-API-Key": "valid_api_key_123456"}
            )
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["message"] == "Schema deleted successfully"

    def test_delete_schema_not_found(self):
        """Test deleting a non-existent schema"""
        with patch('app.core.schema_registry.schema_registry') as mock_registry:
            mock_registry.delete_schema.return_value = False  # Schema not found or access denied
            
            response = self.client.delete(
                "/v1/schemas/nonexistent_schema",
                headers={"X-API-Key": "valid_api_key_123456"}
            )
            
            assert response.status_code == 403  # Forbidden
            assert "Access denied or schema not found" in response.json()["detail"]

    def test_delete_schema_no_api_key(self):
        """Test deleting a schema without API key"""
        response = self.client.delete("/v1/schemas/test_schema")
        assert response.status_code == 401  # Unauthorized

    def test_extract_custom_success(self):
        """Test successful custom schema extraction"""
        # Prepare a mock schema
        mock_schema = SchemaDefinition(
            schema_id="test_schema",
            schema_name="Test Schema",
            description="A test schema",
            fields=[FieldConfig(name="name", type=FieldType.string, description="A name field")],
            created_by="any_user"  # This should match the user_id from the API key
        )

        # Mock the extractor
        mock_result = {
            "name": "Test Value",
            "source_documents": [{"document_title": "Test", "filename": "test.pdf"}],
            "citations": {},
            "bounding_boxes": {}
        }

        # We need to patch the schema registry imported in the main function
        # The extract_summary_custom function imports schema_registry locally as:
        # from app.core.schema_registry import schema_registry
        with patch('app.core.schema_registry.schema_registry') as mock_registry:
            # Mock schema registry to return the schema
            def mock_get_schema(schema_id, user_id):
                if schema_id == "test_schema":
                    return mock_schema
                return None

            mock_registry.get_schema.side_effect = mock_get_schema

            # Mock the ConfigurableExtractor's extract method to return mock results
            with patch('app.main.ConfigurableExtractor') as mock_extractor_class:
                # Create a mock extractor instance and mock its extract method
                mock_extractor_instance = Mock()
                mock_extractor_instance.extract.return_value = mock_result
                mock_extractor_class.return_value = mock_extractor_instance

                # Create test file
                test_file_content = b"test pdf content"
                files = [
                    ("files", ("test.pdf", test_file_content, "application/pdf"))
                ]

                response = self.client.post(
                    "/v1/extract-custom",
                    data={"schema_id": "test_schema"},
                    files=files,
                    headers={"X-API-Key": "valid_api_key_123456"}
                )

                assert response.status_code == 200
                response_data = response.json()
                assert response_data["name"] == "Test Value"

                # Ensure ConfigurableExtractor was instantiated and extract was called
                mock_extractor_class.assert_called_once()
                mock_extractor_instance.extract.assert_called_once()

    def test_extract_custom_schema_not_found(self):
        """Test custom extraction with non-existent schema"""
        with patch('app.core.schema_registry.schema_registry') as mock_registry:
            # Mock schema registry to always return None for nonexistent schema
            def mock_get_schema(schema_id, user_id):
                return None  # Schema not found

            mock_registry.get_schema.side_effect = mock_get_schema

            test_file_content = b"test pdf content"
            files = [
                ("files", ("test.pdf", test_file_content, "application/pdf"))
            ]

            response = self.client.post(
                "/v1/extract-custom",
                data={"schema_id": "nonexistent_schema"},
                files=files,
                headers={"X-API-Key": "valid_api_key_123456"}
            )

            assert response.status_code == 403  # Forbidden
            assert "Access denied to this schema" in response.json()["detail"]

    def test_extract_custom_no_api_key(self):
        """Test custom extraction without API key"""
        test_file_content = b"test pdf content"
        files = [
            ("files", ("test.pdf", test_file_content, "application/pdf"))
        ]
        
        response = self.client.post(
            "/v1/extract-custom",
            data={"schema_id": "test_schema"},
            files=files
        )
        assert response.status_code == 401  # Unauthorized

    def test_extract_custom_extractor_error(self):
        """Test custom extraction with extraction error"""
        # Prepare a mock schema
        mock_schema = SchemaDefinition(
            schema_id="test_schema",
            schema_name="Test Schema",
            description="A test schema",
            fields=[FieldConfig(name="name", type=FieldType.string, description="A name field")],
            created_by="any_user"  # This should match the user_id from the API key
        )

        with patch('app.core.schema_registry.schema_registry') as mock_registry:
            # Mock schema registry to return the schema for any user requesting it
            def mock_get_schema(schema_id, user_id):
                if schema_id == "test_schema":
                    return mock_schema
                return None

            mock_registry.get_schema.side_effect = mock_get_schema

            with patch('app.main.ConfigurableExtractor') as mock_extractor_class:
                # Create a mock extractor instance that raises an error
                mock_extractor_instance = Mock()
                mock_extractor_instance.extract.side_effect = Exception("Extraction error")
                mock_extractor_class.return_value = mock_extractor_instance

                test_file_content = b"test pdf content"
                files = [
                    ("files", ("test.pdf", test_file_content, "application/pdf"))
                ]

                response = self.client.post(
                    "/v1/extract-custom",
                    data={"schema_id": "test_schema"},
                    files=files,
                    headers={"X-API-Key": "valid_api_key_123456"}
                )

                assert response.status_code == 500  # Internal Server Error