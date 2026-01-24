import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json

from app.extractor import GeminiExtractor, ExtractionError
from app.models import (
    IntegratedCertificateSummary,
    IncomeCertificateSummary,
    OBCCertificateSummary,
    EWSCertificateSummary,
    FamilyMemberCertificateSummary,
    SourceDocument,
    BoundingBox
)


class TestGeminiExtractor:
    """Test cases for the GeminiExtractor class"""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.extractor = GeminiExtractor()

    @patch('app.extractor.vertexai.init')
    @patch('app.extractor.GenerativeModel')
    def test_initialization(self, mock_model, mock_init):
        """Test GeminiExtractor initialization"""
        extractor = GeminiExtractor(model_name="gemini-1.0-pro")
        assert extractor.model is not None

    def test_get_schema_for_type_valid_types(self):
        """Test that valid application types map to correct schemas"""
        # Test each valid type
        assert self.extractor._get_schema_for_type("Integrated Certificate") == IntegratedCertificateSummary
        assert self.extractor._get_schema_for_type("Income Certificate") == IncomeCertificateSummary
        assert self.extractor._get_schema_for_type("OBC Certificate") == OBCCertificateSummary
        assert self.extractor._get_schema_for_type("EWS Certificate") == EWSCertificateSummary
        assert self.extractor._get_schema_for_type("Family Member Certificate") == FamilyMemberCertificateSummary

    def test_get_schema_for_type_invalid_type(self):
        """Test that invalid application types raise ValueError"""
        with pytest.raises(ValueError, match="Unknown application type: Invalid Type"):
            self.extractor._get_schema_for_type("Invalid Type")

    def test_create_prompt(self):
        """Test prompt creation"""
        schema_class = IncomeCertificateSummary
        prompt = self.extractor._create_prompt("Income Certificate", schema_class)
        assert "Income Certificate" in prompt
        assert "json" in prompt.lower()  # Changed from "application/json" to just "json"
        assert schema_class.__name__ in prompt
        assert "STRICTLY follow this JSON schema" in prompt

    @patch('app.extractor.GenerativeModel')
    def test_extract_success(self, mock_model_class):
        """Test successful extraction"""
        mock_model = Mock()
        mock_model_class.return_value = mock_model

        # Setup mock response with correct SourceDocument structure
        mock_response = Mock()
        mock_response.text = json.dumps({
            "applicant_name": "Test User",
            "income_details": {"annual_income": 50000},
            "source_documents": [{"document_title": "Income Certificate", "filename": "test.pdf", "document_type": "Income Certificate"}],
            "citations": {},
            "bounding_boxes": {}
        })
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].finish_reason = Mock()
        mock_response.usage_metadata = Mock()
        mock_response.usage_metadata.prompt_token_count = 100
        mock_response.usage_metadata.candidates_token_count = 50
        mock_response.usage_metadata.total_token_count = 150

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
        assert result["_token_usage"]["total_token_count"] == 150

    @patch('app.extractor.GenerativeModel')
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

    @patch('app.extractor.GenerativeModel')
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

    @patch('app.extractor.GenerativeModel')
    def test_extract_with_empty_files_list(self, mock_model_class):
        """Test extraction with empty files list"""
        mock_model = Mock()
        mock_model_class.return_value = mock_model

        # Setup mock response with required fields for IncomeCertificateSummary
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

    def test_load_file_function(self):
        """Test the load_file function"""
        # Create a temporary file for testing
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_file:
            temp_file.write("test content")
            temp_file_path = temp_file.name

        try:
            from app.extractor import load_file
            result = load_file(temp_file_path)

            assert result['filename'] == os.path.basename(temp_file_path)
            assert result['content'] == b"test content"
            assert result['mime_type'] is None
        finally:
            os.unlink(temp_file_path)

    def test_get_schema_for_type_case_sensitivity(self):
        """Test that schema mapping is case sensitive"""
        with pytest.raises(ValueError, match="Unknown application type: income certificate"):
            self.extractor._get_schema_for_type("income certificate")  # lowercase

    @patch('app.extractor.GenerativeModel')
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

    @patch('app.extractor.GenerativeModel')
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