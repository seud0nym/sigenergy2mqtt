"""Entry point for the sigenergy2mqtt application.

Bootstraps configuration, installs early signal handlers for the
initialisation phase, then hands off to the async runtime.
"""

import asyncio
import logging
import os
import signal
import sys

import sigenergy2mqtt.config.auto_discovery as auto_discovery
from sigenergy2mqtt.config import ConfigurationError, active_config, initialize
from sigenergy2mqtt.main import async_main, validate_connections


def _make_early_signal_handler():
    """Return a signal handler for use during the synchronous initialisation phase.

    The handler covers two scenarios:

    * **First signal** — auto-discovery is still running.  Sets the shared
      ``auto_discovery._interrupted`` flag so that the discovery loop can
      exit cleanly, then returns to allow the normal shutdown path to
      complete.
    * **Second signal** — the process is not responding quickly enough.
      Calls :func:`os._exit` immediately, bypassing any blocked threads or
      cleanup code that might otherwise prevent termination.

    Exit codes follow Unix convention (128 + signal number):
    * ``130`` for SIGINT  (128 + 2)
    * ``143`` for SIGTERM (128 + 15)

    Note:
        Only :func:`os._exit` and flag mutation are used inside the handler
        itself.  Logging calls are intentionally kept outside the hot path
        where possible because neither the logging framework nor most libc
        functions are guaranteed async-signal-safe.  In CPython this is
        benign in practice, but callers should be aware of the limitation.

    Returns:
        A signal handler callable compatible with :func:`signal.signal`.
    """
    interrupted = False

    def _handler(signum, frame):
        nonlocal interrupted
        if interrupted:
            # Second signal — force immediate exit so blocked threads cannot
            # prevent shutdown.  os._exit is used deliberately here.
            os._exit(130 if signum == signal.SIGINT else 143)
        interrupted = True
        auto_discovery._interrupted = True  # signal the discovery loop to stop cleanly

    return _handler


def main():
    """Configure and run the application.

    Execution is split into two phases:

    1. **Synchronous initialisation** — :func:`~sigenergy2mqtt.config.initialize`
       loads and validates configuration (including optional auto-discovery of
       Sigenergy devices).  A lightweight signal handler is installed for this
       phase so that Ctrl-C or SIGTERM interrupts auto-discovery gracefully
       rather than raising an unhandled exception.

    2. **Async runtime** — :func:`asyncio.run` starts the event loop and
       delegates to :func:`~sigenergy2mqtt.main.async_main`, which installs
       its own, more capable signal handlers for the long-running phase.
       asyncio debug mode is enabled when the configured log level is DEBUG,
       which activates slow-callback detection and coroutine origin tracking
       (both useful during development but too noisy for production).

    Exit codes:
        * ``0``  — clean exit or ``--help`` / dry-run path.
        * ``1``  — configuration error.
        * ``130`` — interrupted by SIGINT during initialisation.
    """
    early_handler = _make_early_signal_handler()
    signal.signal(signal.SIGINT, early_handler)
    signal.signal(signal.SIGTERM, early_handler)

    try:
        continuing = initialize()
        if not continuing:
            sys.exit(0)

        if getattr(active_config, "validate_only_mode", None):
            # Restore default Ctrl-C behaviour for validation mode so a single
            # SIGINT raises KeyboardInterrupt during network checks.
            signal.signal(signal.SIGINT, signal.default_int_handler)
            logging.info("Configuration is valid; testing configured connection and authentication settings")
            logging.info("Validation configuration:\n%s", active_config)
            asyncio.run(validate_connections(show_credentials=getattr(active_config, "validate_show_credentials", False)))
            logging.info("Validation checks completed successfully")
            sys.exit(0)
    except ConfigurationError as e:
        logging.critical("Configuration error: %s", e)
        sys.exit(1)
    except KeyboardInterrupt:
        logging.info("Initialization interrupted — exiting")
        sys.exit(130)

    # Check if smartport is enabled
    for modbus in active_config.modbus:  # type: ignore
        if modbus.smartport.enabled:
            logging.warning("*****************************************************************************************************************************")
            logging.warning("* Third-Party PV generation support (smartport) is enabled but has been DEPRECATED and will be removed in a future release! *")
            logging.warning("*****************************************************************************************************************************")
            break

    # debug=True enables asyncio's slow-callback detector, ResourceWarning
    # emission, and coroutine origin tracking — valuable during development,
    # but adds overhead so it is gated on the DEBUG log level.
    asyncio.run(async_main(), debug=active_config.log_level == logging.DEBUG)  # pyrefly: ignore


if __name__ == "__main__":
    main()
