# Document Validation Service - v1 API Documentation

## Overview

This document describes the v1 API endpoints for the Document Validation Service. These endpoints provide enhanced functionality for user authentication, session management, and API key management with proper user ownership and access controls.

## Authentication

All v1 endpoints require JWT authentication. Include your JWT token in the Authorization header as:

```
Authorization: Bearer {your-jwt-token}
```

## Available Endpoints

### V1 User Session Management

#### List User Sessions
**GET** `/v1/me/sessions/`

Lists all sessions owned by the authenticated user.

**Parameters:**
- `limit` (optional, integer, default: 50): Maximum number of sessions to return per page (1-100)
- `offset` (optional, integer, default: 0): Number of sessions to skip before starting to collect the result set

**Response:**
```json
{
  "items": [
    {
      "session_id": "string",
      "application_type": "string", 
      "created_at": "2025-12-09T10:30:45.123456Z",
      "file_count": 2
    }
  ],
  "total_count": 15
}
```

#### Get Session Details
**GET** `/v1/me/sessions/{session_id}`

Retrieves detailed information about a specific session owned by the user.

**Path Parameters:**
- `session_id` (string): Unique identifier of the session to retrieve

**Response:**
```json
{
  "session_id": "string",
  "application_type": "string",
  "created_at": "2025-12-09T10:30:45.123456Z",
  "summary": {},
  "bounding_boxes": {},
  "citations": {},
  "documents": []
}
```

---

### V1 User API Key Management

#### List User API Keys
**GET** `/v1/me/api-keys/`

Lists all API keys owned by the authenticated user.

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "description": "string",
      "created_at": "2025-12-09T10:30:45.123456Z",
      "last_used_at": "2025-12-09T12:15:30.246810Z",
      "revoked": false,
      "total_requests": 150,
      "total_errors": 2,
      "total_documents": 10
    }
  ]
}
```

#### Create User API Key
**POST** `/v1/me/api-keys/`

Creates a new API key for the authenticated user.

**Request Body:**
```json
{
  "description": "string"
}
```

**Response:**
```json
{
  "api_key": "string",
  "id": 3,
  "message": "API key created"
}
```

> **Important**: The API key is returned in plaintext only once. Store it securely in your client application.

#### Revoke User API Key
**DELETE** `/v1/me/api-keys/{key_id}`

Revokes an API key owned by the authenticated user.

**Path Parameters:**
- `key_id` (integer): Unique identifier of the API key to revoke

**Response:**
```json
{
  "message": "API key revoked"
}
```

---

## Error Handling

All endpoints follow standard HTTP error response patterns:

- `401 Unauthorized`: Invalid or missing authentication credentials
- `403 Forbidden / 404 Not Found`: Attempting to access resources owned by other users (404 used for security to prevent information leakage)
- `404 Not Found`: Resource does not exist
- `422 Unprocessable Entity`: Invalid request parameters
- `500 Internal Server Error`: Server-side error

## Usage Notes

### Session Management
- Sessions are user-specific and can only be accessed by their owners
- Pagination parameters allow efficient retrieval of large session collections
- Session data includes extracted information, bounding boxes, and citations

### API Key Management
- API keys are user-specific and can only be managed by their owners
- Revoked API keys become immediately invalid
- Created API keys should be stored securely since they are only shown once

## Versioning

These endpoints are part of the v1 API and are designed to maintain backward compatibility. Breaking changes would result in a new version prefix (e.g., v2).

## Security Considerations

- JWT tokens have expiration times and must be refreshed periodically
- API keys should be treated as sensitive credentials and stored securely
- Access is strictly limited to user-owned resources
- Sensitive information (like plaintext API keys) is only exposed during creation