"""
Test nested fields functionality in validation configs
"""
import pytest
from app.verification.schema import VerificationConfig, KeyDetailDefinition, ValidationRuleDefinition


def test_nested_fields_in_key_detail_definition():
    """Test that KeyDetailDefinition supports nested fields"""
    
    # Create a parent field with nested fields
    parent_field = KeyDetailDefinition(
        field_path="family_members",
        display_name="Family Members List",
        description="List of all family members",
        valid_proof_documents=["Aadhaar Card", "Application Form"],
        nested_fields=[
            KeyDetailDefinition(
                field_path="name",
                display_name="Name",
                description="Full name of the family member",
                valid_proof_documents=["Aadhaar Card", "Application Form"]
            ),
            KeyDetailDefinition(
                field_path="age",
                display_name="Age",
                description="Age of the family member",
                valid_proof_documents=["Aadhaar Card", "Application Form"]
            ),
            KeyDetailDefinition(
                field_path="relationship",
                display_name="Relationship",
                description="Relation to the applicant",
                valid_proof_documents=["Application Form", "Affidavit"]
            )
        ]
    )
    
    # Verify the parent field
    assert parent_field.field_path == "family_members"
    assert parent_field.display_name == "Family Members List"
    assert parent_field.nested_fields is not None
    assert len(parent_field.nested_fields) == 3
    
    # Verify nested fields
    assert parent_field.nested_fields[0].field_path == "name"
    assert parent_field.nested_fields[1].field_path == "age"
    assert parent_field.nested_fields[2].field_path == "relationship"


def test_verification_config_with_nested_fields():
    """Test that VerificationConfig works with nested fields"""
    
    config = VerificationConfig(
        application_type="Test Certificate with Nested Fields",
        key_details=[
            KeyDetailDefinition(
                field_path="applicant_name",
                display_name="Applicant Name",
                description="Full name of the applicant",
                valid_proof_documents=["Aadhaar Card", "Application Form"]
            ),
            KeyDetailDefinition(
                field_path="properties",
                display_name="Properties List",
                description="List of all properties",
                valid_proof_documents=["Property Documents"],
                nested_fields=[
                    KeyDetailDefinition(
                        field_path="property_id",
                        display_name="Property ID",
                        description="Unique identifier",
                        valid_proof_documents=["Property Documents"]
                    ),
                    KeyDetailDefinition(
                        field_path="address",
                        display_name="Property Address",
                        description="Full address",
                        valid_proof_documents=["Property Documents"]
                    ),
                    KeyDetailDefinition(
                        field_path="area_sqft",
                        display_name="Area (sq ft)",
                        description="Total area",
                        valid_proof_documents=["Property Documents"]
                    )
                ]
            )
        ],
        rules=[
            ValidationRuleDefinition(
                rule_id="name_consistency",
                description="Name must be consistent",
                severity="error",
                rule_type="consistency",
                fields_involved=["applicant_name"]
            )
        ]
    )
    
    # Verify config
    assert config.application_type == "Test Certificate with Nested Fields"
    assert len(config.key_details) == 2
    
    # Verify the nested field
    properties_field = config.key_details[1]
    assert properties_field.field_path == "properties"
    assert properties_field.nested_fields is not None
    assert len(properties_field.nested_fields) == 3
    
    # Verify nested subfields
    assert properties_field.nested_fields[0].field_path == "property_id"
    assert properties_field.nested_fields[1].field_path == "address"
    assert properties_field.nested_fields[2].field_path == "area_sqft"


def test_nested_fields_serialization():
    """Test that nested fields can be serialized and deserialized"""
    
    original_config = VerificationConfig(
        application_type="Serialization Test",
        key_details=[
            KeyDetailDefinition(
                field_path="income_sources",
                display_name="Income Sources",
                description="List of income sources",
                nested_fields=[
                    KeyDetailDefinition(
                        field_path="source_type",
                        display_name="Source Type",
                        description="Type of income",
                        valid_proof_documents=["Income Certificate"]
                    ),
                    KeyDetailDefinition(
                        field_path="annual_income",
                        display_name="Annual Income",
                        description="Annual income amount",
                        valid_proof_documents=["Salary Slip", "IT Returns"]
                    )
                ]
            )
        ],
        rules=[]
    )
    
    # Serialize to dict
    config_dict = original_config.model_dump()
    
    # Verify serialization
    assert "key_details" in config_dict
    assert len(config_dict["key_details"]) == 1
    assert "nested_fields" in config_dict["key_details"][0]
    assert len(config_dict["key_details"][0]["nested_fields"]) == 2
    
    # Deserialize back
    restored_config = VerificationConfig(**config_dict)
    
    # Verify deserialization
    assert restored_config.application_type == original_config.application_type
    assert len(restored_config.key_details) == 1
    assert restored_config.key_details[0].nested_fields is not None
    assert len(restored_config.key_details[0].nested_fields) == 2
    assert restored_config.key_details[0].nested_fields[0].field_path == "source_type"
    assert restored_config.key_details[0].nested_fields[1].field_path == "annual_income"


def test_nested_fields_optional():
    """Test that nested_fields is optional"""
    
    # Create a field without nested fields
    simple_field = KeyDetailDefinition(
        field_path="applicant_name",
        display_name="Applicant Name",
        description="Full name",
        valid_proof_documents=["Aadhaar Card"]
    )
    
    assert simple_field.nested_fields is None
    
    # Create a config with mixed fields (some with nested, some without)
    config = VerificationConfig(
        application_type="Mixed Fields Test",
        key_details=[
            KeyDetailDefinition(
                field_path="applicant_name",
                display_name="Applicant Name",
                description="Full name",
                valid_proof_documents=["Aadhaar Card"]
            ),
            KeyDetailDefinition(
                field_path="family_members",
                display_name="Family Members",
                description="List of family members",
                nested_fields=[
                    KeyDetailDefinition(
                        field_path="name",
                        display_name="Name",
                        description="Member name",
                        valid_proof_documents=["Aadhaar Card"]
                    )
                ]
            )
        ],
        rules=[]
    )
    
    assert config.key_details[0].nested_fields is None
    assert config.key_details[1].nested_fields is not None
    assert len(config.key_details[1].nested_fields) == 1


def test_family_member_config_has_nested_fields():
    """Test that the FAMILY_MEMBER_CONFIG uses nested fields correctly"""
    from app.verification.registry import FAMILY_MEMBER_CONFIG
    
    # Find the family_members field
    family_members_field = None
    for field in FAMILY_MEMBER_CONFIG.key_details:
        if field.field_path == "family_members":
            family_members_field = field
            break
    
    assert family_members_field is not None, "family_members field not found in FAMILY_MEMBER_CONFIG"
    assert family_members_field.nested_fields is not None, "family_members should have nested_fields"
    assert len(family_members_field.nested_fields) == 5, "family_members should have 5 nested fields"
    
    # Verify the nested field names
    nested_field_paths = [f.field_path for f in family_members_field.nested_fields]
    expected_paths = ["name", "age", "gender", "relationship", "aadhaar"]
    assert nested_field_paths == expected_paths, f"Expected {expected_paths}, got {nested_field_paths}"
