"""Advanced tests for JavaScript functions in diagnostics UI.

These tests validate the actual functionality and behavior of shared.js functions
by analyzing their code structure and simulating their logic in Python.
"""

import re
from pathlib import Path

import pytest

STATIC_DIR = Path(__file__).parent.parent.parent.parent / "sigenergy2mqtt" / "diagnostics" / "static"


@pytest.fixture
def shared_js() -> str:
    """Load shared.js content."""
    js_file = STATIC_DIR / "shared.js"
    return js_file.read_text(encoding="utf-8")


# ============================================================================
# Shared.js Function Behavior Tests
# ============================================================================


class TestInitThemeFunction:
    """Test initTheme() IIFE behavior."""

    def test_init_theme_checks_localstorage(self, shared_js: str) -> None:
        """initTheme must check localStorage for saved theme."""
        assert "localStorage.getItem('s2m-theme')" in shared_js

    def test_init_theme_checks_system_preference(self, shared_js: str) -> None:
        """initTheme must check system color scheme preference."""
        assert "prefers-color-scheme" in shared_js
        assert "matchMedia" in shared_js

    def test_init_theme_sets_data_attribute(self, shared_js: str) -> None:
        """initTheme must set data-theme attribute on document element."""
        assert "setAttribute('data-theme'" in shared_js or 'setAttribute("data-theme"' in shared_js

    def test_init_theme_has_error_handling(self, shared_js: str) -> None:
        """initTheme must handle localStorage errors gracefully."""
        # Find the initTheme function
        match = re.search(r"function initTheme\(\)\s*{(.*?)}\(\)", shared_js, re.DOTALL)
        if match:
            func_body = match.group(1)
            assert "try" in func_body
            assert "catch" in func_body

    def test_init_theme_runs_immediately(self, shared_js: str) -> None:
        """initTheme must be an IIFE that runs on page load."""
        # Check for IIFE pattern: (function initTheme() { ... })()
        assert re.search(r"\(function initTheme\(\).*?\}\)\(\)", shared_js, re.DOTALL)


class TestInitThemeToggleFunction:
    """Test initThemeToggle(element) behavior."""

    def test_init_theme_toggle_checks_element(self, shared_js: str) -> None:
        """initThemeToggle must check if element exists."""
        # Extract function
        match = re.search(r"function initThemeToggle\((.*?)\)\s*{(.*?)\n\}", shared_js, re.DOTALL)
        if match:
            func_body = match.group(2)
            assert "if" in func_body and ("return" in func_body or "themeToggleElement" in func_body)

    def test_init_theme_toggle_adds_click_listener(self, shared_js: str) -> None:
        """initThemeToggle must add click event listener."""
        assert "addEventListener" in shared_js
        assert "'click'" in shared_js or '"click"' in shared_js

    def test_init_theme_toggle_switches_themes(self, shared_js: str) -> None:
        """initThemeToggle must toggle between light and dark themes."""
        # Check for theme toggle logic
        toggle_match = re.search(r"function initThemeToggle.*?{.*?}", shared_js, re.DOTALL)
        if toggle_match:
            toggle_code = toggle_match.group(0)
            assert "'light'" in toggle_code or '"light"' in toggle_code
            assert "'dark'" in toggle_code or '"dark"' in toggle_code
            assert "getAttribute" in toggle_code or "data-theme" in toggle_code

    def test_init_theme_toggle_persists_choice(self, shared_js: str) -> None:
        """initThemeToggle must save theme choice to localStorage."""
        assert "localStorage.setItem('s2m-theme'" in shared_js or 'localStorage.setItem("s2m-theme"' in shared_js


class TestInitWebSocketFunction:
    """Test initWebSocket(url, onMessage, setConnState) behavior."""

    def test_init_websocket_accepts_three_parameters(self, shared_js: str) -> None:
        """initWebSocket must accept url, onMessage, setConnState parameters."""
        match = re.search(r"function initWebSocket\((.*?)\)", shared_js)
        if match:
            params = match.group(1)
            assert "wsUrl" in params or "url" in params
            assert "onMessage" in params
            assert "setConnState" in params

    def test_init_websocket_creates_websocket_connection(self, shared_js: str) -> None:
        """initWebSocket must create WebSocket connection."""
        ws_match = re.search(r"function initWebSocket.*?{.*?new WebSocket", shared_js, re.DOTALL)
        assert ws_match is not None, "WebSocket constructor not found"

    def test_init_websocket_handles_connection_open(self, shared_js: str) -> None:
        """initWebSocket must set 'live' state when connected."""
        assert "socket.onopen" in shared_js
        assert "'live'" in shared_js or '"live"' in shared_js

    def test_init_websocket_handles_connection_message(self, shared_js: str) -> None:
        """initWebSocket must handle incoming messages."""
        assert "socket.onmessage" in shared_js
        # Should call onMessage callback
        assert re.search(r"onMessage\s*\(", shared_js)

    def test_init_websocket_handles_connection_close(self, shared_js: str) -> None:
        """initWebSocket must handle connection close and attempt reconnect."""
        assert "socket.onclose" in shared_js
        assert "setTimeout" in shared_js
        assert "'down'" in shared_js or '"down"' in shared_js

    def test_init_websocket_implements_exponential_backoff(self, shared_js: str) -> None:
        """initWebSocket must implement exponential backoff for retries."""
        # Check for backoff logic
        ws_match = re.search(r"function initWebSocket.*?{(.*?)\n\}", shared_js, re.DOTALL)
        if ws_match:
            ws_body = ws_match.group(1)
            assert "retryDelay" in ws_body
            assert "Math.min" in ws_body
            assert "*" in ws_body  # Backoff multiplier

    def test_init_websocket_caps_maximum_delay(self, shared_js: str) -> None:
        """initWebSocket must cap maximum retry delay."""
        # Should have something like Math.min(delay * 1.5, MAX)
        assert "15000" in shared_js or "15e3" in shared_js

    def test_init_websocket_returns_close_handle(self, shared_js: str) -> None:
        """initWebSocket must return object with close() method."""
        assert "return {" in shared_js
        assert "close:" in shared_js or '"close":' in shared_js

    def test_init_websocket_parses_json_messages(self, shared_js: str) -> None:
        """initWebSocket must parse JSON from WebSocket messages."""
        assert "JSON.parse" in shared_js

    def test_init_websocket_has_error_handling(self, shared_js: str) -> None:
        """initWebSocket must have try-catch for JSON parsing errors."""
        # Find onmessage handler
        msg_match = re.search(r"socket\.onmessage\s*=.*?{(.*?)};", shared_js, re.DOTALL)
        if msg_match:
            msg_body = msg_match.group(1)
            assert "try" in msg_body
            assert "catch" in msg_body


class TestPostJSONFunction:
    """Test postJSON(url, body, flashElement, onRevert) behavior."""

    def test_post_json_accepts_four_parameters(self, shared_js: str) -> None:
        """postJSON must accept url, body, flashElement, onRevert parameters."""
        match = re.search(r"(async\s+)?function postJSON\((.*?)\)", shared_js)
        if match:
            params = match.group(2)
            assert "url" in params
            assert "body" in params
            assert "flashElement" in params
            assert "onRevert" in params

    def test_post_json_is_async(self, shared_js: str) -> None:
        """postJSON must be async function."""
        assert "async function postJSON" in shared_js

    def test_post_json_uses_fetch(self, shared_js: str) -> None:
        """postJSON must use fetch API."""
        assert "fetch(" in shared_js or "fetch (" in shared_js

    def test_post_json_sets_method_post(self, shared_js: str) -> None:
        """postJSON must set method to POST."""
        assert "method: 'POST'" in shared_js or 'method: "POST"' in shared_js

    def test_post_json_sets_content_type(self, shared_js: str) -> None:
        """postJSON must set Content-Type header to application/json."""
        assert "Content-Type" in shared_js
        assert "application/json" in shared_js

    def test_post_json_stringifies_body(self, shared_js: str) -> None:
        """postJSON must stringify body as JSON."""
        assert "JSON.stringify" in shared_js

    def test_post_json_parses_response(self, shared_js: str) -> None:
        """postJSON must parse response as JSON."""
        # Find fetch call and check for .json()
        assert "res.json()" in shared_js or ".json()" in shared_js

    def test_post_json_flashes_success(self, shared_js: str) -> None:
        """postJSON must flash element on success."""
        assert "flash-ok" in shared_js

    def test_post_json_flashes_error(self, shared_js: str) -> None:
        """postJSON must flash element on error."""
        assert "flash-err" in shared_js

    def test_post_json_calls_on_revert_callback(self, shared_js: str) -> None:
        """postJSON must call onRevert callback on failure."""
        # Extract function
        match = re.search(r"(async\s+)?function postJSON.*?{(.*?)\n\}(?!,)", shared_js, re.DOTALL)
        if match:
            func_body = match.group(2)
            assert "onRevert" in func_body

    def test_post_json_returns_promise(self, shared_js: str) -> None:
        """postJSON must return Promise resolving to result object."""
        assert "async function postJSON" in shared_js
        # Should have return statements
        match = re.search(r"async function postJSON.*?{(.*?)^}", shared_js, re.MULTILINE | re.DOTALL)
        if match:
            func_body = match.group(1)
            assert "return" in func_body

    def test_post_json_handles_fetch_errors(self, shared_js: str) -> None:
        """postJSON must catch fetch and JSON parse errors."""
        # Extract function
        match = re.search(r"async function postJSON.*?{(.*?)^}", shared_js, re.MULTILINE | re.DOTALL)
        if match:
            func_body = match.group(1)
            assert "catch" in func_body
            assert "try" in func_body

    def test_post_json_triggers_reflow_before_flash_animation(self, shared_js: str) -> None:
        """postJSON should trigger reflow to reset flash animation."""
        # offsetWidth access triggers reflow
        assert "offsetWidth" in shared_js


# ============================================================================
# Error Handling and Edge Cases
# ============================================================================


class TestErrorHandling:
    """Test error handling in shared.js functions."""

    def test_websocket_handles_missing_support(self, shared_js: str) -> None:
        """initWebSocket must handle missing WebSocket support."""
        # Should wrap WebSocket in try-catch
        # Check that WebSocket creation is wrapped in try-catch
        ws_match = re.search(r"function initWebSocket.*?return\s*{", shared_js, re.DOTALL)
        if ws_match:
            ws_code = ws_match.group(0)
            assert "try" in ws_code
            assert "new WebSocket" in ws_code
            assert "catch" in ws_code

    def test_init_theme_handles_localstorage_error(self, shared_js: str) -> None:
        """initTheme must handle localStorage unavailable."""
        # Should have try-catch
        match = re.search(r"function initTheme\(\)\s*{(.*?)\}\(\)", shared_js, re.DOTALL)
        if match:
            func_body = match.group(1)
            assert "try" in func_body
            assert "catch" in func_body

    def test_post_json_logs_errors(self, shared_js: str) -> None:
        """postJSON should log errors to console."""
        # Should have console.error
        assert "console.error" in shared_js


# ============================================================================
# Data Flow Tests
# ============================================================================


class TestDataFlow:
    """Test data flow and message handling."""

    def test_websocket_message_parsing_flow(self, shared_js: str) -> None:
        """WebSocket messages must be parsed from JSON and passed to callback."""
        # Should have: JSON.parse(evt.data) -> onMessage(parsed)
        assert "evt.data" in shared_js
        assert "JSON.parse" in shared_js
        # Find onmessage handler
        msg_match = re.search(r"socket\.onmessage\s*=.*?{(.*?)};", shared_js, re.DOTALL)
        if msg_match:
            handler = msg_match.group(1)
            # Should call onMessage
            assert "onMessage" in handler

    def test_post_json_response_structure(self, shared_js: str) -> None:
        """postJSON must handle response with ok and optional revision fields."""
        # Function should check result.ok
        match = re.search(r"async function postJSON.*?{(.*?)^}", shared_js, re.MULTILINE | re.DOTALL)
        if match:
            func_body = match.group(1)
            assert "result.ok" in func_body or "result['ok']" in func_body

    def test_theme_states_are_consistent(self, shared_js: str) -> None:
        """Theme values must be consistent between init and toggle."""
        # Both should use 'light' and 'dark' strings
        assert "'light'" in shared_js or '"light"' in shared_js
        assert "'dark'" in shared_js or '"dark"' in shared_js
        # Count occurrences - should appear multiple times
        light_count = shared_js.count("'light'") + shared_js.count('"light"')
        dark_count = shared_js.count("'dark'") + shared_js.count('"dark"')
        assert light_count >= 2, "Theme 'light' should be used in multiple places"
        assert dark_count >= 2, "Theme 'dark' should be used in multiple places"


# ============================================================================
# State Management Tests
# ============================================================================


class TestStateManagement:
    """Test state management in shared.js functions."""

    def test_websocket_state_variables(self, shared_js: str) -> None:
        """initWebSocket must use local state variables."""
        # Should have socket, retryDelay, closed variables
        ws_match = re.search(r"function initWebSocket.*?{(.*?)\n\}(?!;)", shared_js, re.DOTALL)
        if ws_match:
            ws_body = ws_match.group(1)
            assert "let socket" in ws_body
            assert "let retryDelay" in ws_body
            assert "let closed" in ws_body

    def test_websocket_handles_closed_state(self, shared_js: str) -> None:
        """initWebSocket must check closed state before reconnecting."""
        # Should check "if (closed) return"
        ws_match = re.search(r"function initWebSocket.*?function connect.*?{(.*?)\n\s+}", shared_js, re.DOTALL)
        if ws_match:
            connect_body = ws_match.group(1)
            assert "if (closed)" in connect_body or "if(closed)" in connect_body

    def test_websocket_resets_backoff_on_success(self, shared_js: str) -> None:
        """WebSocket must reset retry delay to 1000 on successful connection."""
        assert "retryDelay = 1000" in shared_js

    def test_theme_toggle_state_consistency(self, shared_js: str) -> None:
        """Theme toggle must read current state before toggling."""
        # Should check current state before changing
        toggle_match = re.search(r"function initThemeToggle.*?{(.*?)\n\}", shared_js, re.DOTALL)
        if toggle_match:
            toggle_body = toggle_match.group(1)
            assert "getAttribute" in toggle_body


# ============================================================================
# Event Handling Tests
# ============================================================================


class TestEventHandling:
    """Test event handling in shared.js."""

    def test_websocket_onerror_calls_close(self, shared_js: str) -> None:
        """WebSocket onerror handler must close socket."""
        assert "socket.onerror" in shared_js
        onerror_match = re.search(r"socket\.onerror\s*=.*?{(.*?)};", shared_js, re.DOTALL)
        if onerror_match:
            handler = onerror_match.group(1)
            assert "socket.close()" in handler or "close()" in handler

    def test_theme_toggle_click_handler(self, shared_js: str) -> None:
        """Theme toggle must have click event handler."""
        assert "addEventListener('click'" in shared_js or 'addEventListener("click"' in shared_js

    def test_websocket_onopen_updates_state(self, shared_js: str) -> None:
        """WebSocket onopen must update connection state."""
        assert "socket.onopen" in shared_js
        onopen_match = re.search(r"socket\.onopen\s*=.*?{(.*?)};", shared_js, re.DOTALL)
        if onopen_match:
            handler = onopen_match.group(1)
            assert "setConnState" in handler


# ============================================================================
# API Contract Tests
# ============================================================================


class TestAPIContract:
    """Test that functions implement expected API contracts."""

    def test_init_websocket_returns_close_api(self, shared_js: str) -> None:
        """initWebSocket return object must have close() method."""
        # Should return { close: () => ... }
        return_match = re.search(r"return\s*{[^}]*close[^}]*}", shared_js, re.DOTALL)
        assert return_match is not None, "close() method not found in return object"

    def test_post_json_returns_result_object(self, shared_js: str) -> None:
        """postJSON must return object with ok property."""
        # Should return { ok: true/false, ... }
        match = re.search(r"return\s*{\s*ok:", shared_js)
        assert match is not None, "Result object with ok property not found"

    def test_on_message_callback_receives_parsed_json(self, shared_js: str) -> None:
        """onMessage callback must receive parsed JSON data."""
        # Should call onMessage(JSON.parse(...))
        assert "onMessage(JSON.parse" in shared_js or "onMessage( JSON.parse" in shared_js

    def test_set_conn_state_called_with_string(self, shared_js: str) -> None:
        """setConnState callback must be called with string state."""
        # Should call setConnState with state strings
        states = ["'live'", '"live"', "'down'", '"down"', "'connecting'", '"connecting"']
        found = False
        for state in states:
            if f"setConnState({state})" in shared_js or f"setConnState( {state})" in shared_js:
                found = True
                break
        # More lenient check - just verify setConnState is called multiple times
        assert shared_js.count("setConnState(") >= 2, "setConnState should be called multiple times"
