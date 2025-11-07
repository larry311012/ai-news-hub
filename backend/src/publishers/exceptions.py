"""
Custom exceptions for social media publishing
"""


class PublisherException(Exception):
    """Base exception for all publisher errors"""

    pass


class AuthenticationException(PublisherException):
    """Token is invalid, expired, or has been revoked"""

    pass


class RateLimitException(PublisherException):
    """Rate limit exceeded"""

    def __init__(self, message, retry_after=None):
        super().__init__(message)
        self.retry_after = retry_after


class PublishingException(PublisherException):
    """Generic publishing error"""

    pass


class ContentRejectedError(PublisherException):
    """Content rejected by platform (policy violation)"""

    pass


class PlatformAPIError(PublisherException):
    """Platform API returned an error"""

    pass
