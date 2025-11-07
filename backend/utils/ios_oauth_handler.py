"""
iOS OAuth Redirect URL Handler (Task 1.6 - Enhanced)

Handles custom URL scheme redirects for iOS app OAuth flows.
Supports: ainewshub://oauth-callback for Twitter, LinkedIn, Instagram, Threads

IMPROVEMENTS:
- Auto-detection of iOS clients via headers
- Support for all OAuth platforms
- Complete callback URL building
- Error handling for OAuth failures
"""
from typing import Optional, Dict, Any
from urllib.parse import urlencode, urlparse, parse_qs
import logging

logger = logging.getLogger(__name__)


class iOSOAuthHandler:
    """Handler for iOS-specific OAuth redirects"""

    # iOS custom URL scheme
    IOS_SCHEME = "ainewshub"
    IOS_CALLBACK_PATH = "oauth-callback"

    # Default web callback (fallback)
    WEB_CALLBACK_BASE = "http://localhost:8000/api/social-media"

    # Supported platforms
    SUPPORTED_PLATFORMS = ["twitter", "linkedin", "instagram", "threads"]

    @staticmethod
    def get_redirect_url(
        platform: str,
        is_mobile: bool = False,
        web_callback_url: Optional[str] = None
    ) -> str:
        """
        Get appropriate OAuth redirect URL based on client type.

        Args:
            platform: Social media platform (twitter, linkedin, instagram, threads)
            is_mobile: Whether request is from iOS mobile app
            web_callback_url: Optional custom web callback URL

        Returns:
            Redirect URL (iOS custom scheme or web URL)

        Example:
            # For iOS app
            ainewshub://oauth-callback?platform=twitter

            # For web app
            http://localhost:8000/api/social-media/twitter/callback
        """
        if platform not in iOSOAuthHandler.SUPPORTED_PLATFORMS:
            logger.warning(f"Unsupported platform for iOS OAuth: {platform}")

        if is_mobile:
            # iOS custom URL scheme with platform identifier
            return f"{iOSOAuthHandler.IOS_SCHEME}://{iOSOAuthHandler.IOS_CALLBACK_PATH}?platform={platform}"
        else:
            # Web callback URL
            if web_callback_url:
                return web_callback_url

            # Default callback URLs per platform
            callback_paths = {
                "twitter": "twitter/callback",
                "linkedin": "oauth-setup/linkedin/callback",
                "instagram": "instagram/callback",
                "threads": "threads/callback"
            }

            path = callback_paths.get(platform, f"{platform}/callback")

            # LinkedIn uses different prefix
            if platform == "linkedin":
                return f"http://localhost:8000/api/{path}"
            else:
                return f"{iOSOAuthHandler.WEB_CALLBACK_BASE}/{path}"

    @staticmethod
    def build_ios_redirect(
        platform: str,
        success: bool = True,
        access_token: Optional[str] = None,
        error: Optional[str] = None,
        error_description: Optional[str] = None,
        additional_params: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Build iOS custom URL scheme redirect with OAuth results.

        Args:
            platform: Social media platform
            success: Whether OAuth was successful
            access_token: Access token if successful
            error: Error code if failed
            error_description: Human-readable error description
            additional_params: Additional query parameters

        Returns:
            Complete iOS redirect URL

        Example:
            Success:
            ainewshub://oauth-callback?platform=twitter&success=true&token=abc123

            Error:
            ainewshub://oauth-callback?platform=twitter&success=false&error=access_denied
        """
        params = {
            "platform": platform,
            "success": "true" if success else "false"
        }

        if success and access_token:
            params["token"] = access_token
        elif not success:
            params["error"] = error or "unknown_error"
            if error_description:
                params["error_description"] = error_description

        # Add any additional parameters
        if additional_params:
            params.update(additional_params)

        query_string = urlencode(params)
        return f"{iOSOAuthHandler.IOS_SCHEME}://{iOSOAuthHandler.IOS_CALLBACK_PATH}?{query_string}"

    @staticmethod
    def detect_ios_client(
        user_agent: Optional[str] = None,
        app_version: Optional[str] = None,
        accept_header: Optional[str] = None
    ) -> bool:
        """
        Detect if request is from iOS mobile app.

        Detection strategy:
        1. Check X-App-Version header (most reliable)
        2. Check User-Agent for iOS app identifiers
        3. Check Accept header for mobile indicators

        Args:
            user_agent: User-Agent header value
            app_version: X-App-Version header value
            accept_header: Accept header value

        Returns:
            True if iOS mobile app, False otherwise
        """
        # 1. App version header is most reliable indicator
        if app_version:
            logger.debug(f"iOS client detected via X-App-Version: {app_version}")
            return True

        # 2. Check User-Agent
        if user_agent:
            user_agent_lower = user_agent.lower()
            ios_indicators = [
                "ainewshub/ios",
                "ainewshub-ios",
                "cfnetwork",  # iOS networking framework
                "darwin",     # macOS/iOS kernel
            ]

            for indicator in ios_indicators:
                if indicator in user_agent_lower:
                    logger.debug(f"iOS client detected via User-Agent: {indicator}")
                    return True

        # 3. Check Accept header for mobile patterns
        if accept_header:
            accept_lower = accept_header.lower()
            if "application/vnd.api+json" in accept_lower:
                # Custom Accept header that iOS app might send
                logger.debug("Possible iOS client detected via Accept header")
                # Don't return True here, just a hint

        return False

    @staticmethod
    def parse_ios_callback_url(url: str) -> Dict[str, Any]:
        """
        Parse iOS custom URL scheme callback.

        Args:
            url: iOS callback URL (ainewshub://oauth-callback?...)

        Returns:
            Dictionary with parsed parameters

        Example:
            Input: ainewshub://oauth-callback?platform=twitter&success=true&token=abc123
            Output: {
                "platform": "twitter",
                "success": True,
                "token": "abc123"
            }
        """
        parsed = urlparse(url)
        params = parse_qs(parsed.query)

        # Convert query params to single values (not lists)
        result = {
            key: values[0] if values else None
            for key, values in params.items()
        }

        # Convert success to boolean
        if "success" in result:
            result["success"] = result["success"].lower() == "true"

        return result

    @staticmethod
    def get_oauth_config_for_platform(
        platform: str,
        is_mobile: bool = False
    ) -> Dict[str, str]:
        """
        Get OAuth configuration with mobile-specific settings.

        Args:
            platform: Social media platform
            is_mobile: Whether to use mobile redirect URLs

        Returns:
            OAuth configuration dictionary

        Example:
            {
                "redirect_uri": "ainewshub://oauth-callback?platform=twitter",
                "response_type": "code",
                "scope": "tweet.read tweet.write users.read"
            }
        """
        base_config = {
            "twitter": {
                "oauth_version": "1.0a",
                "scope": "tweet.read tweet.write users.read offline.access",
            },
            "linkedin": {
                "oauth_version": "2.0",
                "scope": "openid profile email w_member_social",
                "response_type": "code",
            },
            "instagram": {
                "oauth_version": "2.0",
                "scope": "instagram_basic instagram_content_publish",
                "response_type": "code",
            },
            "threads": {
                "oauth_version": "2.0",
                "scope": "threads_basic threads_content_publish",
                "response_type": "code",
            }
        }

        config = base_config.get(platform, {}).copy()
        config["redirect_uri"] = iOSOAuthHandler.get_redirect_url(platform, is_mobile)

        return config


# Helper functions for easy integration

def get_oauth_redirect_uri(
    platform: str,
    user_agent: Optional[str] = None,
    app_version: Optional[str] = None,
    accept_header: Optional[str] = None
) -> str:
    """
    Get appropriate OAuth redirect URI based on client type.

    Convenience function that auto-detects iOS app and returns correct redirect.

    Args:
        platform: Social media platform
        user_agent: User-Agent header
        app_version: X-App-Version header
        accept_header: Accept header

    Returns:
        Redirect URI for OAuth flow
    """
    is_mobile = iOSOAuthHandler.detect_ios_client(user_agent, app_version, accept_header)
    return iOSOAuthHandler.get_redirect_url(platform, is_mobile)


def build_oauth_success_redirect(
    platform: str,
    access_token: str,
    user_agent: Optional[str] = None,
    app_version: Optional[str] = None,
    **kwargs
) -> str:
    """
    Build OAuth success redirect for web or iOS.

    Args:
        platform: Social media platform
        access_token: OAuth access token
        user_agent: User-Agent header
        app_version: X-App-Version header
        **kwargs: Additional parameters

    Returns:
        Redirect URL with token
    """
    is_mobile = iOSOAuthHandler.detect_ios_client(user_agent, app_version)

    if is_mobile:
        return iOSOAuthHandler.build_ios_redirect(
            platform=platform,
            success=True,
            access_token=access_token,
            additional_params=kwargs
        )
    else:
        # Web redirect (to frontend page)
        from urllib.parse import urlencode
        params = {
            "success": "true",
            "platform": platform,
            **kwargs
        }
        return f"/social-media-connected.html?{urlencode(params)}"


def build_oauth_error_redirect(
    platform: str,
    error: str,
    error_description: Optional[str] = None,
    user_agent: Optional[str] = None,
    app_version: Optional[str] = None
) -> str:
    """
    Build OAuth error redirect for web or iOS.

    Args:
        platform: Social media platform
        error: Error code
        error_description: Human-readable error
        user_agent: User-Agent header
        app_version: X-App-Version header

    Returns:
        Redirect URL with error
    """
    is_mobile = iOSOAuthHandler.detect_ios_client(user_agent, app_version)

    if is_mobile:
        return iOSOAuthHandler.build_ios_redirect(
            platform=platform,
            success=False,
            error=error,
            error_description=error_description
        )
    else:
        # Web redirect (to error page)
        from urllib.parse import urlencode
        params = {
            "success": "false",
            "error": error,
            "platform": platform
        }
        if error_description:
            params["error_description"] = error_description
        return f"/oauth-error.html?{urlencode(params)}"


# iOS App Integration Guide (for documentation)
IOS_INTEGRATION_EXAMPLE = """
# iOS App Integration Guide

## 1. Register Custom URL Scheme in Info.plist

```xml
<key>CFBundleURLTypes</key>
<array>
    <dict>
        <key>CFBundleURLSchemes</key>
        <array>
            <string>ainewshub</string>
        </array>
        <key>CFBundleURLName</key>
        <string>com.ainewshub.oauth</string>
    </dict>
</array>
```

## 2. Handle OAuth Callback in AppDelegate

```swift
func application(_ app: UIApplication,
                 open url: URL,
                 options: [UIApplication.OpenURLOptionsKey : Any] = [:]) -> Bool {

    // Check if it's our OAuth callback
    guard url.scheme == "ainewshub",
          url.host == "oauth-callback" else {
        return false
    }

    // Parse query parameters
    let components = URLComponents(url: url, resolvingAgainstBaseURL: false)
    let queryItems = components?.queryItems ?? []

    let params = Dictionary(uniqueKeysWithValues:
        queryItems.map { ($0.name, $0.value ?? "") }
    )

    // Extract OAuth result
    let platform = params["platform"] ?? ""
    let success = params["success"] == "true"
    let token = params["token"]
    let error = params["error"]

    if success, let token = token {
        // Store token securely
        KeychainManager.shared.saveOAuthToken(token, for: platform)

        // Notify app
        NotificationCenter.default.post(
            name: .oauthSuccess,
            object: nil,
            userInfo: ["platform": platform, "token": token]
        )
    } else {
        // Handle error
        NotificationCenter.default.post(
            name: .oauthError,
            object: nil,
            userInfo: ["platform": platform, "error": error ?? "unknown"]
        )
    }

    return true
}
```

## 3. Initiate OAuth Flow

```swift
// Set custom headers to identify iOS app
var request = URLRequest(url: URL(string: "https://api.ainewshub.com/api/social-media/twitter/connect")!)
request.setValue("AiNewsHub/iOS 1.0", forHTTPHeaderField: "User-Agent")
request.setValue("1.0.0", forHTTPHeaderField: "X-App-Version")
request.setValue("Bearer \\(accessToken)", forHTTPHeaderField: "Authorization")

// Make request
let (data, response) = try await URLSession.shared.data(for: request)

// Parse authorization URL
let json = try JSONDecoder().decode(OAuthResponse.self, from: data)

// Open in Safari View Controller (recommended) or Safari
let safariVC = SFSafariViewController(url: URL(string: json.authorization_url)!)
present(safariVC, animated: true)

// App will receive callback via application(_:open:options:)
```

## 4. Complete OAuth Flow

```swift
class OAuthManager {
    static let shared = OAuthManager()

    func connectTwitter() async throws {
        // Step 1: Get authorization URL
        let authURL = try await getAuthorizationURL(platform: "twitter")

        // Step 2: Open Safari for user authentication
        await openSafari(url: authURL)

        // Step 3: Wait for callback (handled by AppDelegate)
        // App will resume with OAuth token
    }

    private func getAuthorizationURL(platform: String) async throws -> URL {
        var request = URLRequest(
            url: URL(string: "https://api.ainewshub.com/api/social-media/\\(platform)/connect")!
        )
        request.setValue("AiNewsHub/iOS 1.0", forHTTPHeaderField: "User-Agent")
        request.setValue(Bundle.main.appVersion, forHTTPHeaderField: "X-App-Version")
        request.setValue("Bearer \\(UserSession.shared.accessToken)", forHTTPHeaderField: "Authorization")

        let (data, _) = try await URLSession.shared.data(for: request)
        let response = try JSONDecoder().decode(OAuthConnectResponse.self, from: data)

        return URL(string: response.authorization_url)!
    }
}
```

## 5. Test OAuth Flow

Use iOS Simulator or physical device:

1. Tap "Connect Twitter" button
2. App opens Safari with Twitter login
3. User authenticates on Twitter
4. Twitter redirects to: ainewshub://oauth-callback?platform=twitter&success=true&token=...
5. iOS opens your app with the callback URL
6. AppDelegate parses token and notifies app
7. App stores token and updates UI
"""
