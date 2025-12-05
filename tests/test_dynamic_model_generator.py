import pytest
from pydantic import ValidationError

from app.core.dynamic_model_generator import DynamicModelGenerator
from app.schemas.schema_models import FieldConfig, FieldType
from app.models import SourceDocument, BoundingBox


class TestDynamicModelGenerator:
    """Test cases for the DynamicModelGenerator class"""

    def test_create_model_from_schema_basic(self):
        """Test creating a dynamic model from a basic schema"""
        fields = [
            FieldConfig(
                name="name",
                type=FieldType.string,
                description="Person's name",
                required=True
            )
        ]

        dynamic_model = DynamicModelGenerator.create_model_from_schema(fields, "test_schema")

        # Create an instance of the dynamic model
        instance = dynamic_model(
            name="John Doe",
            source_documents=[],
            citations={},
            bounding_boxes={}
        )

        assert instance.name == "John Doe"

    def test_create_model_from_schema_multiple_fields(self):
        """Test creating a dynamic model with multiple fields"""
        fields = [
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
        ]

        dynamic_model = DynamicModelGenerator.create_model_from_schema(fields, "multi_field_schema")

        # Create an instance of the dynamic model
        instance = dynamic_model(
            name="John Doe",
            age=30,
            email="john@example.com",
            source_documents=[],
            citations={},
            bounding_boxes={}
        )

        assert instance.name == "John Doe"
        assert instance.age == 30
        assert instance.email == "john@example.com"

    def test_create_model_from_schema_optional_fields(self):
        """Test creating a dynamic model with optional fields"""
        fields = [
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
                required=False  # Optional field
            )
        ]

        dynamic_model = DynamicModelGenerator.create_model_from_schema(fields, "optional_field_schema")

        # Create an instance without the optional field
        instance = dynamic_model(
            name="John Doe",
            source_documents=[],
            citations={},
            bounding_boxes={}
        )

        assert instance.name == "John Doe"
        assert instance.age is None  # Optional field should be None

    def test_create_model_from_schema_with_validation_pattern(self):
        """Test creating a dynamic model with validation patterns"""
        fields = [
            FieldConfig(
                name="phone",
                type=FieldType.phone,
                description="Phone number",
                required=True,
                validation_pattern=r"^\+?[1-9]\d{1,14}$"  # Basic phone pattern
            )
        ]

        dynamic_model = DynamicModelGenerator.create_model_from_schema(fields, "phone_schema")

        # Creating with valid phone should work
        instance = dynamic_model(
            phone="+1234567890",
            source_documents=[],
            citations={},
            bounding_boxes={}
        )
        assert instance.phone == "+1234567890"

    def test_get_field_type_mapping(self):
        """Test field type mapping"""
        # Test all field type mappings
        assert DynamicModelGenerator.get_field_type(FieldType.string) == str
        assert DynamicModelGenerator.get_field_type(FieldType.integer) == int
        assert DynamicModelGenerator.get_field_type(FieldType.float) == float
        assert DynamicModelGenerator.get_field_type(FieldType.boolean) == bool
        assert DynamicModelGenerator.get_field_type(FieldType.date) == str
        assert DynamicModelGenerator.get_field_type(FieldType.email) == str
        assert DynamicModelGenerator.get_field_type(FieldType.phone) == str
        assert DynamicModelGenerator.get_field_type(FieldType.address) == str

    def test_model_to_schema_conversion(self):
        """Test converting a Pydantic model back to a schema definition"""
        fields = [
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
            )
        ]

        dynamic_model = DynamicModelGenerator.create_model_from_schema(fields, "conversion_test")

        schema_info = DynamicModelGenerator.model_to_schema(dynamic_model)

        # Check that it contains the expected parts
        assert 'properties' in schema_info
        assert 'required' in schema_info
        assert 'title' in schema_info

        properties = schema_info['properties']
        # Check for the custom fields that we defined (not the common ones)
        assert 'name' in properties
        assert 'age' in properties
        # Common fields like source_documents, citations, bounding_boxes should not be in custom properties
        # These are handled separately as common fields

    def test_json_type_to_py_type(self):
        """Test JSON type to Py type conversion"""
        assert DynamicModelGenerator.json_type_to_py_type("string") == FieldType.string
        assert DynamicModelGenerator.json_type_to_py_type("integer") == FieldType.integer
        assert DynamicModelGenerator.json_type_to_py_type("number") == FieldType.float
        assert DynamicModelGenerator.json_type_to_py_type("boolean") == FieldType.boolean

        # Test default case
        assert DynamicModelGenerator.json_type_to_py_type("unknown") == FieldType.string

    def test_dynamic_model_includes_common_fields(self):
        """Test that dynamic models always include common fields"""
        fields = [
            FieldConfig(
                name="custom_field",
                type=FieldType.string,
                description="A custom field",
                required=True
            )
        ]

        dynamic_model = DynamicModelGenerator.create_model_from_schema(fields, "common_fields_test")

        # Create an instance with common fields
        instance = dynamic_model(
            custom_field="test value",
            source_documents=[SourceDocument(document_title="Test", filename="test.pdf")],
            citations={"custom_field": "test.pdf (Page 1)"},
            bounding_boxes={"custom_field": BoundingBox(filename="test.pdf", page=1, coordinates=[0, 0, 100, 100])}
        )

        assert instance.custom_field == "test value"
        assert len(instance.source_documents) == 1
        assert "custom_field" in instance.citations
        assert "custom_field" in instance.bounding_boxes

    def test_dynamic_model_field_validation(self):
        """Test that dynamic models validate field types correctly"""
        fields = [
            FieldConfig(
                name="age",
                type=FieldType.integer,
                description="Person's age",
                required=True
            )
        ]

        dynamic_model = DynamicModelGenerator.create_model_from_schema(fields, "validation_test")

        # Creating with correct type should work
        instance = dynamic_model(
            age=25,
            source_documents=[],
            citations={},
            bounding_boxes={}
        )
        assert instance.age == 25

        # Creating with incorrect type should raise ValidationError
        with pytest.raises(ValidationError):
            dynamic_model(
                age="not_a_number",  # Should be integer
                source_documents=[],
                citations={},
                bounding_boxes={}
            )

    def test_dynamic_model_optional_vs_required_fields(self):
        """Test that required and optional fields work correctly"""
        fields = [
            FieldConfig(
                name="required_field",
                type=FieldType.string,
                description="Required field",
                required=True
            ),
            FieldConfig(
                name="optional_field",
                type=FieldType.string,
                description="Optional field",
                required=False
            )
        ]

        dynamic_model = DynamicModelGenerator.create_model_from_schema(fields, "required_optional_test")

        # Creating with only required field should work
        instance = dynamic_model(
            required_field="required_value",
            source_documents=[],
            citations={},
            bounding_boxes={}
        )
        assert instance.required_field == "required_value"
        assert instance.optional_field is None

        # Creating without required field should raise ValidationError
        with pytest.raises(ValidationError):
            dynamic_model(
                # missing required_field
                source_documents=[],
                citations={},
                bounding_boxes={}
            )

    def test_dynamic_model_name_generation(self):
        """Test that dynamic model names are generated correctly"""
        fields = [
            FieldConfig(
                name="field",
                type=FieldType.string,
                description="A field",
                required=True
            )
        ]

        # Test with normal schema ID
        dynamic_model1 = DynamicModelGenerator.create_model_from_schema(fields, "test_schema")
        assert dynamic_model1.__name__ == "Dynamic_test_schema_Model"

        # Test with schema ID containing spaces and hyphens
        dynamic_model2 = DynamicModelGenerator.create_model_from_schema(fields, "test-schema with spaces")
        assert dynamic_model2.__name__ == "Dynamic_test_schema_with_spaces_Model"

    def test_dynamic_model_with_all_field_types(self):
        """Test creating a dynamic model with all field types"""
        fields = [
            FieldConfig(name="str_field", type=FieldType.string, description="String field", required=True),
            FieldConfig(name="int_field", type=FieldType.integer, description="Integer field", required=True),
            FieldConfig(name="float_field", type=FieldType.float, description="Float field", required=True),
            FieldConfig(name="bool_field", type=FieldType.boolean, description="Boolean field", required=True),
            FieldConfig(name="date_field", type=FieldType.date, description="Date field", required=False),
            FieldConfig(name="email_field", type=FieldType.email, description="Email field", required=False),
            FieldConfig(name="phone_field", type=FieldType.phone, description="Phone field", required=False),
            FieldConfig(name="address_field", type=FieldType.address, description="Address field", required=False),
        ]

        dynamic_model = DynamicModelGenerator.create_model_from_schema(fields, "all_types_schema")

        # Create an instance with all field types
        instance = dynamic_model(
            str_field="test",
            int_field=42,
            float_field=3.14,
            bool_field=True,
            date_field="2023-01-01",
            email_field="test@example.com",
            phone_field="+1234567890",
            address_field="123 Main St",
            source_documents=[],
            citations={},
            bounding_boxes={}
        )

        assert instance.str_field == "test"
        assert instance.int_field == 42
        assert instance.float_field == 3.14
        assert instance.bool_field is True
        assert instance.date_field == "2023-01-01"
        assert instance.email_field == "test@example.com"