"""
Configuration Package

Centralized configuration management for the AI News Aggregator backend.

Usage:
    from config import settings

    db_url = settings.DATABASE_URL
    openai_key = settings.OPENAI_API_KEY
"""
from config.settings import settings, get_settings, validate_production_config

__all__ = ["settings", "get_settings", "validate_production_config"]
