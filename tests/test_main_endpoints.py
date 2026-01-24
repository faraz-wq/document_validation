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
from app.database import db


class TestMainEndpoints:
    """Test cases for the main FastAPI endpoints"""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.client = TestClient(app)

    def test_health_check(self):
        """Test health check endpoint"""
        response = self.client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_root_endpoint(self):
        """Test root endpoint"""
        response = self.client.get("/")
        assert response.status_code == 200
        # This will likely be an HTML response, but we test that it returns successfully

    def test_extract_summary_success(self):
        """Test successful extraction summary endpoint"""
        # Create a mock file
        mock_file_content = b"test pdf content"
        files = [
            ("files", ("test.pdf", mock_file_content, "application/pdf"))
        ]
        
        # Mock the extractor to return a successful result
        with patch('app.main.extractor') as mock_extractor:
            mock_result = {
                "applicant_name": "Test User",
                "source_documents": [{"document_title": "Test", "filename": "test.pdf"}],
                "citations": {"applicant_name": "test.pdf (Page 1)"},
                "bounding_boxes": {},
                "_token_usage": {"total_token_count": 100}
            }
            mock_extractor.extract.return_value = mock_result

            response = self.client.post(
                "/extract-summary",
                data={"application_type": "Income Certificate"},
                files=files
            )
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["applicant_name"] == "Test User"
            assert response_data["_token_usage"]["total_token_count"] == 100

    def test_extract_summary_extraction_error(self):
        """Test extraction error handling"""
        from app.extractor import ExtractionError
        
        # Create a mock file
        mock_file_content = b"test pdf content"
        files = [
            ("files", ("test.pdf", mock_file_content, "application/pdf"))
        ]
        
        # Mock the extractor to raise an extraction error
        with patch('app.main.extractor') as mock_extractor:
            mock_extractor.extract.side_effect = ExtractionError("Test extraction error")

            response = self.client.post(
                "/extract-summary",
                data={"application_type": "Income Certificate"},
                files=files
            )
            
            assert response.status_code == 422
            assert "Test extraction error" in response.json()["detail"]

    def test_extract_summary_unexpected_error(self):
        """Test unexpected error handling"""
        # Create a mock file
        mock_file_content = b"test pdf content"
        files = [
            ("files", ("test.pdf", mock_file_content, "application/pdf"))
        ]
        
        # Mock the extractor to raise an unexpected error
        with patch('app.main.extractor') as mock_extractor:
            mock_extractor.extract.side_effect = Exception("Unexpected error")

            response = self.client.post(
                "/extract-summary",
                data={"application_type": "Income Certificate"},
                files=files
            )
            
            assert response.status_code == 500
            assert "Internal Server Error" in response.json()["detail"]

    def test_submit_document_success(self):
        """Test successful document submission"""
        # Create a mock file
        mock_file_content = b"test pdf content"
        files = [
            ("files", ("test.pdf", mock_file_content, "application/pdf"))
        ]
        
        # Mock the extractor to return a successful result
        with patch('app.main.extractor') as mock_extractor:
            mock_result = {
                "applicant_name": "Test User",
                "source_documents": [{"document_title": "Test", "filename": "test.pdf"}],
                "citations": {"applicant_name": "test.pdf (Page 1)"},
                "bounding_boxes": {}
            }
            mock_extractor.extract.return_value = mock_result

            response = self.client.post(
                "/submit",
                data={"application_type": "Income Certificate"},
                files=files
            )
            
            # The submit endpoint returns HTML response (template), so status should be 200
            assert response.status_code == 200

    def test_submit_document_no_files(self):
        """Test document submission with no files"""
        response = self.client.post(
            "/submit",
            data={"application_type": "Income Certificate"}
        )

        # This should return a 422 error because files are required by FastAPI
        assert response.status_code == 422

    def test_submit_document_process_error(self):
        """Test document submission process error"""
        # Create a mock file
        mock_file_content = b"test pdf content"
        files = [
            ("files", ("test.pdf", mock_file_content, "application/pdf"))
        ]
        
        # Mock the extractor to raise an error
        with patch('app.main.extractor') as mock_extractor:
            mock_extractor.extract.side_effect = Exception("Processing error")

            response = self.client.post(
                "/submit",
                data={"application_type": "Income Certificate"},
                files=files
            )
            
            # Should return 200 with error message in template
            assert response.status_code == 200

    def test_view_document_success(self):
        """Test viewing a document"""
        # First, create an uploaded file for testing
        uploads_dir = Path("static/uploads")
        uploads_dir.mkdir(parents=True, exist_ok=True)
        
        test_file_path = uploads_dir / "test_view.pdf"
        test_file_path.write_bytes(b"test pdf content")
        
        try:
            response = self.client.get("/view-document/test_view.pdf")
            assert response.status_code == 200
            assert response.content == b"test pdf content"
        finally:
            # Clean up
            if test_file_path.exists():
                test_file_path.unlink()

    def test_view_document_not_found(self):
        """Test viewing a non-existent document"""
        response = self.client.get("/view-document/nonexistent.pdf")
        assert response.status_code == 404

    def test_list_sessions(self):
        """Test listing sessions endpoint"""
        response = self.client.get("/sessions")
        assert response.status_code == 200
        assert "sessions" in response.json()

    def test_list_sessions_with_limit(self):
        """Test listing sessions endpoint with limit parameter"""
        response = self.client.get("/sessions?limit=10")
        assert response.status_code == 200
        assert "sessions" in response.json()

    def test_get_session_success(self):
        """Test getting a specific session"""
        # Create a test session first
        summary = {
            "applicant_name": "Test User",
            "source_documents": [{"document_title": "Test", "filename": "test.pdf"}],
            "citations": {"applicant_name": "test.pdf (Page 1)"},
            "bounding_boxes": {}
        }
        files = [{
            "filename": "test.pdf",
            "content": b"test content",
            "mime_type": "application/pdf"
        }]

        # Create documents directory to avoid file not found error
        import os
        os.makedirs("documents_v1", exist_ok=True)

        session_id = db.create_session("Income Certificate", summary, files)

        try:
            response = self.client.get(f"/sessions/{session_id}")
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["session_id"] == session_id
            assert response_data["summary"]["applicant_name"] == "Test User"
        finally:
            # Clean up
            db.delete_session(session_id)

    def test_get_session_not_found(self):
        """Test getting a non-existent session"""
        response = self.client.get("/sessions/nonexistent_session_id")
        assert response.status_code == 404

    def test_delete_session_success(self):
        """Test deleting a session"""
        # Create a test session first
        summary = {
            "applicant_name": "Test User",
            "source_documents": [{"document_title": "Test", "filename": "test.pdf"}],
            "citations": {"applicant_name": "test.pdf (Page 1)"},
            "bounding_boxes": {}
        }
        files = [{
            "filename": "test.pdf",
            "content": b"test content",
            "mime_type": "application/pdf"
        }]

        # Create documents directory to avoid file not found error
        import os
        os.makedirs("documents_v1", exist_ok=True)

        session_id = db.create_session("Income Certificate", summary, files)

        response = self.client.delete(f"/sessions/{session_id}")
        assert response.status_code == 200
        assert response.json()["message"] == "Session deleted successfully"

        # Verify the session is actually deleted
        response = self.client.get(f"/sessions/{session_id}")
        assert response.status_code == 404

    def test_delete_session_not_found(self):
        """Test deleting a non-existent session"""
        response = self.client.delete("/sessions/nonexistent_session_id")
        # According to the implementation, the delete function returns success even if the session doesn't exist
        # So this may return 200 with "Session deleted successfully" message
        # Let's check the actual behavior - it should return 200 since the delete function returns success=True
        assert response.status_code == 200

    def test_v1_endpoints_require_auth(self):
        """Test that v1 schema endpoints require authentication"""
        # Test schema creation endpoint
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
        # Should return 401 since no API key is provided
        assert response.status_code == 401

    def test_extract_summary_custom_requires_auth(self):
        """Test that custom extraction endpoint requires authentication"""
        # Create a mock file
        mock_file_content = b"test pdf content"
        files = [
            ("files", ("test.pdf", mock_file_content, "application/pdf"))
        ]
        
        response = self.client.post(
            "/v1/extract-custom",
            data={"schema_id": "test_schema"},
            files=files
        )
        # Should return 401 since no API key is provided
        assert response.status_code == 401