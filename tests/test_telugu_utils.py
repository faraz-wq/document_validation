"""
Unit tests for Telugu utilities.

Tests:
- Telugu digit normalization
- Devanagari digit normalization
- Language detection
- Telugu text extraction
"""

import pytest
from core.telugu_utils import (
    normalize_digits,
    detect_language,
    is_telugu_text,
    extract_telugu_chars
)


class TestNormalizeDigits:
    """Tests for normalize_digits function."""
    
    def test_telugu_digits(self):
        """Test Telugu digit normalization."""
        assert normalize_digits("౦") == "0"
        assert normalize_digits("౧") == "1"
        assert normalize_digits("౨") == "2"
        assert normalize_digits("౩") == "3"
        assert normalize_digits("౪") == "4"
        assert normalize_digits("౫") == "5"
        assert normalize_digits("౬") == "6"
        assert normalize_digits("౭") == "7"
        assert normalize_digits("౮") == "8"
        assert normalize_digits("౯") == "9"
    
    def test_telugu_number_sequence(self):
        """Test Telugu number sequence."""
        assert normalize_digits("౧౨౩౪౫౬౭౮౯౦") == "1234567890"
    
    def test_devanagari_digits(self):
        """Test Devanagari digit normalization."""
        assert normalize_digits("०") == "0"
        assert normalize_digits("१") == "1"
        assert normalize_digits("२") == "2"
        assert normalize_digits("३") == "3"
        assert normalize_digits("४") == "4"
        assert normalize_digits("५") == "5"
        assert normalize_digits("६") == "6"
        assert normalize_digits("७") == "7"
        assert normalize_digits("८") == "8"
        assert normalize_digits("९") == "9"
    
    def test_devanagari_number_sequence(self):
        """Test Devanagari number sequence."""
        assert normalize_digits("०१२३४५६७८९") == "0123456789"
    
    def test_mixed_text(self):
        """Test normalization in mixed text."""
        assert normalize_digits("Phone: ౯౮౭౬౫౪౩౨౧౦") == "Phone: 9876543210"
        assert normalize_digits("Aadhaar: ०१२३४५६७८९०१") == "Aadhaar: 012345678901"
    
    def test_mixed_telugu_devanagari(self):
        """Test mixed Telugu and Devanagari digits."""
        assert normalize_digits("౧౨౩ and ०१२") == "123 and 012"
    
    def test_empty_string(self):
        """Test empty string."""
        assert normalize_digits("") == ""
    
    def test_no_digits(self):
        """Test text with no digits."""
        assert normalize_digits("Hello World") == "Hello World"
    
    def test_ascii_digits_unchanged(self):
        """Test that ASCII digits are unchanged."""
        assert normalize_digits("1234567890") == "1234567890"


class TestDetectLanguage:
    """Tests for detect_language function."""
    
    def test_english_text(self):
        """Test English text detection."""
        assert detect_language("Hello World") == "en"
        assert detect_language("This is a test") == "en"
    
    def test_telugu_text(self):
        """Test Telugu text detection."""
        assert detect_language("హలో వరల్డ్") == "te"
        assert detect_language("తెలుగు భాష") == "te"
    
    def test_mixed_text(self):
        """Test mixed language detection."""
        assert detect_language("Hello హలో") == "mixed"
        assert detect_language("Test తెలుగు") == "mixed"
    
    def test_numbers_only(self):
        """Test numbers-only text."""
        assert detect_language("123456") == "en"
        assert detect_language("౧౨౩౪౫౬") == "en"  # Telugu digits, but no alpha chars
    
    def test_empty_string(self):
        """Test empty string."""
        assert detect_language("") == "en"
    
    def test_punctuation_only(self):
        """Test punctuation-only text."""
        assert detect_language(".,!?") == "en"


class TestIsTeluguText:
    """Tests for is_telugu_text function."""
    
    def test_telugu_text(self):
        """Test Telugu text detection."""
        assert is_telugu_text("హలో") is True
        assert is_telugu_text("తెలుగు") is True
    
    def test_english_text(self):
        """Test English text detection."""
        assert is_telugu_text("Hello") is False
        assert is_telugu_text("World") is False
    
    def test_mixed_text(self):
        """Test mixed text detection."""
        assert is_telugu_text("Hello హలో") is True
    
    def test_empty_string(self):
        """Test empty string."""
        assert is_telugu_text("") is False
    
    def test_numbers_only(self):
        """Test numbers-only text."""
        assert is_telugu_text("123456") is False


class TestExtractTeluguChars:
    """Tests for extract_telugu_chars function."""
    
    def test_pure_telugu(self):
        """Test pure Telugu text."""
        text = "హలో"
        assert extract_telugu_chars(text) == "హలో"
    
    def test_mixed_text(self):
        """Test mixed text."""
        text = "Hello హలో World"
        assert extract_telugu_chars(text) == "హలో"
    
    def test_english_only(self):
        """Test English-only text."""
        text = "Hello World"
        assert extract_telugu_chars(text) == ""
    
    def test_empty_string(self):
        """Test empty string."""
        assert extract_telugu_chars("") == ""
    
    def test_numbers_and_telugu(self):
        """Test numbers with Telugu."""
        text = "123 హలో 456"
        assert extract_telugu_chars(text) == "హలో"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
