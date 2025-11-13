# AP Seva Document Validation Workflow

A comprehensive document validation system for processing certificate applications from Andhra Pradesh's AP Seva Portal. The system leverages Google Gemini 2.5's powerful multimodal capabilities to extract, digitize, and validate data from PDFs and images without requiring local OCR processing.

## Overview

This system implements a **two-stage processing pipeline**:

1. **Stage 1: Document Digitization** - Individual documents are sent directly to Gemini API for OCR and structured data extraction
2. **Stage 2: Cross-Document Summary** - Consolidated data is aggregated and validated across all documents to generate a comprehensive summary table

## Supported Certificate Types

The system handles 5 types of certificate applications:

1. **Integrated Certificate** - Community, Nativity, DOB verification
2. **Income Certificate** - Income verification from various sources
3. **OBC Certificate** - Other Backward Classes certification
4. **EWS Certificate** - Economically Weaker Sections certification
5. **Family Member Certificate** - Family member certification for deceased HOF

## Features

- Direct file transmission to Gemini API (no local OCR needed)
- Supports PDF and image formats (JPG, JPEG, PNG)
- Automatic document classification and validation
- Structured key-value extraction with maximum readability
- Cross-document consistency checking
- Comprehensive markdown summary tables
- Robust error handling with automatic retries
- Detailed logging and progress tracking
- Configurable processing parameters

## Installation

### Prerequisites

- Python 3.8 or higher
- Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))

### Setup Steps

1. **Clone the repository**
```bash
git clone <repository-url>
cd document_validation
```

2. **Create virtual environment** (recommended)
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**
```bash
cp .env.example .env
```

Edit `.env` and add your Gemini API key:
```
GEMINI_API_KEY=your_actual_api_key_here
```

## Project Structure

```
document_validation/
├── src/
│   ├── main.py                 # Entry point and workflow orchestration
│   ├── config.py               # Configuration management
│   ├── certificate_types.py   # Certificate specifications
│   ├── gemini_client.py        # Gemini API wrapper
│   ├── document_processor.py  # Stage 1: Document digitization
│   ├── summary_generator.py   # Stage 2: Summary generation
│   ├── file_handler.py         # File validation and metadata
│   └── utils.py                # Utilities and logging
├── tests/
│   └── sample_documents/       # Test documents
├── outputs/
│   ├── stage1_extractions/     # Individual document extractions
│   └── stage2_summaries/       # Final summary tables
├── requirements.txt
├── .env.example
└── README.md
```

## Usage

### Basic Usage

Process documents for an integrated certificate:

```bash
cd src
python main.py \
  --cert-type integrated \
  --files application.pdf caste_cert.pdf ration_card.jpg
```

### With Custom Document Names

```bash
python main.py \
  --cert-type income \
  --files doc1.pdf doc2.jpg doc3.pdf \
  --names "Application Form" "Ration Card" "IT Returns"
```

### Using Wildcards

```bash
python main.py \
  --cert-type ews \
  --files ../tests/sample_documents/*.pdf
```

### Custom Output Directory

```bash
python main.py \
  --cert-type obc \
  --files *.pdf \
  --output ../my_output
```

### With Debug Logging

```bash
python main.py \
  --cert-type family_member \
  --files *.pdf *.jpg \
  --log-level DEBUG \
  --log-file debug.log
```

## Command-Line Options

```
usage: main.py [-h] --files FILES [FILES ...] --cert-type {integrated,income,obc,ews,family_member}
               [--names NAMES [NAMES ...]] [--output OUTPUT] [--no-save-stage1]
               [--log-level {DEBUG,INFO,WARNING,ERROR}] [--log-file LOG_FILE]

Arguments:
  --files               Paths to document files (PDFs and images)
  --cert-type           Type of certificate application
  --names               Optional custom names for documents
  --output              Custom output directory
  --no-save-stage1      Do not save Stage 1 intermediate results
  --log-level           Logging level (default: INFO)
  --log-file            Path to log file
```

## Configuration

### Environment Variables

Edit `.env` to customize behavior:

```bash
# API Configuration
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.0-flash-exp  # or gemini-2.5-pro

# Generation Parameters
TEMPERATURE=0.1          # Lower = more deterministic
TOP_P=0.95
TOP_K=40
MAX_OUTPUT_TOKENS=8192

# File Configuration
MAX_FILE_SIZE_MB=20      # Maximum file size

# Retry Configuration
MAX_RETRIES=3
RETRY_DELAY=2.0
RETRY_BACKOFF=2.0

# Logging
LOG_LEVEL=INFO
```

## Output Format

### Stage 1: Document Extraction

Each document produces two files:

1. **`{document_id}_extracted.txt`** - Raw extracted text with key-value pairs
```
Full name of the Applicant: John Doe

Father's Name: James Doe

Date of Birth: 01/01/1990

...
```

2. **`{document_id}_metadata.json`** - Processing metadata
```json
{
  "document_id": "application_20250113_143022",
  "file_name": "application.pdf",
  "success": true,
  ...
}
```

### Stage 2: Cross-Document Summary

Generates two files:

1. **`{cert_type}_{timestamp}_summary.md`** - Markdown summary table
```markdown
# INTEGRATED Certificate Summary

| Field | Value | Source Document(s) |
| --- | --- | --- |
| Name of the Applicant | John Doe | application.pdf, caste_cert.pdf |
| Father's Name | James Doe | application.pdf |
| Age/DOB | 01/01/1990 | application.pdf, ssc_memo.pdf |
...
```

2. **`{cert_type}_{timestamp}_metadata.json`** - Summary metadata

## Workflow Details

### Stage 1: Document Digitization

For each uploaded document:

1. File is validated (format, size)
2. File metadata is extracted
3. File is uploaded directly to Gemini API
4. Gemini processes the document using its native OCR capabilities
5. Structured key-value pairs are extracted with maximum line separation
6. Results are saved to `outputs/stage1_extractions/`

### Stage 2: Cross-Document Summary

After all documents are processed:

1. All Stage 1 extractions are aggregated
2. Certificate-specific summary fields are defined
3. Consolidated prompt is sent to Gemini API (text-only)
4. Gemini generates a 3-column markdown table:
   - Field name
   - Extracted value
   - Source document(s)
5. Summary is saved to `outputs/stage2_summaries/`

## Certificate-Specific Fields

### Integrated Certificate
- Name, Father's Name, Address, Gender, Age/DOB
- Phone Number, Ration Card Number
- Community, Nativity, Family Income
- Issuer, Date of Issue

### Income Certificate
- Name, Father's Name, Address, Gender, Age/DOB
- Phone Number, Ration Card Number
- Income Details (Lands, Business, Buildings, Labour, Salary, Other, Total)
- Issuer, Date of Issue

### OBC Certificate
- Name, Father's Name, Address, Gender, Age/DOB
- Phone Number, Caste, Sub-Caste, Family Income
- Issuer, Date of Issue

### EWS Certificate
- Name, Father's Name, Address, Gender, Age/DOB
- Phone Number, Ration Card Number, Community
- Assets Details (Agriculture Land, Residential Flat, Residential Plot)
- Gross Annual Income, Issuer, Date of Issue

### Family Member Certificate
- Name, Father's Name, Address, Gender, Age/DOB, Phone Number
- Deceased Details (Name, Father/Husband, Date/Reason/Place of Death, Occupation, Aadhaar)
- Family Members Details (Name, Gender, Age, Relationship with HOF)
- Issuer, Date of Issue

## Error Handling

The system handles various error scenarios:

- **File not found** - Clear error message with file path
- **Unsupported format** - Lists supported formats
- **File too large** - Indicates maximum size limit
- **API failures** - Automatic retry with exponential backoff
- **Processing errors** - Logged with detailed error messages
- **Partial failures** - Continues processing remaining documents

## Best Practices

1. **File Organization** - Organize documents by application/certificate type
2. **File Naming** - Use descriptive filenames (e.g., "application_form.pdf", "ration_card.jpg")
3. **Document Quality** - Ensure documents are clear and readable
4. **Batch Processing** - Process related documents together for better cross-validation
5. **Review Outputs** - Always review Stage 2 summaries for consistency
6. **API Limits** - Be mindful of Gemini API rate limits and quotas

## Troubleshooting

### API Key Issues
```
ValueError: GEMINI_API_KEY environment variable is required
```
**Solution:** Set your API key in `.env` file

### File Upload Failures
```
Error uploading file: File processing failed
```
**Solution:** Check file format, size, and quality. Ensure PDF is not corrupted.

### Import Errors
```
ModuleNotFoundError: No module named 'google.generativeai'
```
**Solution:** Run `pip install -r requirements.txt`

### Permission Errors
```
PermissionError: [Errno 13] Permission denied
```
**Solution:** Ensure output directories are writable

## API Costs

Google Gemini API pricing (as of 2025):
- **Gemini 2.0 Flash**: Most cost-effective for document processing
- **Gemini 2.5 Pro**: Higher accuracy but more expensive

Estimate costs based on:
- Number of documents
- File sizes
- API calls (2 calls per document: upload + generation)

## Limitations

- Maximum file size: 20 MB (configurable)
- Supported formats: PDF, JPG, JPEG, PNG
- Requires active internet connection for API access
- Processing speed depends on file size and API latency
- OCR accuracy depends on document quality

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

[Specify your license here]

## Support

For issues and questions:
- Open an issue on GitHub
- Check the troubleshooting section
- Review Gemini API documentation

## Acknowledgments

- Built for AP Seva Portal certificate verification
- Powered by Google Gemini 2.5 API
- Designed for Andhra Pradesh government services

---

**Note:** This system is designed for authorized government use in processing certificate applications. Ensure compliance with data privacy regulations when handling sensitive documents.
