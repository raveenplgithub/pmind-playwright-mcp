"""FastMCP server for browser automation using Playwright."""

import asyncio
import atexit
import logging
from datetime import datetime
from typing import Annotated, Any

from fastmcp import FastMCP
from playwright.async_api import TimeoutError as PlaywrightTimeout
from pydantic import Field

from .config import config
from .services.browser import BrowserError, BrowserService

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.logging_level), format=config.logging_format
)
logger = logging.getLogger(__name__)

# Create FastMCP app instance
app = FastMCP("pmind-playwright-mcp")


def create_server() -> FastMCP:
    """Create and configure the MCP server"""
    logger.info("Initializing PMIND Playwright MCP server...")

    # Initialize browser service
    browser_service = BrowserService()

    # Store in server state for tools to access
    app.state = {"browser_service": browser_service}

    # Register cleanup handler
    def cleanup():
        """Clean up browser resources on exit"""
        if browser_service:
            logger.info("Running browser cleanup...")
            # Create a new event loop if needed for cleanup
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                loop.run_until_complete(browser_service.cleanup())
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")

    atexit.register(cleanup)

    logger.info("Browser service initialized and stored in server state")
    return app


@app.tool()
async def playwright_navigate(
    url: Annotated[str, Field(description="URL to navigate to")],
    timeout: Annotated[
        int | None,
        Field(default=None, description="Navigation timeout in milliseconds"),
    ] = None,
    mobile: Annotated[
        bool,
        Field(
            default=False,
            description="Navigate in mobile mode (uses iPhone 13 by default)",
        ),
    ] = False,
    device: Annotated[
        str | None,
        Field(
            default=None,
            description="Specific device to emulate (e.g., 'iPhone 13', 'Pixel 5')",
        ),
    ] = None,
    record_video: Annotated[
        bool, Field(default=False, description="Record video of the browser session")
    ] = False,
) -> dict[str, Any]:
    """Navigate to a URL in the browser.

    This tool navigates the browser to the specified URL. You can optionally
    enable mobile mode or specify a particular device to emulate.
    """
    try:
        logger.info(f"Attempting to navigate to {url}")
        nav_timeout = timeout or config.timeout_navigation

        # Determine which device to use (if any)
        device_name = None
        if mobile or device:
            device_name = device if device else config.mobile_default_device

        # Get browser service from app state
        browser_service = app.state["browser_service"]

        # Ensure browser with proper device emulation and video recording
        page = await browser_service.ensure_browser(
            device_name, record_video=record_video
        )

        try:
            # Navigate with wait_until options for better compatibility
            response = await page.goto(
                url, timeout=nav_timeout, wait_until="domcontentloaded"
            )

            # Additional wait for network to be idle (helps with dynamic content)
            try:
                await page.wait_for_load_state(
                    "networkidle", timeout=config.timeout_network_idle
                )
            except PlaywrightTimeout:
                # Network idle timeout is not critical
                logger.debug(
                    "Network idle timeout - page may still be loading resources"
                )

            # Check response status
            if response and response.status >= 400:
                return {
                    "error": f"Navigation completed but server returned error {response.status} for {url}"
                }

            return {
                "success": True,
                "url": url,
                "device": device_name,
                "recording_video": browser_service.is_recording,
            }

        except PlaywrightTimeout:
            return {
                "error": f"Navigation timeout ({nav_timeout}ms) exceeded for {url}. The page might be loading too slowly."
            }
        except Exception as e:
            return {"error": f"Failed to navigate to {url}: {str(e)}"}

    except BrowserError as e:
        logger.error(f"Browser error in navigate: {str(e)}")
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error in navigate: {str(e)}")
        return {"error": f"Unexpected error: {str(e)}"}


@app.tool()
async def playwright_screenshot(
    name: Annotated[str, Field(description="Name for the screenshot")],
    selector: Annotated[
        str | None,
        Field(default=None, description="CSS selector for element to screenshot"),
    ] = None,
    full_page: Annotated[
        bool, Field(default=False, description="Capture full scrollable page")
    ] = False,
    timeout: Annotated[
        int | None,
        Field(default=None, description="Timeout in milliseconds for finding elements"),
    ] = None,
) -> dict[str, Any]:
    """Take a screenshot of the current page or a specific element.

    Captures a screenshot of the entire page or a specific element selected by
    CSS selector. Screenshots are always saved to disk to avoid token limit issues.
    """
    try:
        # Get browser service from app state
        browser_service = app.state["browser_service"]

        page = await browser_service.ensure_browser()
        element_timeout = timeout or config.timeout_default

        # Get current viewport size
        current_viewport = page.viewport_size

        screenshot = None
        if selector:
            logger.info(f"Taking screenshot of element: {selector}")
            try:
                element = await page.wait_for_selector(
                    selector, timeout=element_timeout
                )
                if element:
                    screenshot = await element.screenshot()
                else:
                    return {"error": f"Element with selector '{selector}' not found"}
            except PlaywrightTimeout:
                return {"error": f"Timeout waiting for element: {selector}"}
        else:
            logger.info("Taking full page screenshot")
            screenshot = await page.screenshot(full_page=full_page)

        if screenshot:
            browser_service.screenshots[name] = screenshot

            # Calculate screenshot size
            size_kb = len(screenshot) / 1024
            size_mb = size_kb / 1024

            # Create screenshots directory if it doesn't exist
            screenshots_dir = browser_service.get_screenshots_dir()
            screenshots_dir.mkdir(exist_ok=True)

            # Generate filename with timestamp
            timestamp = datetime.now().strftime(config.screenshots_timestamp_format)
            safe_name = "".join(c for c in name if c.isalnum() or c in "._-")
            filename = f"{safe_name}_{timestamp}.png"
            filepath = screenshots_dir / filename

            # Save screenshot to file
            with open(filepath, "wb") as f:
                f.write(screenshot)
            saved_path = str(filepath)
            logger.info(f"Screenshot saved to: {saved_path} ({size_mb:.2f} MB)")

            # Report actual viewport size
            viewport_info = f"{current_viewport['width']}x{current_viewport['height']}"
            if browser_service.current_device:
                viewport_info += f" ({browser_service.current_device})"

            return {
                "success": True,
                "name": name,
                "path": saved_path,
                "viewport": viewport_info,
                "size_mb": round(size_mb, 2),
            }

    except BrowserError as e:
        logger.error(f"Browser error in screenshot: {str(e)}")
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error in screenshot: {str(e)}")
        return {"error": f"Unexpected error: {str(e)}"}


@app.tool()
async def playwright_click(
    selector: Annotated[str, Field(description="CSS selector for element to click")],
    timeout: Annotated[
        int | None, Field(default=None, description="Timeout in milliseconds")
    ] = None,
) -> dict[str, Any]:
    """Click an element on the page.

    Clicks the element matching the provided CSS selector.
    """
    try:
        # Get browser service from app state
        browser_service = app.state["browser_service"]

        page = await browser_service.ensure_browser()
        click_timeout = timeout or config.timeout_default

        logger.info(f"Clicking element: {selector}")
        await page.click(selector, timeout=click_timeout)

        return {"success": True, "selector": selector}

    except PlaywrightTimeout:
        return {
            "error": f"Click timeout ({click_timeout}ms) exceeded for selector: {selector}"
        }
    except Exception as e:
        logger.error(f"Error in click: {str(e)}")
        return {"error": f"Click failed: {str(e)}"}


@app.tool()
async def playwright_fill(
    selector: Annotated[str, Field(description="CSS selector for input field")],
    value: Annotated[str, Field(description="Value to fill")],
    timeout: Annotated[
        int | None, Field(default=None, description="Timeout in milliseconds")
    ] = None,
) -> dict[str, Any]:
    """Fill out an input field.

    Fills the input field matching the provided CSS selector with the specified value.
    """
    try:
        # Get browser service from app state
        browser_service = app.state["browser_service"]

        page = await browser_service.ensure_browser()
        fill_timeout = timeout or config.timeout_default

        logger.info(f"Filling element: {selector}")
        await page.fill(selector, value, timeout=fill_timeout)

        return {"success": True, "selector": selector, "value": value}

    except PlaywrightTimeout:
        return {
            "error": f"Fill timeout ({fill_timeout}ms) exceeded for selector: {selector}"
        }
    except Exception as e:
        logger.error(f"Error in fill: {str(e)}")
        return {"error": f"Fill failed: {str(e)}"}


@app.tool()
async def playwright_evaluate(
    script: Annotated[str, Field(description="JavaScript code to execute")],
    timeout: Annotated[
        int | None, Field(default=None, description="Timeout in milliseconds")
    ] = None,
) -> dict[str, Any]:
    """Execute JavaScript in the browser console.

    Evaluates the provided JavaScript code in the context of the current page.
    """
    try:
        # Get browser service from app state
        browser_service = app.state["browser_service"]

        page = await browser_service.ensure_browser()

        logger.info("Evaluating JavaScript")
        result = await page.evaluate(script)

        return {"success": True, "result": result}

    except Exception as e:
        logger.error(f"JavaScript evaluation error: {str(e)}")
        return {"error": f"JavaScript evaluation error: {str(e)}"}


@app.tool()
async def playwright_stop_recording(
    session_name: Annotated[str, Field(description="Name for the video session")],
) -> dict[str, Any]:
    """Stop recording and save the video to disk.

    Stops the current browser session's video recording and saves it with the specified name.
    This will close the current browser context, so you'll need to navigate again after stopping.
    """
    try:
        # Get browser service from app state
        browser_service = app.state["browser_service"]

        if not browser_service.is_recording:
            return {
                "error": "No video recording in progress. Enable record_video in playwright_navigate."
            }

        # Save the video
        video_path = await browser_service.save_video(session_name)

        if video_path:
            return {
                "success": True,
                "video_path": str(video_path),
                "session_name": session_name,
                "message": "Recording stopped and saved. Browser context closed.",
            }
        else:
            return {"error": "Failed to save video recording"}

    except Exception as e:
        logger.error(f"Error saving video: {str(e)}")
        return {"error": f"Failed to save video: {str(e)}"}


@app.tool()
async def playwright_list_videos() -> dict[str, Any]:
    """List all saved video recordings.

    Returns a list of all video recordings saved during the current session.
    """
    try:
        # Get browser service from app state
        browser_service = app.state["browser_service"]

        videos = []
        for session_name, video_path in browser_service.videos.items():
            if video_path.exists():
                videos.append(
                    {
                        "session_name": session_name,
                        "path": str(video_path),
                        "size_mb": round(video_path.stat().st_size / (1024 * 1024), 2),
                    }
                )

        return {"success": True, "videos": videos, "count": len(videos)}

    except Exception as e:
        logger.error(f"Error listing videos: {str(e)}")
        return {"error": f"Failed to list videos: {str(e)}"}


# Note: Cleanup will be handled by the browser service's destructor
# or by the client's exit signal


def main():
    """Main entry point for PMIND Playwright MCP server."""
    import argparse

    parser = argparse.ArgumentParser(description="PMIND Playwright MCP Server")
    # Add any command-line arguments here if needed in the future
    parser.parse_args()

    # Create and run the server
    server = create_server()
    server.run()


if __name__ == "__main__":
    main()
