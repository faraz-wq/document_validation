# JWT Authentication API Documentation

## Overview
This document describes the JWT-based authentication endpoints that have been added to the Document Validation Service. These endpoints are part of the v1 API and provide user registration, login, token refresh, and logout functionality using JWT tokens.

## Base URL
```
http://your-domain.com/
```

## Authentication
- All `/v1/auth/*` endpoints are public except for `/v1/auth/refresh` which requires a valid refresh token
- After login, access tokens should be used for protected endpoints with the `Authorization: Bearer {token}` header

## Endpoints

### POST /v1/auth/register
Register a new user account with email, username, and password.

#### Request
**URL:** `/v1/auth/register`

**Content-Type:** `application/json`

**Request Body:**
```json
{
  "email": "user@example.com",
  "username": "johndoe",
  "password": "securePassword123"
}
```

**Fields:**
- `email` (string, required): Valid email address for the user
- `username` (string, required): Unique username (3-50 characters)
- `password` (string, required): Password with minimum 8 characters

#### Response
**Success Response (200):**
```json
{
  "user": {
    "id": 123,
    "email": "user@example.com", 
    "username": "johndoe",
    "is_admin": false
  },
  "api_key": "dv_xxxxxxxxxxxxxxxxxxxxxxxxxx"  // Optional
}
```

**Error Response (400):**
```json
{
  "detail": "User with this email or username already exists"
}
```

**Request Body Schema:**
```json
{
  "type": "object",
  "properties": {
    "email": {
      "type": "string",
      "format": "email",
      "description": "Valid email address for the user"
    },
    "username": {
      "type": "string", 
      "minLength": 3,
      "maxLength": 50,
      "description": "Unique username for the account"
    },
    "password": {
      "type": "string",
      "minLength": 8,
      "description": "Password with minimum 8 characters"
    }
  },
  "required": ["email", "username", "password"]
}
```

**Response Schema:**
```json
{
  "type": "object",
  "properties": {
    "user": {
      "type": "object",
      "properties": {
        "id": {"type": "integer", "description": "Unique user identifier"},
        "email": {"type": "string", "format": "email"},
        "username": {"type": "string"},
        "is_admin": {"type": "boolean"}
      },
      "required": ["id", "email", "username", "is_admin"]
    },
    "api_key": {
      "type": ["string", "null"],
      "description": "API key for the user if created, otherwise null"
    }
  },
  "required": ["user"]
}
```

---

### POST /v1/auth/login
Authenticate user with email and password to receive JWT tokens.

#### Request
**URL:** `/v1/auth/login`

**Content-Type:** `application/json`

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securePassword123"
}
```

**Fields:**
- `email` (string, required): User's email address
- `password` (string, required): User's password

#### Response
**Success Response (200):**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "user": {
    "id": 123,
    "email": "user@example.com", 
    "username": "johndoe",
    "is_admin": false
  }
}
```

**Error Response (401):**
```json
{
  "detail": "Incorrect email or user is inactive"
}
```

**Error Response (401):**
```json
{
  "detail": "Incorrect password"
}
```

**Request Body Schema:**
```json
{
  "type": "object",
  "properties": {
    "email": {
      "type": "string",
      "format": "email",
      "description": "User's email address"
    },
    "password": {
      "type": "string",
      "description": "User's password"
    }
  },
  "required": ["email", "password"]
}
```

**Response Schema:**
```json
{
  "type": "object",
  "properties": {
    "access_token": {"type": "string", "description": "JWT access token"},
    "refresh_token": {"type": "string", "description": "JWT refresh token"},
    "token_type": {"type": "string", "enum": ["bearer"], "description": "Type of token"},
    "user": {
      "type": "object",
      "properties": {
        "id": {"type": "integer", "description": "Unique user identifier"},
        "email": {"type": "string", "format": "email"},
        "username": {"type": "string"},
        "is_admin": {"type": "boolean"}
      },
      "required": ["id", "email", "username", "is_admin"]
    }
  },
  "required": ["access_token", "refresh_token", "token_type", "user"]
}
```

---

### POST /v1/auth/refresh
Refresh the access token using a valid refresh token.

#### Request
**URL:** `/v1/auth/refresh`

**Content-Type:** `application/json`

**Request Body:**
```json
{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Fields:**
- `refresh_token` (string, required): Valid JWT refresh token

#### Response
**Success Response (200):**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer"
}
```

**Error Response (401):**
```json
{
  "detail": "Invalid refresh token"
}
```

**Error Response (401):**
```json
{
  "detail": "Invalid token type"
}
```

**Request Body Schema:**
```json
{
  "type": "object",
  "properties": {
    "refresh_token": {
      "type": "string",
      "description": "Valid JWT refresh token"
    }
  },
  "required": ["refresh_token"]
}
```

**Response Schema:**
```json
{
  "type": "object",
  "properties": {
    "access_token": {"type": "string", "description": "New JWT access token"},
    "token_type": {"type": "string", "enum": ["bearer"], "description": "Type of token"}
  },
  "required": ["access_token", "token_type"]
}
```

---

### POST /v1/auth/logout
Logout the user (stateless implementation).

#### Request
**URL:** `/v1/auth/logout`

**Content-Type:** `application/json`

**Request Body (optional):**
```json
{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Fields (optional):**
- `refresh_token` (string): Refresh token to optionally invalidate

#### Response
**Success Response (200):**
```json
{
  "message": "ok"
}
```

**Response Schema:**
```json
{
  "type": "object",
  "properties": {
    "message": {"type": "string", "enum": ["ok"], "description": "Success message"}
  },
  "required": ["message"]
}
```

---

## JWT Token Structure

### Access Token Payload
```json
{
  "sub": "123",                     // User ID as string
  "email": "user@example.com",      // User email
  "is_admin": false,                // Whether user is admin
  "exp": 1678886400,                // Expiration timestamp
  "type": "access"                  // Token type
}
```

### Refresh Token Payload
```json
{
  "sub": "123",                     // User ID as string
  "exp": 1678886400,                // Expiration timestamp
  "type": "refresh"                 // Token type
}
```

## Token Expiration
- **Access Token:** 30 minutes (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`)
- **Refresh Token:** 7 days (configurable via `REFRESH_TOKEN_EXPIRE_DAYS`)

## Security Considerations
1. Access tokens should be stored securely in the client (e.g., httpOnly cookies or secure localStorage)
2. Refresh tokens should be stored more securely (preferably httpOnly cookies)
3. Both tokens are signed with HS256 algorithm using the server's secret key
4. Tokens contain expiration times to limit their validity period
5. The system checks user's active status during token validation

## Error Codes
- `200` - Success
- `400` - Bad Request (validation errors, duplicate users)
- `401` - Unauthorized (invalid credentials, expired/invalid tokens)
- `500` - Internal Server Error

## Integration Notes
- These endpoints are part of the v1 API namespace
- Existing API-key authentication endpoints remain unchanged
- User accounts created through this system will have `hashed_password` and `is_active` fields properly set
- Optional API key creation happens during registration as a convenience for new users