# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PMIND Playwright MCP is a Python implementation of a Model Context Protocol (MCP) server that provides browser automation capabilities using Playwright. It enables LLMs to interact with web pages through browser automation. The server is built using the FastMCP framework for better structure and error handling.

## Key Commands

### Installation
```bash
# Install dependencies using UV
uv sync

# Install Playwright browsers (required for browser automation)
uv run playwright install
```

### Running the Server
```bash
# Run the server directly with UV
uv run pmind-playwright-mcp
```

### Development Setup
```bash
# Install with dev dependencies
uv sync --dev

# Run linting
uv run ruff check .
uv run black --check .

# Format code
uv run black .
uv run ruff check --fix .
```

## Architecture

### Core Components

1. **src/server.py** - FastMCP server implementation
   - Entry point via `main()` function
   - Defines all MCP tools using FastMCP decorators
   - Handles tool registration and error responses
   - Uses Pydantic models for input validation

2. **src/config.py** - Configuration management
   - Pydantic models for all configuration sections
   - Loads settings from environment variables using dotenv
   - Type-safe configuration access with sensible defaults
   - Helper functions for parsing environment variables

3. **src/services/browser.py** - Browser service
   - `BrowserService` class handles browser lifecycle
   - Manages page creation and device emulation
   - Applies stealth mode settings
   - Handles screenshot storage

4. **.env** - Environment configuration file
   - All settings defined as environment variables
   - Copy from .env.example to get started
   - Supports lists (comma-separated) and booleans

### Available MCP Tools

- `playwright_navigate` - Navigate to URLs with configurable timeout and device emulation
- `playwright_screenshot` - Capture screenshots (full page or specific elements) with optional disk storage
- `playwright_click` - Click elements on the page
- `playwright_fill` - Fill input fields
- `playwright_evaluate` - Execute JavaScript in browser context

### Key Technical Details

- Built with FastMCP framework for robust MCP implementation
- Uses Playwright async API for browser automation
- Pydantic models for input validation and configuration
- Custom exception hierarchy for better error handling
- Console logs are captured and stored
- Screenshots can be saved to disk or returned as base64
- All operations have configurable timeouts
- Stealth mode with playwright-stealth integration
- Mobile device emulation support

### Dependencies

- `fastmcp>=2.10.4` - FastMCP framework for MCP servers
- `playwright>=1.40.0` - Browser automation library
- `playwright-stealth>=1.0.6` - Anti-bot detection measures
- `pydantic>=2.11.7` - Data validation and settings management
- `python-dotenv>=1.0.0` - Environment variable loading
- Python 3.10+ required

### Package Management

This project uses UV for fast, reliable Python package management. All dependencies are locked in `uv.lock` for reproducible builds.