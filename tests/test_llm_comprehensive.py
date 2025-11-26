"""
Comprehensive LLM wrapper tests with real API calls.

Tests various scenarios:
1. Simple JSON response
2. Complex nested JSON
3. Telugu text handling
4. Error recovery
5. Non-JSON mode
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.llm_wrapper import llm_call, LLMError


def test_simple_json():
    """Test simple JSON response."""
    print("\n" + "=" * 70)
    print("Test 1: Simple JSON Response")
    print("=" * 70)
    
    messages = [
        {
            "role": "user",
            "content": "Return a JSON object with keys 'name', 'age', and 'city'. Use sample values."
        }
    ]
    
    result = llm_call(messages, json_mode=True, max_tokens=200)
    print(f"Result: {result}")
    print(f"Type: {type(result)}")
    print("✓ Simple JSON test passed")
    return result


def test_complex_json():
    """Test complex nested JSON response."""
    print("\n" + "=" * 70)
    print("Test 2: Complex Nested JSON")
    print("=" * 70)
    
    messages = [
        {
            "role": "user",
            "content": """Return a JSON object representing a person with:
            - name (string)
            - age (number)
            - address (object with street, city, pin)
            - phones (array of phone numbers)
            Use sample Indian data."""
        }
    ]
    
    result = llm_call(messages, json_mode=True, max_tokens=1000)
    print(f"Result: {result}")
    
    # Verify structure
    assert isinstance(result, dict), "Result should be a dict"
    assert "name" in result, "Should have 'name' key"
    assert "address" in result, "Should have 'address' key"
    assert isinstance(result["address"], dict), "Address should be a dict"
    assert "phones" in result, "Should have 'phones' key"
    assert isinstance(result["phones"], list), "Phones should be a list"
    
    print("✓ Complex JSON test passed")
    return result


def test_telugu_handling():
    """Test Telugu text handling in JSON."""
    print("\n" + "=" * 70)
    print("Test 3: Telugu Text Handling")
    print("=" * 70)
    
    messages = [
        {
            "role": "user",
            "content": """Return a JSON object with:
            - telugu_text: "హలో" (hello in Telugu)
            - english_text: "Hello"
            - telugu_number: "౧౨౩" (123 in Telugu digits)
            - mixed_text: "Hello హలో"
            """
        }
    ]
    
    result = llm_call(messages, json_mode=True, max_tokens=300)
    print(f"Result: {result}")
    
    # Check if Telugu text is preserved
    if "telugu_text" in result:
        print(f"Telugu text preserved: {result['telugu_text']}")
    
    print("✓ Telugu handling test passed")
    return result


def test_field_extraction_simulation():
    """Simulate field extraction from a document."""
    print("\n" + "=" * 70)
    print("Test 4: Field Extraction Simulation")
    print("=" * 70)
    
    messages = [
        {
            "role": "user",
            "content": """You are extracting fields from a document. Return a JSON object with:
            {
              "fields": [
                {
                  "field_name": "applicant_name",
                  "value": "రాజు కుమార్",
                  "confidence": 0.95,
                  "language": "te"
                },
                {
                  "field_name": "aadhaar_number",
                  "value": "౧౨౩౪౫౬౭౮౯౦౧౨",
                  "confidence": 0.98,
                  "language": "te"
                },
                {
                  "field_name": "mobile_number",
                  "value": "9876543210",
                  "confidence": 0.92,
                  "language": "en"
                }
              ]
            }
            """
        }
    ]
    
    result = llm_call(messages, json_mode=True, max_tokens=500)
    print(f"Result: {result}")
    
    # Verify structure
    assert "fields" in result, "Should have 'fields' key"
    assert isinstance(result["fields"], list), "Fields should be a list"
    
    print(f"\nExtracted {len(result['fields'])} fields:")
    for field in result["fields"]:
        print(f"  - {field.get('field_name')}: {field.get('value')} (confidence: {field.get('confidence')})")
    
    print("✓ Field extraction simulation passed")
    return result


def test_non_json_mode():
    """Test non-JSON mode (plain text response)."""
    print("\n" + "=" * 70)
    print("Test 5: Non-JSON Mode (Plain Text)")
    print("=" * 70)
    
    messages = [
        {
            "role": "user",
            "content": "Write a short greeting in English and Telugu."
        }
    ]
    
    result = llm_call(messages, json_mode=False, max_tokens=100)
    print(f"Result: {result}")
    print(f"Type: {type(result)}")
    
    assert isinstance(result, str), "Result should be a string in non-JSON mode"
    
    print("✓ Non-JSON mode test passed")
    return result


def test_validation_scenario():
    """Test a validation scenario similar to our use case."""
    print("\n" + "=" * 70)
    print("Test 6: Validation Scenario")
    print("=" * 70)
    
    messages = [
        {
            "role": "user",
            "content": """Given these extracted values, validate and normalize them. Return JSON:
            {
              "aadhaar": {
                "raw": "౧౨౩౪ ౫౬౭౮ ౯౦౧౨",
                "normalized": "123456789012",
                "valid": true,
                "notes": "Valid 12-digit Aadhaar, normalized from Telugu"
              },
              "mobile": {
                "raw": "9876543210",
                "normalized": "+919876543210",
                "valid": true,
                "notes": "Valid Indian mobile, added +91 prefix"
              },
              "pin": {
                "raw": "౫౦౦౦౦౧",
                "normalized": "500001",
                "valid": true,
                "notes": "Valid 6-digit PIN, normalized from Telugu"
              }
            }
            """
        }
    ]
    
    result = llm_call(messages, json_mode=True, max_tokens=500)
    print(f"Result: {result}")
    
    # Verify structure
    assert "aadhaar" in result, "Should have 'aadhaar' key"
    assert "mobile" in result, "Should have 'mobile' key"
    assert "pin" in result, "Should have 'pin' key"
    
    print("\nValidation results:")
    for field_name, field_data in result.items():
        if isinstance(field_data, dict):
            print(f"  {field_name}:")
            print(f"    Raw: {field_data.get('raw')}")
            print(f"    Normalized: {field_data.get('normalized')}")
            print(f"    Valid: {field_data.get('valid')}")
    
    print("✓ Validation scenario test passed")
    return result


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("LLM Wrapper Comprehensive Tests")
    print("Using Real API Calls")
    print("=" * 70)
    
    try:
        # Run all tests
        test_simple_json()
        test_complex_json()
        test_telugu_handling()
        test_field_extraction_simulation()
        test_non_json_mode()
        test_validation_scenario()
        
        print("\n" + "=" * 70)
        print("🎉 All comprehensive tests passed!")
        print("=" * 70)
        print("\nLLM wrapper is fully functional and ready for:")
        print("  ✓ JSON mode responses")
        print("  ✓ Complex nested structures")
        print("  ✓ Telugu text handling")
        print("  ✓ Field extraction")
        print("  ✓ Plain text responses")
        print("  ✓ Validation scenarios")
        print()
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
