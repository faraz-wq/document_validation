# Persistence Quick Reference

Everything you need to know about data persistence in the document validation system.

## ✅ What's Already Persisted Automatically

### **Stage 1 Outputs** (Per Document)
```
outputs/stage1_extractions/
├── {document_id}_extracted.txt     ✓ Extracted key-value pairs
└── {document_id}_metadata.json     ✓ Complete file & processing metadata
```

### **Stage 2 Outputs** (Per Application)
```
outputs/stage2_summaries/
├── {cert_type}_{timestamp}_summary.md      ✓ Markdown summary table
└── {cert_type}_{timestamp}_metadata.json   ✓ Summary metadata
```

### **Evaluation Outputs**
```
outputs/
├── evaluation_report.txt           ✓ Human-readable metrics
└── evaluation_results.json         ✓ Complete evaluation data
```

### **Session Tracking** (NEW)
```
outputs/session_{timestamp}/
├── manifest.json                   ✓ Complete session manifest
└── session_summary.txt             ✓ Human-readable summary
```

### **Logs**
```
document_validation.log             ✓ All processing logs
```

---

## 🚀 Quick Usage

### **Normal Processing** (Everything Auto-Saved)

```bash
cd src
python main.py \
  --cert-type integrated \
  --files ../tests/sample_documents/*.pdf
```

**What gets saved**:
- ✅ Stage 1 extractions (`.txt` + `.json` per document)
- ✅ Stage 2 summary (`.md` + `.json`)
- ✅ All logs to file

**Where to find it**:
```
outputs/
├── stage1_extractions/
│   ├── application_20250117_143022_extracted.txt
│   ├── application_20250117_143022_metadata.json
│   └── ...
└── stage2_summaries/
    ├── integrated_20250117_143500_summary.md
    └── integrated_20250117_143500_metadata.json
```

### **Evaluation** (Metrics Persisted)

```bash
cd src
python evaluate.py \
  --ground-truth ../tests/ground_truth.json \
  --documents ../tests/sample_documents/
```

**What gets saved**:
- ✅ All workflow outputs (Stage 1 + Stage 2)
- ✅ Evaluation report (`.txt`)
- ✅ Evaluation results (`.json`)
- ✅ Per-document metrics

**Where to find it**:
```
outputs/
├── evaluation_report.txt
├── evaluation_results.json
├── stage1_extractions/
└── stage2_summaries/
```

### **PDF Analysis** (Structure Report Saved)

```bash
cd src
python pdf_analyzer.py ../path/to/document.pdf
```

**What gets saved**:
- ✅ PDF analysis report (`.txt`)

**Where to find it**:
```
outputs/
└── document_analysis.txt
```

---

## 📋 Verify Persistence

### **Check Recent Outputs**

```bash
# List Stage 1 outputs
ls -lht outputs/stage1_extractions/ | head

# List Stage 2 outputs
ls -lht outputs/stage2_summaries/ | head

# View latest summary
cat outputs/stage2_summaries/$(ls -t outputs/stage2_summaries/*.md | head -1)
```

### **Check Evaluation Results**

```bash
# View evaluation report
cat outputs/evaluation_report.txt

# View evaluation JSON
cat outputs/evaluation_results.json | jq .

# Check specific metrics
cat outputs/evaluation_results.json | jq '.document_metrics[].field_accuracy'
```

### **Check Logs**

```bash
# View recent logs
tail -f document_validation.log

# Search for warnings
grep "WARNING" document_validation.log

# Search for multi-page PDFs
grep "Multi-page" document_validation.log
```

---

## 🔍 Session Management (NEW)

### **List All Sessions**

```bash
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
```

### **View Session Details**

```bash
# View session manifest
cat outputs/session_20250117_143022/manifest.json | jq .

# View session summary
cat outputs/session_20250117_143022/session_summary.txt
```

---

## 💾 Backup & Recovery

### **Create Backup**

```python
from pathlib import Path
from src.persistence_manager import create_backup

# Backup all outputs
backup_dir = create_backup(Path("outputs"))
print(f"Backup created: {backup_dir}")
```

Or via command line:
```bash
python -c "
from pathlib import Path
from src.persistence_manager import create_backup
create_backup(Path('outputs'))
"
```

### **Restore from Backup**

```bash
# Restore entire outputs directory
cp -r backups/backup_20250117_150000/outputs ./outputs

# Or restore specific session
cp -r backups/backup_20250117_150000/outputs/session_* ./outputs/
```

---

## 📊 What's in Each File

### **`_extracted.txt`** - Extracted Text
```
Full name of the Applicant: Ramesh Kumar

Father's Name: Suresh Kumar

[... all fields with blank line separation ...]
```

### **`_metadata.json`** - Processing Metadata
```json
{
  "document_id": "application_20250117_143022",
  "file_name": "application.pdf",
  "file_metadata": {
    "page_count": 3,
    "is_multi_page": true,
    "file_hash": "abc123..."
  },
  "processing_timestamp": "2025-01-17T14:30:45",
  "success": true
}
```

### **`_summary.md`** - Summary Table
```markdown
| Field | Value | Source Document(s) |
| --- | --- | --- |
| Name | Ramesh Kumar | application.pdf, caste.pdf |
```

### **`manifest.json`** - Session Manifest
```json
{
  "session_id": "20250117_143022",
  "input_files": [...],
  "stage1_outputs": [...],
  "stage2_output": "...",
  "metadata_files": [...]
}
```

---

## 🎯 Common Tasks

### **Find All Outputs for Specific Document**

```bash
DOC_ID="application_20250117_143022"

find outputs -name "${DOC_ID}*"
```

### **Export All Summaries**

```bash
# Copy all markdown summaries to export folder
mkdir -p exports/summaries
cp outputs/stage2_summaries/*.md exports/summaries/
```

### **Clean Up Old Sessions**

```bash
# Remove sessions older than 30 days
find outputs/session_* -type d -mtime +30 -exec rm -rf {} \;
```

### **Generate Processing Report**

```bash
# Count total files processed
echo "Total Stage 1 outputs: $(ls outputs/stage1_extractions/*.txt 2>/dev/null | wc -l)"
echo "Total Stage 2 summaries: $(ls outputs/stage2_summaries/*.md 2>/dev/null | wc -l)"
echo "Total sessions: $(ls -d outputs/session_* 2>/dev/null | wc -l)"
```

---

## ⚡ Advanced: Programmatic Access

### **Access Session Data**

```python
from pathlib import Path
import json

# Load session manifest
session_dir = Path("outputs/session_20250117_143022")
with open(session_dir / "manifest.json") as f:
    manifest = json.load(f)

# Get all Stage 1 outputs
for output_file in manifest["stage1_outputs"]:
    print(f"Stage 1: {output_file}")

# Get Stage 2 output
print(f"Stage 2: {manifest['stage2_output']}")
```

### **Load Extraction Results**

```python
from pathlib import Path
import json

# Load metadata
metadata_file = Path("outputs/stage1_extractions/app_001_metadata.json")
with open(metadata_file) as f:
    metadata = json.load(f)

# Check if multi-page
if metadata["file_metadata"]["is_multi_page"]:
    print(f"Multi-page PDF: {metadata['file_metadata']['page_count']} pages")

# Load extracted text
text_file = Path("outputs/stage1_extractions/app_001_extracted.txt")
with open(text_file) as f:
    extracted_text = f.read()
```

### **Load Evaluation Results**

```python
import json

# Load evaluation results
with open("outputs/evaluation_results.json") as f:
    results = json.load(f)

# Print metrics
for doc_metrics in results["document_metrics"]:
    print(f"{doc_metrics['document_id']}: {doc_metrics['field_accuracy']:.2%}")
```

---

## ✅ Persistence Checklist

Before processing:
- [ ] Outputs directory exists
- [ ] Sufficient disk space
- [ ] Write permissions

After processing:
- [ ] Check `outputs/stage1_extractions/` for extracted files
- [ ] Check `outputs/stage2_summaries/` for summary
- [ ] Check `document_validation.log` for logs
- [ ] Check `outputs/session_*/` for session tracking

For evaluation:
- [ ] Check `outputs/evaluation_report.txt`
- [ ] Check `outputs/evaluation_results.json`

For production:
- [ ] Create backups regularly
- [ ] Monitor disk usage
- [ ] Archive old sessions

---

## 🆘 Troubleshooting

### **No outputs found**

Check if processing succeeded:
```bash
tail -100 document_validation.log | grep "ERROR\|WARNING"
```

### **Permission denied**

Ensure write permissions:
```bash
chmod -R u+w outputs/
```

### **Disk full**

Check disk usage:
```bash
du -sh outputs/
df -h
```

Clean up old sessions:
```bash
find outputs/session_* -type d -mtime +7 -exec rm -rf {} \;
```

### **Missing files**

Check if `save_intermediate` was disabled:
```bash
# Stage 1 files only saved if save_intermediate=True
python main.py --files *.pdf --cert-type integrated
# NOT: --no-save-stage1
```

---

## 📚 Full Documentation

- **Complete Guide**: `PERSISTENCE_AUDIT.md`
- **Code Reference**: `src/persistence_manager.py`
- **Main README**: `README.md`

---

**Everything is automatically persisted - no configuration needed!** 🎉
