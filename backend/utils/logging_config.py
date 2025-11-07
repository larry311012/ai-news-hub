"""
Structured Logging Configuration using structlog
Provides JSON-formatted logs for better parsing and analysis.
"""
import structlog
import logging
import sys
import os


def configure_logging(log_level: str = None):
    """
    Configure structured logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
                   If None, reads from LOG_LEVEL environment variable or defaults to INFO

    Features:
    - JSON-formatted output for easy parsing
    - Timestamp in ISO format
    - Logger name and level included
    - Exception info formatted properly
    - Works seamlessly with standard Python logging

    Usage:
        from utils.logging_config import configure_logging
        configure_logging()

        import structlog
        logger = structlog.get_logger()
        logger.info("user_login", user_id=123, email="user@example.com")
    """
    # Determine log level
    if log_level is None:
        log_level = os.getenv("LOG_LEVEL", "INFO")

    # Configure structlog processors
    structlog.configure(
        processors=[
            # Add log level filter
            structlog.stdlib.filter_by_level,
            # Add logger name
            structlog.stdlib.add_logger_name,
            # Add log level
            structlog.stdlib.add_log_level,
            # Process positional arguments
            structlog.stdlib.PositionalArgumentsFormatter(),
            # Add timestamp in ISO format
            structlog.processors.TimeStamper(fmt="iso"),
            # Render stack info if available
            structlog.processors.StackInfoRenderer(),
            # Format exception info
            structlog.processors.format_exc_info,
            # Decode unicode
            structlog.processors.UnicodeDecoder(),
            # Output as JSON for production, or pretty-print for development
            structlog.processors.JSONRenderer() if os.getenv("ENVIRONMENT", "development") == "production"
            else structlog.dev.ConsoleRenderer()
        ],
        # Use standard library's BoundLogger
        wrapper_class=structlog.stdlib.BoundLogger,
        # Use dict for context
        context_class=dict,
        # Use standard library's logger factory
        logger_factory=structlog.stdlib.LoggerFactory(),
        # Cache loggers for performance
        cache_logger_on_first_use=True,
    )

    # Configure standard logging to work with structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )

    # Create and test logger
    logger = structlog.get_logger()
    logger.debug(
        "logging_configured",
        log_level=log_level,
        environment=os.getenv("ENVIRONMENT", "development")
    )
