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

### V0 Endpoints (Legacy)

#### Endpoint: `POST /extract-summary`

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

### V1 Endpoints (New User-Specific Features)

The v1 endpoints provide enhanced functionality with proper user authentication and ownership controls. All v1 endpoints require JWT authentication.

#### Authentication Setup

First, register/login to get a JWT token:

```bash
# Register new user
curl -X 'POST' \
  'http://localhost:8000/v1/register' \
  -H 'Content-Type: application/json' \
  -d '{"email": "user@example.com", "username": "username", "password": "password"}'

# Or login with existing credentials
curl -X 'POST' \
  'http://localhost:8000/v1/login' \
  -H 'Content-Type: application/json' \
  -d '{"username": "username", "password": "password"}'
```

The response will include a JWT token for authentication.

#### V1 Session Management

##### List User Sessions
`GET /v1/me/sessions/`

**Headers:**
- `Authorization: Bearer {jwt_token}`

**Query Parameters:**
- `limit` (optional, integer, default: 50, min: 1, max: 100)
- `offset` (optional, integer, default: 0, min: 0)

**Example:**
```bash
curl -X 'GET' \
  'http://localhost:8000/v1/me/sessions/?limit=25' \
  -H 'Authorization: Bearer {jwt_token}'
```

##### Get Specific Session
`GET /v1/me/sessions/{session_id}`

**Headers:**
- `Authorization: Bearer {jwt_token}`
- `session_id`: Unique identifier of the session

**Example:**
```bash
curl -X 'GET' \
  'http://localhost:8000/v1/me/sessions/uuid-here' \
  -H 'Authorization: Bearer {jwt_token}'
```

#### V1 API Key Management

##### List User API Keys
`GET /v1/me/api-keys/`

**Headers:**
- `Authorization: Bearer {jwt_token}`

**Example:**
```bash
curl -X 'GET' \
  'http://localhost:8000/v1/me/api-keys/' \
  -H 'Authorization: Bearer {jwt_token}'
```

##### Create User API Key
`POST /v1/me/api-keys/`

**Headers:**
- `Authorization: Bearer {jwt_token}`
- `Content-Type: application/json`

**Request Body:**
```json
{
  "description": "string"  // optional description
}
```

**Example:**
```bash
curl -X 'POST' \
  'http://localhost:8000/v1/me/api-keys/' \
  -H 'Authorization: Bearer {jwt_token}' \
  -H 'Content-Type: application/json' \
  -d '{"description": "My production API key"}'
```

> **Note:** API key is returned in plaintext only once. Store it securely.

##### Revoke User API Key
`DELETE /v1/me/api-keys/{key_id}`

**Headers:**
- `Authorization: Bearer {jwt_token}`
- `key_id`: Integer ID of the API key to revoke

**Example:**
```bash
curl -X 'DELETE' \
  'http://localhost:8000/v1/me/api-keys/5' \
  -H 'Authorization: Bearer {jwt_token}'
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
