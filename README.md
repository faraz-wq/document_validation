# Document Validation Service

This service uses Google Vertex AI (Gemini 1.5 Pro) to extract structured data from uploaded documents for various application types.

## Features

- **Multi-format Support**: Accepts PDF, JPG, PNG, etc.
- **Structured Extraction**: Returns JSON conforming to strict Pydantic models.
- **Schema Validation**: Enforces data types and required fields.
- **Source Traceability**: Links extracted data back to source files.
- **Modern React UI**: Beautiful, responsive interface with drag & drop support.

## Project Structure

```
document_validation/
├── app/                    # FastAPI backend
│   ├── main.py            # API endpoints
│   ├── extractor.py       # Gemini extraction logic
│   ├── models.py          # Pydantic schemas
│   └── logging_config.py  # Logging setup
├── frontend/              # React frontend
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── App.jsx        # Main app
│   │   └── index.css      # Global styles
│   └── package.json
├── templates/             # Legacy HTML templates (deprecated)
├── tests/                 # Unit tests
└── requirements.txt       # Python dependencies
```

## Prerequisites

- Python 3.10+
- Node.js 16+
- Google Cloud Project with Vertex AI API enabled
- `gcloud` CLI installed and authenticated (or Service Account key)

## Installation

### Backend Setup

1. Clone the repository
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set environment variables:
   ```bash
   export GOOGLE_CLOUD_PROJECT=your-project-id
   export GOOGLE_CLOUD_LOCATION=us-central1
   ```

   If running locally without `gcloud auth application-default login`:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
   ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install Node dependencies:
   ```bash
   npm install
   ```

## Running the Application

### Start the Backend

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.
Interactive API docs: `http://localhost:8000/docs`.

### Start the Frontend

In a separate terminal:

```bash
cd frontend
npm run dev
```

The React app will be available at `http://localhost:3000`.

## Using the Application

1. Open `http://localhost:3000` in your browser
2. Select an application type from the dropdown
3. Upload a document (PDF, JPG, or PNG) via drag & drop or file browser
4. Click "Validate Document" to process
5. View the extracted data alongside the document preview

## API Usage

### Endpoint: `POST /extract-summary`

**Parameters:**
- `application_type` (string): One of:
  - "Integrated Certificate"
  - "Income Certificate"
  - "OBC Certificate"
  - "EWS Certificate"
  - "Family Member Certificate"
- `files` (list of files): The documents to process

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

1. **Add new schemas**: Define new Pydantic models in `app/models.py`
2. **Update Extractor**: Add the new type mapping in `app/extractor.py` inside `_get_schema_for_type`
3. **Update Frontend**: Add the new type to `APPLICATION_TYPES` in `frontend/src/components/UploadForm.jsx`
