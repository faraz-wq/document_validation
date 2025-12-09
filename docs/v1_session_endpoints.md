# Document Validation Service - v1 Session Endpoints Documentation

## Endpoints

### List User Sessions
`GET /v1/me/sessions`

#### Description
Retrieves a paginated list of sessions owned by the authenticated user. This endpoint requires a valid JWT token in the Authorization header.

#### Authentication
JWT Bearer token required. The token must be included in the `Authorization` header as `Bearer {token}`.

#### Query Parameters
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| limit | integer | No | 50 | Number of sessions to return per page. Must be between 1 and 100. |
| offset | integer | No | 0 | Number of sessions to skip before starting to collect the result set. |

#### Response
**Status Code: 200 OK**

```json
{
  "items": [
    {
      "session_id": "string",
      "application_type": "string",
      "created_at": "2025-12-09T12:00:00Z",
      "file_count": 0
    }
  ],
  "total_count": 0
}
```

##### Response Fields
- **items**: Array of session objects
  - **session_id**: Unique identifier of the session
  - **application_type**: The type of application used for this session (e.g., "Income Certificate", "OBC Certificate")
  - **created_at**: ISO 8601 timestamp of when the session was created
  - **file_count**: Number of documents associated with this session
- **total_count**: Total number of sessions available for the user (useful for pagination)

#### Error Responses
- **401 Unauthorized**: Returned when the JWT token is missing or invalid
- **422 Unprocessable Entity**: Returned when query parameters are invalid (e.g., limit < 1 or > 100)

#### Example Request
```
GET /v1/me/sessions?limit=25&offset=0
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### Example Response
```json
{
  "items": [
    {
      "session_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
      "application_type": "Income Certificate",
      "created_at": "2025-12-09T10:30:45.123456Z",
      "file_count": 2
    },
    {
      "session_id": "f0e9d8c7-b6a5-4321-fedc-ba9876543210",
      "application_type": "EWS Certificate",
      "created_at": "2025-12-08T15:22:33.987654Z",
      "file_count": 1
    }
  ],
  "total_count": 15
}
```

---

### Get User Session Detail
`GET /v1/me/sessions/{session_id}`

#### Description
Retrieves detailed information about a specific session owned by the authenticated user. Only returns sessions that belong to the authenticated user. If the session doesn't exist or doesn't belong to the user, returns a 404 error.

#### Authentication
JWT Bearer token required. The token must be included in the `Authorization` header as `Bearer {token}`.

#### Path Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| session_id | string | Yes | Unique identifier of the session to retrieve |

#### Response
**Status Code: 200 OK**

```json
{
  "session_id": "string",
  "application_type": "string",
  "created_at": "2025-12-09T12:00:00Z",
  "summary": {},
  "bounding_boxes": {},
  "citations": {},
  "documents": []
}
```

##### Response Fields
- **session_id**: Unique identifier of the session
- **application_type**: The type of application used for this session (e.g., "Income Certificate", "OBC Certificate")
- **created_at**: ISO 8601 timestamp of when the session was created
- **summary**: Object containing extracted data from the documents
- **bounding_boxes**: Object mapping field names to their bounding box coordinates in the documents
- **citations**: Object mapping field names to their source citations
- **documents**: Array of document objects
  - **filename**: Original filename of the document
  - **file_path**: Path to the stored document file
  - **mime_type**: MIME type of the document

#### Error Responses
- **401 Unauthorized**: Returned when the JWT token is missing or invalid
- **403 Forbidden/404 Not Found**: Returned when the session exists but doesn't belong to the authenticated user (returning 404 to avoid leaking existence of sessions owned by other users)
- **404 Not Found**: Returned when the session doesn't exist

#### Example Request
```
GET /v1/me/sessions/a1b2c3d4-e5f6-7890-1234-567890abcdef
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### Example Response
```json
{
  "session_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
  "application_type": "Income Certificate",
  "created_at": "2025-12-09T10:30:45.123456Z",
  "summary": {
    "applicant_name": "John Doe",
    "fathers_name": "Robert Doe",
    "address": "123 Main Street, City, State",
    "income_details": {
      "total_gross_income": "₹500,000",
      "salary_wife_husband": "₹300,000"
    }
  },
  "bounding_boxes": {
    "applicant_name": {
      "filename": "document.pdf",
      "page": 1,
      "coordinates": [120, 340, 220, 560]
    }
  },
  "citations": {
    "applicant_name": "document.pdf (Page 1)"
  },
  "documents": [
    {
      "filename": "document.pdf",
      "file_path": "a1b2c3d4-e5f6-7890-1234-567890abcdef_document.pdf",
      "mime_type": "application/pdf"
    }
  ]
}
```

---

## Authentication and Authorization

Both endpoints require a valid JWT token to access user session data. The authentication flow works as follows:

1. User authenticates via the `/v1/auth/login` endpoint to obtain a JWT token
2. The token must be included in the Authorization header for all requests to these endpoints
3. The system validates the JWT token and extracts the user ID
4. Session access is restricted to the authenticated user's sessions only
5. Attempting to access another user's session will result in a 404 error

## Error Handling

All endpoints follow standard HTTP error response patterns:

- **401 Unauthorized**: Invalid or missing authentication credentials
- **403 Forbidden/404 Not Found**: User attempting to access resources they don't own (404 used to prevent information leakage)
- **404 Not Found**: Resource does not exist
- **422 Unprocessable Entity**: Invalid request parameters
- **500 Internal Server Error**: Unexpected server-side error

## Rate Limiting

All v1 endpoints may be subject to rate limiting. Exceeding rate limits will result in a 429 Too Many Requests response.

## Versioning

These endpoints are part of the v1 API and are prefixed with `/v1`. They follow semantic versioning, and breaking changes will result in a new version prefix (e.g., `/v2`).