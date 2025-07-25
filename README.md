# PMIND Playwright MCP Server

> ⚠️ **Experimental**: This MCP server is in an experimental state and may have rough edges. Please report any issues you encounter.

A Python implementation of a browser automation MCP (Model Context Protocol) server using FastMCP and Playwright. This server provides comprehensive tools to interact with web pages, take screenshots, and execute JavaScript in a real browser environment with advanced features like stealth mode and mobile device emulation.

## 🎯 Features

This MCP server provides browser automation capabilities with advanced anti-detection measures and mobile emulation support.

### 📦 Core Capabilities

- **🌐 Navigation**: Navigate to URLs with configurable timeouts and device emulation
- **📸 Screenshots**: Capture full page or element screenshots (automatically saved to `~/.pmind-playwright-mcp/screenshots`)
- **🎥 Video Recording**: Record browser sessions across multiple navigations
- **🖱️ Interactions**: Click elements and fill forms programmatically
- **💻 JavaScript**: Execute custom JavaScript in the browser context
- **📱 Mobile Emulation**: Full device emulation (iPhone, Android, tablets)
- **🥷 Stealth Mode**: Anti-bot detection with playwright-stealth
- **🔍 Console Monitoring**: Capture and store browser console logs

### ✨ Key Features

- **🏗️ FastMCP Framework**: Built on FastMCP for robust MCP implementation
- **🔒 Type Safety**: Pydantic models for input validation and configuration
- **⚙️ Configurable**: Environment-based configuration with dotenv support
- **🎭 Playwright Backend**: Using Playwright for reliable browser automation
- **🛡️ Security First**: Removed dangerous browser flags, custom exception handling
- **📁 Organized Architecture**: Clean service-based structure with proper separation of concerns
- **💾 Persistent Storage**: All screenshots and videos saved to `~/.pmind-playwright-mcp/`

## Installation & Setup

### Step 1: Clone the Repository

```bash
git clone https://github.com/raveenplgithub/pmind-playwright-mcp.git
cd pmind-playwright-mcp
```

### Step 2: Install Dependencies

```bash
# Install dependencies using uv
uv sync

# Install Playwright browsers (required for browser automation)
uv run playwright install
```

### Step 3: Configure the Server

The server uses environment variables for configuration. Copy the example `.env` file and customize as needed:

```bash
cp .env.example .env
```

To customize settings, edit `.env`:

```env
# Browser Settings
BROWSER_HEADLESS=false  # Set to true for headless mode
BROWSER_VIEWPORT_WIDTH=1280
BROWSER_VIEWPORT_HEIGHT=720

# See .env.example for all available options
```

### Step 4: Configure with Your Client

Add the MCP server to your client's MCP configuration:

```json
{
  "mcpServers": {
    "pmind-playwright-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/pmind-playwright-mcp", "pmind-playwright-mcp"]
    }
  }
}
```

Replace `/path/to/pmind-playwright-mcp` with the actual path where you cloned the repository.

#### For Claude Code (CLI)

Use the following command to add the server:

```bash
claude mcp add pmind-playwright-mcp -- uv run --directory /path/to/pmind-playwright-mcp pmind-playwright-mcp
```

## Configuration Options

### Storage Locations

All media files are saved to `~/.pmind-playwright-mcp/`:
- **Screenshots**: `~/.pmind-playwright-mcp/screenshots/`
- **Videos**: `~/.pmind-playwright-mcp/videos/`

These directories are created automatically when needed.

### Configuration File Structure

The `.env` file controls all server settings:

- **Browser Settings**: Headless mode, viewport size, launch arguments
- **Context Settings**: Locale, timezone, permissions, color scheme
- **Timeouts**: Default, navigation, page load check, network idle
- **Screenshots**: Save directory and timestamp format
- **Stealth Mode**: Anti-detection feature toggles
- **Mobile Defaults**: Default device for mobile emulation
- **Logging**: Log level and format
- **Video Recording**: Video directory and dimensions

See `.env.example` for detailed documentation of each option and available environment variables.

## Usage

Once configured, you can start using the Playwright MCP server through your client. The server will automatically start when your client connects.

### Available Tools

- **playwright_navigate** - Navigate to URLs with optional device emulation and video recording
- **playwright_screenshot** - Capture screenshots of pages or specific elements
- **playwright_click** - Click elements on the page
- **playwright_fill** - Fill input fields with text
- **playwright_evaluate** - Execute JavaScript in the browser context
- **playwright_stop_recording** - Stop and save video recordings
- **playwright_list_videos** - List all saved video recordings

### Video Recording Example

To record a browsing session across multiple sites:

1. Start recording with the first navigation:
   ```
   playwright_navigate(url="https://example.com", record_video=true)
   ```

2. Continue recording while navigating to other sites:
   ```
   playwright_navigate(url="https://another-site.com", record_video=true)
   ```

3. Stop recording and save the video:
   ```
   playwright_stop_recording(session_name="my_browsing_session")
   ```

The video will be saved to `~/.pmind-playwright-mcp/videos/my_browsing_session_[timestamp].webm`

### Manual Server Testing

To test the server manually:

```bash
# Run the MCP server
uv run pmind-playwright-mcp
```

## Development

### Running Tests

```bash
# Install dev dependencies
uv sync --dev

# Run tests (when available)
uv run pytest
```

### Code Quality

```bash
# Format code
uv run black .
uv run ruff check --fix .

# Check code quality
uv run black --check .
uv run ruff check .
```

## Architecture

- **src/server.py**: FastMCP server implementation with tool definitions and entry point
- **src/config.py**: Pydantic configuration models with dotenv support
- **src/services/browser.py**: Browser service managing Playwright instances
- **.env**: Environment variables configuration file
- **.env.example**: Example configuration file with all available options

