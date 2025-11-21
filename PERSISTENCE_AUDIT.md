# Data Persistence Audit & Guide

Complete audit of all data persistence mechanisms in the document validation system.

## Table of Contents
1. [What Gets Persisted](#what-gets-persisted)
2. [Directory Structure](#directory-structure)
3. [File Formats](#file-formats)
4. [Persistence Workflow](#persistence-workflow)
5. [Session Management](#session-management)
6. [Data Retention](#data-retention)
7. [Backup & Recovery](#backup--recovery)

---

## What Gets Persisted

### 1. **Stage 1: Document Extraction Outputs**

**Location**: `outputs/stage1_extractions/`

**Files per document**:
```
{document_id}_extracted.txt        # Extracted text with key-value pairs
{document_id}_metadata.json        # Processing metadata
```

**Content**:

**`_extracted.txt`**:
```
Full name of the Applicant: Ramesh Kumar

Father's Name: Suresh Kumar

Date of Birth: 15/08/1995

[... all extracted fields with blank line separation ...]
```

**`_metadata.json`**:
```json
{
  "document_id": "application_20250117_143022",
  "file_name": "application.pdf",
  "file_metadata": {
    "file_path": "/path/to/application.pdf",
    "file_size": 245760,
    "page_count": 3,
    "is_multi_page": true,
    "potential_multi_doc": false,
    "file_hash": "abc123...",
    "upload_timestamp": "2025-01-17T14:30:22"
  },
  "extracted_text": "[full text...]",
  "processing_timestamp": "2025-01-17T14:30:45",
  "success": true
}
```

### 2. **Stage 2: Summary Generation Outputs**

**Location**: `outputs/stage2_summaries/`

**Files per application**:
```
{cert_type}_{timestamp}_summary.md       # Markdown summary table
{cert_type}_{timestamp}_metadata.json    # Summary metadata
```

**Content**:

**`_summary.md`**:
```markdown
# INTEGRATED Certificate Summary

**Generated:** 2025-01-17T14:35:00

**Documents Processed:** 3

---

| Field | Value | Source Document(s) |
| --- | --- | --- |
| Name of the Applicant | Ramesh Kumar | application.pdf, caste_cert.pdf |
| Father's Name | Suresh Kumar | application.pdf |
[... full summary table ...]
```

**`_metadata.json`**:
```json
{
  "summary_id": "integrated_20250117_143500",
  "certificate_type": "integrated",
  "document_count": 3,
  "document_ids": ["app_001", "caste_002", "ration_003"],
  "processing_timestamp": "2025-01-17T14:35:00",
  "success": true
}
```

### 3. **Evaluation Outputs**

**Location**: `outputs/`

**Files**:
```
evaluation_report.txt        # Human-readable metrics report
evaluation_results.json      # Complete evaluation data
```

**Content**:

**`evaluation_report.txt`**:
```
================================================================================
                  DOCUMENT VALIDATION METRICS REPORT
================================================================================

Generated: 2025-01-17 14:40:00

STAGE 1: DOCUMENT EXTRACTION METRICS
Total Documents: 25
Average Extraction Rate: 94.50%
Average Field Accuracy: 89.20%
Average CER: 0.0234
Average WER: 0.0456

STAGE 2: SUMMARY GENERATION METRICS
Completeness: 96.50%
Value Accuracy: 91.30%
Source Attribution Accuracy: 87.60%
```

**`evaluation_results.json`**:
```json
{
  "total_cases": 10,
  "successful_cases": 9,
  "failed_cases": 1,
  "document_metrics": [
    {
      "document_id": "test_001",
      "extraction_rate": 0.95,
      "field_accuracy": 0.92,
      "character_error_rate": 0.023,
      "processing_time": 3.2,
      "page_count": 3,
      "is_multi_page": true
    }
  ],
  "summary_metrics": [...],
  "failed_case_details": [...]
}
```

### 4. **PDF Analysis Outputs**

**Location**: `outputs/` or custom directory

**Files**:
```
{pdf_name}_analysis.txt      # PDF structure analysis report
```

**Content**:
```
================================================================================
PDF ANALYSIS REPORT: application_bundle.pdf
================================================================================

Total Pages: 7
Potential Documents: 3
Document Start Pages: [1, 3, 6]

PAGE-BY-PAGE ANALYSIS
Page  1: ✓  1234 chars | Type: application
Page  2: ✓  1156 chars | Type: application
[... per-page breakdown ...]

WARNINGS
⚠  Detected 3 potential documents starting at pages: [1, 3, 6]
```

### 5. **Session Manifests** (NEW)

**Location**: `outputs/session_{timestamp}/`

**Files**:
```
manifest.json          # Complete session manifest
session_summary.txt    # Human-readable summary
```

**Content**:

**`manifest.json`**:
```json
{
  "session_id": "20250117_143022",
  "session_start": "2025-01-17T14:30:22",
  "session_end": "2025-01-17T14:35:45",
  "certificate_type": "integrated",

  "input_files": [
    "/path/to/application.pdf",
    "/path/to/caste_cert.pdf"
  ],
  "total_files": 2,

  "stage1_outputs": [
    "/path/to/outputs/stage1_extractions/app_001_extracted.txt",
    "/path/to/outputs/stage1_extractions/caste_002_extracted.txt"
  ],
  "stage1_success_count": 2,
  "stage1_failed_count": 0,

  "stage2_output": "/path/to/outputs/stage2_summaries/integrated_summary.md",
  "stage2_success": true,

  "metadata_files": [...],
  "log_files": [...],
  "evaluation_outputs": [...],
  "pdf_analysis_outputs": [...]
}
```

### 6. **Log Files**

**Location**: Current directory (configurable)

**Files**:
```
document_validation.log     # Main application log
```

**Content**:
```
2025-01-17 14:30:22 - INFO - Processing document: application.pdf
2025-01-17 14:30:23 - INFO - PDF application.pdf has 3 page(s)
2025-01-17 14:30:25 - INFO - Uploading file to Gemini: application.pdf (2.34 MB)
2025-01-17 14:30:30 - INFO - File uploaded successfully to Gemini
2025-01-17 14:30:42 - INFO - ✓ Content generated successfully
2025-01-17 14:30:42 - INFO -   → Extracted approximately 25 fields
[... complete processing log ...]
```

---

## Directory Structure

```
document_validation/
├── outputs/                          # All persistent outputs
│   ├── session_20250117_143022/     # Session-specific directory
│   │   ├── manifest.json            # Session manifest
│   │   └── session_summary.txt      # Human-readable summary
│   │
│   ├── stage1_extractions/          # Stage 1 outputs
│   │   ├── app_001_extracted.txt
│   │   ├── app_001_metadata.json
│   │   ├── caste_002_extracted.txt
│   │   └── caste_002_metadata.json
│   │
│   ├── stage2_summaries/            # Stage 2 outputs
│   │   ├── integrated_20250117_summary.md
│   │   └── integrated_20250117_metadata.json
│   │
│   ├── evaluation_report.txt        # Evaluation outputs
│   └── evaluation_results.json
│
├── backups/                          # Backup directory
│   └── backup_20250117_150000/
│       └── outputs/
│
├── document_validation.log           # Main log file
│
└── [source code directories...]
```

---

## File Formats

### **Text Files (.txt)**
- UTF-8 encoding
- Extracted document content
- Session summaries
- Evaluation reports
- PDF analysis reports

### **JSON Files (.json)**
- UTF-8 encoding
- Pretty-printed (indented)
- Metadata and structured data
- Manifests
- Evaluation results

### **Markdown Files (.md)**
- UTF-8 encoding
- Stage 2 summary tables
- Human-readable reports

---

## Persistence Workflow

### **Standard Processing Workflow**

```
1. User initiates processing
   └─> PersistenceManager created
       └─> Session ID generated
       └─> Session directory created

2. Input files registered
   └─> File paths added to manifest

3. Stage 1 Processing
   └─> For each document:
       ├─> Extract data with Gemini
       ├─> Save extracted text (.txt)
       ├─> Save metadata (.json)
       └─> Register outputs in manifest

4. Stage 2 Processing
   └─> Generate summary
   ├─> Save summary table (.md)
   ├─> Save metadata (.json)
   └─> Register outputs in manifest

5. Session finalized
   └─> Manifest saved with end time
   └─> Session summary generated
   └─> Summary printed to console
```

### **Evaluation Workflow**

```
1. Evaluation initiated
   └─> PersistenceManager created

2. For each test case:
   ├─> Run workflow (Stage 1 + Stage 2)
   ├─> Compare against ground truth
   └─> Calculate metrics

3. Generate reports
   ├─> evaluation_report.txt
   ├─> evaluation_results.json
   └─> Register in manifest

4. Session finalized
```

### **PDF Analysis Workflow**

```
1. PDF submitted for analysis
   └─> Analyze page count and structure

2. Extract page-level information
   └─> Detect document boundaries

3. Generate report
   ├─> {pdf_name}_analysis.txt
   └─> Register in manifest (if part of session)
```

---

## Session Management

### **Creating a Session**

```python
from src.persistence_manager import PersistenceManager

# Automatic session ID
manager = PersistenceManager()

# Or custom session ID
manager = PersistenceManager(session_id="my_custom_session")
```

### **Tracking Outputs**

```python
# Register input files
manager.register_input_file(Path("application.pdf"))

# Register Stage 1 outputs
manager.register_stage1_output(
    text_file=Path("outputs/stage1_extractions/app_001_extracted.txt"),
    metadata_file=Path("outputs/stage1_extractions/app_001_metadata.json"),
    success=True
)

# Register Stage 2 outputs
manager.register_stage2_output(
    summary_file=Path("outputs/stage2_summaries/integrated_summary.md"),
    metadata_file=Path("outputs/stage2_summaries/integrated_metadata.json"),
    success=True
)
```

### **Finalizing Session**

```python
# Finalize and save all tracking data
manager.finalize_session()

# Output:
# - outputs/session_{id}/manifest.json
# - outputs/session_{id}/session_summary.txt
# - Summary printed to console
```

### **Listing Sessions**

```bash
# List all processing sessions
cd src
python persistence_manager.py list
```

Output:
```
================================================================================
PROCESSING SESSIONS
================================================================================

1. Session: 20250117_143022
   Start: 2025-01-17T14:30:22
   End: 2025-01-17T14:35:45
   Files: 3
   Stage 1 Success: 3
   Stage 2 Success: Yes
   Location: outputs/session_20250117_143022

2. Session: 20250117_120000
   [...]
```

---

## Data Retention

### **What to Keep**

**Essential (keep indefinitely)**:
- Session manifests (`manifest.json`)
- Evaluation results (`evaluation_results.json`)
- PDF analysis reports

**Important (keep for reference)**:
- Stage 2 summaries (`.md` files)
- Evaluation reports (`.txt` files)
- Session summaries

**Can be cleaned up**:
- Stage 1 extracted text (if summary is sufficient)
- Individual metadata files (if manifest exists)
- Old log files

### **Cleanup Strategy**

```bash
# Keep sessions from last 30 days
find outputs/session_* -mtime +30 -type d -exec rm -rf {} \;

# Keep only essential files from old sessions
# Manual review recommended
```

### **Archive Old Data**

```python
from src.persistence_manager import create_backup

# Create backup before cleanup
backup_dir = create_backup(Path("outputs"))
# Then clean up old sessions
```

---

## Backup & Recovery

### **Creating Backups**

```python
from src.persistence_manager import create_backup
from pathlib import Path

# Backup outputs directory
backup_dir = create_backup(Path("outputs"))

# Or specify custom backup location
backup_dir = create_backup(
    source_dir=Path("outputs"),
    backup_dir=Path("/external/drive/backups")
)
```

### **Automated Backup Script**

```bash
#!/bin/bash
# backup_outputs.sh

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/document_validation_$TIMESTAMP"

# Create backup
python -c "
from src.persistence_manager import create_backup
from pathlib import Path
create_backup(Path('outputs'), Path('$BACKUP_DIR'))
"

echo "Backup created: $BACKUP_DIR"
```

### **Recovery**

```bash
# Restore from backup
cp -r /backups/document_validation_20250117/outputs ./outputs

# Or restore specific session
cp -r /backups/document_validation_20250117/outputs/session_20250117_143022 \
      ./outputs/session_20250117_143022
```

---

## Persistence Checklist

Before running processing:
- [ ] Outputs directory exists and is writable
- [ ] Sufficient disk space available
- [ ] Backup strategy in place (for production)

After processing:
- [ ] Stage 1 outputs saved (`.txt` and `.json`)
- [ ] Stage 2 outputs saved (`.md` and `.json`)
- [ ] Session manifest saved
- [ ] Session summary generated
- [ ] Log files captured

For evaluation:
- [ ] Evaluation report generated (`.txt`)
- [ ] Evaluation results saved (`.json`)
- [ ] All metrics persisted

For long-term storage:
- [ ] Create backups of important sessions
- [ ] Archive old sessions
- [ ] Clean up temporary files

---

## CLI Commands Reference

```bash
# List all sessions
python src/persistence_manager.py list

# Analyze PDF structure (saves to outputs/)
python src/pdf_analyzer.py document.pdf

# Run with logging to file
python src/main.py --files *.pdf --cert-type integrated --log-file session.log

# Evaluate with output persistence
python src/evaluate.py \
  --ground-truth tests/ground_truth.json \
  --documents tests/sample_documents/
```

---

## Integration with Existing Code

The persistence manager integrates seamlessly:

```python
# In your processing code
from src.persistence_manager import PersistenceManager

def process_documents(files, cert_type):
    # Create persistence manager
    pm = PersistenceManager()

    # Track inputs
    for file in files:
        pm.register_input_file(file)

    # Run processing
    results = run_stage1(files)
    for result in results:
        pm.register_stage1_output(...)

    summary = run_stage2(results)
    pm.register_stage2_output(...)

    # Finalize
    pm.finalize_session()
```

---

## Summary

**All data is persisted automatically**, including:
- ✅ Extracted document text
- ✅ Complete metadata (file info, page counts, timestamps)
- ✅ Summary tables
- ✅ Evaluation results
- ✅ PDF analyses
- ✅ Processing logs
- ✅ Session manifests
- ✅ Human-readable summaries

**Storage is organized by**:
- Processing stage (Stage 1 / Stage 2)
- Session (time-based)
- File type (text / JSON / markdown)

**No data is lost** - everything is tracked and saved!
