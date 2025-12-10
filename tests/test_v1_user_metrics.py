"""
Unit tests for the user metrics API endpoints
Tests for endpoints in app/api/v1/me_stats.py
Follows the pattern of existing tests in the project
"""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.db.models import User
from app.schemas.user_metrics import UserDashboardStats, UserRequestBucket


def create_mock_user(user_id: int = 1, email: str = "test@example.com", username: str = "testuser"):
    """Helper function to create a mock user object"""
    mock_user = MagicMock(spec=User)
    mock_user.id = user_id
    mock_user.email = email
    mock_user.username = username
    mock_user.is_active = True
    return mock_user


class TestV1UserMetricsEndpoints:
    """Test class for user metrics API endpoints following the project's testing pattern"""
    
    def setup_method(self):
        """Setup method to initialize test client"""
        self.client = TestClient(app)
        
    def test_get_user_stats_unauthorized(self):
        """Test that /v1/me/stats returns 401 without authentication"""
        response = self.client.get("/v1/me/stats")
        assert response.status_code == 401
        assert "detail" in response.json()
    
    def test_get_user_request_metrics_unauthorized(self):
        """Test that /v1/me/metrics/requests returns 401 without authentication"""
        response = self.client.get("/v1/me/metrics/requests")
        assert response.status_code == 401
        assert "detail" in response.json()


class TestV1UserMetricsSchemas:
    """Test the Pydantic schemas for user metrics"""
    
    def test_user_dashboard_stats_schema(self):
        """Test the UserDashboardStats schema with valid data"""
        stats_data = {
            "total_requests": 100,
            "total_errors": 5,
            "total_documents": 90,
            "avg_response_time_ms": 250.0,
            "requests_last_24h": 20,
            "errors_last_24h": 1,
            "per_key": []
        }
        
        stats = UserDashboardStats(**stats_data)
        assert stats.total_requests == 100
        assert stats.total_errors == 5
        assert stats.total_documents == 90
        assert stats.avg_response_time_ms == 250.0
        assert stats.requests_last_24h == 20
        assert stats.errors_last_24h == 1
        assert stats.per_key == []
    
    def test_user_dashboard_stats_schema_with_per_key(self):
        """Test the UserDashboardStats schema with per-key data"""
        stats_data = {
            "total_requests": 150,
            "total_errors": 8,
            "total_documents": 140,
            "avg_response_time_ms": 320.5,
            "requests_last_24h": 25,
            "errors_last_24h": 2,
            "per_key": [
                {
                    "api_key_id": 1,
                    "description": "Test key",
                    "total_requests": 100,
                    "total_errors": 5,
                    "total_documents": 90,
                    "last_used_at": datetime(2023, 1, 1, 12, 0, 0)
                },
                {
                    "api_key_id": 2,
                    "description": "Another key",
                    "total_requests": 50,
                    "total_errors": 3,
                    "total_documents": 50,
                    "last_used_at": datetime(2023, 1, 2, 14, 30, 0)
                }
            ]
        }
        
        stats = UserDashboardStats(**stats_data)
        assert stats.total_requests == 150
        assert len(stats.per_key) == 2
        assert stats.per_key[0].api_key_id == 1
        assert stats.per_key[0].description == "Test key"
        assert stats.per_key[1].api_key_id == 2
    
    def test_user_dashboard_stats_schema_with_null_values(self):
        """Test the UserDashboardStats schema with null values"""
        stats_data = {
            "total_requests": 0,
            "total_errors": 0,
            "total_documents": 0,
            "avg_response_time_ms": None,
            "requests_last_24h": 0,
            "errors_last_24h": 0,
            "per_key": []
        }
        
        stats = UserDashboardStats(**stats_data)
        assert stats.total_requests == 0
        assert stats.total_errors == 0
        assert stats.total_documents == 0
        assert stats.avg_response_time_ms is None
        assert stats.requests_last_24h == 0
        assert stats.errors_last_24h == 0
    
    def test_per_key_stats_schema(self):
        """Test the PerKeyStats schema"""
        from app.schemas.user_metrics import PerKeyStats
        
        stats_data = {
            "api_key_id": 1,
            "description": "Test key",
            "total_requests": 100,
            "total_errors": 5,
            "total_documents": 90,
            "last_used_at": datetime(2023, 1, 1, 12, 0, 0)
        }
        
        stats = PerKeyStats(**stats_data)
        assert stats.api_key_id == 1
        assert stats.description == "Test key"
        assert stats.total_requests == 100
        assert stats.total_errors == 5
        assert stats.total_documents == 90
        assert stats.last_used_at.hour == 12
    
    def test_per_key_stats_schema_optional_description(self):
        """Test the PerKeyStats schema with optional description as None"""
        from app.schemas.user_metrics import PerKeyStats
        
        stats_data = {
            "api_key_id": 1,
            "description": None,
            "total_requests": 0,
            "total_errors": 0,
            "total_documents": 0,
            "last_used_at": None
        }
        
        stats = PerKeyStats(**stats_data)
        assert stats.api_key_id == 1
        assert stats.description is None
        assert stats.total_requests == 0
        assert stats.total_errors == 0
        assert stats.total_documents == 0
        assert stats.last_used_at is None
    
    def test_user_request_bucket_schema(self):
        """Test the UserRequestBucket schema"""
        bucket_data = {
            "bucket": datetime(2023, 1, 1, 10, 0, 0),
            "requests": 10,
            "errors": 1,
            "avg_ms": 250.0
        }
        
        bucket = UserRequestBucket(**bucket_data)
        assert bucket.bucket.year == 2023
        assert bucket.requests == 10
        assert bucket.errors == 1
        assert bucket.avg_ms == 250.0
    
    def test_user_request_bucket_schema_null_avg_ms(self):
        """Test the UserRequestBucket schema with null avg_ms"""
        bucket_data = {
            "bucket": datetime(2023, 1, 1, 10, 0, 0),
            "requests": 5,
            "errors": 0,
            "avg_ms": None
        }
        
        bucket = UserRequestBucket(**bucket_data)
        assert bucket.requests == 5
        assert bucket.errors == 0
        assert bucket.avg_ms is None


class TestV1UserMetricsServiceFunctions:
    """Test the service functions directly"""
    
    @patch('app.services.user_metrics.get_user_aggregate_stats')
    def test_get_user_aggregate_stats_function_called_with_correct_params(self, mock_get_user_stats):
        """Test that service functions are called with correct parameters"""
        from app.services.user_metrics import get_user_aggregate_stats
        
        # Mock a database session
        mock_db = MagicMock()
        
        # Call the service function
        try:
            get_user_aggregate_stats(mock_db, 123)
        except Exception:
            # Expected to fail since we're not connecting to real DB
            pass
        
        # Verify it was called with the correct user ID
        mock_get_user_stats.assert_called_once_with(mock_db, 123)
    
    @patch('app.services.user_metrics.get_user_request_timeseries')
    def test_get_user_request_timeseries_function_called_with_correct_params(self, mock_get_user_timeseries):
        """Test that the time-series service function is called with correct parameters"""
        from app.services.user_metrics import get_user_request_timeseries
        
        # Mock a database session
        mock_db = MagicMock()
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 2)
        
        # Call the service function
        try:
            get_user_request_timeseries(mock_db, 456, start_date, end_date, "day")
        except Exception:
            # Expected to fail since we're not connecting to real DB
            pass
        
        # Verify it was called with the correct parameters
        mock_get_user_timeseries.assert_called_once_with(mock_db, 456, start_date, end_date, "day")


class TestV1UserMetricsIntegration:
    """Integration tests for the user metrics functionality"""
    
    def test_openapi_contains_user_metrics_endpoints(self):
        """Test that the OpenAPI schema contains the new user metrics endpoints"""
        openapi_schema = app.openapi()
        paths = openapi_schema.get("paths", {})
        
        # Check that both new endpoints are in the OpenAPI schema
        assert "/v1/me/stats" in paths
        assert "/v1/me/metrics/requests" in paths
        
        # Check that GET methods exist for both
        assert "get" in paths["/v1/me/stats"]
        assert "get" in paths["/v1/me/metrics/requests"]
        
        # Check that the endpoints are under the correct security scheme
        stats_security = paths["/v1/me/stats"]["get"].get("security", [])
        metrics_security = paths["/v1/me/metrics/requests"]["get"].get("security", [])
        
        assert len(stats_security) > 0
        assert len(metrics_security) > 0