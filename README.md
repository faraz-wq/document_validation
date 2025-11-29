# Document Validation Service

This service uses Google Vertex AI (Gemini 1.5 Pro) to extract structured data from uploaded documents for various application types.

## Features

- **Multi-format Support**: Accepts PDF, JPG, PNG, etc.
- **Structured Extraction**: Returns JSON conforming to strict Pydantic models.
- **Schema Validation**: Enforces data types and required fields.
- **Source Traceability**: Links extracted data back to source files.

## Prerequisites

- Python 3.10+
- Google Cloud Project with Vertex AI API enabled.
- `gcloud` CLI installed and authenticated (or Service Account key).

## Installation

1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

Set the following environment variables (or use a `.env` file):

```bash
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1 # or your preferred region
```

If running locally without `gcloud auth application-default login`, set:
```bash
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

## Running the Service

Start the FastAPI server:

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.
Interactive API docs: `http://localhost:8000/docs`.

## API Usage

### Endpoint: `POST /extract-summary`

**Parameters:**
- `application_type` (string): One of:
  - "Integrated Certificate"
  - "Income Certificate"
  - "OBC Certificate"
  - "EWS Certificate"
  - "Family Member Certificate"
- `files` (list of files): The documents to process.

**Example (using curl):**

```bash
curl -X 'POST' \
  'http://localhost:8000/extract-summary' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'application_type=Income Certificate' \
  -F 'files=@/path/to/document.pdf'
```

## Testing

Run unit tests:

```bash
python3 -m pytest tests/
```

## Extending

1. **Add new schemas**: Define new Pydantic models in `app/models.py`.
2. **Update Extractor**: Add the new type mapping in `app/extractor.py` inside `_get_schema_for_type`.
