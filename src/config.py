"""Configuration management for Playwright MCP server using environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field


class Config(BaseModel):
    """Server configuration"""

    # Browser settings
    browser_headless: bool = Field(description="Run browser in headless mode")
    browser_viewport_width: int = Field(description="Browser viewport width")
    browser_viewport_height: int = Field(description="Browser viewport height")
    browser_args: list[str] = Field(description="Browser launch arguments")

    # Context settings
    context_locale: str = Field(description="Browser locale")
    context_timezone: str = Field(description="Browser timezone")
    context_permissions: list[str] = Field(description="Browser permissions")
    context_color_scheme: str = Field(description="Color scheme (light/dark)")
    context_accept_downloads: bool = Field(description="Accept downloads")

    # Timeouts (in milliseconds)
    timeout_default: int = Field(description="Default timeout")
    timeout_navigation: int = Field(description="Navigation timeout")
    timeout_page_load_check: int = Field(description="Page load check timeout")
    timeout_network_idle: int = Field(description="Network idle timeout")

    # Directories
    screenshots_directory: str = Field(description="Screenshots directory")
    screenshots_timestamp_format: str = Field(description="Screenshot timestamp format")
    video_directory: str = Field(description="Video recordings directory")
    video_size_width: int = Field(description="Video width")
    video_size_height: int = Field(description="Video height")

    # Mobile settings
    mobile_default_device: str = Field(description="Default mobile device")

    # Logging
    logging_level: str = Field(description="Logging level")
    logging_format: str = Field(description="Logging format")

    # Stealth settings
    stealth_enabled: bool = Field(description="Enable stealth mode")

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables"""
        # Load .env file if it exists
        load_dotenv()

        # Parse browser args - use semicolon separator to handle args with commas
        browser_args = []
        browser_args_str = os.getenv("BROWSER_ARGS")
        if browser_args_str:
            browser_args = [
                arg.strip() for arg in browser_args_str.split(";") if arg.strip()
            ]

        # Parse permissions list
        permissions = []
        permissions_str = os.getenv("CONTEXT_PERMISSIONS")
        if permissions_str:
            permissions = [p.strip() for p in permissions_str.split(",") if p.strip()]

        # Helper function to expand paths
        def expand_path(path_str: str | None) -> str | None:
            """Expand ~ and environment variables in paths"""
            if path_str is None:
                return None
            return str(Path(path_str).expanduser())

        # Create config dict - Pydantic will validate required fields and types
        config_data = {
            # Browser settings
            "browser_headless": os.getenv("BROWSER_HEADLESS"),
            "browser_viewport_width": os.getenv("BROWSER_VIEWPORT_WIDTH"),
            "browser_viewport_height": os.getenv("BROWSER_VIEWPORT_HEIGHT"),
            "browser_args": browser_args,
            # Context settings
            "context_locale": os.getenv("CONTEXT_LOCALE"),
            "context_timezone": os.getenv("CONTEXT_TIMEZONE"),
            "context_permissions": permissions,
            "context_color_scheme": os.getenv("CONTEXT_COLOR_SCHEME"),
            "context_accept_downloads": os.getenv("CONTEXT_ACCEPT_DOWNLOADS"),
            # Timeouts
            "timeout_default": os.getenv("TIMEOUT_DEFAULT"),
            "timeout_navigation": os.getenv("TIMEOUT_NAVIGATION"),
            "timeout_page_load_check": os.getenv("TIMEOUT_PAGE_LOAD_CHECK"),
            "timeout_network_idle": os.getenv("TIMEOUT_NETWORK_IDLE"),
            # Directories
            "screenshots_directory": expand_path(os.getenv("SCREENSHOTS_DIRECTORY")),
            "screenshots_timestamp_format": os.getenv("SCREENSHOTS_TIMESTAMP_FORMAT"),
            "video_directory": expand_path(os.getenv("VIDEO_DIRECTORY")),
            "video_size_width": os.getenv("VIDEO_SIZE_WIDTH"),
            "video_size_height": os.getenv("VIDEO_SIZE_HEIGHT"),
            # Mobile settings
            "mobile_default_device": os.getenv("MOBILE_DEFAULT_DEVICE"),
            # Logging
            "logging_level": os.getenv("LOGGING_LEVEL"),
            "logging_format": os.getenv("LOGGING_FORMAT"),
            # Stealth
            "stealth_enabled": os.getenv("STEALTH_ENABLED"),
        }

        # Remove None values to let Pydantic raise validation errors for missing required fields
        config_data = {k: v for k, v in config_data.items() if v is not None}

        return cls(**config_data)


# Global configuration instance
config = Config.from_env()
