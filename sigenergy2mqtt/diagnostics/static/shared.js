/* Shared utilities for all diagnostic pages: theme init, theme toggle,
   WebSocket reconnect loop, and fetch-and-flash helper. */

/* Initialize theme from localStorage or system preference before rendering
   (run synchronously in head <script> to avoid flash). */
(function initTheme() {
  try {
    const saved = localStorage.getItem('s2m-theme');
    const theme = saved || (window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
    if (theme === 'light') document.documentElement.setAttribute('data-theme', 'light');
  } catch (e) { /* localStorage unavailable — default to dark */ }
})();

/* Set up theme toggle button: call once the DOM is ready.
   Pass the themeToggleElement (the button with id="themeToggle"). */
function initThemeToggle(themeToggleElement) {
  if (!themeToggleElement) return;
  themeToggleElement.addEventListener('click', () => {
    const isLight = document.documentElement.getAttribute('data-theme') === 'light';
    const next = isLight ? 'dark' : 'light';
    if (next === 'light') {
      document.documentElement.setAttribute('data-theme', 'light');
    } else {
      document.documentElement.removeAttribute('data-theme');
    }
    try { localStorage.setItem('s2m-theme', next); } catch (e) { /* ignore */ }
  });
}

/* Initialize WebSocket connection with automatic reconnect and exponential backoff.
   - wsUrl: full URL to the WebSocket endpoint (e.g. "ws://host/diagnostics/ws")
   - onMessage: callback(parsedJSON) called when data arrives
   - setConnState: callback(state) to update the connection pill ("live", "down", "connecting", etc.)
   Returns an object with { close() } to shut down the connection. */
function initWebSocket(wsUrl, onMessage, setConnState) {
  let socket = null;
  let retryDelay = 1000;
  let closed = false;
  let firstMessage = false;

  function connect() {
    if (closed) return;
    try {
      socket = new WebSocket(wsUrl);
    } catch (e) {
      // No WebSocket support or invalid URL — don't retry
      return;
    }

    firstMessage = false;
    socket.onopen = () => {
      // Don't mark as 'live' yet — wait for first real data to avoid showing
      // demo values with a 'Live' indicator.
    };
    socket.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data);
        onMessage(data);
        // On first successfully processed message, mark connection as live and reset backoff
        if (!firstMessage) {
          firstMessage = true;
          setConnState('live');
          retryDelay = 1000;
        }
      } catch (e) {
        console.error('Bad WS payload', e);
      }
    };
    socket.onclose = () => {
      if (!closed) {
        setConnState('down');
        setTimeout(connect, retryDelay);
        retryDelay = Math.min(retryDelay * 1.5, 15000);
      }
    };
    socket.onerror = () => {
      socket.close();
    };
  }

  connect();

  return {
    close: () => {
      closed = true;
      if (socket) socket.close();
    }
  };
}

/* POST JSON to a URL and flash an element on success/error.
   - url: endpoint URL (relative or absolute)
   - body: object to POST as JSON
   - flashElement: DOM element to flash with "flash-ok" or "flash-err" class
   - onRevert: optional callback(prevValue) if the request fails (for checkbox revert, etc.)
   Returns a Promise resolving to { ok: boolean, revision?: number }.
   The result object contains whatever the server JSON response includes. */
async function postJSON(url, body, flashElement, onRevert) {
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    const result = await res.json();

    if (res.ok && result.ok) {
      // Flash green
      flashElement.classList.remove('flash-ok', 'flash-err');
      void flashElement.offsetWidth; // Trigger reflow to reset animation
      flashElement.classList.add('flash-ok');
      return { ok: true, revision: result.revision };
    } else {
      throw new Error(result.error || 'Update failed');
    }
  } catch (err) {
    console.error(`POST ${url} failed:`, err);
    // Flash red
    flashElement.classList.remove('flash-ok', 'flash-err');
    void flashElement.offsetWidth; // Trigger reflow to reset animation
    flashElement.classList.add('flash-err');
    if (onRevert) onRevert();
    return { ok: false };
  }
}
