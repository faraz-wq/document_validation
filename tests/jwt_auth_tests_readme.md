# JWT Authentication Tests

This test suite provides comprehensive unit tests for the JWT-based authentication system implemented for the Document Validation Service.

## Test Coverage

The test suite covers all four JWT authentication endpoints:

### 1. Registration Endpoint (`/v1/auth/register`)
- ✅ Successful user registration
- ✅ Duplicate email validation
- ✅ Duplicate username validation
- ✅ Email format validation
- ✅ Password length validation (min 8 chars)
- ✅ Username length validation (min 3, max 50 chars)
- ✅ User data validation after registration

### 2. Login Endpoint (`/v1/auth/login`)
- ✅ Successful login with correct credentials
- ✅ Invalid email (user doesn't exist)
- ✅ Wrong password validation
- ✅ Active user validation

### 3. Token Refresh Endpoint (`/v1/auth/refresh`)
- ✅ Successful token refresh with valid refresh token
- ✅ Invalid refresh token handling
- ✅ Attempt to use access token as refresh token
- ✅ JWT token validation and structure

### 4. Logout Endpoint (`/v1/auth/logout`)
- ✅ Successful logout (stateless)
- ✅ Logout with refresh token (optional parameter)

### 5. Core Security Functions
- ✅ Password hashing and verification
- ✅ Access token creation and decoding
- ✅ Refresh token creation and decoding
- ✅ Token structure validation
- ✅ Complete registration → login → refresh → logout flow

## Test File Structure

```
tests/test_jwt_auth.py
├── TestAuthEndpoints class
│   ├── setup_method() - Database cleanup before each test
│   ├── test_register_*() - Registration tests
│   ├── test_login_*() - Login tests
│   ├── test_refresh_token_*() - Token refresh tests
│   ├── test_logout_*() - Logout tests
│   ├── test_*() - Core functionality tests
│   └── test_register_login_flow_complete() - End-to-end flow
└── Helper functions and fixtures
```

## Database Setup

- Uses in-memory SQLite database for isolated testing
- Each test method starts with a clean database state
- No external database dependencies required

## Test Execution

To run the tests:

```bash
# Activate virtual environment
source venv/bin/activate

# Run all JWT auth tests
python -m pytest tests/test_jwt_auth.py -v

# Run with short traceback
python -m pytest tests/test_jwt_auth.py --tb=short

# Run specific test
python -m pytest tests/test_jwt_auth.py::TestAuthEndpoints::test_register_success
```

## Test Quality

- **Complete Coverage**: All endpoints and error scenarios tested
- **Isolation**: Each test runs in isolation with clean state
- **Validation**: Request/response schemas validated
- **Error Handling**: Comprehensive error scenario testing
- **Integration**: End-to-end flow testing
- **Security**: Token validation and security checks

## Expected Results

All tests should pass, confirming that the JWT authentication system functions correctly and handles all expected scenarios properly.