"""
Performance Monitoring Middleware
Tracks request duration and identifies slow requests for the FastAPI application.
"""
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import structlog

logger = structlog.get_logger()


class PerformanceMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track request performance and log slow requests.

    Features:
    - Tracks duration of all requests
    - Logs regular requests as info with "request_completed" event
    - Logs slow requests (>1s) as warnings with "slow_request" event
    - Adds X-Response-Time header to all responses
    - Uses structured logging with path, method, duration, and status_code

    Usage:
        from middleware.performance import PerformanceMiddleware
        app.add_middleware(PerformanceMiddleware)
    """

    # Threshold for slow request warnings (in seconds)
    SLOW_REQUEST_THRESHOLD = 1.0

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process request and track performance metrics.

        Args:
            request: The incoming request
            call_next: The next middleware or route handler

        Returns:
            Response with X-Response-Time header added
        """
        # Record start time
        start_time = time.time()

        # Process the request
        response = await call_next(request)

        # Calculate duration in seconds
        duration = time.time() - start_time

        # Extract request details for logging
        path = request.url.path
        method = request.method
        status_code = response.status_code

        # Log based on duration threshold
        if duration > self.SLOW_REQUEST_THRESHOLD:
            # Slow request - log as warning
            logger.warning(
                "slow_request",
                path=path,
                method=method,
                duration=duration,
                status_code=status_code
            )
        else:
            # Normal request - log as info
            logger.info(
                "request_completed",
                path=path,
                method=method,
                duration=duration,
                status_code=status_code
            )

        # Add response time header (format: "0.123s")
        response.headers["X-Response-Time"] = f"{duration:.3f}s"

        return response
