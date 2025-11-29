import pytest
from unittest.mock import MagicMock, patch
from app.extractor import GeminiExtractor
from app.models import IncomeCertificateSummary

# Mock response data
MOCK_JSON_RESPONSE = """
{
  "applicant_name": "John Doe",
  "fathers_name": "Richard Doe",
  "address": "123 Main St, City",
  "gender": "Male",
  "age_dob": "01/01/1980",
  "phone_number": "9876543210",
  "income_details": {
    "total_gross_income": "100000"
  },
  "source_documents": [
    {
      "document_title": "Income Certificate Application",
      "filename": "test_doc.pdf"
    }
  ]
}
"""

@pytest.fixture
def mock_vertexai():
    with patch("app.extractor.vertexai") as mock:
        yield mock

@pytest.fixture
def mock_generative_model():
    with patch("app.extractor.GenerativeModel") as mock:
        yield mock

def test_extractor_initialization(mock_vertexai, mock_generative_model):
    extractor = GeminiExtractor()
    mock_generative_model.assert_called_with("gemini-1.5-pro-001")

def test_extract_income_certificate(mock_vertexai, mock_generative_model):
    # Setup mock
    mock_model_instance = mock_generative_model.return_value
    mock_response = MagicMock()
    mock_response.text = MOCK_JSON_RESPONSE
    mock_response.finish_reason = 1 # STOP
    mock_model_instance.generate_content.return_value = mock_response

    extractor = GeminiExtractor()
    
    files = [{"filename": "test_doc.pdf", "content": b"fake_pdf_content"}]
    result = extractor.extract("Income Certificate", files)
    
    assert result["applicant_name"] == "John Doe"
    assert result["income_details"]["total_gross_income"] == "100000"
    assert len(result["source_documents"]) == 1
    assert result["source_documents"][0]["filename"] == "test_doc.pdf"

def test_extract_invalid_app_type():
    extractor = GeminiExtractor()
    with pytest.raises(Exception) as excinfo:
        extractor.extract("Invalid Type", [])
    assert "Unknown application type" in str(excinfo.value)
