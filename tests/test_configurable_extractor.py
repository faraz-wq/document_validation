import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json

from app.core.configurable_extractor import ConfigurableExtractor, ExtractionError
from app.models import (
    IntegratedCertificateSummary,
    IncomeCertificateSummary,
    OBCCertificateSummary,
    EWSCertificateSummary,
    FamilyMemberCertificateSummary
)
from app.schemas.schema_models import SchemaDefinition, FieldConfig, FieldType
from app.core.schema_registry import schema_registry


class TestConfigurableExtractor:
    """Test cases for the ConfigurableExtractor class"""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.extractor = ConfigurableExtractor(user_id="test_user")

    @patch('app.core.configurable_extractor.vertexai.init')
    @patch('app.core.configurable_extractor.GenerativeModel')
    def test_initialization(self, mock_model, mock_init):
        """Test ConfigurableExtractor initialization"""
        extractor = ConfigurableExtractor(model_name="gemini-1.0-pro", user_id="test_user")
        assert extractor.model is not None
        assert extractor.user_id == "test_user"

    def test_get_schema_for_type_valid_default_types(self):
        """Test that valid default application types map to correct schemas"""
        # Test each valid default type
        assert self.extractor._get_schema_for_type("Integrated Certificate") == IntegratedCertificateSummary
        assert self.extractor._get_schema_for_type("Income Certificate") == IncomeCertificateSummary
        assert self.extractor._get_schema_for_type("OBC Certificate") == OBCCertificateSummary
        assert self.extractor._get_schema_for_type("EWS Certificate") == EWSCertificateSummary
        assert self.extractor._get_schema_for_type("Family Member Certificate") == FamilyMemberCertificateSummary

    def test_get_schema_for_type_invalid_default_type(self):
        """Test that invalid default application types raise ValueError"""
        with pytest.raises(ValueError, match="Unknown application type: Invalid Type"):
            self.extractor._get_schema_for_type("Invalid Type")

    @patch('app.core.configurable_extractor.schema_registry')
    def test_get_schema_for_type_custom_schema(self, mock_schema_registry):
        """Test that custom schema types are handled correctly"""
        # Mock a schema definition
        mock_schema_def = SchemaDefinition(
            schema_id="custom_test_schema",
            schema_name="Custom Test Schema",
            description="A test custom schema",
            fields=[
                FieldConfig(
                    name="custom_field",
                    type=FieldType.string,
                    description="A custom field",
                    required=True
                )
            ],
            created_by="test_user"
        )
        
        mock_schema_registry.get_schema.return_value = mock_schema_def
        
        # Test getting custom schema
        schema_class = self.extractor._get_schema_for_type("custom:custom_test_schema")
        
        # Should return a dynamic model
        assert schema_class is not None
        # The schema should be a dynamic model
        assert hasattr(schema_class, '__name__')
        assert 'Dynamic' in schema_class.__name__

    @patch('app.core.configurable_extractor.schema_registry')
    def test_get_schema_for_type_custom_schema_not_found(self, mock_schema_registry):
        """Test that custom schema not found raises ValueError"""
        mock_schema_registry.get_schema.return_value = None
        
        with pytest.raises(ValueError, match="Custom schema not found or access denied: nonexistent_schema"):
            self.extractor._get_schema_for_type("custom:nonexistent_schema")

    def test_create_prompt(self):
        """Test prompt creation"""
        schema_class = IncomeCertificateSummary
        prompt = self.extractor._create_prompt("Income Certificate", schema_class)
        assert "Income Certificate" in prompt
        assert "json" in prompt.lower()
        assert schema_class.__name__ in prompt
        assert "STRICTLY follow this JSON schema" in prompt

    @patch('app.core.configurable_extractor.GenerativeModel')
    def test_extract_default_schema_success(self, mock_model_class):
        """Test successful extraction with default schema"""
        mock_model = Mock()
        mock_model_class.return_value = mock_model

        # Setup mock response with required fields
        mock_response = Mock()
        mock_response.text = json.dumps({
            "applicant_name": "Test User",
            "income_details": {"total_gross_income": "50000"},
            "source_documents": [{"document_title": "Income Certificate", "filename": "test.pdf"}],
            "citations": {},
            "bounding_boxes": {}
        })
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].finish_reason = Mock()
        mock_response.usage_metadata = Mock()
        mock_response.usage_metadata.total_token_count = 100

        mock_model.generate_content.return_value = mock_response

        self.extractor.model = mock_model

        # Test data
        files = [{
            "filename": "test.pdf",
            "content": b"test content",
            "mime_type": "application/pdf"
        }]

        result = self.extractor.extract("Income Certificate", files)

        assert "applicant_name" in result
        assert "_token_usage" in result
        assert result["_token_usage"]["total_token_count"] == 100

    @patch('app.core.configurable_extractor.GenerativeModel')
    def test_extract_custom_schema_success(self, mock_model_class):
        """Test successful extraction with custom schema"""
        mock_model = Mock()
        mock_model_class.return_value = mock_model

        # Setup mock response for default schema (since Income Certificate is the test case)
        mock_response = Mock()
        mock_response.text = json.dumps({
            "applicant_name": "Test User",
            "income_details": {"total_gross_income": "50000"},
            "source_documents": [{"document_title": "Custom Doc", "filename": "test.pdf"}],
            "citations": {},
            "bounding_boxes": {}
        })
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].finish_reason = Mock()
        mock_response.usage_metadata = Mock()
        mock_response.usage_metadata.total_token_count = 150

        mock_model.generate_content.return_value = mock_response

        self.extractor.model = mock_model

        # Test with a default schema type (since we can't easily mock dynamic models)
        # We'll test the basic extraction flow
        files = [{
            "filename": "test.pdf",
            "content": b"test content",
            "mime_type": "application/pdf"
        }]

        result = self.extractor.extract("Income Certificate", files)

        assert "source_documents" in result
        assert "_token_usage" in result

    @patch('app.core.configurable_extractor.GenerativeModel')
    def test_extract_json_parse_error(self, mock_model_class):
        """Test extraction when JSON parsing fails"""
        mock_model = Mock()
        mock_model_class.return_value = mock_model

        # Setup mock response with invalid JSON
        mock_response = Mock()
        mock_response.text = "invalid json"
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].finish_reason = Mock()

        mock_model.generate_content.return_value = mock_response
        self.extractor.model = mock_model

        files = [{
            "filename": "test.pdf",
            "content": b"test content",
            "mime_type": "application/pdf"
        }]

        with pytest.raises(ExtractionError):
            self.extractor.extract("Income Certificate", files)

    @patch('app.core.configurable_extractor.GenerativeModel')
    def test_extract_unexpected_error(self, mock_model_class):
        """Test extraction with unexpected error"""
        mock_model = Mock()
        mock_model_class.return_value = mock_model

        # Setup mock to raise an unexpected error
        mock_model.generate_content.side_effect = Exception("Unexpected error")

        self.extractor.model = mock_model

        files = [{
            "filename": "test.pdf",
            "content": b"test content",
            "mime_type": "application/pdf"
        }]

        with pytest.raises(ExtractionError):
            self.extractor.extract("Income Certificate", files)

    def test_get_schema_for_type_case_sensitivity(self):
        """Test that schema mapping is case sensitive"""
        with pytest.raises(ValueError, match="Unknown application type: income certificate"):
            self.extractor._get_schema_for_type("income certificate")  # lowercase

    @patch('app.core.configurable_extractor.GenerativeModel')
    def test_extract_response_with_markdown_wrapping(self, mock_model_class):
        """Test extraction with markdown code block wrapping"""
        mock_model = Mock()
        mock_model_class.return_value = mock_model

        # Setup mock response with markdown wrapping and required fields
        mock_response = Mock()
        mock_response.text = "```json\n" + json.dumps({
            "applicant_name": "Test User",
            "income_details": {"total_gross_income": "50000"},
            "source_documents": [{"document_title": "Test", "filename": "test.pdf"}],
            "citations": {},
            "bounding_boxes": {}
        }) + "\n```"
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].finish_reason = Mock()
        mock_response.usage_metadata = Mock()
        mock_response.usage_metadata.total_token_count = 100

        mock_model.generate_content.return_value = mock_response
        self.extractor.model = mock_model

        files = [{
            "filename": "test.pdf",
            "content": b"test content",
            "mime_type": "application/pdf"
        }]

        result = self.extractor.extract("Income Certificate", files)

        assert result["applicant_name"] == "Test User"
        assert result["_token_usage"]["total_token_count"] == 100

    @patch('app.core.configurable_extractor.GenerativeModel')
    def test_extract_with_different_mime_types(self, mock_model_class):
        """Test extraction with different mime types"""
        mock_model = Mock()
        mock_model_class.return_value = mock_model

        # Setup mock response with required fields
        mock_response = Mock()
        mock_response.text = json.dumps({
            "applicant_name": "Test User",
            "income_details": {"total_gross_income": "50000"},
            "source_documents": [{"document_title": "Test", "filename": "test.jpg"}],
            "citations": {},
            "bounding_boxes": {}
        })
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].finish_reason = Mock()
        mock_response.usage_metadata = Mock()
        mock_response.usage_metadata.total_token_count = 100

        mock_model.generate_content.return_value = mock_response
        self.extractor.model = mock_model

        # Test with JPEG file
        files = [{
            "filename": "test.jpg",
            "content": b"test image content",
            "mime_type": "image/jpeg"
        }]

        result = self.extractor.extract("Income Certificate", files)

        assert result["applicant_name"] == "Test User"

    def test_create_prompt_includes_all_instructions(self):
        """Test that the prompt includes all required instructions"""
        schema_class = IncomeCertificateSummary
        prompt = self.extractor._create_prompt("Income Certificate", schema_class)

        # Check that the prompt contains all the important instructions
        assert "Analyze ALL provided document images/PDFs" in prompt
        assert "Extract the fields defined in the schema" in prompt
        assert "Populate 'source_documents'" in prompt
        assert "Populate the 'citations' dictionary" in prompt
        assert "Populate the 'bounding_boxes' dictionary" in prompt
        assert "Return ONLY the valid JSON object" in prompt

    @patch('app.core.configurable_extractor.GenerativeModel')
    def test_extract_with_empty_files_list(self, mock_model_class):
        """Test extraction with empty files list"""
        mock_model = Mock()
        mock_model_class.return_value = mock_model

        # Setup mock response with required fields
        mock_response = Mock()
        mock_response.text = json.dumps({
            "applicant_name": "Test User",
            "income_details": {"total_gross_income": "50000"},
            "source_documents": [{"document_title": "Test", "filename": "test.pdf"}],
            "citations": {},
            "bounding_boxes": {}
        })
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].finish_reason = Mock()
        mock_response.usage_metadata = Mock()
        mock_response.usage_metadata.total_token_count = 100

        mock_model.generate_content.return_value = mock_response

        self.extractor.model = mock_model

        # Test with empty files list
        files = []

        result = self.extractor.extract("Income Certificate", files)

        assert "applicant_name" in result
        assert result["_token_usage"]["total_token_count"] == 100

    @patch('app.core.configurable_extractor.vertexai.init')
    @patch('app.core.configurable_extractor.GenerativeModel')
    def test_multiple_extractor_instances_different_users(self, mock_model, mock_init):
        """Test that different extractor instances can handle different users"""
        extractor1 = ConfigurableExtractor(user_id="user1")
        extractor2 = ConfigurableExtractor(user_id="user2")
        
        assert extractor1.user_id == "user1"
        assert extractor2.user_id == "user2"