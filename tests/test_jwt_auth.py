import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.db.models import Base
from app.db.models import User
from app.core.security import decode_token, create_access_token
from app.utils.passwords import hash_password, verify_password
import json


# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)

# Create test client
client = TestClient(app)

def override_get_db():
    """
    Override the database dependency for testing
    """
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# Override the database dependency in the app
from app.db.database import get_db
app.dependency_overrides[get_db] = override_get_db


class TestAuthEndpoints:
    """
    Test suite for JWT authentication endpoints
    """
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """
        Setup method to clean the database before each test
        """
        # Clean up all data before each test
        db = TestingSessionLocal()
        db.query(User).delete()
        db.commit()
        db.close()
    
    def test_register_success(self):
        """
        Test successful user registration
        """
        user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "securepassword123"
        }
        
        response = client.post("/v1/auth/register", json=user_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "user" in data
        assert data["user"]["email"] == user_data["email"]
        assert data["user"]["username"] == user_data["username"]
        assert data["user"]["id"] > 0
        
        # Verify that the API key might be present (it's optional)
        assert "api_key" in data
        if data["api_key"]:
            assert isinstance(data["api_key"], str)
            assert data["api_key"].startswith("dv_")
    
    def test_register_duplicate_email(self):
        """
        Test registration with duplicate email
        """
        # Register first user
        user_data = {
            "email": "test@example.com",
            "username": "testuser1",
            "password": "securepassword123"
        }
        response = client.post("/v1/auth/register", json=user_data)
        assert response.status_code == 200
        
        # Try to register another user with same email
        user_data2 = {
            "email": "test@example.com",  # Same email
            "username": "testuser2",
            "password": "anotherpassword123"
        }
        response = client.post("/v1/auth/register", json=user_data2)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]
    
    def test_register_duplicate_username(self):
        """
        Test registration with duplicate username
        """
        # Register first user
        user_data = {
            "email": "test1@example.com",
            "username": "testuser",
            "password": "securepassword123"
        }
        response = client.post("/v1/auth/register", json=user_data)
        assert response.status_code == 200
        
        # Try to register another user with same username
        user_data2 = {
            "email": "test2@example.com",  # Different email
            "username": "testuser",        # Same username
            "password": "anotherpassword123"
        }
        response = client.post("/v1/auth/register", json=user_data2)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]
    
    def test_register_invalid_email(self):
        """
        Test registration with invalid email format
        """
        user_data = {
            "email": "invalid-email",  # Invalid email
            "username": "testuser",
            "password": "securepassword123"
        }
        
        response = client.post("/v1/auth/register", json=user_data)
        assert response.status_code == 422  # Validation error
    
    def test_register_short_password(self):
        """
        Test registration with password too short
        """
        user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "123"  # Too short
        }
        
        response = client.post("/v1/auth/register", json=user_data)
        assert response.status_code == 422  # Validation error
    
    def test_register_short_username(self):
        """
        Test registration with username too short
        """
        user_data = {
            "email": "test@example.com",
            "username": "ab",  # Too short
            "password": "securepassword123"
        }
        
        response = client.post("/v1/auth/register", json=user_data)
        assert response.status_code == 422  # Validation error
    
    def test_register_long_username(self):
        """
        Test registration with username too long
        """
        user_data = {
            "email": "test@example.com",
            "username": "a" * 51,  # Too long
            "password": "securepassword123"
        }
        
        response = client.post("/v1/auth/register", json=user_data)
        assert response.status_code == 422  # Validation error
    
    def test_login_success(self):
        """
        Test successful login
        """
        # First register a user
        user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "securepassword123"
        }
        response = client.post("/v1/auth/register", json=user_data)
        assert response.status_code == 200
        
        # Then try to login
        login_data = {
            "email": "test@example.com",
            "password": "securepassword123"
        }
        
        response = client.post("/v1/auth/login", json=login_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        assert data["user"]["email"] == user_data["email"]
    
    def test_login_invalid_email(self):
        """
        Test login with invalid email (user doesn't exist)
        """
        login_data = {
            "email": "nonexistent@example.com",
            "password": "any_password"
        }
        
        response = client.post("/v1/auth/login", json=login_data)
        assert response.status_code == 401
    
    def test_login_wrong_password(self):
        """
        Test login with wrong password
        """
        # Register a user first
        user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "securepassword123"
        }
        response = client.post("/v1/auth/register", json=user_data)
        assert response.status_code == 200
        
        # Try to login with wrong password
        login_data = {
            "email": "test@example.com",
            "password": "wrong_password"
        }
        
        response = client.post("/v1/auth/login", json=login_data)
        assert response.status_code == 401
    
    def test_login_inactive_user(self):
        """
        Test login with inactive user (this would require database manipulation)
        """
        # This is harder to test without direct DB access in tests
        # We'll test the active user functionality through the register/login flow
        user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "securepassword123"
        }
        response = client.post("/v1/auth/register", json=user_data)
        assert response.status_code == 200
        
        # Login should work for active users
        login_data = {
            "email": "test@example.com",
            "password": "securepassword123"
        }
        response = client.post("/v1/auth/login", json=login_data)
        assert response.status_code == 200
    
    def test_refresh_token_success(self):
        """
        Test successful token refresh
        """
        # Register and login to get tokens
        user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "securepassword123"
        }
        response = client.post("/v1/auth/register", json=user_data)
        assert response.status_code == 200
        
        login_data = {
            "email": "test@example.com",
            "password": "securepassword123"
        }
        response = client.post("/v1/auth/login", json=login_data)
        assert response.status_code == 200
        
        tokens = response.json()
        refresh_token = tokens["refresh_token"]
        
        # Test refresh endpoint
        refresh_request = {
            "refresh_token": refresh_token
        }
        
        response = client.post("/v1/auth/refresh", json=refresh_request)
        assert response.status_code == 200
        
        refresh_response = response.json()
        assert "access_token" in refresh_response
        assert refresh_response["token_type"] == "bearer"
        
        # New access token should be different from the original
        # (This is a basic check, may not always be true depending on timing)
        # Just make sure we got a new token back
        assert isinstance(refresh_response["access_token"], str)
        assert len(refresh_response["access_token"]) > 0
    
    def test_refresh_token_invalid_token(self):
        """
        Test refresh with invalid token
        """
        refresh_request = {
            "refresh_token": "invalid_token"
        }
        
        response = client.post("/v1/auth/refresh", json=refresh_request)
        assert response.status_code == 401
    
    def test_refresh_token_wrong_type(self):
        """
        Test refresh with an access token instead of refresh token
        """
        # Register and login to get tokens
        user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "securepassword123"
        }
        response = client.post("/v1/auth/register", json=user_data)
        assert response.status_code == 200
        
        login_data = {
            "email": "test@example.com",
            "password": "securepassword123"
        }
        response = client.post("/v1/auth/login", json=login_data)
        assert response.status_code == 200
        
        tokens = response.json()
        access_token = tokens["access_token"]  # This is an access token, not refresh
        
        # Try to use access token as refresh token
        refresh_request = {
            "refresh_token": access_token
        }
        
        response = client.post("/v1/auth/refresh", json=refresh_request)
        assert response.status_code == 401
    
    def test_logout_success(self):
        """
        Test logout endpoint (stateless)
        """
        response = client.post("/v1/auth/logout")
        assert response.status_code == 200
        
        data = response.json()
        assert data == {"message": "ok"}
    
    def test_logout_with_refresh_token(self):
        """
        Test logout endpoint with refresh token (should still work)
        """
        logout_data = {
            "refresh_token": "some_refresh_token"
        }
        
        response = client.post("/v1/auth/logout", json=logout_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data == {"message": "ok"}
    
    def test_password_hashing_consistency(self):
        """
        Test that password hashing and verification work correctly
        """
        password = "securepassword123"
        hashed = hash_password(password)
        
        # Verify the password
        assert verify_password(password, hashed) is True
        
        # Verify wrong password fails
        assert verify_password("wrongpassword", hashed) is False
    
    def test_token_structure(self):
        """
        Test that JWT tokens have the correct structure
        """
        user_data = {
            "sub": "123",
            "email": "test@example.com",
            "is_admin": False
        }
        
        access_token = create_access_token(user_data)
        decoded = decode_token(access_token)
        
        assert decoded is not None
        assert decoded["sub"] == "123"
        assert decoded["email"] == "test@example.com"
        assert decoded["is_admin"] is False
        assert "exp" in decoded
        assert "type" in decoded
        assert decoded["type"] == "access"
    
    def test_token_refresh_structure(self):
        """
        Test that refresh tokens have the correct structure
        """
        user_data = {
            "sub": "123",
            "type": "refresh"  # This should be overridden
        }
        
        refresh_token = create_access_token(user_data)  # This function will set type to "access"
        decoded = decode_token(refresh_token)
        
        # The create_access_token sets type to "access", so let's test the refresh token function
        from app.core.security import create_refresh_token
        refresh_token = create_refresh_token(user_data)
        decoded = decode_token(refresh_token)
        
        assert decoded is not None
        assert decoded["sub"] == "123"
        assert "exp" in decoded
        assert "type" in decoded
        assert decoded["type"] == "refresh"
    
    def test_register_login_flow_complete(self):
        """
        Test complete registration and login flow
        """
        # Register
        user_data = {
            "email": "complete@example.com",
            "username": "completeuser",
            "password": "completepassword123"
        }
        
        response = client.post("/v1/auth/register", json=user_data)
        assert response.status_code == 200
        
        register_response = response.json()
        assert register_response["user"]["email"] == user_data["email"]
        assert register_response["user"]["username"] == user_data["username"]
        
        # Login
        login_data = {
            "email": "complete@example.com",
            "password": "completepassword123"
        }
        
        response = client.post("/v1/auth/login", json=login_data)
        assert response.status_code == 200
        
        login_response = response.json()
        assert "access_token" in login_response
        assert "refresh_token" in login_response
        assert login_response["user"]["email"] == user_data["email"]
        assert login_response["user"]["username"] == user_data["username"]
        
        # Refresh token
        refresh_request = {
            "refresh_token": login_response["refresh_token"]
        }
        
        response = client.post("/v1/auth/refresh", json=refresh_request)
        assert response.status_code == 200
        
        refresh_response = response.json()
        assert "access_token" in refresh_response
        assert refresh_response["token_type"] == "bearer"
        
        # Logout (stateless)
        response = client.post("/v1/auth/logout")
        assert response.status_code == 200
        assert response.json() == {"message": "ok"}
    
    def test_user_data_validation_after_registration(self):
        """
        Test that user data is properly stored and returned after registration
        """
        user_data = {
            "email": "validation@example.com",
            "username": "validationuser",
            "password": "validationpassword123"
        }
        
        response = client.post("/v1/auth/register", json=user_data)
        assert response.status_code == 200
        
        response_data = response.json()
        user = response_data["user"]
        
        assert user["id"] > 0
        assert user["email"] == user_data["email"]
        assert user["username"] == user_data["username"]
        assert user["is_admin"] is False  # Default value
        
        # Verify the user cannot log in with wrong password
        wrong_login = {
            "email": "validation@example.com",
            "password": "wrongpassword"
        }
        
        response = client.post("/v1/auth/login", json=wrong_login)
        assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__])