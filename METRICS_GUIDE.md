# Metrics and Evaluation Guide

Complete guide for implementing metrics and evaluating the AP Seva Document Validation system.

## Table of Contents

1. [Overview](#overview)
2. [Metrics Categories](#metrics-categories)
3. [Data Preparation](#data-preparation)
4. [Running Evaluations](#running-evaluations)
5. [Understanding Results](#understanding-results)
6. [Best Practices](#best-practices)

---

## Overview

This system implements comprehensive metrics across two dimensions:

### Traditional OCR Metrics
- **Character Error Rate (CER)** - Measures character-level accuracy
- **Word Error Rate (WER)** - Measures word-level accuracy
- **Edit Distance** - Levenshtein distance between extracted and ground truth text

### Project-Specific Metrics
- **Field Extraction Rate** - Percentage of fields successfully extracted
- **Field Accuracy** - Percentage of correctly extracted field values
- **Completeness** - Coverage of required fields
- **Source Attribution Accuracy** - Correct identification of source documents
- **Cross-Document Consistency** - Value agreement across documents
- **Processing Time** - Performance metrics

---

## Metrics Categories

### Stage 1: Document Digitization Metrics

#### Per-Document Metrics
```python
DocumentMetrics(
    document_id: str,
    processing_time: float,
    total_fields: int,           # Expected fields in ground truth
    extracted_fields: int,        # Fields extracted by system
    correct_fields: int,          # Correctly extracted fields
    missing_fields: int,          # Fields not extracted
    incorrect_fields: int,        # Extracted but wrong value
    character_error_rate: float,  # CER score
    word_error_rate: float        # WER score
)
```

**Derived Metrics:**
- **Extraction Rate** = `extracted_fields / total_fields`
- **Field Accuracy** = `correct_fields / extracted_fields`

#### Field-Level Metrics
```python
FieldMetrics(
    field_name: str,
    true_positive: int,    # Correctly extracted
    false_positive: int,   # Extracted but wrong
    false_negative: int,   # Not extracted
    exact_matches: int,    # Exact string match
    partial_matches: int   # Fuzzy match
)
```

**Derived Metrics:**
- **Precision** = `TP / (TP + FP)`
- **Recall** = `TP / (TP + FN)`
- **F1 Score** = `2 * (Precision * Recall) / (Precision + Recall)`

### Stage 2: Summary Generation Metrics

```python
SummaryMetrics(
    summary_id: str,
    total_required_fields: int,      # Required fields for cert type
    fields_in_summary: int,           # Fields in generated summary
    correct_values: int,              # Correct field values
    incorrect_values: int,            # Incorrect field values
    missing_values: int,              # Missing fields
    source_attribution_correct: int,  # Correct source identifications
    source_attribution_total: int,    # Total source attributions
    cross_document_conflicts: int,    # Conflicting values
    format_compliance: bool           # Markdown table format
)
```

**Derived Metrics:**
- **Completeness** = `fields_in_summary / total_required_fields`
- **Value Accuracy** = `correct_values / fields_in_summary`
- **Source Accuracy** = `source_attribution_correct / source_attribution_total`

---

## Data Preparation

### 1. Collect Test Documents

Organize your test documents:

```
tests/sample_documents/
├── integrated_cert/
│   ├── test_001/
│   │   ├── application_form.pdf
│   │   ├── caste_certificate.pdf
│   │   ├── ration_card.jpg
│   │   └── ssc_memo.pdf
│   ├── test_002/
│   │   └── ...
│   └── ...
├── income_cert/
│   ├── test_001/
│   │   ├── application.pdf
│   │   ├── it_returns.pdf
│   │   └── pay_slips.pdf
│   └── ...
└── ...
```

**Document Quality Levels:**
- **Clean** (30%): High-quality scans, typed text, clear images
- **Medium** (50%): Some blur, minor artifacts, standard quality
- **Challenging** (20%): Handwritten text, poor scans, skewed images

### 2. Create Ground Truth Annotations

Use the schema in `tests/ground_truth_schema.json` as a template.

#### Annotation Format

```json
{
  "document_id": "unique_test_case_id",
  "certificate_type": "integrated|income|obc|ews|family_member",
  "documents": [
    {
      "file_name": "application_form.pdf",
      "document_type": "Application Form",
      "quality_level": "clean|medium|challenging",
      "ground_truth_fields": {
        "Field Name 1": "Correct Value 1",
        "Field Name 2": "Correct Value 2"
      },
      "notes": "Optional notes about this document"
    }
  ],
  "expected_summary": {
    "Summary Field 1": {
      "value": "Expected Value",
      "source_documents": ["file1.pdf", "file2.jpg"]
    }
  },
  "metadata": {
    "annotator": "Annotator Name",
    "annotation_date": "2025-01-17",
    "difficulty": "easy|medium|hard"
  }
}
```

#### Field Naming Guidelines

**Use exact field names as they appear in documents:**
- ✓ "Full name of the Applicant"
- ✓ "Date of Birth"
- ✓ "Father's Name"
- ✗ "Name" (too ambiguous)
- ✗ "DOB" (use full form)

**For Stage 1 (document-level):**
Extract ALL fields visible in the document, even if blank.

**For Stage 2 (summary-level):**
Use the certificate-specific field names from `certificate_types.py`.

### 3. Annotation Best Practices

#### Value Normalization
- Preserve original formatting (dates, numbers, capitalization)
- Include punctuation as it appears
- Don't add extra spaces or formatting

**Example:**
```json
{
  "Date of Birth": "15/08/1995",        // Not "15-08-1995" or "1995-08-15"
  "Phone Number": "9876543210",         // Not "+91 9876543210"
  "Amount": "2,50,000"                  // Keep comma formatting
}
```

#### Source Document Attribution
List ALL documents where a field appears:

```json
"Name of the Applicant": {
  "value": "Ramesh Kumar",
  "source_documents": [
    "application_form.pdf",
    "caste_certificate.pdf",
    "ssc_memo.pdf"
  ]
}
```

#### Handling Variations

If a field has slight variations across documents, use the most complete/official version:

```json
// Document 1: "Ramesh Kumar"
// Document 2: "RAMESH KUMAR"
// Document 3: "Mr. Ramesh Kumar"

"Name of the Applicant": {
  "value": "Ramesh Kumar",  // Use standard capitalization
  "source_documents": ["doc1.pdf", "doc2.pdf", "doc3.pdf"]
}
```

### 4. Dataset Size Recommendations

**Minimum for Initial Testing:**
- 5-10 test cases per certificate type
- 25-50 total test cases
- Mix of quality levels

**Recommended for Production:**
- 50+ test cases per certificate type
- 250+ total test cases
- Balanced across:
  - Quality levels (clean, medium, challenging)
  - Document types
  - Edge cases (handwritten, stamps, watermarks)

**Comprehensive Benchmark:**
- 100+ test cases per certificate type
- 500+ total test cases
- Include:
  - Regional language documents
  - Various government form versions
  - Different scanning qualities
  - Historical documents

### 5. Annotation Tools

#### Manual Annotation
Create JSON files manually using the template:

```bash
cp tests/ground_truth_example.json tests/ground_truth_my_dataset.json
# Edit with your favorite text editor or JSON editor
```

#### Semi-Automated Annotation
1. Run the system on test documents
2. Review outputs
3. Correct errors and save as ground truth
4. Add source attribution manually

```python
# Example script to convert system output to ground truth template
import json

system_output = load_system_output()
ground_truth = {
    "document_id": "test_001",
    "documents": [{
        "file_name": "doc.pdf",
        "ground_truth_fields": {}
    }]
}

# Copy extracted fields
for field, value in system_output.items():
    # Review and correct each field
    corrected_value = review_and_correct(field, value)
    ground_truth["documents"][0]["ground_truth_fields"][field] = corrected_value

save_ground_truth(ground_truth)
```

---

## Running Evaluations

### Basic Evaluation

```bash
cd src

# Run evaluation with default settings
python evaluate.py

# With custom paths
python evaluate.py \
  --ground-truth ../tests/my_ground_truth.json \
  --documents ../tests/my_documents/

# Without saving intermediate outputs
python evaluate.py --no-save-outputs
```

### Programmatic Evaluation

```python
from pathlib import Path
from src.evaluate import SystemEvaluator
from src.config import Config

# Setup
Config.validate()

# Create evaluator
evaluator = SystemEvaluator(
    ground_truth_path=Path("tests/ground_truth_example.json"),
    documents_dir=Path("tests/sample_documents/")
)

# Run evaluation
results = evaluator.evaluate_all(save_outputs=True)

# Access metrics
for doc_metric in results['document_metrics']:
    print(f"{doc_metric.document_id}: "
          f"Accuracy={doc_metric.field_accuracy:.2%}, "
          f"CER={doc_metric.character_error_rate:.4f}")
```

### Batch Evaluation

Evaluate multiple datasets:

```bash
# Create evaluation script
cat > run_all_evaluations.sh << 'EOF'
#!/bin/bash

datasets=(
  "clean_documents"
  "medium_quality"
  "challenging_cases"
)

for dataset in "${datasets[@]}"; do
  echo "Evaluating: $dataset"
  python evaluate.py \
    --ground-truth "../tests/${dataset}/ground_truth.json" \
    --documents "../tests/${dataset}/" \
    >> "evaluation_${dataset}.log" 2>&1
done
EOF

chmod +x run_all_evaluations.sh
./run_all_evaluations.sh
```

---

## Understanding Results

### Evaluation Report Format

```
================================================================================
                  DOCUMENT VALIDATION METRICS REPORT
================================================================================

Generated: 2025-01-17 14:30:00

--------------------------------------------------------------------------------
STAGE 1: DOCUMENT EXTRACTION METRICS
--------------------------------------------------------------------------------
Total Documents: 25
Average Extraction Rate: 94.50%
Average Field Accuracy: 89.20%
Average CER: 0.0234
Average WER: 0.0456
Average Processing Time: 3.45s

--------------------------------------------------------------------------------
STAGE 2: SUMMARY GENERATION METRICS
--------------------------------------------------------------------------------
Completeness: 96.50%
Value Accuracy: 91.30%
Source Attribution Accuracy: 87.60%
Format Compliance: Yes
```

### Interpreting Metrics

#### Character Error Rate (CER)
- **< 0.01**: Excellent (< 1% character errors)
- **0.01 - 0.05**: Good (1-5% character errors)
- **0.05 - 0.10**: Acceptable (5-10% character errors)
- **> 0.10**: Needs improvement

#### Word Error Rate (WER)
- **< 0.05**: Excellent
- **0.05 - 0.15**: Good
- **0.15 - 0.25**: Acceptable
- **> 0.25**: Needs improvement

#### Field Accuracy
- **> 95%**: Excellent
- **90-95%**: Good
- **85-90%**: Acceptable
- **< 85%**: Needs improvement

#### Extraction Rate
- **> 95%**: Excellent (most fields extracted)
- **90-95%**: Good
- **85-90%**: Acceptable
- **< 85%**: Needs improvement (many missing fields)

### Results Files

**outputs/evaluation_report.txt**
- Human-readable text report
- Aggregate metrics
- Summary statistics

**outputs/evaluation_results.json**
- Complete results in JSON format
- Per-document metrics
- Per-summary metrics
- Failed case details

```json
{
  "total_cases": 10,
  "successful_cases": 9,
  "failed_cases": 1,
  "document_metrics": [
    {
      "document_id": "test_001_application.pdf",
      "extraction_rate": 0.95,
      "field_accuracy": 0.92,
      "character_error_rate": 0.023,
      "word_error_rate": 0.045,
      "processing_time": 3.2
    }
  ],
  "summary_metrics": [...],
  "failed_case_details": [...]
}
```

---

## Best Practices

### 1. Start Small, Scale Up
- Begin with 5-10 clean, well-annotated test cases
- Verify your annotation process is correct
- Gradually add more cases and complexity

### 2. Balance Your Dataset
- **Document Quality**: 30% clean, 50% medium, 20% challenging
- **Certificate Types**: Equal representation
- **Edge Cases**: Include 10-15% edge cases

### 3. Regular Re-evaluation
- Re-run evaluations after system changes
- Track metrics over time
- Identify regression issues early

### 4. Focus on Critical Fields
Prioritize accuracy for critical fields:
- Names (applicant, father, mother)
- Dates (DOB, issue date)
- ID numbers (Aadhaar, ration card)
- Amounts (income, assets)

### 5. Error Analysis
When metrics are low:
1. Examine failed cases
2. Categorize error types:
   - OCR errors (misread text)
   - Extraction errors (wrong field mapping)
   - Format errors (incorrect parsing)
3. Adjust system or prompts accordingly

### 6. Continuous Annotation
- Add new test cases from production data
- Include cases where system fails
- Maintain diverse test coverage

### 7. Version Control for Annotations
```bash
# Keep ground truth in git
git add tests/ground_truth_*.json
git commit -m "Add test cases for income certificates"

# Tag versions
git tag -a v1.0-dataset -m "Initial test dataset"
```

---

## Metrics Improvement Strategies

### If CER/WER is High
- Check document image quality
- Try different Gemini models (Pro vs Flash)
- Adjust temperature and generation parameters
- Add preprocessing instructions to prompts

### If Extraction Rate is Low
- Review Stage 1 prompt clarity
- Check if field names are descriptive enough
- Ensure documents contain expected fields
- Verify file upload is working correctly

### If Field Accuracy is Low
- Improve field name descriptions in prompts
- Add examples to prompts
- Use more specific extraction instructions
- Check for systematic parsing errors

### If Source Attribution is Low
- Clarify source tracking instructions in Stage 2 prompt
- Ensure document names are clear
- Add explicit source attribution requirements

---

## Example Workflow

### Complete Evaluation Workflow

```bash
# 1. Prepare test data
mkdir -p tests/my_evaluation/test_001
cp my_documents/* tests/my_evaluation/test_001/

# 2. Create ground truth annotation
nano tests/my_evaluation/ground_truth.json

# 3. Validate annotation format
python -m json.tool tests/my_evaluation/ground_truth.json > /dev/null
echo "Ground truth JSON is valid"

# 4. Run evaluation
cd src
python evaluate.py \
  --ground-truth ../tests/my_evaluation/ground_truth.json \
  --documents ../tests/my_evaluation/ \
  --log-level DEBUG

# 5. Review results
cat ../outputs/evaluation_report.txt
cat ../outputs/evaluation_results.json | jq '.document_metrics[].field_accuracy'

# 6. Analyze failures
cat ../outputs/evaluation_results.json | jq '.failed_case_details'
```

---

## Additional Resources

- **Schema Definition**: `tests/ground_truth_schema.json`
- **Example Annotations**: `tests/ground_truth_example.json`
- **Metrics Module**: `src/metrics.py`
- **Evaluation Script**: `src/evaluate.py`

---

## Support

For questions or issues with metrics:
1. Check this guide
2. Review example annotations
3. Examine the metrics module source code
4. Open an issue with evaluation results and logs
