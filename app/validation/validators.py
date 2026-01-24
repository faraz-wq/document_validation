"""
Core validation functions for document data.
"""

from typing import Any, List, Optional
import re
from datetime import datetime

def validate_required(value: Any) -> bool:
    """Check if a value is present and not empty."""
    if value is None:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    if isinstance(value, list) and not value:
        return False
    if isinstance(value, dict) and not value:
        return False
    return True

def validate_date_format(value: str) -> bool:
    """Check if a date string follows common formats (DD/MM/YYYY, YYYY-MM-DD)."""
    if not value or not isinstance(value, str):
        return False
    
    formats = ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"]
    for fmt in formats:
        try:
            datetime.strptime(value, fmt)
            return True
        except ValueError:
            continue
    return False

def validate_phone(value: str) -> bool:
    """Check if a string looks like a phone number."""
    if not value or not isinstance(value, str):
        return False
    # Simple regex for 10 digits
    return bool(re.match(r'^\+?[\d\s-]{10,}$', value))

def validate_aadhaar(value: str) -> bool:
    """Check if a string looks like an Aadhaar number (12 digits)."""
    if not value or not isinstance(value, str):
        return False
    clean_value = re.sub(r'[\s-]', '', value)
    return bool(re.match(r'^\d{12}$', clean_value))

def validate_income(value: Any) -> bool:
    """Check if a value looks like a valid income amount."""
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return value >= 0
    if isinstance(value, str):
        # Remove currency symbols and commas
        clean_value = re.sub(r'[^\d.]', '', value)
        try:
            float(clean_value)
            return True
        except ValueError:
            return False
    return False

def generate_validation_summary_deterministic(issues: List[Any], auto_approved: bool) -> str:
    """
    Generate a deterministic natural language summary of validation issues.
    Replaces the Gemini-based summary for more consistent and faster results.
    """
    if auto_approved and not issues:
        return "Extraction complete. All mandatory fields and rules are satisfied."
    
    if auto_approved:
        warnings = [i for i in issues if i.severity == 'warning']
        if warnings:
            return f"Extraction successful with {len(warnings)} minor observation(s) requiring manual verification."
        return "Extraction complete. Some non-critical fields may require review."

    errors = [i for i in issues if i.severity == 'error']
    if not errors:
        return "Extraction successful. Please review the details."
    
    # Sort errors by importance (this is a simple implementation)
    # Pick the first few to mention
    error_fields = []
    for error in errors[:3]:
        field_name = str(error.field).replace('_', ' ').title()
        error_fields.append(field_name)
    
    msg = f"Critical validation failed: Missing or invalid {', '.join(error_fields)}"
    if len(errors) > 3:
        msg += f" and {len(errors) - 3} other fields"
    msg += ". Manual audit required."
    
    return msg
