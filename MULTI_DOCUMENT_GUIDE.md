# Multi-Page PDF and Multi-Document Detection Guide

## Overview

The document validation system now includes comprehensive logging and detection for multi-page PDFs that may contain multiple documents. This guide explains the new features and how to use them.

## Problem Addressed

**Issue**: A single PDF file can contain multiple documents (e.g., pages 1-2 are an application form, pages 3-5 are a caste certificate, pages 6-7 are a ration card scan). The system needs to:
1. Detect when PDFs have multiple pages
2. Warn when a PDF likely contains multiple separate documents
3. Log whether all pages are being processed
4. Alert if some documents/pages might be skipped

## New Features

### 1. Page Count Tracking

**File**: `src/file_handler.py`

Every PDF now has page count metadata:

```python
@dataclass
class FileMetadata:
    page_count: Optional[int] = None  # Number of pages
    is_multi_page: bool = False  # True if > 1 page
    potential_multi_doc: bool = False  # True if > 3 pages
```

**Automatic Warnings**:
- **> 1 page**: Info message about multi-page document
- **> 3 pages**: Warning that PDF may contain multiple documents

### 2. Enhanced Logging

**Files**: `src/gemini_client.py`, `src/document_processor.py`

Comprehensive logging at every stage:

```
INFO: PDF application_bundle.pdf has 7 page(s)
WARNING: PDF application_bundle.pdf has 7 pages - may contain multiple documents
INFO: Multi-page document detected: 7 pages
INFO: All pages will be sent to Gemini for processing
WARNING: ⚠️  WARNING: This PDF may contain MULTIPLE DOCUMENTS
WARNING:    File has 7 pages - consider:
WARNING:    1. Reviewing extracted results carefully
WARNING:    2. Splitting PDF into separate documents if needed
WARNING:    3. Verifying no documents/pages were skipped
INFO: Sending application_bundle.pdf to Gemini for Stage 1 processing...
INFO: Uploading file to Gemini: application_bundle.pdf (2.34 MB)
INFO: File uploaded successfully to Gemini
INFO: File processed successfully by Gemini
INFO: ✓ Content generated successfully for application_bundle.pdf
INFO:   → Extracted text: 8534 chars, 312 lines
INFO:   → Extracted approximately 45 fields
INFO:   → High field count (45) for 7-page PDF
INFO:     This may indicate multiple documents in single PDF
```

### 3. Extraction Completeness Analysis

**File**: `src/document_processor.py`

Automatic analysis of extraction results:

- **Field count estimation**: ~5-15 fields expected per page
- **Too few fields**: Warning that pages may have been skipped
- **Too many fields**: Info that multiple documents detected
- **Document boundary detection**: Looks for indicators like "Page 1", "Document 2", etc.

Example warnings:

```
WARNING: ⚠ Extracted only 8 fields from 5-page PDF
WARNING:    Expected at least 25 fields
WARNING:    Some pages may have been skipped or poorly extracted
```

### 4. PDF Structure Analyzer

**File**: `src/pdf_analyzer.py`

Standalone utility to analyze PDF structure before processing:

```bash
# Analyze a PDF
cd src
python pdf_analyzer.py ../tests/sample_documents/application_bundle.pdf

# Or within Python
from src.pdf_analyzer import analyze_and_report
analysis = analyze_and_report(Path("document.pdf"), Path("outputs"))
```

**Output Example**:

```
================================================================================
PDF ANALYSIS REPORT: application_bundle.pdf
================================================================================

Total Pages: 7
Potential Documents: 3
Document Start Pages: [1, 3, 6]

--------------------------------------------------------------------------------
PAGE-BY-PAGE ANALYSIS
--------------------------------------------------------------------------------
Page  1: ✓  1234 chars | Type: application
Page  2: ✓  1156 chars | Type: application
Page  3: ✓  1890 chars | Type: certificate
Page  4: ✓  1654 chars | Type: certificate
Page  5: ✓   987 chars | Type: certificate
Page  6: ✓   543 chars | Type: ration_card
Page  7: ✓   421 chars | Type: ration_card

--------------------------------------------------------------------------------
WARNINGS
--------------------------------------------------------------------------------
⚠  Detected 3 potential documents starting at pages: [1, 3, 6]
```

### 5. Metrics Integration

**File**: `src/metrics.py`

DocumentMetrics now tracks page-level information:

```python
@dataclass
class DocumentMetrics:
    page_count: Optional[int] = None
    is_multi_page: bool = False
    potential_multi_doc: bool = False
    has_warnings: bool = False
    warning_messages: List[str] = None

    @property
    def fields_per_page(self) -> Optional[float]:
        """Average fields extracted per page"""
        return self.extracted_fields / self.page_count
```

## Usage Examples

### Example 1: Processing with Logging

```bash
cd src
python main.py \
  --cert-type integrated \
  --files ../tests/sample_documents/multi_page_bundle.pdf \
  --log-level INFO
```

You'll see detailed logs about:
- Page count detection
- Multi-document warnings
- Upload progress
- Extraction completeness analysis

### Example 2: Pre-Analysis

Before processing, analyze PDF structure:

```bash
cd src
python pdf_analyzer.py ../path/to/suspicious.pdf

# Check if it reports multiple documents
# If yes, consider splitting the PDF first
```

### Example 3: Programmatic Usage

```python
from pathlib import Path
from src.file_handler import FileHandler
from src.pdf_analyzer import PDFAnalyzer

# Check page count
pdf_path = Path("application.pdf")
metadata = FileHandler.get_file_metadata(pdf_path)

if metadata.potential_multi_doc:
    print(f"⚠ Warning: {metadata.page_count} pages detected")

    # Analyze structure
    analysis = PDFAnalyzer.analyze_pdf(pdf_path)
    print(f"Potential documents at pages: {analysis.potential_document_boundaries}")

    # Decide whether to split or process as-is
```

### Example 4: Evaluation with Page Tracking

```bash
cd src
python evaluate.py \
  --ground-truth ../tests/ground_truth.json \
  --documents ../tests/sample_documents/ \
  --log-level DEBUG

# Check outputs/evaluation_results.json for page-level metrics
```

## Best Practices

### 1. **Pre-Process Large PDFs**

If you know a PDF contains multiple documents:

```bash
# Option A: Use PDF splitting tools
pdftk input.pdf cat 1-2 output application.pdf
pdftk input.pdf cat 3-5 output certificate.pdf

# Option B: Process as-is but review carefully
python main.py --files bundle.pdf --log-level INFO > log.txt
# Review log.txt for warnings
```

### 2. **Monitor Logs**

Always check logs for:
- ✓ Expected page counts
- ⚠ Multi-document warnings
- ⚠ Field count mismatches
- ℹ Document boundary indicators

### 3. **Validate Extraction**

For multi-page PDFs:

```python
# Check field count makes sense
expected_min = page_count * 5
expected_max = page_count * 15

if field_count < expected_min:
    print("⚠ Possible missed pages!")
```

### 4. **Update Ground Truth**

When annotating multi-page PDFs for testing:

```json
{
  "document_id": "multipage_001",
  "documents": [
    {
      "file_name": "bundle.pdf",
      "page_count": 7,
      "contains_multiple_docs": true,
      "document_breakdown": {
        "pages_1_2": "Application Form",
        "pages_3_5": "Caste Certificate",
        "pages_6_7": "Ration Card"
      },
      "ground_truth_fields": {
        "// Fields from ALL pages"
      }
    }
  ]
}
```

## Logging Levels

**DEBUG**: Maximum detail
- Every file operation
- Gemini API details
- Field-by-field analysis

**INFO**: Recommended for production
- Page counts
- Processing progress
- Extraction summaries
- Multi-document indicators

**WARNING**: Critical issues only
- Multi-document PDFs (>3 pages)
- Field count mismatches
- Potential missing pages

## Troubleshooting

### Issue: "Only extracted N fields from M-page PDF"

**Possible causes**:
1. Pages contain images only (no text)
2. Gemini skipped some pages
3. Pages are truly blank

**Solution**:
```bash
# Analyze PDF structure
python pdf_analyzer.py suspicious.pdf

# Check for blank/image-only pages
# If confirmed issue, try:
# - Better quality scans
# - Re-upload to Gemini
# - Split PDF manually
```

### Issue: "Detected multiple document type indicators"

**Meaning**: Extraction shows evidence of different document types

**Solution**:
```bash
# This is expected for multi-document PDFs
# Review extraction to ensure all documents are present
# Consider splitting if you need separate extractions
```

### Issue: No page count displayed

**Cause**: PyPDF2 not installed

**Solution**:
```bash
pip install PyPDF2>=3.0.0
```

## New Dependencies

Add to your environment:

```bash
pip install PyPDF2>=3.0.0
```

Already in `requirements.txt`.

## Integration with Existing Workflow

**No breaking changes** - all features are additive:
- Existing code continues to work
- New metadata fields are optional
- Logging is automatic
- Analyzer is standalone utility

## Summary

The system now provides:
- ✅ Automatic page count detection
- ✅ Multi-document warnings
- ✅ Extraction completeness analysis
- ✅ Detailed logging at every stage
- ✅ Standalone PDF analyzer tool
- ✅ Metrics integration
- ✅ No breaking changes

Use these features to ensure complete document processing and catch potential issues early!
