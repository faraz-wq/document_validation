# Test Data Preparation Format Guide

Complete guide for preparing test data to evaluate document validation metrics.

## Table of Contents
1. [Ground Truth Data Format](#ground-truth-data-format)
2. [Single-Document Examples](#single-document-examples)
3. [Multi-Page PDF Examples](#multi-page-pdf-examples)
4. [Multi-Document PDF Examples](#multi-document-pdf-examples)
5. [Directory Structure](#directory-structure)
6. [Annotation Checklist](#annotation-checklist)

---

## Ground Truth Data Format

### Complete Schema

```json
{
  "document_id": "unique_test_case_id",
  "certificate_type": "integrated|income|obc|ews|family_member",
  "description": "Brief description of this test case",

  "documents": [
    {
      "file_name": "document.pdf",
      "document_type": "Application Form",
      "quality_level": "clean|medium|challenging",

      // NEW: Page-level metadata
      "page_count": 3,
      "is_multi_page": true,
      "contains_multiple_docs": false,
      "expected_field_count_range": [15, 25],

      "ground_truth_fields": {
        "Field Name 1": "Exact Value 1",
        "Field Name 2": "Exact Value 2"
      },

      "notes": "Optional notes about this document"
    }
  ],

  "expected_summary": {
    "Summary Field Name": {
      "value": "Expected Value",
      "source_documents": ["file1.pdf", "file2.jpg"]
    }
  },

  // NEW: Expected metrics for validation
  "expected_metrics": {
    "total_pages": 5,
    "should_warn_multi_doc": false,
    "minimum_field_count": 20,
    "maximum_field_count": 40
  },

  "metadata": {
    "annotator": "Your Name",
    "annotation_date": "2025-01-17",
    "difficulty": "easy|medium|hard",
    "special_considerations": ["multi_page", "handwritten", "poor_quality"]
  }
}
```

---

## Single-Document Examples

### Example 1: Clean Single-Page Document

```json
{
  "document_id": "clean_single_001",
  "certificate_type": "income",
  "description": "Clean single-page income application form",

  "documents": [
    {
      "file_name": "income_application_001.pdf",
      "document_type": "Application Form",
      "quality_level": "clean",

      "page_count": 1,
      "is_multi_page": false,
      "contains_multiple_docs": false,
      "expected_field_count_range": [10, 15],

      "ground_truth_fields": {
        "Full name of the Applicant": "Sita Reddy",
        "Father's Name": "Rama Reddy",
        "Mother's Name": "Lakshmi Devi",
        "Date of Birth": "20/05/1988",
        "Age": "36 years",
        "Gender": "Female",
        "Address": "Plot No. 45, MIG Colony, Kukatpally, Hyderabad - 500072",
        "Phone Number": "9123456789",
        "Email": "sita.reddy@email.com",
        "Ration Card Number": "AP-HYD-987654321",
        "Aadhaar Number": "1234-5678-9012",
        "Occupation": "Self-employed (Small Business)",
        "Purpose of Certificate": "Educational scholarship",
        "Application Date": "15/01/2025"
      }
    }
  ],

  "expected_summary": {
    "Title of the document": {
      "value": "Income Certificate Application",
      "source_documents": ["income_application_001.pdf"]
    },
    "Name of the Applicant": {
      "value": "Sita Reddy",
      "source_documents": ["income_application_001.pdf"]
    },
    "Father's Name": {
      "value": "Rama Reddy",
      "source_documents": ["income_application_001.pdf"]
    },
    "Gender": {
      "value": "Female",
      "source_documents": ["income_application_001.pdf"]
    },
    "Age/DOB": {
      "value": "20/05/1988",
      "source_documents": ["income_application_001.pdf"]
    }
  },

  "expected_metrics": {
    "total_pages": 1,
    "should_warn_multi_doc": false,
    "minimum_field_count": 10,
    "maximum_field_count": 15
  },

  "metadata": {
    "annotator": "Test Team",
    "annotation_date": "2025-01-17",
    "difficulty": "easy",
    "special_considerations": []
  }
}
```

---

## Multi-Page PDF Examples

### Example 2: Multi-Page Single Document

```json
{
  "document_id": "multipage_single_002",
  "certificate_type": "integrated",
  "description": "3-page application form (single document spread across pages)",

  "documents": [
    {
      "file_name": "application_form_3pages.pdf",
      "document_type": "Application Form",
      "quality_level": "medium",

      "page_count": 3,
      "is_multi_page": true,
      "contains_multiple_docs": false,
      "expected_field_count_range": [20, 35],

      // Annotate ALL fields from ALL pages
      "ground_truth_fields": {
        // Page 1 fields
        "Full name of the Applicant": "Ramesh Kumar",
        "Father's Name": "Suresh Kumar",
        "Mother's Name": "Lakshmi Devi",
        "Date of Birth": "15/08/1995",
        "Age": "29 years",
        "Gender": "Male",
        "Marital Status": "Unmarried",

        // Page 2 fields
        "Address": "H.No. 12-34, Street 5, Jubilee Hills, Hyderabad, Telangana - 500033",
        "Permanent Address": "Same as above",
        "Phone Number": "9876543210",
        "Email": "ramesh.kumar@email.com",
        "Aadhaar Number": "1234 5678 9012",
        "Ration Card Number": "AP-HYD-123456789",
        "Community": "OBC",
        "Sub-Caste": "Yadav",
        "Religion": "Hindu",

        // Page 3 fields
        "Father's Occupation": "Farmer",
        "Mother's Occupation": "Homemaker",
        "Annual Family Income": "2,50,000",
        "Number of Family Members": "4",
        "Educational Qualification": "Intermediate",
        "School/College Name": "Government Junior College, Hyderabad",
        "Year of Passing": "2013",
        "Purpose of Certificate": "Higher Education",
        "Application Date": "15/01/2025",
        "Place": "Hyderabad"
      },

      "notes": "All 3 pages contain related information for same application. No separate documents."
    }
  ],

  "expected_summary": {
    "Name of the Applicant": {
      "value": "Ramesh Kumar",
      "source_documents": ["application_form_3pages.pdf"]
    },
    "Father's Name": {
      "value": "Suresh Kumar",
      "source_documents": ["application_form_3pages.pdf"]
    },
    "Community": {
      "value": "OBC",
      "source_documents": ["application_form_3pages.pdf"]
    },
    "Family Income": {
      "value": "2,50,000",
      "source_documents": ["application_form_3pages.pdf"]
    }
  },

  "expected_metrics": {
    "total_pages": 3,
    "should_warn_multi_doc": false,
    "minimum_field_count": 20,
    "maximum_field_count": 35,
    "notes": "System should log multi-page but not warn about multiple documents"
  },

  "metadata": {
    "annotator": "Test Team",
    "annotation_date": "2025-01-17",
    "difficulty": "medium",
    "special_considerations": ["multi_page"]
  }
}
```

---

## Multi-Document PDF Examples

### Example 3: Multi-Document Bundle (7 pages, 3 documents)

```json
{
  "document_id": "bundle_multi_003",
  "certificate_type": "integrated",
  "description": "7-page PDF containing 3 separate documents",

  "documents": [
    {
      "file_name": "integrated_bundle_7pages.pdf",
      "document_type": "Document Bundle",
      "quality_level": "medium",

      "page_count": 7,
      "is_multi_page": true,
      "contains_multiple_docs": true,

      // Document breakdown
      "document_breakdown": {
        "pages_1_2": "Application Form (2 pages)",
        "pages_3_5": "Caste Certificate (3 pages)",
        "pages_6_7": "Ration Card Scan (2 pages)"
      },

      "expected_field_count_range": [35, 70],

      // Annotate ALL fields from ALL documents/pages
      "ground_truth_fields": {
        // ===== DOCUMENT 1: Application Form (Pages 1-2) =====
        "Application Form - Full name": "Ramesh Kumar",
        "Application Form - Father's Name": "Suresh Kumar",
        "Application Form - Mother's Name": "Lakshmi Devi",
        "Application Form - Date of Birth": "15/08/1995",
        "Application Form - Gender": "Male",
        "Application Form - Address": "H.No. 12-34, Jubilee Hills, Hyderabad",
        "Application Form - Phone Number": "9876543210",
        "Application Form - Aadhaar": "1234 5678 9012",
        "Application Form - Ration Card": "AP-HYD-123456789",
        "Application Form - Community": "OBC",
        "Application Form - Annual Income": "2,50,000",
        "Application Form - Purpose": "Higher Education",
        "Application Form - Date": "15/01/2025",

        // ===== DOCUMENT 2: Caste Certificate (Pages 3-5) =====
        "Caste Certificate - Certificate Number": "CC/2020/12345",
        "Caste Certificate - Name": "Ramesh Kumar",
        "Caste Certificate - Father's Name": "Suresh Kumar",
        "Caste Certificate - Date of Birth": "15/08/1995",
        "Caste Certificate - Community": "OBC",
        "Caste Certificate - Sub-Caste": "Yadav",
        "Caste Certificate - Issuing Authority": "Tahsildar, Jubilee Hills",
        "Caste Certificate - District": "Hyderabad",
        "Caste Certificate - Date of Issue": "10/01/2020",
        "Caste Certificate - Validity": "Permanent",
        "Caste Certificate - Signature": "Tahsildar Seal and Signature",

        // ===== DOCUMENT 3: Ration Card (Pages 6-7) =====
        "Ration Card - Card Number": "AP-HYD-123456789",
        "Ration Card - Head of Family": "Suresh Kumar",
        "Ration Card - Family Members": "Ramesh Kumar, Lakshmi Devi, Priya Kumar",
        "Ration Card - Address": "H.No. 12-34, Jubilee Hills, Hyderabad",
        "Ration Card - Card Type": "White Card",
        "Ration Card - Issue Date": "05/03/2018",
        "Ration Card - Fair Price Shop": "FPS-500033-12",
        "Ration Card - Aadhaar Seeding Status": "Linked"
      },

      "notes": "CRITICAL: This is a BUNDLE of 3 different documents. System should warn about multiple documents."
    }
  ],

  "expected_summary": {
    "Name of the Applicant": {
      "value": "Ramesh Kumar",
      "source_documents": ["integrated_bundle_7pages.pdf"]
    },
    "Father's Name": {
      "value": "Suresh Kumar",
      "source_documents": ["integrated_bundle_7pages.pdf"]
    },
    "Date of Birth": {
      "value": "15/08/1995",
      "source_documents": ["integrated_bundle_7pages.pdf"]
    },
    "Community": {
      "value": "OBC",
      "source_documents": ["integrated_bundle_7pages.pdf"]
    },
    "Ration Card Number": {
      "value": "AP-HYD-123456789",
      "source_documents": ["integrated_bundle_7pages.pdf"]
    }
  },

  "expected_metrics": {
    "total_pages": 7,
    "should_warn_multi_doc": true,
    "minimum_field_count": 35,
    "maximum_field_count": 70,
    "expected_warnings": [
      "PDF has 7 pages - may contain multiple documents",
      "High field count for multi-page PDF",
      "Multiple document type indicators detected"
    ]
  },

  "metadata": {
    "annotator": "Test Team",
    "annotation_date": "2025-01-17",
    "difficulty": "hard",
    "special_considerations": ["multi_page", "multi_document", "bundle"]
  }
}
```

---

## Directory Structure

Organize your test data like this:

```
tests/
├── ground_truth_datasets/
│   ├── clean_documents.json          # Clean, single-page documents
│   ├── multipage_documents.json      # Multi-page single documents
│   ├── bundle_documents.json         # Multi-document PDFs
│   ├── challenging_documents.json    # Poor quality, handwritten
│   └── complete_dataset.json         # All test cases combined
│
├── sample_documents/
│   ├── clean/
│   │   ├── income_001.pdf
│   │   ├── income_002.pdf
│   │   └── ...
│   │
│   ├── multipage/
│   │   ├── application_3pages.pdf
│   │   ├── certificate_5pages.pdf
│   │   └── ...
│   │
│   ├── bundles/
│   │   ├── integrated_bundle_7pages.pdf
│   │   ├── income_bundle_10pages.pdf
│   │   └── ...
│   │
│   └── challenging/
│       ├── handwritten_001.jpg
│       ├── poor_scan_002.pdf
│       └── ...
│
└── expected_outputs/
    ├── clean/
    ├── multipage/
    └── bundles/
```

---

## Annotation Checklist

### For Each Test Case

- [ ] **Unique document_id**: Use descriptive naming (e.g., `bundle_integrated_7pg_001`)
- [ ] **Correct certificate_type**: One of: integrated, income, obc, ews, family_member
- [ ] **Page count metadata**: Set page_count, is_multi_page, contains_multiple_docs
- [ ] **Expected field count range**: Set realistic min/max based on pages
- [ ] **All fields annotated**: Extract EVERY visible field from EVERY page
- [ ] **Exact values**: Copy values exactly as they appear (including punctuation, spacing)
- [ ] **Field naming consistency**: Use descriptive, unique field names
- [ ] **Expected summary**: Define expected Stage 2 output with source tracking
- [ ] **Expected metrics**: Set thresholds for validation
- [ ] **Metadata complete**: Annotator, date, difficulty, special considerations

### Field Naming Best Practices

**For Single Documents:**
```json
"Full name of the Applicant": "Ramesh Kumar",
"Father's Name": "Suresh Kumar"
```

**For Multi-Document PDFs (prefix with document type):**
```json
"Application Form - Full name": "Ramesh Kumar",
"Caste Certificate - Name": "Ramesh Kumar",
"Ration Card - Head of Family": "Suresh Kumar"
```

### Value Format Guidelines

1. **Dates**: Use exact format from document
   - ✓ "15/08/1995"
   - ✗ "1995-08-15"

2. **Numbers**: Preserve formatting
   - ✓ "2,50,000"
   - ✗ "250000"

3. **Phone**: No country codes unless in document
   - ✓ "9876543210"
   - ✗ "+91 9876543210"

4. **Addresses**: Complete with punctuation
   - ✓ "H.No. 12-34, Street 5, Hyderabad - 500033"
   - ✗ "12-34 Street 5 Hyderabad"

5. **Names**: Match capitalization
   - ✓ "Ramesh Kumar"
   - ✗ "RAMESH KUMAR"

6. **Blank fields**: Use "(Not specified)"
   - ✓ "Email": "(Not specified)"
   - ✗ "Email": ""

---

## Validation Workflow

1. **Create ground truth file**
```bash
nano tests/ground_truth_datasets/my_test_set.json
```

2. **Validate JSON format**
```bash
python -m json.tool tests/ground_truth_datasets/my_test_set.json > /dev/null
echo "✓ Valid JSON"
```

3. **Run evaluation**
```bash
cd src
python evaluate.py \
  --ground-truth ../tests/ground_truth_datasets/my_test_set.json \
  --documents ../tests/sample_documents/my_docs/
```

4. **Review metrics**
```bash
cat ../outputs/evaluation_report.txt
cat ../outputs/evaluation_results.json | jq .
```

---

## Example: Complete Test Dataset File

```json
[
  {
    "document_id": "test_001_clean_single",
    "certificate_type": "income",
    "...": "..."
  },
  {
    "document_id": "test_002_multipage_3pg",
    "certificate_type": "integrated",
    "...": "..."
  },
  {
    "document_id": "test_003_bundle_7pg",
    "certificate_type": "integrated",
    "...": "..."
  }
]
```

---

## Next Steps

1. **Start small**: Annotate 5-10 clean documents
2. **Validate**: Run evaluation to verify annotation format
3. **Expand**: Add multi-page and bundle cases
4. **Balance**: Mix of quality levels and certificate types
5. **Iterate**: Add edge cases as you find them

Refer to:
- `tests/ground_truth_schema.json` - JSON schema
- `tests/ground_truth_example.json` - Working examples
- `METRICS_GUIDE.md` - Metrics interpretation
- `MULTI_DOCUMENT_GUIDE.md` - Multi-page PDF guidance
