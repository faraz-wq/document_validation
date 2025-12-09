# Differences Between Current System and Prompt Requirements

## Overview

This document compares the current document validation system with the requirements described in `prompt.txt`. The current system is a working document validation service with API key-based authentication and schema management, while the prompt describes additional features for JWT-based authentication and user-facing APIs.

## Backend Features

### 1. Authentication System

**Current System:**
- Uses API key-based authentication only
- API keys are validated through header (`X-API-Key`)
- No JWT support
- Users are identified through API key hashes

**Prompt Requirements:**
- JWT authentication with user registration/login endpoints
- Password hashing with bcrypt
- JWT tokens with access/refresh token rotation
- `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout` endpoints
- JWT dependency function `get_current_user_from_jwt()`

### 2. Database Schema

**Current System:**
- Uses PostgreSQL with SQLAlchemy ORM
- `User` table with `email`, `username`, `hashed_password`, `is_active`, `is_admin`
- `ApiKey` table with usage tracking
- `Session` table without user association (no `user_id` or `api_key_id` FKs)
- Separate tables for document processing: `RequestLog`, `SchemaDefinition`, `Document`, `BoundingBox`, `Citation`

**Prompt Requirements:**
- `Session` model should have nullable `user_id` and `api_key_id` foreign keys
- Multi-tenancy support through user association
- Migration of existing `Session` table to add user relations

### 3. API Key Management

**Current System:**
- API key management exists but only through API key authentication
- Functions: `create_api_key()`, `validate_api_key()`, `list_user_api_keys()`, `revoke_api_key()`

**Prompt Requirements:**
- Additional JWT-protected "me" endpoints for user-scoped API key management:
  - `GET /v1/me/api-keys`
  - `POST /v1/me/api-keys`
  - `DELETE /v1/me/api-keys/{key_id}`
- Keep existing API-key-auth endpoints for programmatic usage

### 4. Statistics & Metrics

**Current System:**
- Admin endpoints exist: `/v1/admin/stats`, `/v1/admin/logs`, `/v1/admin/api-keys/usage`
- Basic statistical functions for admin usage

**Prompt Requirements:**
- User-scoped statistics endpoints:
  - `GET /v1/me/stats` - user-specific usage aggregated from their API keys
  - `GET /v1/me/metrics/requests` - time-series data for user's requests
  - `GET /v1/me/logs` - user-filtered request logs
- Refactored shared logic to accept optional `user_id` parameter
- Reusable service functions in `app/services/metrics.py`

### 5. Session Management

**Current System:**
- Public session endpoints: `/sessions`, `/sessions/{session_id}`, `/sessions/{session_id}/document/{filename}`
- Sessions not associated with users (anonymous)
- No user ownership or access control

**Prompt Requirements:**
- User-scoped session endpoints:
  - `GET /v1/me/sessions?limit=50` - user's sessions only
  - `GET /v1/me/sessions/{session_id}` - user's specific session only
- JWT-protected with ownership verification
- Potential deprecation of public session endpoints for multi-tenant safety

### 6. Schema Management

**Current System:**
- API-key-authenticated schema endpoints: `/v1/schemas`, `/v1/schemas/{schema_id}`, etc.
- Schema ownership through `owner_id` relationship
- Configurable extractor with user-based schema access

**Prompt Requirements:**
- JWT-based schema endpoints (parallel to existing API-key endpoints):
  - `GET /v1/me/schemas`
  - `GET /v1/me/schemas/{schema_id}`
  - `POST /v1/me/schemas`
  - `PUT /v1/me/schemas/{schema_id}`
  - `DELETE /v1/me/schemas/{schema_id}`
- Keep existing `/v1/schemas` endpoints for server-to-server clients

## Frontend Features

### 1. Architecture

**Current System:**
- Simple HTML/JS frontend using Jinja2 templates
- Basic upload form and results display
- No routing or authentication UI
- Uses `/static` directory for static files

**Prompt Requirements:**
- React + Vite application with complete dashboard
- `react-router-dom` for routing
- Global auth context and `AuthProvider`
- Protected routes with `ProtectedLayout`
- Multiple dashboard pages (API keys, schemas, sessions, logs)

### 2. Authentication UI

**Current System:**
- No user authentication UI
- Only API key-based access

**Prompt Requirements:**
- Login page (`/login`) with email/password form
- Registration page (`/register`) with email, username, password
- Auth context with token storage and refresh handling
- `fetchWithAuth` wrapper for API calls
- Protected layout components

### 3. Dashboard Features

**Current System:**
- Basic HTML interface with document upload and results display
- No metrics or statistics dashboard
- No API key management UI
- No schema management UI

**Prompt Requirements:**
- Dashboard overview with metrics and charts
- API keys management page with CRUD operations
- Schema management page with create/edit/delete
- Session management page with filters
- Optional logs page with filtering

## Security & Access Control

### Current System
- API key-based authentication for schema endpoints
- Admin endpoints protected with `get_current_admin_user`
- No user ownership verification for sessions
- No JWT-based authentication

### Prompt Requirements
- JWT-based authentication for user endpoints
- Multi-tenant safety with user ownership verification
- All `v1/me/*` endpoints must filter by `current_user.id`
- Consider deprecating or restricting public session endpoints

## Implementation Status Summary

| Feature | Current Status | Required by Prompt |
|---------|----------------|-------------------|
| Basic Document Extraction | ✅ Implemented | ✅ Required |
| API Key Authentication | ✅ Implemented | ✅ Keep existing |
| JWT Authentication | ❌ Missing | ✅ Required |
| User Registration/Login | ❌ Missing | ✅ Required |
| User Dashboard | ❌ Missing | ✅ Required |
| Session Multi-tenancy | ❌ Missing | ✅ Required |
| User-scoped Endpoints | ❌ Missing | ✅ Required |
| React Frontend | ❌ Missing | ✅ Required |
| OAuth/SSO | ❌ Missing | ❌ Not mentioned |

## Next Steps for Complete Implementation

1. **Implement JWT Authentication**: Add registration, login, refresh, and logout endpoints
2. **Migrate Database Schema**: Add user_id/api_key_id to Session table
3. **Create User-Scoped Endpoints**: Implement all `/v1/me/*` endpoints
4. **Develop React Frontend**: Create complete dashboard with routing and authentication
5. **Refactor Shared Logic**: Create reusable service functions for admin/user endpoints
6. **Add Security Measures**: Implement proper ownership checks and multi-tenant safety