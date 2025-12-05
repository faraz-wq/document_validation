import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json
import sqlite3

from app.core.schema_registry import SchemaRegistry
from app.schemas.schema_models import SchemaDefinition, FieldConfig, FieldType


class TestSchemaRegistry:
    """Test cases for the SchemaRegistry class"""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Use a temporary file for testing
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.registry = SchemaRegistry(db_path=self.temp_db.name)

    def teardown_method(self):
        """Clean up after each test method."""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def test_initialization(self):
        """Test schema registry initialization"""
        assert os.path.exists(self.temp_db.name)

    def test_init_database_creates_tables(self):
        """Test that database initialization creates the required tables"""
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()

        # Check that user_schemas table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_schemas';")
        assert cursor.fetchone() is not None

        # Check that schema_permissions table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_permissions';")
        assert cursor.fetchone() is not None

        conn.close()

    def test_register_schema(self):
        """Test registering a schema"""
        user_id = "test_user"
        schema_def = SchemaDefinition(
            schema_id="test_schema",
            schema_name="Test Schema",
            description="A test schema",
            fields=[
                FieldConfig(
                    name="name",
                    type=FieldType.string,
                    description="Person's name",
                    required=True
                )
            ],
            created_by=user_id
        )

        result = self.registry.register_schema(schema_def)
        assert result is True

        # Retrieve the schema back
        retrieved_schema = self.registry.get_schema("test_schema", user_id)
        assert retrieved_schema is not None
        assert retrieved_schema.schema_name == "Test Schema"
        assert len(retrieved_schema.fields) == 1
        assert retrieved_schema.fields[0].name == "name"

    def test_register_duplicate_schema(self):
        """Test registering a duplicate schema ID"""
        user_id = "test_user"
        schema_def = SchemaDefinition(
            schema_id="duplicate_schema",
            schema_name="Test Schema",
            description="A test schema",
            fields=[
                FieldConfig(
                    name="name",
                    type=FieldType.string,
                    description="Person's name",
                    required=True
                )
            ],
            created_by=user_id
        )

        # First registration should succeed
        result1 = self.registry.register_schema(schema_def)
        assert result1 is True

        # Second registration with same ID should fail
        result2 = self.registry.register_schema(schema_def)
        assert result2 is False

    def test_get_nonexistent_schema(self):
        """Test retrieving a non-existent schema"""
        schema = self.registry.get_schema("nonexistent_schema", "test_user")
        assert schema is None

    def test_get_schema_no_permission(self):
        """Test retrieving a schema without permission"""
        user_id = "test_user"
        another_user = "another_user"
        
        schema_def = SchemaDefinition(
            schema_id="permission_test_schema",
            schema_name="Permission Test Schema",
            description="A test schema",
            fields=[
                FieldConfig(
                    name="name",
                    type=FieldType.string,
                    description="Person's name",
                    required=True
                )
            ],
            created_by=user_id
        )

        # Register the schema
        result = self.registry.register_schema(schema_def)
        assert result is True

        # Try to access with different user (should fail)
        schema = self.registry.get_schema("permission_test_schema", another_user)
        assert schema is None

    def test_list_user_schemas(self):
        """Test listing schemas for a user"""
        user_id = "test_user"

        # Register a few schemas
        for i in range(3):
            schema_def = SchemaDefinition(
                schema_id=f"test_schema_{i}",
                schema_name=f"Test Schema {i}",
                description=f"A test schema {i}",
                fields=[
                    FieldConfig(
                        name="name",
                        type=FieldType.string,
                        description="Person's name",
                        required=True
                    )
                ],
                created_by=user_id
            )
            self.registry.register_schema(schema_def)

        schemas = self.registry.list_user_schemas(user_id)
        assert len(schemas) == 3

    def test_update_schema(self):
        """Test updating a schema"""
        user_id = "test_user"
        schema_def = SchemaDefinition(
            schema_id="update_test_schema",
            schema_name="Original Schema",
            description="Original description",
            fields=[
                FieldConfig(
                    name="name",
                    type=FieldType.string,
                    description="Person's name",
                    required=True
                )
            ],
            created_by=user_id
        )

        # Register the schema
        result = self.registry.register_schema(schema_def)
        assert result is True

        # Update the schema
        updates = {
            "schema_name": "Updated Schema",
            "description": "Updated description"
        }
        update_result = self.registry.update_schema("update_test_schema", user_id, updates)
        assert update_result is True

        # Verify the update
        updated_schema = self.registry.get_schema("update_test_schema", user_id)
        assert updated_schema.schema_name == "Updated Schema"
        assert updated_schema.description == "Updated description"

    def test_update_schema_no_permission(self):
        """Test updating a schema without permission"""
        user_id = "test_user"
        another_user = "another_user"
        
        schema_def = SchemaDefinition(
            schema_id="update_no_perm_schema",
            schema_name="Original Schema",
            description="Original description",
            fields=[
                FieldConfig(
                    name="name",
                    type=FieldType.string,
                    description="Person's name",
                    required=True
                )
            ],
            created_by=user_id
        )

        # Register the schema
        result = self.registry.register_schema(schema_def)
        assert result is True

        # Try to update with different user (should fail)
        updates = {
            "schema_name": "Updated Schema"
        }
        update_result = self.registry.update_schema("update_no_perm_schema", another_user, updates)
        assert update_result is False

    def test_delete_schema(self):
        """Test deleting a schema"""
        user_id = "test_user"
        schema_def = SchemaDefinition(
            schema_id="delete_test_schema",
            schema_name="Delete Test Schema",
            description="A schema for deletion test",
            fields=[
                FieldConfig(
                    name="name",
                    type=FieldType.string,
                    description="Person's name",
                    required=True
                )
            ],
            created_by=user_id
        )

        # Register the schema
        result = self.registry.register_schema(schema_def)
        assert result is True

        # Verify it exists
        schema = self.registry.get_schema("delete_test_schema", user_id)
        assert schema is not None

        # Delete the schema
        delete_result = self.registry.delete_schema("delete_test_schema", user_id)
        assert delete_result is True

        # Verify it's gone
        schema = self.registry.get_schema("delete_test_schema", user_id)
        assert schema is None

    def test_delete_schema_no_permission(self):
        """Test deleting a schema without permission"""
        user_id = "test_user"
        another_user = "another_user"
        
        schema_def = SchemaDefinition(
            schema_id="delete_no_perm_schema",
            schema_name="Delete Test Schema",
            description="A schema for deletion test",
            fields=[
                FieldConfig(
                    name="name",
                    type=FieldType.string,
                    description="Person's name",
                    required=True
                )
            ],
            created_by=user_id
        )

        # Register the schema
        result = self.registry.register_schema(schema_def)
        assert result is True

        # Try to delete with different user (should fail)
        delete_result = self.registry.delete_schema("delete_no_perm_schema", another_user)
        assert delete_result is False

        # Schema should still exist for original user
        schema = self.registry.get_schema("delete_no_perm_schema", user_id)
        assert schema is not None

    def test_register_schema_with_multiple_fields(self):
        """Test registering a schema with multiple fields"""
        user_id = "test_user"
        schema_def = SchemaDefinition(
            schema_id="multi_field_schema",
            schema_name="Multi Field Schema",
            description="A schema with multiple fields",
            fields=[
                FieldConfig(
                    name="name",
                    type=FieldType.string,
                    description="Person's name",
                    required=True
                ),
                FieldConfig(
                    name="age",
                    type=FieldType.integer,
                    description="Person's age",
                    required=False
                ),
                FieldConfig(
                    name="email",
                    type=FieldType.email,
                    description="Person's email",
                    required=True
                )
            ],
            created_by=user_id
        )

        result = self.registry.register_schema(schema_def)
        assert result is True

        # Retrieve and verify all fields
        retrieved_schema = self.registry.get_schema("multi_field_schema", user_id)
        assert retrieved_schema is not None
        assert len(retrieved_schema.fields) == 3
        
        field_names = [field.name for field in retrieved_schema.fields]
        assert "name" in field_names
        assert "age" in field_names
        assert "email" in field_names

    def test_register_schema_with_validation_pattern(self):
        """Test registering a schema with validation patterns"""
        user_id = "test_user"
        schema_def = SchemaDefinition(
            schema_id="pattern_schema",
            schema_name="Pattern Schema",
            description="A schema with validation patterns",
            fields=[
                FieldConfig(
                    name="phone",
                    type=FieldType.phone,
                    description="Phone number",
                    required=True,
                    validation_pattern=r"^\+?[1-9]\d{1,14}$"  # Basic phone pattern
                )
            ],
            created_by=user_id
        )

        result = self.registry.register_schema(schema_def)
        assert result is True

        # Retrieve and verify the validation pattern
        retrieved_schema = self.registry.get_schema("pattern_schema", user_id)
        assert retrieved_schema is not None
        assert retrieved_schema.fields[0].validation_pattern == r"^\+?[1-9]\d{1,14}$"

    def test_list_user_schemas_empty(self):
        """Test listing schemas for a user with no schemas"""
        schemas = self.registry.list_user_schemas("user_with_no_schemas")
        assert len(schemas) == 0

    def test_schema_fields_are_properly_stored_and_retrieved(self):
        """Test that field configurations are properly stored and retrieved"""
        user_id = "test_user"
        original_fields = [
            FieldConfig(
                name="string_field",
                type=FieldType.string,
                description="A string field",
                required=True
            ),
            FieldConfig(
                name="int_field",
                type=FieldType.integer,
                description="An integer field",
                required=False
            ),
            FieldConfig(
                name="email_field",
                type=FieldType.email,
                description="An email field",
                required=True
            )
        ]
        
        schema_def = SchemaDefinition(
            schema_id="field_storage_test",
            schema_name="Field Storage Test",
            description="Test field storage",
            fields=original_fields,
            created_by=user_id
        )

        # Register the schema
        result = self.registry.register_schema(schema_def)
        assert result is True

        # Retrieve the schema
        retrieved_schema = self.registry.get_schema("field_storage_test", user_id)
        assert retrieved_schema is not None
        
        # Verify all fields are preserved with correct properties
        assert len(retrieved_schema.fields) == len(original_fields)
        
        for original, retrieved in zip(original_fields, retrieved_schema.fields):
            assert original.name == retrieved.name
            assert original.type == retrieved.type
            assert original.description == retrieved.description
            assert original.required == retrieved.required