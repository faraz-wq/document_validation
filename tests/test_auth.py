import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.utils.auth import get_current_user, get_user_from_api_key


class TestAuth:
    """Test cases for the authentication functions"""

    def test_get_current_user(self):
        """Test getting current user (placeholder function)"""
        user = get_current_user()
        
        # The placeholder function returns a default user
        assert user["user_id"] == "default_user"
        assert user["username"] == "default_user"

    def test_get_user_from_api_key_valid_key(self):
        """Test getting user from valid API key"""
        # Valid API key should be longer than 5 characters
        valid_api_key = "valid_api_key_12345"
        
        user = get_user_from_api_key(valid_api_key)
        
        # Should return a user object with computed user ID
        assert "user_id" in user
        assert "username" in user
        assert user["user_id"].startswith("user_")
        assert user["username"].startswith("user_")

    def test_get_user_from_api_key_invalid_short_key(self):
        """Test getting user from invalid short API key"""
        # Short API key should be rejected
        short_api_key = "short"
        
        with pytest.raises(HTTPException) as exc_info:
            get_user_from_api_key(short_api_key)
        
        assert exc_info.value.status_code == 401
        assert "Invalid API key" in exc_info.value.detail

    def test_get_user_from_api_key_empty_key(self):
        """Test getting user from empty API key"""
        # Empty API key should be rejected
        with pytest.raises(HTTPException) as exc_info:
            get_user_from_api_key("")
        
        assert exc_info.value.status_code == 401
        assert "Invalid API key" in exc_info.value.detail

    def test_get_user_from_api_key_none_key(self):
        """Test getting user from None API key"""
        # None API key should be rejected
        with pytest.raises(HTTPException) as exc_info:
            get_user_from_api_key(None)
        
        assert exc_info.value.status_code == 401
        assert "Invalid API key" in exc_info.value.detail

    def test_api_key_hashing_consistency(self):
        """Test that the same API key always produces the same user ID"""
        api_key = "consistent_test_key_12345"
        
        user1 = get_user_from_api_key(api_key)
        user2 = get_user_from_api_key(api_key)
        
        # The same API key should result in the same user ID
        assert user1["user_id"] == user2["user_id"]
        assert user1["username"] == user2["username"]

    def test_different_api_keys_produce_different_users(self):
        """Test that different API keys produce different user IDs"""
        api_key1 = "api_key_12345"
        api_key2 = "api_key_67890"
        
        user1 = get_user_from_api_key(api_key1)
        user2 = get_user_from_api_key(api_key2)
        
        # Different API keys should result in different user IDs
        assert user1["user_id"] != user2["user_id"]
        assert user1["username"] != user2["username"]

    def test_get_user_from_api_key_with_special_characters(self):
        """Test getting user from API key with special characters"""
        api_key = "special!@#$%^&*()_+=-{}[]|\\:;\"'<>?,./"
        
        # If the key is long enough, it should be accepted
        if len(api_key) > 5:
            user = get_user_from_api_key(api_key)
            assert "user_id" in user
            assert "username" in user
        else:
            # If it's too short, it should raise an exception
            with pytest.raises(HTTPException) as exc_info:
                get_user_from_api_key(api_key)
            assert exc_info.value.status_code == 401

    def test_get_user_from_api_key_edge_case_boundary(self):
        """Test API key validation at the length boundary"""
        # 6 characters should work (more than 5)
        api_key_6_chars = "123456"
        user = get_user_from_api_key(api_key_6_chars)
        assert "user_id" in user
        
        # 5 characters should not work (not more than 5)
        api_key_5_chars = "12345"
        with pytest.raises(HTTPException) as exc_info:
            get_user_from_api_key(api_key_5_chars)
        assert exc_info.value.status_code == 401
        
        # 4 characters should not work
        api_key_4_chars = "1234"
        with pytest.raises(HTTPException) as exc_info:
            get_user_from_api_key(api_key_4_chars)
        assert exc_info.value.status_code == 401