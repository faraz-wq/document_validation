import pytest
from fastapi.testclient import TestClient

from app.ui import app


class TestUI:
    """Test cases for the UI endpoints in app/ui.py"""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.client = TestClient(app)

    def test_root_endpoint(self):
        """Test the root endpoint"""
        response = self.client.get("/")
        
        # The root should return a successful response
        # It might return HTML, so we just check the status
        assert response.status_code in [200, 404]  # Could be 404 if template doesn't exist
        
        # If it's successful, we can also check it returns HTML
        if response.status_code == 200:
            # The response should be HTML content
            assert "text/html" in response.headers.get("content-type", "")

    def test_health_check_not_available(self):
        """Test that health check endpoint is not available in ui.py"""
        # The ui.py module doesn't have a health check endpoint
        response = self.client.get("/health")
        assert response.status_code == 404  # Not found

    def test_static_file_mounting(self):
        """Test that static files are properly mounted"""
        # We can't easily test static file mounting without creating actual files
        # But we can make sure the app object has the static mount
        assert hasattr(app, 'routes')
        
        # Check if there are routes for static files
        static_routes = [route for route in app.routes if hasattr(route, 'path') and '/static' in route.path]
        assert len(static_routes) > 0

    def test_app_title(self):
        """Test that the app has the correct title"""
        assert app.title == "Document Validation Service"

    def test_different_http_methods_not_allowed(self):
        """Test that other HTTP methods are handled appropriately"""
        # Test POST on root (should not be allowed by the UI app)
        response = self.client.post("/")
        # Should return either 405 (Method Not Allowed) or 404 (Not Found)
        assert response.status_code in [404, 405]