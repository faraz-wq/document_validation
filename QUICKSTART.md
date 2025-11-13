# Quick Start Guide

Get up and running with the AP Seva Document Validation Workflow in 5 minutes.

## Prerequisites

- Python 3.8 or higher
- Google Gemini API key ([Get one free here](https://makersuite.google.com/app/apikey))

## Setup (3 steps)

### 1. Install Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

### 2. Configure API Key

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your API key
# GEMINI_API_KEY=your_actual_api_key_here
```

Or set it directly in your shell:
```bash
export GEMINI_API_KEY="your_actual_api_key_here"
```

### 3. Run Your First Workflow

```bash
cd src

# Process some documents (replace with your files)
python main.py \
  --cert-type integrated \
  --files document1.pdf document2.jpg
```

## Example Commands

### Integrated Certificate
```bash
python main.py \
  --cert-type integrated \
  --files application.pdf caste_cert.pdf ration_card.jpg \
  --names "Application Form" "Caste Certificate" "Ration Card"
```

### Income Certificate
```bash
python main.py \
  --cert-type income \
  --files application.pdf it_returns.pdf pay_slips.pdf
```

### OBC Certificate
```bash
python main.py \
  --cert-type obc \
  --files application.pdf ration_card.jpg property_docs.pdf
```

### EWS Certificate
```bash
python main.py \
  --cert-type ews \
  --files application.pdf it_returns.pdf affidavit.pdf
```

### Family Member Certificate
```bash
python main.py \
  --cert-type family_member \
  --files application.pdf death_cert.pdf affidavit.pdf
```

## Understanding the Output

After running, check these directories:

### Stage 1 Output (`outputs/stage1_extractions/`)
- `{document_id}_extracted.txt` - Extracted data in key-value format
- `{document_id}_metadata.json` - Processing metadata

### Stage 2 Output (`outputs/stage2_summaries/`)
- `{cert_type}_{timestamp}_summary.md` - Final summary table
- `{cert_type}_{timestamp}_metadata.json` - Summary metadata

## Example Output

### Stage 1 - Extracted Text
```
Full name of the Applicant: John Doe

Father's Name: James Doe

Date of Birth: 01/01/1990

Gender: Male

Address: 123 Main Street, Hyderabad
```

### Stage 2 - Summary Table
```markdown
| Field | Value | Source Document(s) |
| --- | --- | --- |
| Name of the Applicant | John Doe | application.pdf, caste_cert.pdf |
| Father's Name | James Doe | application.pdf |
| Date of Birth | 01/01/1990 | application.pdf, ssc_memo.pdf |
```

## Common Issues

### "GEMINI_API_KEY environment variable is required"
**Solution:** Set your API key in `.env` or environment

### "File not found"
**Solution:** Use absolute paths or run from correct directory

### "Unsupported file format"
**Solution:** Only PDF, JPG, JPEG, PNG are supported

## Next Steps

1. **Read the full README** - `README.md` for detailed documentation
2. **Check examples** - `example_usage.py` for programmatic usage
3. **Customize configuration** - Edit `.env` for your needs
4. **Test with sample documents** - Place test files in `tests/sample_documents/`

## Getting Help

- Check the main `README.md` for detailed documentation
- Review troubleshooting section in README
- Examine log files for detailed error messages

## Cost Estimation

Gemini 2.0 Flash (recommended):
- Very low cost per document
- Typically $0.01-0.05 per certificate application
- Free tier available for testing

---

**You're ready to go! 🚀**

Process your first certificate application and see the magic happen.
