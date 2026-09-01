"""Test coverage for HTML/CSS/JS static resources in the diagnostics web UI.

Tests verify:
- All static files exist and are readable
- HTML files are well-formed and include required resources
- HTML files have required structural elements
- CSS contains all theme variables
- JavaScript functions are defined and properly structured
- Integration between HTML and shared resources
"""

import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

STATIC_DIR = Path(__file__).parent.parent.parent.parent / "sigenergy2mqtt" / "diagnostics" / "static"


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def static_dir() -> Path:
    """Return the path to the static resources directory."""
    assert STATIC_DIR.exists(), f"Static directory not found: {STATIC_DIR}"
    return STATIC_DIR


@pytest.fixture
def shared_css(static_dir) -> str:
    """Load shared.css content."""
    css_file = static_dir / "shared.css"
    assert css_file.exists(), f"shared.css not found: {css_file}"
    return css_file.read_text(encoding="utf-8")


@pytest.fixture
def shared_js(static_dir) -> str:
    """Load shared.js content."""
    js_file = static_dir / "shared.js"
    assert js_file.exists(), f"shared.js not found: {js_file}"
    return js_file.read_text(encoding="utf-8")


@pytest.fixture
def dashboard_html(static_dir) -> str:
    """Load dashboard.html content."""
    html_file = static_dir / "dashboard.html"
    assert html_file.exists(), f"dashboard.html not found: {html_file}"
    return html_file.read_text(encoding="utf-8")


@pytest.fixture
def debug_html(static_dir) -> str:
    """Load debug.html content."""
    html_file = static_dir / "debug.html"
    assert html_file.exists(), f"debug.html not found: {html_file}"
    return html_file.read_text(encoding="utf-8")


@pytest.fixture
def diagnostics_html(static_dir) -> str:
    """Load diagnostics.html content."""
    html_file = static_dir / "diagnostics.html"
    assert html_file.exists(), f"diagnostics.html not found: {html_file}"
    return html_file.read_text(encoding="utf-8")


# ============================================================================
# Static Files Existence Tests
# ============================================================================


class TestStaticFilesExist:
    """Verify all required static files exist and are readable."""

    def test_static_directory_exists(self, static_dir: Path) -> None:
        """Static resources directory must exist."""
        assert static_dir.is_dir()

    def test_favicon_exists(self, static_dir: Path) -> None:
        """favicon.ico must exist."""
        favicon = static_dir / "favicon.ico"
        assert favicon.exists()
        assert favicon.stat().st_size > 0

    def test_logo_exists(self, static_dir: Path) -> None:
        """logo.png must exist."""
        logo = static_dir / "logo.png"
        assert logo.exists()
        assert logo.stat().st_size > 0

    def test_shared_css_exists(self, static_dir: Path) -> None:
        """shared.css must exist and be readable."""
        shared = static_dir / "shared.css"
        assert shared.exists()
        assert shared.stat().st_size > 0

    def test_shared_js_exists(self, static_dir: Path) -> None:
        """shared.js must exist and be readable."""
        shared = static_dir / "shared.js"
        assert shared.exists()
        assert shared.stat().st_size > 0

    def test_html_pages_exist(self, static_dir: Path) -> None:
        """All three HTML pages must exist."""
        for page in ["dashboard.html", "debug.html", "diagnostics.html"]:
            html_file = static_dir / page
            assert html_file.exists(), f"{page} not found"
            assert html_file.stat().st_size > 0


# ============================================================================
# CSS Variables and Structure Tests
# ============================================================================


class TestSharedCSS:
    """Verify shared.css structure and content."""

    def test_css_is_not_empty(self, shared_css: str) -> None:
        """CSS file must contain content."""
        assert len(shared_css.strip()) > 0

    def test_dark_theme_variables_defined(self, shared_css: str) -> None:
        """Dark theme CSS variables must be defined."""
        required_vars = [
            "--bg",
            "--bg-panel",
            "--bg-card",
            "--border",
            "--text",
            "--text-dim",
            "--accent",
            "--accent-dim",
            "--warn",
            "--warn-dim",
            "--bad",
            "--bad-dim",
            "--unknown",
            "--mono",
            "--glow-1",
            "--glow-2",
            "--dash-border",
            "--dash-border-strong",
            "--header-bg",
            "--scheme",
        ]
        for var in required_vars:
            # Check for variable definition in :root
            pattern = rf":root\s*{{[^}}]*{re.escape(var)}\s*:"
            assert re.search(pattern, shared_css), f"Dark theme variable {var} not found in :root"

    def test_light_theme_variables_defined(self, shared_css: str) -> None:
        """Light theme CSS variables must be defined."""
        required_vars = [
            "--bg",
            "--bg-panel",
            "--bg-card",
            "--border",
            "--text",
            "--text-dim",
            "--accent",
            "--accent-dim",
            "--warn",
            "--warn-dim",
            "--bad",
            "--bad-dim",
            "--unknown",
            "--glow-1",
            "--glow-2",
            "--dash-border",
            "--dash-border-strong",
            "--header-bg",
            "--scheme",
        ]
        for var in required_vars:
            # Check for variable definition in :root[data-theme="light"]
            pattern = rf":root\[data-theme\s*=\s*[\"']light[\"']\][^{{]*{{[^}}]*{re.escape(var)}\s*:"
            assert re.search(pattern, shared_css, re.DOTALL), f"Light theme variable {var} not found in :root[data-theme='light']"

    def test_body_styles_defined(self, shared_css: str) -> None:
        """Body element styling must be defined."""
        assert "body" in shared_css
        assert "margin: 0" in shared_css or "margin:0" in shared_css.replace(" ", "")
        assert "color: var(--text)" in shared_css or "color:var(--text)" in shared_css.replace(" ", "")

    def test_header_styles_defined(self, shared_css: str) -> None:
        """Header element styling must be defined."""
        assert "header" in shared_css
        assert "display: flex" in shared_css or "display:flex" in shared_css.replace(" ", "")

    def test_connection_pill_styles_defined(self, shared_css: str) -> None:
        """Connection pill styling must be defined for various states."""
        assert ".conn-pill" in shared_css
        assert ".conn-pill.live" in shared_css
        assert ".conn-pill.down" in shared_css

    def test_button_styles_defined(self, shared_css: str) -> None:
        """.btn class must be defined for buttons."""
        assert ".btn" in shared_css


# ============================================================================
# JavaScript Functions Tests
# ============================================================================


class TestSharedJS:
    """Verify shared.js contains all required functions and logic."""

    def test_js_is_not_empty(self, shared_js: str) -> None:
        """JavaScript file must contain content."""
        assert len(shared_js.strip()) > 0

    def test_init_theme_function_defined(self, shared_js: str) -> None:
        """initTheme() IIFE must be defined."""
        # initTheme is an IIFE, check for function initTheme or (function initTheme)
        assert "function initTheme" in shared_js
        assert "localStorage.getItem" in shared_js
        assert "data-theme" in shared_js

    def test_init_theme_toggle_function_defined(self, shared_js: str) -> None:
        """initThemeToggle() function must be defined."""
        assert "function initThemeToggle" in shared_js
        assert "addEventListener" in shared_js
        assert "localStorage.setItem" in shared_js

    def test_init_websocket_function_defined(self, shared_js: str) -> None:
        """initWebSocket() function must be defined."""
        assert "function initWebSocket" in shared_js
        assert "WebSocket" in shared_js
        assert "onmessage" in shared_js
        assert "onclose" in shared_js
        assert "onerror" in shared_js

    def test_init_websocket_reconnect_logic(self, shared_js: str) -> None:
        """WebSocket must have reconnect and exponential backoff logic."""
        assert "retryDelay" in shared_js
        assert "Math.min" in shared_js
        assert "setTimeout" in shared_js

    def test_post_json_function_defined(self, shared_js: str) -> None:
        """postJSON() function must be defined."""
        assert "function postJSON" in shared_js or "async function postJSON" in shared_js
        assert "fetch" in shared_js
        assert "Content-Type" in shared_js
        assert "application/json" in shared_js

    def test_post_json_flash_logic(self, shared_js: str) -> None:
        """postJSON must have flash feedback logic."""
        assert "flash-ok" in shared_js
        assert "flash-err" in shared_js
        assert "classList" in shared_js

    def test_websocket_connection_states(self, shared_js: str) -> None:
        """WebSocket must handle connection state transitions."""
        assert "'live'" in shared_js or '"live"' in shared_js
        assert "'down'" in shared_js or '"down"' in shared_js
        assert "'connecting'" in shared_js or '"connecting"' in shared_js

    def test_json_parsing(self, shared_js: str) -> None:
        """JavaScript must parse JSON from WebSocket and fetch responses."""
        assert "JSON.parse" in shared_js
        assert "JSON.stringify" in shared_js


# ============================================================================
# HTML Structure Tests
# ============================================================================


class SimpleHTMLParser(HTMLParser):
    """Simple HTML parser to extract elements and attributes."""

    def __init__(self):
        super().__init__()
        self.links = []  # (rel, href)
        self.scripts = []  # src
        self.elements = []  # tag names
        self.ids = []  # id attributes
        self.classes = []  # class attributes

    def handle_starttag(self, tag, attrs):
        self.elements.append(tag)
        attrs_dict = dict(attrs)
        if "id" in attrs_dict:
            self.ids.append(attrs_dict["id"])
        if "class" in attrs_dict:
            self.classes.extend(attrs_dict["class"].split())
        if tag == "link":
            rel = attrs_dict.get("rel", [None])[0] if isinstance(attrs_dict.get("rel"), list) else attrs_dict.get("rel")
            href = attrs_dict.get("href")
            if rel or href:
                self.links.append((rel, href))
        elif tag == "script":
            src = attrs_dict.get("src")
            if src:
                self.scripts.append(src)


def parse_html(html_content: str) -> SimpleHTMLParser:
    """Parse HTML content and return parser with extracted info."""
    parser = SimpleHTMLParser()
    parser.feed(html_content)
    return parser


class TestHTMLStructure:
    """Verify HTML pages have correct structure and reference shared resources."""

    def test_dashboard_html_is_valid(self, dashboard_html: str) -> None:
        """dashboard.html must be valid HTML."""
        parser = parse_html(dashboard_html)
        assert "html" in parser.elements
        assert "head" in parser.elements
        assert "body" in parser.elements

    def test_debug_html_is_valid(self, debug_html: str) -> None:
        """debug.html must be valid HTML."""
        parser = parse_html(debug_html)
        assert "html" in parser.elements
        assert "head" in parser.elements
        assert "body" in parser.elements

    def test_diagnostics_html_is_valid(self, diagnostics_html: str) -> None:
        """diagnostics.html must be valid HTML."""
        parser = parse_html(diagnostics_html)
        assert "html" in parser.elements
        assert "head" in parser.elements
        assert "body" in parser.elements

    def test_html_pages_have_correct_lang_attribute(self, dashboard_html: str, debug_html: str, diagnostics_html: str) -> None:
        """HTML pages must have lang="en" attribute."""
        for html_content in [dashboard_html, debug_html, diagnostics_html]:
            assert 'lang="en"' in html_content or "lang='en'" in html_content

    def test_dashboard_html_includes_shared_css(self, dashboard_html: str) -> None:
        """dashboard.html must link to shared.css."""
        assert 'href="static/shared.css"' in dashboard_html or "href='static/shared.css'" in dashboard_html

    def test_debug_html_includes_shared_css(self, debug_html: str) -> None:
        """debug.html must link to shared.css."""
        assert 'href="static/shared.css"' in debug_html or "href='static/shared.css'" in debug_html

    def test_diagnostics_html_includes_shared_css(self, diagnostics_html: str) -> None:
        """diagnostics.html must link to shared.css."""
        assert 'href="static/shared.css"' in diagnostics_html or "href='static/shared.css'" in diagnostics_html

    def test_dashboard_html_includes_shared_js(self, dashboard_html: str) -> None:
        """dashboard.html must load shared.js."""
        assert 'src="static/shared.js"' in dashboard_html or "src='static/shared.js'" in dashboard_html

    def test_debug_html_includes_shared_js(self, debug_html: str) -> None:
        """debug.html must load shared.js."""
        assert 'src="static/shared.js"' in debug_html or "src='static/shared.js'" in debug_html

    def test_diagnostics_html_includes_shared_js(self, diagnostics_html: str) -> None:
        """diagnostics.html must load shared.js."""
        assert 'src="static/shared.js"' in diagnostics_html or "src='static/shared.js'" in diagnostics_html

    def test_html_pages_have_favicon_reference(self, dashboard_html: str, debug_html: str, diagnostics_html: str) -> None:
        """HTML pages must reference favicon.ico."""
        for html_content in [dashboard_html, debug_html, diagnostics_html]:
            assert "favicon.ico" in html_content

    def test_html_pages_have_viewport_meta(self, dashboard_html: str, debug_html: str, diagnostics_html: str) -> None:
        """HTML pages must have viewport meta tag for responsive design."""
        for html_content in [dashboard_html, debug_html, diagnostics_html]:
            assert "viewport" in html_content

    def test_html_pages_have_charset_meta(self, dashboard_html: str, debug_html: str, diagnostics_html: str) -> None:
        """HTML pages must have charset meta tag."""
        for html_content in [dashboard_html, debug_html, diagnostics_html]:
            assert "UTF-8" in html_content or "utf-8" in html_content

    def test_dashboard_html_has_header_element(self, dashboard_html: str) -> None:
        """dashboard.html must have header element."""
        parser = parse_html(dashboard_html)
        assert "header" in parser.elements

    def test_debug_html_has_header_element(self, debug_html: str) -> None:
        """debug.html must have header element."""
        parser = parse_html(debug_html)
        assert "header" in parser.elements

    def test_diagnostics_html_has_header_element(self, diagnostics_html: str) -> None:
        """diagnostics.html must have header element."""
        parser = parse_html(diagnostics_html)
        assert "header" in parser.elements

    def test_html_pages_have_connection_pill(self, dashboard_html: str, debug_html: str, diagnostics_html: str) -> None:
        """HTML pages must have connection status pill (conn-pill class)."""
        for html_content in [dashboard_html, debug_html, diagnostics_html]:
            assert "conn-pill" in html_content

    def test_dashboard_html_has_theme_toggle(self, dashboard_html: str) -> None:
        """dashboard.html must have theme toggle button."""
        assert "themeToggle" in dashboard_html or "theme" in dashboard_html.lower()

    def test_debug_html_has_theme_toggle(self, debug_html: str) -> None:
        """debug.html must have theme toggle button."""
        assert "themeToggle" in debug_html or "theme" in debug_html.lower()

    def test_diagnostics_html_has_theme_toggle(self, diagnostics_html: str) -> None:
        """diagnostics.html must have theme toggle button."""
        assert "themeToggle" in diagnostics_html or "theme" in diagnostics_html.lower()


# ============================================================================
# Page-Specific Content Tests
# ============================================================================


class TestDashboardPage:
    """Test dashboard.html specific content."""

    def test_dashboard_title(self, dashboard_html: str) -> None:
        """dashboard.html must have appropriate title."""
        assert "<title>" in dashboard_html
        assert "Solar" in dashboard_html or "Battery" in dashboard_html or "sigenergy" in dashboard_html.lower()

    def test_dashboard_has_grid_layout(self, dashboard_html: str) -> None:
        """dashboard.html must use grid layout for cards."""
        assert ".grid" in dashboard_html

    def test_dashboard_has_cards(self, dashboard_html: str) -> None:
        """dashboard.html must have card elements."""
        assert ".card" in dashboard_html or "card" in dashboard_html


class TestDebugPage:
    """Test debug.html specific content."""

    def test_debug_title(self, debug_html: str) -> None:
        """debug.html must have appropriate title."""
        assert "<title>" in debug_html
        assert "Debug" in debug_html or "Logging" in debug_html or "sigenergy" in debug_html.lower()

    def test_debug_has_filter_input(self, debug_html: str) -> None:
        """debug.html must have filter input for log filtering."""
        assert "filter" in debug_html.lower()

    def test_debug_has_grid_layout(self, debug_html: str) -> None:
        """debug.html must use grid layout for cards."""
        assert ".grid" in debug_html


class TestDiagnosticsPage:
    """Test diagnostics.html specific content."""

    def test_diagnostics_title(self, diagnostics_html: str) -> None:
        """diagnostics.html must have appropriate title."""
        assert "<title>" in diagnostics_html
        assert "Diagnostics" in diagnostics_html or "sigenergy" in diagnostics_html.lower()

    def test_diagnostics_has_status_banner(self, diagnostics_html: str) -> None:
        """diagnostics.html must have status banner."""
        assert "status-banner" in diagnostics_html

    def test_diagnostics_has_grid_layout(self, diagnostics_html: str) -> None:
        """diagnostics.html must use grid layout for cards."""
        assert ".grid" in diagnostics_html


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Test integration between HTML pages and shared resources."""

    def test_shared_css_referenced_consistently(self, dashboard_html: str, debug_html: str, diagnostics_html: str) -> None:
        """All HTML pages must reference shared.css with same path."""
        shared_css_ref = "static/shared.css"
        for html_content in [dashboard_html, debug_html, diagnostics_html]:
            assert shared_css_ref in html_content, "shared.css reference not found"

    def test_shared_js_referenced_consistently(self, dashboard_html: str, debug_html: str, diagnostics_html: str) -> None:
        """All HTML pages must reference shared.js with same path."""
        shared_js_ref = "static/shared.js"
        for html_content in [dashboard_html, debug_html, diagnostics_html]:
            assert shared_js_ref in html_content, "shared.js reference not found"

    def test_html_pages_use_css_variables(self, dashboard_html: str, debug_html: str, diagnostics_html: str) -> None:
        """HTML pages must use CSS variables for styling."""
        for html_content in [dashboard_html, debug_html, diagnostics_html]:
            # Check for use of CSS variables (var(--...))
            assert "var(--" in html_content, "CSS variables not used in page"

    def test_websocket_initialization_in_pages(self, dashboard_html: str, debug_html: str, diagnostics_html: str) -> None:
        """Pages must initialize WebSocket for live updates."""
        for html_content in [dashboard_html, debug_html, diagnostics_html]:
            # Pages should call initWebSocket function
            assert "initWebSocket" in html_content, "WebSocket initialization not found"

    def test_theme_toggle_initialization_in_pages(self, dashboard_html: str, debug_html: str, diagnostics_html: str) -> None:
        """Pages must initialize theme toggle."""
        for html_content in [dashboard_html, debug_html, diagnostics_html]:
            # Pages should call initThemeToggle function
            assert "initThemeToggle" in html_content, "Theme toggle initialization not found"

    def test_no_duplicate_theme_initialization(self, shared_js: str, dashboard_html: str) -> None:
        """Theme initialization should be in shared.js, not duplicated in HTML."""
        # shared.js should have theme init
        assert "function initTheme" in shared_js
        # HTML pages should not duplicate it
        assert "localStorage.getItem('s2m-theme')" not in dashboard_html


# ============================================================================
# Accessibility and Standards Tests
# ============================================================================


class TestAccessibilityAndStandards:
    """Test for web accessibility and standards compliance."""

    def test_html_pages_have_lang_attribute(self, dashboard_html: str, debug_html: str, diagnostics_html: str) -> None:
        """HTML pages must have lang attribute on html element."""
        for html_content in [dashboard_html, debug_html, diagnostics_html]:
            assert "lang=" in html_content

    def test_html_pages_have_content_type_meta(self, dashboard_html: str, debug_html: str, diagnostics_html: str) -> None:
        """HTML pages must specify charset."""
        for html_content in [dashboard_html, debug_html, diagnostics_html]:
            assert "charset" in html_content.lower()

    def test_html_pages_have_title(self, dashboard_html: str, debug_html: str, diagnostics_html: str) -> None:
        """HTML pages must have title element."""
        for html_content in [dashboard_html, debug_html, diagnostics_html]:
            assert "<title>" in html_content
            assert "</title>" in html_content

    def test_buttons_have_text_or_aria_label(self, dashboard_html: str, debug_html: str, diagnostics_html: str) -> None:
        """Interactive elements should have accessible labels."""
        # This is a basic check - more detailed accessibility testing would require a11y library
        for html_content in [dashboard_html, debug_html, diagnostics_html]:
            # Should have either visible text or ARIA labels for interactive elements
            assert "button" not in html_content or "btn" in html_content or "aria" in html_content.lower()
