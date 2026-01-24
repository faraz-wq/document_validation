import pytest
from pydantic import ValidationError

from app.schemas.schema_models import FieldType, FieldConfig, SchemaDefinition, SchemaTemplates


class TestSchemaModels:
    """Test cases for the schema model definitions"""

    def test_field_type_enum_values(self):
        """Test that FieldType enum has all expected values"""
        assert FieldType.string.value == "string"
        assert FieldType.integer.value == "integer"
        assert FieldType.float.value == "float"
        assert FieldType.boolean.value == "boolean"
        assert FieldType.date.value == "date"
        assert FieldType.email.value == "email"
        assert FieldType.phone.value == "phone"
        assert FieldType.address.value == "address"
        assert FieldType.nested.value == "nested"

        # Test that we can convert string values back to enum
        assert FieldType("string") == FieldType.string
        assert FieldType("integer") == FieldType.integer

    def test_field_config_model_required_fields(self):
        """Test FieldConfig model with required fields"""
        field_config = FieldConfig(
            name="test_field",
            type=FieldType.string,
            description="A test field"
        )

        assert field_config.name == "test_field"
        assert field_config.type == FieldType.string
        assert field_config.description == "A test field"
        assert field_config.required is True  # Default value

    def test_field_config_model_optional_fields(self):
        """Test FieldConfig model with optional fields"""
        field_config = FieldConfig(
            name="test_field",
            type=FieldType.string,
            description="A test field",
            required=False,
            validation_pattern=r"^[A-Za-z]+$",
            nested_schema_id="nested_schema"
        )

        assert field_config.name == "test_field"
        assert field_config.type == FieldType.string
        assert field_config.description == "A test field"
        assert field_config.required is False
        assert field_config.validation_pattern == r"^[A-Za-z]+$"
        assert field_config.nested_schema_id == "nested_schema"

    def test_field_config_model_validation(self):
        """Test FieldConfig model validation"""
        # Should work with valid data
        field_config = FieldConfig(
            name="valid_name",
            type=FieldType.string,
            description="Valid description"
        )
        assert field_config.name == "valid_name"

        # Should fail with invalid field type
        with pytest.raises(ValidationError):
            FieldConfig(
                name="test_field",
                type="invalid_type",  # This should be a FieldType enum value
                description="A test field"
            )

    def test_schema_definition_model_all_fields(self):
        """Test SchemaDefinition model with all fields"""
        field_config = FieldConfig(
            name="field1",
            type=FieldType.string,
            description="A field"
        )
        
        schema_def = SchemaDefinition(
            schema_id="test_schema",
            schema_name="Test Schema",
            description="A test schema description",
            fields=[field_config],
            created_by="test_user"
        )

        assert schema_def.schema_id == "test_schema"
        assert schema_def.schema_name == "Test Schema"
        assert schema_def.description == "A test schema description"
        assert len(schema_def.fields) == 1
        assert schema_def.created_by == "test_user"
        assert schema_def.created_at == ""  # Default value

    def test_schema_definition_model_with_created_at(self):
        """Test SchemaDefinition model with created_at specified"""
        field_config = FieldConfig(
            name="field1",
            type=FieldType.string,
            description="A field"
        )
        
        schema_def = SchemaDefinition(
            schema_id="test_schema",
            schema_name="Test Schema",
            description="A test schema description",
            fields=[field_config],
            created_by="test_user",
            created_at="2023-01-01T00:00:00Z"
        )

        assert schema_def.created_at == "2023-01-01T00:00:00Z"

    def test_schema_definition_model_validation(self):
        """Test SchemaDefinition model validation"""
        field_config = FieldConfig(
            name="field1",
            type=FieldType.string,
            description="A field"
        )

        # Should work with valid data
        schema_def = SchemaDefinition(
            schema_id="valid_schema",
            schema_name="Valid Schema",
            description="Valid description",
            fields=[field_config],
            created_by="test_user"
        )
        assert schema_def.schema_id == "valid_schema"

        # Should fail without required fields
        with pytest.raises(ValidationError):
            SchemaDefinition(
                # Missing required fields
            )

    def test_schema_definition_model_multiple_fields(self):
        """Test SchemaDefinition model with multiple fields"""
        fields = [
            FieldConfig(name="field1", type=FieldType.string, description="Field 1"),
            FieldConfig(name="field2", type=FieldType.integer, description="Field 2", required=False),
            FieldConfig(name="field3", type=FieldType.email, description="Field 3")
        ]
        
        schema_def = SchemaDefinition(
            schema_id="multi_field_schema",
            schema_name="Multi Field Schema",
            description="Schema with multiple fields",
            fields=fields,
            created_by="test_user"
        )

        assert len(schema_def.fields) == 3
        assert schema_def.fields[0].name == "field1"
        assert schema_def.fields[1].name == "field2"
        assert schema_def.fields[2].name == "field3"

    def test_schema_templates_invoice_schema(self):
        """Test SchemaTemplates INVOICE_SCHEMA structure"""
        invoice_schema = SchemaTemplates.INVOICE_SCHEMA

        assert invoice_schema["schema_id"] == "invoice_template"
        assert invoice_schema["schema_name"] == "Invoice"
        assert "fields" in invoice_schema
        assert len(invoice_schema["fields"]) == 4  # Should have 4 fields

        # Check that all required fields are present
        field_names = [field["name"] for field in invoice_schema["fields"]]
        assert "invoice_number" in field_names
        assert "invoice_date" in field_names
        assert "vendor_name" in field_names
        assert "total_amount" in field_names

    def test_schema_templates_employee_schema(self):
        """Test SchemaTemplates EMPLOYEE_SCHEMA structure"""
        employee_schema = SchemaTemplates.EMPLOYEE_SCHEMA

        assert employee_schema["schema_id"] == "employee_template"
        assert employee_schema["schema_name"] == "Employee Info"
        assert "fields" in employee_schema
        assert len(employee_schema["fields"]) == 5  # Should have 5 fields

        # Check that all required fields are present
        field_names = [field["name"] for field in employee_schema["fields"]]
        assert "employee_id" in field_names
        assert "name" in field_names
        assert "email" in field_names
        assert "department" in field_names
        assert "hire_date" in field_names

    def test_schema_templates_get_templates(self):
        """Test SchemaTemplates.get_templates method"""
        templates = SchemaTemplates.get_templates()

        assert "invoice" in templates
        assert "employee" in templates
        assert templates["invoice"] == SchemaTemplates.INVOICE_SCHEMA
        assert templates["employee"] == SchemaTemplates.EMPLOYEE_SCHEMA

    def test_field_config_with_validation_pattern(self):
        """Test FieldConfig with validation pattern"""
        field_config = FieldConfig(
            name="phone_field",
            type=FieldType.phone,
            description="Phone number field",
            validation_pattern=r"^\+?[1-9]\d{1,14}$"  # Basic phone pattern
        )

        assert field_config.validation_pattern == r"^\+?[1-9]\d{1,14}$"

    def test_field_config_with_nested_schema_id(self):
        """Test FieldConfig with nested schema ID"""
        field_config = FieldConfig(
            name="address_field",
            type=FieldType.nested,
            description="Address field with nested schema",
            nested_schema_id="address_schema"
        )

        assert field_config.nested_schema_id == "address_schema"
        assert field_config.type == FieldType.nested

    def test_field_config_optional_validation_pattern(self):
        """Test that validation pattern is optional"""
        field_config = FieldConfig(
            name="simple_field",
            type=FieldType.string,
            description="Simple field without validation"
            # No validation_pattern provided
        )

        assert field_config.validation_pattern is None

    def test_schema_definition_field_types_preserved(self):
        """Test that field types are preserved in schema definition"""
        fields = [
            FieldConfig(name="string_field", type=FieldType.string, description="String field"),
            FieldConfig(name="int_field", type=FieldType.integer, description="Int field"),
            FieldConfig(name="float_field", type=FieldType.float, description="Float field"),
            FieldConfig(name="bool_field", type=FieldType.boolean, description="Bool field"),
            FieldConfig(name="date_field", type=FieldType.date, description="Date field"),
            FieldConfig(name="email_field", type=FieldType.email, description="Email field"),
            FieldConfig(name="phone_field", type=FieldType.phone, description="Phone field"),
            FieldConfig(name="address_field", type=FieldType.address, description="Address field"),
        ]
        
        schema_def = SchemaDefinition(
            schema_id="type_preservation_test",
            schema_name="Type Preservation Test",
            description="Test type preservation",
            fields=fields,
            created_by="test_user"
        )

        # Check that types are preserved
        field_types = [field.type for field in schema_def.fields]
        expected_types = [FieldType.string, FieldType.integer, FieldType.float, 
                         FieldType.boolean, FieldType.date, FieldType.email, 
                         FieldType.phone, FieldType.address]
        
        assert field_types == expected_types

    def test_schema_templates_immutability(self):
        """Test that schema templates are not accidentally modified"""
        # Get the original template
        original_invoice = SchemaTemplates.INVOICE_SCHEMA
        original_employee = SchemaTemplates.EMPLOYEE_SCHEMA

        # Get templates again
        templates = SchemaTemplates.get_templates()

        # They should be the same
        assert templates["invoice"] == original_invoice
        assert templates["employee"] == original_employee