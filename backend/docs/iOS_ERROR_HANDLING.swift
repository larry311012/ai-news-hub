///
/// iOS Error Handling Reference (Task 1.7)
///
/// This file provides Swift code examples for handling standardized
/// error responses from the AI Post Generator API.
///

import Foundation

// MARK: - Error Response Models

/// Standard error response from API
struct APIErrorResponse: Codable {
    let error: ErrorDetail
}

/// Detailed error information
struct ErrorDetail: Codable {
    let code: String
    let message: String
    let details: [String: AnyCodable]?
    let timestamp: String
}

/// Type-erased wrapper for heterogeneous JSON
struct AnyCodable: Codable {
    let value: Any

    init(_ value: Any) {
        self.value = value
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()

        if let bool = try? container.decode(Bool.self) {
            value = bool
        } else if let int = try? container.decode(Int.self) {
            value = int
        } else if let double = try? container.decode(Double.self) {
            value = double
        } else if let string = try? container.decode(String.self) {
            value = string
        } else if let array = try? container.decode([AnyCodable].self) {
            value = array.map { $0.value }
        } else if let dictionary = try? container.decode([String: AnyCodable].self) {
            value = dictionary.mapValues { $0.value }
        } else {
            value = NSNull()
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()

        switch value {
        case let bool as Bool:
            try container.encode(bool)
        case let int as Int:
            try container.encode(int)
        case let double as Double:
            try container.encode(double)
        case let string as String:
            try container.encode(string)
        case let array as [Any]:
            try container.encode(array.map { AnyCodable($0) })
        case let dictionary as [String: Any]:
            try container.encode(dictionary.mapValues { AnyCodable($0) })
        default:
            try container.encodeNil()
        }
    }
}

// MARK: - Error Codes Enum

/// All possible error codes from the API
enum ErrorCode: String {
    // Authentication Errors
    case authInvalidCredentials = "AUTH_INVALID_CREDENTIALS"
    case authTokenExpired = "AUTH_TOKEN_EXPIRED"
    case authTokenInvalid = "AUTH_TOKEN_INVALID"
    case authTokenMissing = "AUTH_TOKEN_MISSING"
    case authSessionExpired = "AUTH_SESSION_EXPIRED"
    case authUserNotFound = "AUTH_USER_NOT_FOUND"
    case authUserInactive = "AUTH_USER_INACTIVE"
    case authUserSuspended = "AUTH_USER_SUSPENDED"
    case authEmailExists = "AUTH_EMAIL_EXISTS"
    case authWeakPassword = "AUTH_WEAK_PASSWORD"
    case authRefreshFailed = "AUTH_REFRESH_FAILED"
    case authDeviceNotRegistered = "AUTH_DEVICE_NOT_REGISTERED"
    case authOAuthFailed = "AUTH_OAUTH_FAILED"
    case authOAuthCancelled = "AUTH_OAUTH_CANCELLED"

    // Validation Errors
    case validationInvalidInput = "VALIDATION_INVALID_INPUT"
    case validationMissingField = "VALIDATION_MISSING_FIELD"
    case validationInvalidEmail = "VALIDATION_INVALID_EMAIL"
    case validationInvalidFormat = "VALIDATION_INVALID_FORMAT"
    case validationFieldTooLong = "VALIDATION_FIELD_TOO_LONG"
    case validationFieldTooShort = "VALIDATION_FIELD_TOO_SHORT"
    case validationInvalidDate = "VALIDATION_INVALID_DATE"
    case validationInvalidURL = "VALIDATION_INVALID_URL"

    // Rate Limiting Errors
    case rateLimitExceeded = "RATE_LIMIT_EXCEEDED"
    case rateLimitTooManyRequests = "RATE_LIMIT_TOO_MANY_REQUESTS"
    case rateLimitQuotaExceeded = "RATE_LIMIT_QUOTA_EXCEEDED"
    case rateLimitDeviceLimit = "RATE_LIMIT_DEVICE_LIMIT"
    case rateLimitAPILimit = "RATE_LIMIT_API_LIMIT"

    // Server Errors
    case serverInternalError = "SERVER_INTERNAL_ERROR"
    case serverDatabaseError = "SERVER_DATABASE_ERROR"
    case serverNetworkError = "SERVER_NETWORK_ERROR"
    case serverServiceUnavailable = "SERVER_SERVICE_UNAVAILABLE"
    case serverTimeout = "SERVER_TIMEOUT"
    case serverMaintenance = "SERVER_MAINTENANCE"

    // Resource Errors
    case resourceNotFound = "RESOURCE_NOT_FOUND"
    case resourceAlreadyExists = "RESOURCE_ALREADY_EXISTS"
    case resourceDeleted = "RESOURCE_DELETED"
    case resourceForbidden = "RESOURCE_FORBIDDEN"

    // API Key Errors
    case apiKeyMissing = "API_KEY_MISSING"
    case apiKeyInvalid = "API_KEY_INVALID"
    case apiKeyExpired = "API_KEY_EXPIRED"
    case apiKeyQuotaExceeded = "API_KEY_QUOTA_EXCEEDED"

    // Social Media Errors
    case socialConnectionFailed = "SOCIAL_CONNECTION_FAILED"
    case socialTokenExpired = "SOCIAL_TOKEN_EXPIRED"
    case socialPublishFailed = "SOCIAL_PUBLISH_FAILED"
    case socialPlatformError = "SOCIAL_PLATFORM_ERROR"
    case socialNotConnected = "SOCIAL_NOT_CONNECTED"

    // Content Errors
    case contentGenerationFailed = "CONTENT_GENERATION_FAILED"
    case contentTooLong = "CONTENT_TOO_LONG"
    case contentInvalidFormat = "CONTENT_INVALID_FORMAT"
    case contentModerationFailed = "CONTENT_MODERATION_FAILED"

    // Unknown
    case unknown = "UNKNOWN"

    /// Initialize from string, defaults to unknown if not recognized
    init(rawValue: String) {
        self = ErrorCode(rawValue: rawValue) ?? .unknown
    }

    /// User-friendly error message
    var userMessage: String {
        switch self {
        case .authInvalidCredentials:
            return "Invalid email or password. Please try again."
        case .authTokenExpired:
            return "Your session has expired. Please log in again."
        case .authEmailExists:
            return "This email is already registered."
        case .validationInvalidEmail:
            return "Please enter a valid email address."
        case .validationInvalidInput:
            return "Please check your input and try again."
        case .rateLimitExceeded:
            return "Too many attempts. Please wait a moment."
        case .serverInternalError, .serverDatabaseError:
            return "Something went wrong. We're working on it!"
        case .serverServiceUnavailable, .serverMaintenance:
            return "Service temporarily unavailable. Please try again later."
        case .resourceNotFound:
            return "The requested item could not be found."
        case .socialTokenExpired:
            return "Please reconnect your social media account."
        case .apiKeyMissing:
            return "Please add your API key in settings."
        default:
            return "An error occurred. Please try again."
        }
    }

    /// Whether error is recoverable by user action
    var isRecoverable: Bool {
        switch self {
        case .authInvalidCredentials, .validationInvalidInput, .validationInvalidEmail,
             .authEmailExists, .apiKeyMissing:
            return true
        case .serverInternalError, .serverDatabaseError:
            return false
        default:
            return true
        }
    }
}

// MARK: - Custom Error Type

/// Custom error type for API errors
struct APIError: Error, LocalizedError {
    let code: ErrorCode
    let message: String
    let details: [String: Any]
    let timestamp: String
    let statusCode: Int

    var errorDescription: String? {
        return code.userMessage
    }

    var failureReason: String? {
        return message
    }

    /// Create from API error response
    init(from response: APIErrorResponse, statusCode: Int) {
        self.code = ErrorCode(rawValue: response.error.code)
        self.message = response.error.message
        self.details = response.error.details?.mapValues { $0.value } ?? [:]
        self.timestamp = response.error.timestamp
        self.statusCode = statusCode
    }
}

// MARK: - Error Handler

/// Centralized error handler for API errors
class ErrorHandler {
    static let shared = ErrorHandler()

    /// Parse error from HTTP response
    func parseError(data: Data, statusCode: Int) -> APIError? {
        guard let errorResponse = try? JSONDecoder().decode(APIErrorResponse.self, from: data) else {
            return nil
        }
        return APIError(from: errorResponse, statusCode: statusCode)
    }

    /// Handle API error with appropriate user action
    func handle(_ error: APIError, on viewController: UIViewController) {
        switch error.code {
        case .authTokenExpired, .authSessionExpired:
            handleTokenExpired(on: viewController)

        case .authInvalidCredentials:
            showAlert(title: "Login Failed", message: error.code.userMessage, on: viewController)

        case .rateLimitExceeded, .rateLimitTooManyRequests:
            handleRateLimit(error: error, on: viewController)

        case .validationInvalidInput:
            handleValidationError(error: error, on: viewController)

        case .socialTokenExpired:
            handleSocialTokenExpired(on: viewController)

        case .serverInternalError, .serverDatabaseError, .serverServiceUnavailable:
            showAlert(title: "Server Error", message: error.code.userMessage, on: viewController)

        default:
            showAlert(title: "Error", message: error.code.userMessage, on: viewController)
        }

        // Log error for analytics
        logError(error)
    }

    private func handleTokenExpired(on viewController: UIViewController) {
        // Try to refresh token
        Task {
            do {
                try await TokenManager.shared.refreshToken()
                // Retry the original request
            } catch {
                // Refresh failed, redirect to login
                redirectToLogin(from: viewController)
            }
        }
    }

    private func handleRateLimit(error: APIError, on viewController: UIViewController) {
        let retryAfter = error.details["retry_after"] as? Int ?? 60
        showAlert(
            title: "Too Many Requests",
            message: "Please try again in \(retryAfter) seconds.",
            on: viewController
        )
    }

    private func handleValidationError(error: APIError, on viewController: UIViewController) {
        // Parse validation errors if available
        if let validationErrors = error.details["validation_errors"] as? [[String: Any]] {
            let messages = validationErrors.compactMap { $0["message"] as? String }
            let message = messages.joined(separator: "\n")
            showAlert(title: "Validation Error", message: message, on: viewController)
        } else {
            showAlert(title: "Invalid Input", message: error.code.userMessage, on: viewController)
        }
    }

    private func handleSocialTokenExpired(on viewController: UIViewController) {
        showAlert(
            title: "Reconnect Account",
            message: "Your social media connection has expired. Please reconnect your account.",
            on: viewController,
            actions: [
                UIAlertAction(title: "Reconnect", style: .default) { _ in
                    // Navigate to social media settings
                },
                UIAlertAction(title: "Cancel", style: .cancel)
            ]
        )
    }

    private func showAlert(
        title: String,
        message: String,
        on viewController: UIViewController,
        actions: [UIAlertAction] = [UIAlertAction(title: "OK", style: .default)]
    ) {
        let alert = UIAlertController(title: title, message: message, preferredStyle: .alert)
        actions.forEach { alert.addAction($0) }
        viewController.present(alert, animated: true)
    }

    private func redirectToLogin(from viewController: UIViewController) {
        // Clear stored credentials
        TokenManager.shared.clearTokens()

        // Navigate to login screen
        if let window = viewController.view.window,
           let loginVC = UIStoryboard(name: "Main", bundle: nil).instantiateViewController(withIdentifier: "LoginViewController") as? UIViewController {
            window.rootViewController = loginVC
        }
    }

    private func logError(_ error: APIError) {
        // Log to analytics service
        Analytics.logEvent("api_error", parameters: [
            "code": error.code.rawValue,
            "message": error.message,
            "status_code": error.statusCode,
            "timestamp": error.timestamp
        ])
    }
}

// MARK: - API Client Extension

extension APIClient {
    /// Perform request with automatic error handling
    func performRequest<T: Decodable>(
        _ endpoint: String,
        method: HTTPMethod = .get,
        body: Encodable? = nil
    ) async throws -> T {
        var request = URLRequest(url: URL(string: baseURL + endpoint)!)
        request.httpMethod = method.rawValue
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        // Add auth token if available
        if let token = TokenManager.shared.accessToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        // Add body if provided
        if let body = body {
            request.httpBody = try JSONEncoder().encode(body)
        }

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw URLError(.badServerResponse)
        }

        // Check for error status codes
        if (400...599).contains(httpResponse.statusCode) {
            if let apiError = ErrorHandler.shared.parseError(data: data, statusCode: httpResponse.statusCode) {
                throw apiError
            } else {
                throw URLError(.badServerResponse)
            }
        }

        // Decode successful response
        return try JSONDecoder().decode(T.self, from: data)
    }
}

// MARK: - Retry Logic with Exponential Backoff

extension APIClient {
    /// Retry request with exponential backoff for rate limit errors
    func performRequestWithRetry<T: Decodable>(
        _ endpoint: String,
        method: HTTPMethod = .get,
        body: Encodable? = nil,
        maxRetries: Int = 3
    ) async throws -> T {
        var attempt = 0

        while attempt < maxRetries {
            do {
                return try await performRequest(endpoint, method: method, body: body)
            } catch let error as APIError {
                // Only retry for rate limit errors
                if error.code.rawValue.hasPrefix("RATE_LIMIT_") && attempt < maxRetries - 1 {
                    let delay = pow(2.0, Double(attempt)) // Exponential backoff: 1s, 2s, 4s
                    try await Task.sleep(nanoseconds: UInt64(delay * 1_000_000_000))
                    attempt += 1
                } else {
                    throw error
                }
            }
        }

        throw URLError(.timedOut)
    }
}

// MARK: - Usage Examples

/*
 // Example 1: Login with error handling
 Task {
     do {
         let response: LoginResponse = try await apiClient.performRequest(
             "/api/auth/login",
             method: .post,
             body: LoginRequest(email: "user@example.com", password: "password")
         )
         // Handle success
     } catch let error as APIError {
         ErrorHandler.shared.handle(error, on: self)
     } catch {
         print("Network error: \(error)")
     }
 }

 // Example 2: Request with retry logic
 Task {
     do {
         let posts: [Post] = try await apiClient.performRequestWithRetry("/api/posts")
         // Handle success
     } catch let error as APIError {
         ErrorHandler.shared.handle(error, on: self)
     }
 }

 // Example 3: Manual error handling
 Task {
     do {
         let response: Response = try await apiClient.performRequest("/api/endpoint")
     } catch let error as APIError {
         switch error.code {
         case .authTokenExpired:
             // Handle token refresh
             try await refreshToken()
             // Retry request
         case .validationInvalidInput:
             // Show validation errors
             if let errors = error.details["validation_errors"] as? [[String: Any]] {
                 showValidationErrors(errors)
             }
         case .rateLimitExceeded:
             // Wait and retry
             let retryAfter = error.details["retry_after"] as? Int ?? 60
             try await Task.sleep(nanoseconds: UInt64(retryAfter * 1_000_000_000))
             // Retry request
         default:
             // Show generic error
             showError(error.code.userMessage)
         }
     }
 }
 */

// MARK: - Token Manager

class TokenManager {
    static let shared = TokenManager()

    var accessToken: String? {
        get { KeychainManager.shared.get(key: "access_token") }
        set { KeychainManager.shared.save(key: "access_token", value: newValue) }
    }

    var refreshToken: String? {
        get { KeychainManager.shared.get(key: "refresh_token") }
        set { KeychainManager.shared.save(key: "refresh_token", value: newValue) }
    }

    func refreshToken() async throws {
        guard let refreshToken = refreshToken else {
            throw APIError(
                from: APIErrorResponse(
                    error: ErrorDetail(
                        code: "AUTH_TOKEN_MISSING",
                        message: "No refresh token available",
                        details: nil,
                        timestamp: ISO8601DateFormatter().string(from: Date())
                    )
                ),
                statusCode: 401
            )
        }

        // Call refresh endpoint
        let response: RefreshTokenResponse = try await APIClient.shared.performRequest(
            "/api/v1/auth/refresh",
            method: .post,
            body: RefreshTokenRequest(refresh_token: refreshToken)
        )

        // Save new access token
        accessToken = response.access_token
    }

    func clearTokens() {
        accessToken = nil
        refreshToken = nil
    }
}
