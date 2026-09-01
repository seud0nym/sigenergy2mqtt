# HTML/CSS/JS Diagnostics UI Test Coverage

This directory contains comprehensive test coverage for the static web resources used in the diagnostics web UI, including HTML pages, CSS styling, and JavaScript functionality.

## Overview

After refactoring the diagnostics UI to extract common CSS and JavaScript into shared resources, comprehensive tests were added to ensure:

1. All static files exist and are accessible
2. HTML pages are well-formed and properly reference shared resources
3. CSS contains all required theme variables for light and dark modes
4. JavaScript functions are implemented correctly with proper error handling
5. Integration between pages and shared resources is consistent
6. Web accessibility and standards compliance

## Test Files

### test_static_resources.py (61 tests)

Validates structure and content of all static resources.

**Test Classes:**

- **TestStaticFilesExist** (6 tests)
  - Verifies all static files (CSS, JS, HTML, images) exist
  - Checks file sizes are non-zero

- **TestSharedCSS** (7 tests)
  - Validates CSS syntax and structure
  - Verifies dark theme variables defined in `:root`
  - Verifies light theme variables defined in `:root[data-theme="light"]`
  - Checks for UI component styles (body, header, connection pill, buttons)

- **TestSharedJS** (9 tests)
  - Verifies all required functions are defined
  - Checks for correct function signatures
  - Validates reconnect and error handling logic
  - Confirms JSON parsing and fetch functionality

- **TestHTMLStructure** (20 tests)
  - Validates HTML syntax and structure
  - Verifies all pages reference shared.css and shared.js correctly
  - Checks for required HTML attributes (lang, charset, viewport)
  - Confirms presence of UI elements (header, connection pill, theme toggle)

- **TestDashboardPage** (3 tests)
  - Validates dashboard.html specific content
  - Checks for grid layout and card components

- **TestDebugPage** (3 tests)
  - Validates debug.html specific content
  - Checks for filter inputs and logging UI

- **TestDiagnosticsPage** (3 tests)
  - Validates diagnostics.html specific content
  - Checks for status banner and diagnostic cards

- **TestIntegration** (6 tests)
  - Verifies consistent use of shared resources across pages
  - Checks for proper initialization of theme and WebSocket
  - Ensures no duplication of code

- **TestAccessibilityAndStandards** (4 tests)
  - Verifies HTML lang attribute
  - Checks for content type meta tag
  - Validates page titles
  - Checks for accessible button labels

### test_shared_js_advanced.py (49 tests)

Advanced behavioral tests for JavaScript functions, simulating logic in Python.

**Test Classes:**

- **TestInitThemeFunction** (4 tests)
  - Verifies localStorage integration
  - Checks system preference detection (prefers-color-scheme)
  - Validates data-theme attribute setting
  - Confirms error handling for localStorage unavailability

- **TestInitThemeToggleFunction** (4 tests)
  - Checks element existence validation
  - Verifies click event listener attachment
  - Validates theme switching logic
  - Confirms localStorage persistence

- **TestInitWebSocketFunction** (10 tests)
  - Validates function parameters (url, onMessage, setConnState)
  - Checks WebSocket connection creation
  - Verifies connection state handling (open, message, close, error)
  - Validates exponential backoff implementation
  - Checks maximum delay capping (15 seconds)
  - Verifies JSON message parsing
  - Confirms error handling

- **TestPostJSONFunction** (13 tests)
  - Validates function parameters
  - Checks async/await implementation
  - Verifies fetch API usage with correct headers
  - Validates JSON stringification and parsing
  - Checks for success/error flash feedback
  - Verifies onRevert callback invocation
  - Confirms error handling and logging

- **TestErrorHandling** (3 tests)
  - WebSocket missing support detection
  - localStorage error handling
  - Error logging to console

- **TestDataFlow** (3 tests)
  - WebSocket message JSON parsing flow
  - postJSON response object structure
  - Theme state consistency across functions

- **TestStateManagement** (4 tests)
  - WebSocket state variables (socket, retryDelay, closed)
  - Closed state checking before reconnect
  - Backoff delay reset on successful connection
  - Theme toggle state reading

- **TestEventHandling** (3 tests)
  - WebSocket onerror handler closing socket
  - Theme toggle click handler
  - WebSocket onopen state update

- **TestAPIContract** (4 tests)
  - initWebSocket return object has close() method
  - postJSON return object structure with ok property
  - onMessage callback receives parsed JSON
  - setConnState called with string states

## Coverage Summary

| Resource | Tests | Coverage |
|----------|-------|----------|
| shared.css | 7 | Theme variables, UI components, responsive design |
| shared.js | 40 | All 4 functions, error handling, state management |
| HTML pages | 20 | Structure, references, accessibility, standards |
| Integration | 12 | Resource coupling, initialization, consistency |
| static files | 6 | Existence, readability, file sizes |
| **Total** | **110** | **Comprehensive** |

## Running the Tests

### Run all static resource tests:
```bash
pytest tests/unit/diagnostics/test_static_resources.py -v
```

### Run all advanced JavaScript tests:
```bash
pytest tests/unit/diagnostics/test_shared_js_advanced.py -v
```

### Run all diagnostics tests (including existing):
```bash
pytest tests/unit/diagnostics/ -v
```

### Run with coverage report:
```bash
pytest tests/unit/diagnostics/ --cov=sigenergy2mqtt.diagnostics --cov-report=html
```

## Test Architecture

The tests use:

1. **HTML Parsing** - Custom `SimpleHTMLParser` class to extract and validate HTML structure
2. **Regex Pattern Matching** - To analyze JavaScript and CSS syntax without requiring a JS runtime
3. **String Content Analysis** - To verify presence of required functions, variables, and logic
4. **Fixtures** - pytest fixtures for loading static file contents
5. **Test Classes** - Organized by functionality (CSS, JS functions, HTML structure)

## Key Testing Patterns

### CSS Validation
- Uses regex to find CSS variable definitions
- Validates variable names and values
- Checks for both light and dark theme definitions

### JavaScript Validation
- Verifies function definitions and signatures
- Checks for required logic patterns (try-catch, setTimeout, etc.)
- Validates callback patterns and return values
- Confirms error handling presence

### HTML Validation
- Custom parser extracts elements, attributes, and links
- Verifies DOCTYPE, lang, meta tags
- Checks for required UI elements
- Validates cross-references to CSS and JS files

## Maintenance Notes

When updating static resources:

1. **CSS Changes**
   - Ensure new variables are defined in both `:root` and `:root[data-theme="light"]`
   - Update tests if new CSS component classes are added

2. **JavaScript Changes**
   - Update function signatures in tests if parameters change
   - Add tests for new functions or callbacks
   - Ensure error handling is maintained

3. **HTML Changes**
   - Verify shared.css and shared.js links remain correct
   - Ensure new components use existing CSS variable names
   - Add tests for new page-specific content

## Integration with CI/CD

These tests are part of the standard test suite and run on:
- Local development with `pytest`
- CI/CD pipelines via `hatch test` or similar commands
- Coverage reports include static resource testing

The tests have zero external dependencies beyond Python standard library, ensuring they run reliably in any environment.
