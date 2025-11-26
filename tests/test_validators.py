"""
Unit tests for field validators.

Tests:
- Aadhaar validation (including Telugu digits)
- Mobile validation (with/without prefix)
- PIN validation
- DOB validation (including future dates)
"""

import pytest
from datetime import datetime, timedelta
from core.validators import (
    validate_aadhaar,
    validate_mobile,
    validate_pin,
    validate_dob,
    ValidationResult
)


class TestValidateAadhaar:
    """Tests for validate_aadhaar function."""
    
    def test_valid_aadhaar(self):
        """Test valid Aadhaar numbers."""
        result = validate_aadhaar("123456789012")
        assert result.valid is True
        assert result.normalized == "123456789012"
        assert "Valid" in result.notes
    
    def test_valid_aadhaar_with_spaces(self):
        """Test valid Aadhaar with spaces."""
        result = validate_aadhaar("1234 5678 9012")
        assert result.valid is True
        assert result.normalized == "123456789012"
    
    def test_valid_aadhaar_with_hyphens(self):
        """Test valid Aadhaar with hyphens."""
        result = validate_aadhaar("1234-5678-9012")
        assert result.valid is True
        assert result.normalized == "123456789012"
    
    def test_valid_aadhaar_telugu_digits(self):
        """Test valid Aadhaar with Telugu digits."""
        result = validate_aadhaar("౧౨౩౪౫౬౭౮౯౦౧౨")
        assert result.valid is True
        assert result.normalized == "123456789012"
    
    def test_invalid_aadhaar_too_short(self):
        """Test invalid Aadhaar (too short)."""
        result = validate_aadhaar("12345")
        assert result.valid is False
        assert result.normalized is None
        assert "12 digits" in result.notes
    
    def test_invalid_aadhaar_too_long(self):
        """Test invalid Aadhaar (too long)."""
        result = validate_aadhaar("1234567890123")
        assert result.valid is False
        assert result.normalized is None
    
    def test_invalid_aadhaar_with_letters(self):
        """Test invalid Aadhaar with letters."""
        result = validate_aadhaar("12345678901A")
        assert result.valid is False
        assert result.normalized is None
    
    def test_none_aadhaar(self):
        """Test None Aadhaar."""
        result = validate_aadhaar(None)
        assert result.valid is None
        assert result.normalized is None
        assert "not found" in result.notes


class TestValidateMobile:
    """Tests for validate_mobile function."""
    
    def test_valid_mobile_10_digits(self):
        """Test valid 10-digit mobile."""
        result = validate_mobile("9876543210")
        assert result.valid is True
        assert result.normalized == "+919876543210"
    
    def test_valid_mobile_with_plus_91(self):
        """Test valid mobile with +91 prefix."""
        result = validate_mobile("+919876543210")
        assert result.valid is True
        assert result.normalized == "+919876543210"
    
    def test_valid_mobile_with_91(self):
        """Test valid mobile with 91 prefix (no +)."""
        result = validate_mobile("919876543210")
        assert result.valid is True
        assert result.normalized == "+919876543210"
    
    def test_valid_mobile_telugu_digits(self):
        """Test valid mobile with Telugu digits."""
        result = validate_mobile("౯౮౭౬౫౪౩౨౧౦")
        assert result.valid is True
        assert result.normalized == "+919876543210"
    
    def test_valid_mobile_starts_with_6(self):
        """Test valid mobile starting with 6."""
        result = validate_mobile("6123456789")
        assert result.valid is True
        assert result.normalized == "+916123456789"
    
    def test_valid_mobile_starts_with_7(self):
        """Test valid mobile starting with 7."""
        result = validate_mobile("7123456789")
        assert result.valid is True
        assert result.normalized == "+917123456789"
    
    def test_valid_mobile_starts_with_8(self):
        """Test valid mobile starting with 8."""
        result = validate_mobile("8123456789")
        assert result.valid is True
        assert result.normalized == "+918123456789"
    
    def test_invalid_mobile_starts_with_5(self):
        """Test invalid mobile starting with 5."""
        result = validate_mobile("5876543210")
        assert result.valid is False
        assert result.normalized is None
        assert "start with 6-9" in result.notes
    
    def test_invalid_mobile_too_short(self):
        """Test invalid mobile (too short)."""
        result = validate_mobile("987654321")
        assert result.valid is False
        assert result.normalized is None
        assert "too short" in result.notes
    
    def test_invalid_mobile_too_long(self):
        """Test invalid mobile (too long)."""
        result = validate_mobile("98765432101234")
        assert result.valid is False
        assert result.normalized is None
        assert "too long" in result.notes
    
    def test_none_mobile(self):
        """Test None mobile."""
        result = validate_mobile(None)
        assert result.valid is None
        assert result.normalized is None
        assert "not found" in result.notes


class TestValidatePin:
    """Tests for validate_pin function."""
    
    def test_valid_pin(self):
        """Test valid PIN code."""
        result = validate_pin("500001")
        assert result.valid is True
        assert result.normalized == "500001"
    
    def test_valid_pin_telugu_digits(self):
        """Test valid PIN with Telugu digits."""
        result = validate_pin("౫౦౦౦౦౧")
        assert result.valid is True
        assert result.normalized == "500001"
    
    def test_valid_pin_with_spaces(self):
        """Test valid PIN with spaces."""
        result = validate_pin("500 001")
        assert result.valid is True
        assert result.normalized == "500001"
    
    def test_invalid_pin_too_short(self):
        """Test invalid PIN (too short)."""
        result = validate_pin("12345")
        assert result.valid is False
        assert result.normalized is None
        assert "6 digits" in result.notes
    
    def test_invalid_pin_too_long(self):
        """Test invalid PIN (too long)."""
        result = validate_pin("1234567")
        assert result.valid is False
        assert result.normalized is None
    
    def test_invalid_pin_with_letters(self):
        """Test invalid PIN with letters."""
        result = validate_pin("50000A")
        assert result.valid is False
        assert result.normalized is None
    
    def test_none_pin(self):
        """Test None PIN."""
        result = validate_pin(None)
        assert result.valid is None
        assert result.normalized is None
        assert "not found" in result.notes


class TestValidateDob:
    """Tests for validate_dob function."""
    
    def test_valid_dob(self):
        """Test valid date of birth."""
        result = validate_dob("1990-05-15")
        assert result.valid is True
        assert result.normalized == "1990-05-15"
    
    def test_valid_dob_recent(self):
        """Test valid recent date of birth."""
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        result = validate_dob(yesterday)
        assert result.valid is True
        assert result.normalized == yesterday
    
    def test_invalid_dob_future(self):
        """Test invalid future date of birth."""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        result = validate_dob(tomorrow)
        assert result.valid is False
        assert result.normalized is None
        assert "future" in result.notes
    
    def test_invalid_dob_too_old(self):
        """Test invalid date of birth (too old)."""
        result = validate_dob("1850-01-01")
        assert result.valid is False
        assert result.normalized is None
        assert "too old" in result.notes
    
    def test_invalid_dob_format(self):
        """Test invalid date format."""
        result = validate_dob("1990-13-45")
        assert result.valid is False
        assert result.normalized is None
        assert "Invalid" in result.notes
    
    def test_invalid_dob_wrong_format(self):
        """Test wrong date format."""
        result = validate_dob("15/05/1990")
        assert result.valid is False
        assert result.normalized is None
    
    def test_none_dob(self):
        """Test None DOB."""
        result = validate_dob(None)
        assert result.valid is None
        assert result.normalized is None
        assert "not found" in result.notes


class TestValidationResult:
    """Tests for ValidationResult dataclass."""
    
    def test_validation_result_creation(self):
        """Test creating ValidationResult."""
        result = ValidationResult(
            normalized="123456789012",
            valid=True,
            notes="Test note"
        )
        assert result.normalized == "123456789012"
        assert result.valid is True
        assert result.notes == "Test note"
    
    def test_validation_result_none_values(self):
        """Test ValidationResult with None values."""
        result = ValidationResult(
            normalized=None,
            valid=None,
            notes="Not found"
        )
        assert result.normalized is None
        assert result.valid is None
        assert result.notes == "Not found"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
