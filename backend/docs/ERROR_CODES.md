# Mobile API Error Codes Documentation

## Overview

All API errors follow a standardized format for consistent error handling in the iOS mobile app. This document provides a comprehensive reference for all error codes, their meanings, and recommended client-side handling.

## Error Response Format

All errors are returned in the following JSON format:

```json
{
  "error": {
    "code": "AUTH_INVALID_CREDENTIALS",
    "message": "Invalid email or password",
    "details": {},
    "timestamp": "2025-11-04T10:30:00Z"
  }
}
```

### Fields

- **code**: String error code from the `ErrorCode` enum (see categories below)
- **message**: Human-readable error message for display
- **details**: Object containing additional error-specific information
- **timestamp**: ISO 8601 timestamp when the error occurred

## Error Categories

### Authentication Errors (AUTH_*)

Errors related to user authentication, tokens, and sessions.

| Code | Status | Description | User Action |
|------|--------|-------------|-------------|
| `AUTH_INVALID_CREDENTIALS` | 401 | Invalid email or password provided during login | Check credentials and try again |
| `AUTH_TOKEN_EXPIRED` | 401 | Access token has expired and needs refresh | Request token refresh using refresh token |
| `AUTH_TOKEN_INVALID` | 401 | Token is malformed or invalid | Re-authenticate to get new token |
| `AUTH_TOKEN_MISSING` | 401 | Authorization token not provided in request | Include valid token in Authorization header |
| `AUTH_SESSION_EXPIRED` | 401 | Session has expired due to inactivity | Log in again |
| `AUTH_USER_NOT_FOUND` | 404 | User account does not exist | Verify email or create new account |
| `AUTH_USER_INACTIVE` | 403 | User account is inactive or deactivated | Contact support to reactivate account |
| `AUTH_USER_SUSPENDED` | 403 | User account is suspended | Contact support |
| `AUTH_EMAIL_EXISTS` | 400 | Email address already registered | Use different email or log in with existing account |
| `AUTH_WEAK_PASSWORD` | 400 | Password does not meet requirements | Use stronger password (8+ characters) |
| `AUTH_REFRESH_FAILED` | 401 | Failed to refresh access token | Re-authenticate with credentials |
| `AUTH_DEVICE_NOT_REGISTERED` | 400 | Device not registered for push notifications | Register device first |
| `AUTH_OAUTH_FAILED` | 500 | OAuth authentication failed | Try reconnecting or contact support |
| `AUTH_OAUTH_CANCELLED` | 400 | User cancelled OAuth flow | Restart OAuth flow if needed |

**iOS Handling Example:**
```swift
switch errorCode {
case "AUTH_TOKEN_EXPIRED":
    // Attempt token refresh
    await tokenManager.refreshToken()
case "AUTH_INVALID_CREDENTIALS":
    // Show login error
    showAlert("Invalid credentials")
case "AUTH_SESSION_EXPIRED":
    // Redirect to login
    navigationController.popToRootViewController()
}
```

### Validation Errors (VALIDATION_*)

Errors related to input validation and data format.

| Code | Status | Description | User Action |
|------|--------|-------------|-------------|
| `VALIDATION_INVALID_INPUT` | 400 | Input data validation failed | Check input format and try again |
| `VALIDATION_MISSING_FIELD` | 400 | Required field is missing | Provide all required fields |
| `VALIDATION_INVALID_EMAIL` | 400 | Email format is invalid | Enter valid email address |
| `VALIDATION_INVALID_FORMAT` | 400 | Data format is incorrect | Check format requirements |
| `VALIDATION_FIELD_TOO_LONG` | 400 | Field exceeds maximum length | Reduce field length |
| `VALIDATION_FIELD_TOO_SHORT` | 400 | Field below minimum length | Increase field length |
| `VALIDATION_INVALID_DATE` | 400 | Date format or value is invalid | Provide valid date |
| `VALIDATION_INVALID_URL` | 400 | URL format is invalid | Enter valid URL |

**iOS Handling Example:**
```swift
if errorCode == "VALIDATION_INVALID_INPUT" {
    // Parse validation_errors from details
    if let validationErrors = error.details["validation_errors"] as? [[String: Any]] {
        for fieldError in validationErrors {
            let field = fieldError["field"] as? String
            let message = fieldError["message"] as? String
            // Highlight field in UI
            highlightField(field, withError: message)
        }
    }
}
```

### Rate Limiting Errors (RATE_LIMIT_*)

Errors related to API rate limits and quotas.

| Code | Status | Description | User Action |
|------|--------|-------------|-------------|
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests in short time period | Wait before retrying (see retry_after field) |
| `RATE_LIMIT_TOO_MANY_REQUESTS` | 429 | Request rate exceeded | Slow down request rate |
| `RATE_LIMIT_QUOTA_EXCEEDED` | 429 | Daily/monthly quota exceeded | Wait for quota reset or upgrade plan |
| `RATE_LIMIT_DEVICE_LIMIT` | 429 | Too many requests from this device | Wait before retrying |
| `RATE_LIMIT_API_LIMIT` | 429 | API key quota exceeded | Check API key status or upgrade |

**iOS Handling Example:**
```swift
if errorCode.hasPrefix("RATE_LIMIT_") {
    let retryAfter = error.details["retry_after"] as? Int ?? 60
    showAlert("Too many requests. Please try again in \(retryAfter) seconds.")

    // Implement exponential backoff
    DispatchQueue.main.asyncAfter(deadline: .now() + .seconds(retryAfter)) {
        self.retryRequest()
    }
}
```

### Server Errors (SERVER_*)

Errors related to server-side issues.

| Code | Status | Description | User Action |
|------|--------|-------------|-------------|
| `SERVER_INTERNAL_ERROR` | 500 | Internal server error occurred | Try again later or contact support |
| `SERVER_DATABASE_ERROR` | 500 | Database operation failed | Try again later |
| `SERVER_NETWORK_ERROR` | 500 | Network communication error | Check connection and retry |
| `SERVER_SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable | Try again in a few minutes |
| `SERVER_TIMEOUT` | 504 | Request timed out | Check connection and retry |
| `SERVER_MAINTENANCE` | 503 | Server under maintenance | Check status page for updates |

**iOS Handling Example:**
```swift
if errorCode.hasPrefix("SERVER_") {
    // Show user-friendly error
    showAlert("Server error. Please try again later.")

    // Log to analytics
    Analytics.logEvent("server_error", parameters: [
        "code": errorCode,
        "endpoint": endpoint
    ])
}
```

### Resource Errors (RESOURCE_*)

Errors related to resource access and availability.

| Code | Status | Description | User Action |
|------|--------|-------------|-------------|
| `RESOURCE_NOT_FOUND` | 404 | Requested resource does not exist | Verify resource ID and try again |
| `RESOURCE_ALREADY_EXISTS` | 409 | Resource already exists | Use existing resource or choose different identifier |
| `RESOURCE_DELETED` | 410 | Resource has been deleted | Cannot access deleted resource |
| `RESOURCE_FORBIDDEN` | 403 | Access to resource is forbidden | Ensure you have proper permissions |

### API Key Errors (API_KEY_*)

Errors related to user API keys for AI services.

| Code | Status | Description | User Action |
|------|--------|-------------|-------------|
| `API_KEY_MISSING` | 400 | API key not configured | Add API key in settings |
| `API_KEY_INVALID` | 401 | API key is invalid or incorrect | Check API key and update |
| `API_KEY_EXPIRED` | 401 | API key has expired | Renew API key |
| `API_KEY_QUOTA_EXCEEDED` | 429 | API key usage quota exceeded | Wait for reset or upgrade API plan |

### Social Media Errors (SOCIAL_*)

Errors related to social media platform integration.

| Code | Status | Description | User Action |
|------|--------|-------------|-------------|
| `SOCIAL_CONNECTION_FAILED` | 500 | Failed to connect to social media platform | Try reconnecting your account |
| `SOCIAL_TOKEN_EXPIRED` | 401 | Social media access token expired | Reconnect your social media account |
| `SOCIAL_PUBLISH_FAILED` | 500 | Failed to publish content to platform | Check platform status and retry |
| `SOCIAL_PLATFORM_ERROR` | 500 | Social media platform returned an error | Check platform-specific error in details |
| `SOCIAL_NOT_CONNECTED` | 400 | Social media account not connected | Connect your social media account first |

### Content Errors (CONTENT_*)

Errors related to content generation and processing.

| Code | Status | Description | User Action |
|------|--------|-------------|-------------|
| `CONTENT_GENERATION_FAILED` | 500 | Failed to generate content | Check API key and retry |
| `CONTENT_TOO_LONG` | 400 | Content exceeds platform limit | Reduce content length |
| `CONTENT_INVALID_FORMAT` | 400 | Content format is invalid | Check format requirements |
| `CONTENT_MODERATION_FAILED` | 400 | Content failed moderation checks | Review and modify content |

## iOS Error Handling Best Practices

### 1. Centralized Error Handler

```swift
class ErrorHandler {
    static func handle(_ error: APIError, on viewController: UIViewController) {
        switch error.code {
        case let code where code.hasPrefix("AUTH_"):
            handleAuthError(error, on: viewController)
        case let code where code.hasPrefix("VALIDATION_"):
            handleValidationError(error, on: viewController)
        case let code where code.hasPrefix("RATE_LIMIT_"):
            handleRateLimitError(error, on: viewController)
        default:
            showGenericError(error, on: viewController)
        }
    }
}
```

### 2. Retry Logic

```swift
func retryWithBackoff(_ attempt: Int = 0) async throws -> Response {
    do {
        return try await performRequest()
    } catch let error as APIError {
        if error.code.hasPrefix("RATE_LIMIT_") && attempt < 3 {
            let delay = pow(2.0, Double(attempt)) // Exponential backoff
            try await Task.sleep(nanoseconds: UInt64(delay * 1_000_000_000))
            return try await retryWithBackoff(attempt + 1)
        }
        throw error
    }
}
```

### 3. User-Friendly Messages

```swift
extension ErrorCode {
    var userMessage: String {
        switch self {
        case "AUTH_INVALID_CREDENTIALS":
            return "Invalid email or password. Please try again."
        case "RATE_LIMIT_EXCEEDED":
            return "Too many attempts. Please wait a moment."
        case "SERVER_INTERNAL_ERROR":
            return "Something went wrong. We're working on it!"
        default:
            return "An error occurred. Please try again."
        }
    }
}
```

### 4. Analytics Tracking

```swift
func logError(_ error: APIError) {
    Analytics.logEvent("api_error", parameters: [
        "code": error.code,
        "message": error.message,
        "endpoint": currentEndpoint,
        "timestamp": error.timestamp
    ])
}
```

## Testing Error Scenarios

### Using cURL

```bash
# Test invalid credentials
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"wrong@test.com","password":"wrong"}'

# Expected response:
# {
#   "error": {
#     "code": "AUTH_INVALID_CREDENTIALS",
#     "message": "Invalid email or password",
#     "details": {},
#     "timestamp": "2025-11-04T10:30:00Z"
#   }
# }
```

### Using iOS Tests

```swift
func testInvalidCredentialsError() async throws {
    let error = try await APIClient.login(email: "wrong@test.com", password: "wrong")
    XCTAssertEqual(error.code, "AUTH_INVALID_CREDENTIALS")
    XCTAssertEqual(error.statusCode, 401)
}

func testValidationError() async throws {
    let error = try await APIClient.register(email: "invalid", password: "123")
    XCTAssertEqual(error.code, "VALIDATION_INVALID_EMAIL")
    XCTAssertNotNil(error.details["validation_errors"])
}
```

## Migration Guide

If you're migrating from the old error format, follow these steps:

### Old Format
```json
{
  "detail": "Invalid credentials"
}
```

### New Format
```json
{
  "error": {
    "code": "AUTH_INVALID_CREDENTIALS",
    "message": "Invalid email or password",
    "details": {},
    "timestamp": "2025-11-04T10:30:00Z"
  }
}
```

### iOS Migration Code
```swift
// Old parsing
if let detail = json["detail"] as? String {
    showError(detail)
}

// New parsing
if let error = json["error"] as? [String: Any],
   let code = error["code"] as? String,
   let message = error["message"] as? String {
    handleError(code: code, message: message)
}
```

## Support

For questions or issues with error handling:
- Check the API documentation at `/docs`
- Review error logs in your iOS app
- Contact support with error code and timestamp
- Check server logs if you have access

## Changelog

### Version 2.11.0 (2025-11-04)
- Initial standardized error format implementation
- Added comprehensive error code categories
- Implemented global exception handlers
- Added error code documentation
- iOS integration support added
