"""Browser management service for Playwright MCP server."""

import logging
from pathlib import Path
from typing import Any

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)
from playwright.async_api import TimeoutError as PlaywrightTimeout
from playwright_stealth import Stealth

from ..config import config

logger = logging.getLogger(__name__)


class BrowserError(Exception):
    """Base exception for browser-related errors."""

    pass


class DeviceNotFoundError(BrowserError):
    """Raised when a requested device profile is not found."""

    pass


class BrowserService:
    """Manages browser lifecycle and page operations."""

    def __init__(self):
        self.playwright: Playwright | None = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self.console_logs: list[str] = []
        self.screenshots: dict[str, bytes] = {}
        self.videos: dict[str, Path] = {}  # Store video paths by session
        self.current_device: str | None = None
        self.is_mobile: bool = False
        self.is_recording: bool = False
        self._screenshots_dir = Path(config.screenshots_directory)
        if not self._screenshots_dir.is_absolute():
            self._screenshots_dir = (
                Path(__file__).parent.parent.parent / self._screenshots_dir
            )
        self._videos_dir = Path(config.video_directory)
        if not self._videos_dir.is_absolute():
            self._videos_dir = Path(__file__).parent.parent.parent / self._videos_dir

    async def ensure_browser(
        self, device_name: str | None = None, record_video: bool = False
    ) -> Page:
        """Ensure browser is initialized and return the current page."""
        # Check if we need to recreate context for device change
        if device_name and device_name != self.current_device:
            logger.info(
                f"Device change requested from {self.current_device} to {device_name}, recreating context..."
            )
            if self.context:
                await self.context.close()
                self.context = None
                self.page = None

        # Check if we need to start/stop recording
        recording_state_changed = record_video != self.is_recording

        # If we're stopping recording (was recording, now not), we need to recreate context
        if self.is_recording and not record_video:
            logger.info(
                "Stopping recording - context will be recreated. Use playwright_save_video first to save the recording."
            )
            # Don't return here, let it recreate the context below

        # If recording was requested but we're already recording, continue with same context
        elif record_video and self.is_recording and self.browser and self.context:
            logger.info("Continuing with existing recording session")
            try:
                # Check if context and page are still valid
                if self.page and not self.page.is_closed():
                    return self.page
            except Exception as e:
                logger.warning(
                    f"Browser context invalid during recording, this will stop recording: {e}"
                )
                # If we lose the context during recording, we need to save the video first
                if self.context:
                    await self.context.close()
                self.context = None
                self.page = None

        # Check if browser exists and is connected (and recording state hasn't changed)
        elif self.browser and self.context and not recording_state_changed:
            try:
                # Check if context and page are still valid
                if self.page and not self.page.is_closed():
                    return self.page
            except Exception as e:
                logger.warning(f"Browser context invalid, recreating: {e}")
                if self.context:
                    await self.context.close()
                self.context = None
                self.page = None

        # Create new browser instance if needed
        if not self.playwright:
            self.playwright = await async_playwright().start()

        if not self.browser:
            logger.info("Launching new browser...")
            self.browser = await self.playwright.chromium.launch(
                headless=config.browser_headless, args=config.browser_args
            )

        # Prepare context options
        context_options: dict[str, Any] = {
            "viewport": {
                "width": config.browser_viewport_width,
                "height": config.browser_viewport_height,
            },
            "locale": config.context_locale,
            "timezone_id": config.context_timezone,
            "permissions": config.context_permissions,
            "color_scheme": config.context_color_scheme,
            "accept_downloads": config.context_accept_downloads,
        }

        # Apply device emulation if specified
        if device_name:
            if device_name not in self.playwright.devices:
                raise DeviceNotFoundError(
                    f"Device '{device_name}' not found. "
                    f"Available devices include: iPhone 13, iPhone 14, Pixel 5, iPad, etc."
                )

            device_settings = self.playwright.devices[device_name].copy()
            logger.info(f"Applying {device_name} device emulation with full context")

            # Remove default_browser_type as it's not a valid context option
            device_settings.pop("default_browser_type", None)

            # Merge device settings with context options
            context_options.update(device_settings)

            self.current_device = device_name
            self.is_mobile = device_settings.get("is_mobile", False)
        else:
            self.current_device = None
            self.is_mobile = False

        # Add video recording if requested
        if record_video:
            self._videos_dir.mkdir(exist_ok=True, parents=True)
            context_options["record_video_dir"] = str(self._videos_dir)
            context_options["record_video_size"] = {
                "width": config.video_size_width,
                "height": config.video_size_height,
            }
            self.is_recording = True
            logger.info(f"Video recording enabled, saving to: {self._videos_dir}")

        # Create new context
        logger.info("Creating new browser context...")
        self.context = await self.browser.new_context(**context_options)

        # Create new page
        self.page = await self.context.new_page()

        # Apply stealth mode if enabled
        if config.stealth_enabled:
            stealth = Stealth()
            await stealth.apply_stealth_async(self.page)
            logger.info("Stealth mode applied to browser page")

        # Set up console handler
        async def handle_console(msg):
            log_entry = f"[{msg.type}] {msg.text}"
            self.console_logs.append(log_entry)
            logger.info(f"Browser console: {log_entry}")

        self.page.on("console", handle_console)
        logger.info("Browser instance started successfully")
        return self.page

    async def check_page_loaded(self, page: Page, max_wait: int | None = None) -> bool:
        """Check if page has loaded successfully within timeout period."""
        if max_wait is None:
            max_wait = config.timeout_page_load_check
        try:
            await page.wait_for_selector("body *", timeout=max_wait)
            return True
        except PlaywrightTimeout:
            return False
        except Exception as e:
            logger.error(f"Error checking page load: {e}")
            return False

    async def cleanup(self) -> None:
        """Clean up browser resources."""
        try:
            if self.page and not self.page.is_closed():
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            logger.info("Browser cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def get_screenshots_dir(self) -> Path:
        """Get the screenshots directory path."""
        return self._screenshots_dir

    def get_videos_dir(self) -> Path:
        """Get the videos directory path."""
        return self._videos_dir

    async def save_video(self, session_name: str) -> Path | None:
        """Save the recorded video and return its path."""
        if not self.is_recording or not self.page:
            return None

        try:
            # Close the context to save the video
            if self.context:
                await self.context.close()
                self.context = None
                self.page = None

                # Videos are saved in the videos directory with auto-generated names
                # Find the most recent video file
                video_files = list(self._videos_dir.glob("*.webm"))
                if video_files:
                    # Get the most recent video
                    latest_video = max(video_files, key=lambda p: p.stat().st_mtime)

                    # Rename it to our desired name
                    from datetime import datetime

                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    safe_name = "".join(
                        c for c in session_name if c.isalnum() or c in "._-"
                    )
                    new_path = self._videos_dir / f"{safe_name}_{timestamp}.webm"

                    # Move the video to the new location
                    import shutil

                    shutil.move(str(latest_video), str(new_path))

                    self.videos[session_name] = new_path
                    self.is_recording = False
                    logger.info(f"Video saved: {new_path}")
                    return new_path
        except Exception as e:
            logger.error(f"Error saving video: {e}")

        return None
