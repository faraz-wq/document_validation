"""
Telugu text processing utilities.

Provides functions for:
- Normalizing Telugu and Devanagari digits to ASCII
- Detecting language (Telugu, English, or mixed)
"""

# Telugu digit mapping (౦–౯ → 0-9)
TELUGU_DIGITS = {
    '౦': '0',
    '౧': '1',
    '౨': '2',
    '౩': '3',
    '౪': '4',
    '౫': '5',
    '౬': '6',
    '౭': '7',
    '౮': '8',
    '౯': '9',
}

# Devanagari digit mapping (०–९ → 0-9)
DEVANAGARI_DIGITS = {
    '०': '0',
    '१': '1',
    '२': '2',
    '३': '3',
    '४': '4',
    '५': '5',
    '६': '6',
    '७': '7',
    '८': '8',
    '९': '9',
}

# Telugu Unicode range: U+0C00 to U+0C7F
TELUGU_UNICODE_START = 0x0C00
TELUGU_UNICODE_END = 0x0C7F


def normalize_digits(text: str) -> str:
    """
    Normalize Telugu and Devanagari digits to ASCII digits.
    
    Args:
        text: Input text containing Telugu/Devanagari digits
        
    Returns:
        Text with all Telugu and Devanagari digits replaced by ASCII digits
        
    Examples:
        >>> normalize_digits("౧౨౩౪౫౬౭౮౯౦")
        "1234567890"
        >>> normalize_digits("Phone: ౯౮౭౬౫౪౩౨౧౦")
        "Phone: 9876543210"
        >>> normalize_digits("Aadhaar: ०१२३४५६७८९०१")
        "Aadhaar: 012345678901"
    """
    if not text:
        return text
    
    result = text
    
    # Replace Telugu digits
    for telugu_digit, ascii_digit in TELUGU_DIGITS.items():
        result = result.replace(telugu_digit, ascii_digit)
    
    # Replace Devanagari digits
    for devanagari_digit, ascii_digit in DEVANAGARI_DIGITS.items():
        result = result.replace(devanagari_digit, ascii_digit)
    
    return result


def detect_language(text: str) -> str:
    """
    Detect if text is Telugu, English, or mixed.
    
    Args:
        text: Input text to analyze
        
    Returns:
        "te" for Telugu, "en" for English, "mixed" for mixed content
        
    Examples:
        >>> detect_language("Hello World")
        "en"
        >>> detect_language("హలో వరల్డ్")
        "te"
        >>> detect_language("Hello హలో")
        "mixed"
        >>> detect_language("123456")
        "en"
    """
    if not text:
        return "en"
    
    # Count Telugu characters
    telugu_chars = sum(
        1 for char in text
        if TELUGU_UNICODE_START <= ord(char) <= TELUGU_UNICODE_END
    )
    
    # Count total alphabetic characters (excluding digits, punctuation, etc.)
    total_alpha_chars = sum(1 for char in text if char.isalpha())
    
    # If no alphabetic characters, default to English
    if total_alpha_chars == 0:
        return "en"
    
    # Count non-Telugu alphabetic characters
    non_telugu_alpha_chars = total_alpha_chars - telugu_chars
    
    # Determine language based on presence of both scripts
    if telugu_chars > 0 and non_telugu_alpha_chars > 0:
        # Has both Telugu and non-Telugu alphabetic characters
        return "mixed"
    elif telugu_chars > 0:
        # Only Telugu characters
        return "te"
    else:
        # Only non-Telugu characters (English, etc.)
        return "en"



def is_telugu_text(text: str) -> bool:
    """
    Check if text contains any Telugu characters.
    
    Args:
        text: Input text to check
        
    Returns:
        True if text contains Telugu characters, False otherwise
        
    Examples:
        >>> is_telugu_text("Hello")
        False
        >>> is_telugu_text("హలో")
        True
        >>> is_telugu_text("Hello హలో")
        True
    """
    if not text:
        return False
    
    return any(
        TELUGU_UNICODE_START <= ord(char) <= TELUGU_UNICODE_END
        for char in text
    )


def extract_telugu_chars(text: str) -> str:
    """
    Extract only Telugu characters from text.
    
    Args:
        text: Input text
        
    Returns:
        String containing only Telugu characters
        
    Examples:
        >>> extract_telugu_chars("Hello హలో World")
        "హలో"
        >>> extract_telugu_chars("123 హలో 456")
        "హలో"
    """
    if not text:
        return ""
    
    return "".join(
        char for char in text
        if TELUGU_UNICODE_START <= ord(char) <= TELUGU_UNICODE_END
    )


if __name__ == "__main__":
    # Test the functions
    print("Testing Telugu Utils:")
    print("=" * 60)
    
    # Test normalize_digits
    test_cases = [
        "౧౨౩౪౫౬౭౮౯౦",
        "Phone: ౯౮౭౬౫౪౩౨౧౦",
        "Aadhaar: ०१२३४५६७८९०१",
        "Mixed: ౧౨౩ and ०१२",
    ]
    
    print("\nDigit Normalization:")
    for test in test_cases:
        normalized = normalize_digits(test)
        print(f"  {test} → {normalized}")
    
    # Test detect_language
    lang_tests = [
        "Hello World",
        "హలో వరల్డ్",
        "Hello హలో",
        "123456",
    ]
    
    print("\nLanguage Detection:")
    for test in lang_tests:
        lang = detect_language(test)
        print(f"  '{test}' → {lang}")
    
    print("\n" + "=" * 60)
