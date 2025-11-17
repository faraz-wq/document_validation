# Annotation Quick Start Guide

Quick reference for creating test data annotations.

## 5-Minute Setup

### Step 1: Copy Template

```bash
cd tests
cp ground_truth_template.json my_annotation.json
```

### Step 2: Fill Basic Info

```json
{
  "document_id": "my_test_001",              // Unique ID
  "certificate_type": "integrated",          // Choose type
  "description": "Clean 2-page application", // Brief description
```

### Step 3: Document Metadata

```json
  "documents": [
    {
      "file_name": "application.pdf",        // Actual filename
      "document_type": "Application Form",   // What it is
      "quality_level": "clean",              // clean/medium/challenging

      "page_count": 2,                       // Number of pages
      "is_multi_page": true,                 // true if >1 page
      "contains_multiple_docs": false,       // true if bundle
      "expected_field_count_range": [15, 25] // Min-max fields
```

### Step 4: Extract All Fields

```json
      "ground_truth_fields": {
        "Full name of the Applicant": "Ramesh Kumar",
        "Father's Name": "Suresh Kumar",
        "Date of Birth": "15/08/1995",
        "Gender": "Male",
        // ... ALL fields from ALL pages
      }
```

**Rules:**
- ✓ Extract EVERY field from EVERY page
- ✓ Use exact values (copy-paste)
- ✓ Use "(Not specified)" for blank fields
- ✓ For bundles, prefix with document type

### Step 5: Expected Summary

```json
  "expected_summary": {
    "Name of the Applicant": {
      "value": "Ramesh Kumar",
      "source_documents": ["application.pdf"]
    }
  }
```

### Step 6: Expected Metrics

```json
  "expected_metrics": {
    "total_pages": 2,
    "should_warn_multi_doc": false,
    "minimum_field_count": 15,
    "maximum_field_count": 25
  }
```

### Step 7: Metadata

```json
  "metadata": {
    "annotator": "Your Name",
    "annotation_date": "2025-01-17",
    "difficulty": "medium",
    "special_considerations": ["multi_page"]
  }
}
```

## Field Naming Cheat Sheet

### Single Document
```json
"Full name of the Applicant": "Ramesh Kumar"
"Father's Name": "Suresh Kumar"
```

### Multi-Document Bundle
```json
"Application Form - Full name": "Ramesh Kumar"
"Caste Certificate - Name": "Ramesh Kumar"
"Ration Card - Head of Family": "Suresh Kumar"
```

## Value Formatting

| Type | Format | Example |
|------|--------|---------|
| **Date** | As shown | "15/08/1995" |
| **Number** | With commas | "2,50,000" |
| **Phone** | No spaces | "9876543210" |
| **Name** | As shown | "Ramesh Kumar" |
| **Blank** | Use special | "(Not specified)" |

## Page Count Guidelines

| Pages | is_multi_page | contains_multiple_docs | should_warn |
|-------|---------------|------------------------|-------------|
| 1 | false | false | false |
| 2-3 | true | false | false |
| 4+ | true | maybe | true |
| 5+ with different doc types | true | true | true |

## Field Count Estimation

**Per page estimate:** 5-15 fields

| Pages | Min Fields | Max Fields |
|-------|-----------|-----------|
| 1 | 5 | 15 |
| 2 | 10 | 30 |
| 3 | 15 | 45 |
| 4 | 20 | 60 |
| 7 (bundle) | 35 | 105 |

## Validate Your Annotation

```bash
# Check JSON syntax
python -m json.tool my_annotation.json > /dev/null
echo "Valid!" || echo "Fix JSON errors"

# Test with system
cd ../src
python evaluate.py \
  --ground-truth ../tests/my_annotation.json \
  --documents ../tests/sample_documents/
```

## Common Mistakes

❌ **Wrong**: Empty string for blank fields
```json
"Email": ""
```
✓ **Right**: Use "(Not specified)"
```json
"Email": "(Not specified)"
```

---

❌ **Wrong**: Modified date format
```json
"Date of Birth": "1995-08-15"
```
✓ **Right**: Exact format from document
```json
"Date of Birth": "15/08/1995"
```

---

❌ **Wrong**: Missing page metadata
```json
{
  "file_name": "bundle.pdf",
  "ground_truth_fields": {...}
}
```
✓ **Right**: Include all metadata
```json
{
  "file_name": "bundle.pdf",
  "page_count": 7,
  "is_multi_page": true,
  "contains_multiple_docs": true,
  "ground_truth_fields": {...}
}
```

---

❌ **Wrong**: Forgetting fields from later pages
```json
{
  // Only page 1 fields...
}
```
✓ **Right**: ALL fields from ALL pages
```json
{
  // Page 1 fields
  "Field 1": "Value 1",
  // Page 2 fields
  "Field 10": "Value 10",
  // Page 3 fields
  "Field 20": "Value 20"
}
```

## Quick References

- **Full Guide**: `TEST_DATA_FORMAT.md`
- **Template**: `ground_truth_template.json`
- **Examples**: `ground_truth_multipage_example.json`
- **Schema**: `ground_truth_schema.json`
- **Multi-Page Guide**: `../MULTI_DOCUMENT_GUIDE.md`
