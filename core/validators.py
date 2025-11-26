"""
Field validation functions for critical document fields.

Validates:
- Aadhaar numbers (12 digits)
- Indian mobile numbers (10 digits starting with 6-9)
- PIN codes (6 digits)
- Dates of birth (ISO format, not future-dated)
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .telugu_utils import normalize_digits


@dataclass
class ValidationResult:
    """Result of a field validation."""
    normalized: Optional[str]  # Normalized value (None if invalid)
    valid: Optional[bool]       # True if valid, False if invalid, None if not found
    notes: str                  # Explanation of validation result


def validate_aadhaar(value: Optional[str]) -> ValidationResult:
    r"""
    Validate Aadhaar number.
    
    Rules:
        - Exactly 12 digits after normalization
        - Regex: ^\d{12}$
        
    Args:
        value: Aadhaar number (may contain Telugu/Devanagari digits)
        
    Returns:
        ValidationResult with normalized value and validation status
        
    Examples:
        >>> validate_aadhaar("123456789012")
        ValidationResult(normalized='123456789012', valid=True, notes='Valid 12-digit Aadhaar')
        >>> validate_aadhaar("౧౨౩౪౫౬౭౮౯౦౧౨")
        ValidationResult(normalized='123456789012', valid=True, notes='Valid 12-digit Aadhaar')
        >>> validate_aadhaar("12345")
        ValidationResult(normalized=None, valid=False, notes='Invalid Aadhaar: must be exactly 12 digits')
    """
    if not value:
        return ValidationResult(
            normalized=None,
            valid=None,
            notes="Aadhaar not found"
        )
    
    # Normalize digits (Telugu/Devanagari → ASCII)
    normalized = normalize_digits(str(value))
    
    # Remove spaces and hyphens (common formatting)
    normalized = normalized.replace(" ", "").replace("-", "")
    
    # Validate: exactly 12 digits
    if re.match(r'^\d{12}$', normalized):
        return ValidationResult(
            normalized=normalized,
            valid=True,
            notes="Valid 12-digit Aadhaar"
        )
    else:
        return ValidationResult(
            normalized=None,
            valid=False,
            notes=f"Invalid Aadhaar: must be exactly 12 digits (got {len(normalized)} characters)"
        )


def validate_mobile(value: Optional[str]) -> ValidationResult:
    r"""
    Validate Indian mobile number.
    
    Rules:
        - 10 digits starting with 6-9
        - Optionally prefixed with +91 or 91
        - Regex: ^[6-9]\d{9}$ or ^\+91[6-9]\d{9}$
        
    Args:
        value: Mobile number (may contain Telugu/Devanagari digits)
        
    Returns:
        ValidationResult with normalized value (in +91XXXXXXXXXX format)
        
    Examples:
        >>> validate_mobile("9876543210")
        ValidationResult(normalized='+919876543210', valid=True, notes='Valid Indian mobile')
        >>> validate_mobile("+919876543210")
        ValidationResult(normalized='+919876543210', valid=True, notes='Valid Indian mobile')
        >>> validate_mobile("5876543210")
        ValidationResult(normalized=None, valid=False, notes='Invalid mobile: must start with 6-9')
    """
    if not value:
        return ValidationResult(
            normalized=None,
            valid=None,
            notes="Mobile number not found"
        )
    
    # Normalize digits
    normalized = normalize_digits(str(value))
    
    # Remove spaces, hyphens, parentheses (common formatting)
    normalized = normalized.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    
    # Try with +91 prefix
    if re.match(r'^\+91[6-9]\d{9}$', normalized):
        return ValidationResult(
            normalized=normalized,
            valid=True,
            notes="Valid Indian mobile with +91 prefix"
        )
    
    # Try with 91 prefix (no +)
    if re.match(r'^91[6-9]\d{9}$', normalized):
        normalized_with_plus = f"+{normalized}"
        return ValidationResult(
            normalized=normalized_with_plus,
            valid=True,
            notes="Valid Indian mobile, added + to prefix"
        )
    
    # Try without prefix
    if re.match(r'^[6-9]\d{9}$', normalized):
        normalized_with_prefix = f"+91{normalized}"
        return ValidationResult(
            normalized=normalized_with_prefix,
            valid=True,
            notes="Valid Indian mobile, added +91 prefix"
        )
    
    # Check common error cases
    if len(normalized) < 10:
        notes = f"Invalid mobile: too short (got {len(normalized)} digits, need 10)"
    elif len(normalized) > 12:
        notes = f"Invalid mobile: too long (got {len(normalized)} digits)"
    elif normalized[0] not in '6789':
        notes = "Invalid mobile: must start with 6-9"
    else:
        notes = "Invalid mobile format"
    
    return ValidationResult(
        normalized=None,
        valid=False,
        notes=notes
    )


def validate_pin(value: Optional[str]) -> ValidationResult:
    r"""
    Validate Indian PIN code.
    
    Rules:
        - Exactly 6 digits
        - Regex: ^\d{6}$
        
    Args:
        value: PIN code (may contain Telugu/Devanagari digits)
        
    Returns:
        ValidationResult with normalized value
        
    Examples:
        >>> validate_pin("500001")
        ValidationResult(normalized='500001', valid=True, notes='Valid 6-digit PIN')
        >>> validate_pin("౫౦౦౦౦౧")
        ValidationResult(normalized='500001', valid=True, notes='Valid 6-digit PIN')
        >>> validate_pin("12345")
        ValidationResult(normalized=None, valid=False, notes='Invalid PIN: must be exactly 6 digits')
    """
    if not value:
        return ValidationResult(
            normalized=None,
            valid=None,
            notes="PIN code not found"
        )
    
    # Normalize digits
    normalized = normalize_digits(str(value))
    
    # Remove spaces and hyphens
    normalized = normalized.replace(" ", "").replace("-", "")
    
    # Validate: exactly 6 digits
    if re.match(r'^\d{6}$', normalized):
        return ValidationResult(
            normalized=normalized,
            valid=True,
            notes="Valid 6-digit PIN"
        )
    else:
        return ValidationResult(
            normalized=None,
            valid=False,
            notes=f"Invalid PIN: must be exactly 6 digits (got {len(normalized)} characters)"
        )


def validate_dob(value: Optional[str]) -> ValidationResult:
    """
    Validate date of birth.
    
    Rules:
        - ISO format: YYYY-MM-DD
        - Must not be in the future
        - Must be a valid date
        
    Args:
        value: Date of birth in ISO format
        
    Returns:
        ValidationResult with normalized value
        
    Examples:
        >>> validate_dob("1990-05-15")
        ValidationResult(normalized='1990-05-15', valid=True, notes='Valid date of birth')
        >>> validate_dob("2030-01-01")
        ValidationResult(normalized=None, valid=False, notes='Invalid DOB: date is in the future')
        >>> validate_dob("1990-13-45")
        ValidationResult(normalized=None, valid=False, notes='Invalid DOB: invalid date format')
    """
    if not value:
        return ValidationResult(
            normalized=None,
            valid=None,
            notes="Date of birth not found"
        )
    
    try:
        # Parse date
        dob = datetime.fromisoformat(str(value))
        today = datetime.now()
        
        # Check if future-dated
        if dob > today:
            return ValidationResult(
                normalized=None,
                valid=False,
                notes="Invalid DOB: date is in the future"
            )
        
        # Check if too old (e.g., before 1900)
        if dob.year < 1900:
            return ValidationResult(
                normalized=None,
                valid=False,
                notes=f"Invalid DOB: year {dob.year} is too old (before 1900)"
            )
        
        # Valid date
        return ValidationResult(
            normalized=value,
            valid=True,
            notes="Valid date of birth"
        )
        
    except ValueError as e:
        return ValidationResult(
            normalized=None,
            valid=False,
            notes=f"Invalid DOB: {str(e)}"
        )


if __name__ == "__main__":
    # Test the validators
    print("Testing Validators:")
    print("=" * 60)
    
    # Test Aadhaar
    print("\nAadhaar Validation:")
    aadhaar_tests = [
        "123456789012",
        "౧౨౩౪౫౬౭౮౯౦౧౨",
        "1234 5678 9012",
        "12345",
        None,
    ]
    for test in aadhaar_tests:
        result = validate_aadhaar(test)
        print(f"  {test} → {result.valid} ({result.notes})")
    
    # Test Mobile
    print("\nMobile Validation:")
    mobile_tests = [
        "9876543210",
        "+919876543210",
        "919876543210",
        "౯౮౭౬౫౪౩౨౧౦",
        "5876543210",
        "987654321",
        None,
    ]
    for test in mobile_tests:
        result = validate_mobile(test)
        print(f"  {test} → {result.valid} ({result.normalized})")
    
    # Test PIN
    print("\nPIN Validation:")
    pin_tests = [
        "500001",
        "౫౦౦౦౦౧",
        "12345",
        None,
    ]
    for test in pin_tests:
        result = validate_pin(test)
        print(f"  {test} → {result.valid} ({result.notes})")
    
    # Test DOB
    print("\nDOB Validation:")
    dob_tests = [
        "1990-05-15",
        "2030-01-01",
        "1990-13-45",
        "1850-01-01",
        None,
    ]
    for test in dob_tests:
        result = validate_dob(test)
        print(f"  {test} → {result.valid} ({result.notes})")
    
    print("\n" + "=" * 60)
