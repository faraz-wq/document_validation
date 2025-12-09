# Document Validation Service - v1 Me API Keys Endpoints Documentation

## Endpoints

### List User API Keys
`GET /v1/me/api-keys`

#### Description
Retrieves a list of API keys owned by the authenticated user. This endpoint requires a valid JWT token in the Authorization header.

#### Authentication
JWT Bearer token required. The token must be included in the `Authorization` header as `Bearer {token}`.

#### Response
**Status Code: 200 OK**

```json
{
  "items": [
    {
      "id": 1,
      "description": "My production key",
      "created_at": "2025-12-09T12:00:00Z",
      "last_used_at": "2025-12-09T12:00:00Z",
      "revoked": false,
      "total_requests": 150,
      "total_errors": 2,
      "total_documents": 10
    }
  ]
}
```

##### Response Fields
- **items**: Array of API key objects
  - **id**: Unique identifier of the API key
  - **description**: User-provided description of the API key (can be null)
  - **created_at**: ISO 8601 timestamp of when the API key was created
  - **last_used_at**: ISO 8601 timestamp of when the API key was last used (can be null)
  - **revoked**: Boolean indicating if the API key has been revoked
  - **total_requests**: Total number of requests made using this API key
  - **total_errors**: Total number of errors encountered using this API key
  - **total_documents**: Total number of documents processed using this API key

#### Error Responses
- **401 Unauthorized**: Returned when the JWT token is missing or invalid

#### Example Request
```
GET /v1/me/api-keys
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### Example Response
```json
{
  "items": [
    {
      "id": 1,
      "description": "Production API key",
      "created_at": "2025-12-09T10:30:45.123456Z",
      "last_used_at": "2025-12-09T12:15:30.246810Z",
      "revoked": false,
      "total_requests": 150,
      "total_errors": 2,
      "total_documents": 10
    },
    {
      "id": 2,
      "description": "Development key",
      "created_at": "2025-12-08T14:22:33.987654Z",
      "last_used_at": null,
      "revoked": false,
      "total_requests": 0,
      "total_errors": 0,
      "total_documents": 0
    }
  ]
}
```

---

### Create User API Key
`POST /v1/me/api-keys`

#### Description
Creates a new API key for the authenticated user. The API key is returned in plaintext only once, so it should be stored securely by the client.

#### Authentication
JWT Bearer token required. The token must be included in the `Authorization` header as `Bearer {token}`.

#### Request Body
```json
{
  "description": "string"
}
```

##### Request Fields
- **description**: Optional description for the new API key (default: "")

#### Response
**Status Code: 200 OK**

```json
{
  "api_key": "string",
  "id": 0,
  "message": "API key created"
}
```

##### Response Fields
- **api_key**: The newly created API key in plaintext format (starts with "dv_")
- **id**: Unique identifier of the created API key
- **message**: Status message confirming creation

#### Error Responses
- **401 Unauthorized**: Returned when the JWT token is missing or invalid

#### Example Request
```
POST /v1/me/api-keys
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "description": "My new production API key"
}
```

#### Example Response
```json
{
  "api_key": "dv_BxRc8J3fFp9wE2vN6yH1kL5mQ7zT4sA3dG6hJ8nM2p",
  "id": 3,
  "message": "API key created"
}
```

---

### Revoke User API Key
`DELETE /v1/me/api-keys/{key_id}`

#### Description
Revokes an API key owned by the authenticated user. Once revoked, the API key becomes invalid and cannot be used for authentication.

#### Path Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| key_id | integer | Yes | Unique identifier of the API key to revoke |

#### Authentication
JWT Bearer token required. The token must be included in the `Authorization` header as `Bearer {token}`.

#### Response
**Status Code: 200 OK**

```json
{
  "message": "API key revoked"
}
```

##### Response Fields
- **message**: Status message confirming revocation

#### Error Responses
- **401 Unauthorized**: Returned when the JWT token is missing or invalid
- **404 Not Found**: Returned when the API key doesn't exist or doesn't belong to the authenticated user

#### Example Request
```
DELETE /v1/me/api-keys/3
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### Example Response
```json
{
  "message": "API key revoked"
}
```

---

## Authentication and Authorization

All endpoints require a valid JWT token to access user API keys. The authentication flow works as follows:

1. User authenticates via the `/v1/auth/login` endpoint to obtain a JWT token
2. The token must be included in the Authorization header for all requests to these endpoints
3. API key access is restricted to the authenticated user's keys only
4. Attempting to access or modify another user's API key will result in a 404 error

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