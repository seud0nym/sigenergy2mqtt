import asyncio
import logging
import os
import signal
import sys

from sigenergy2mqtt.config import ConfigurationError, active_config, initialize
from sigenergy2mqtt.config.auto_discovery import _interrupted as _  # noqa: F401 — ensure module is importable
from sigenergy2mqtt.main import async_main


def main():
    import sigenergy2mqtt.config.auto_discovery as auto_discovery

    def _early_exit(signum, frame):
        """Handle signals during initialization (before async_main signal handlers are registered)."""
        if auto_discovery._interrupted:
            # Second signal — force immediate exit (os._exit bypasses blocked threads)
            logging.warning(f"Signal {signum} received again — forcing exit")
            os._exit(130 if signum == signal.SIGINT else 143)
        logging.info(f"Signal {signum} received during initialization — interrupting auto-discovery")
        auto_discovery._interrupted = True

    signal.signal(signal.SIGINT, _early_exit)
    signal.signal(signal.SIGTERM, _early_exit)

    try:
        continuing = initialize()
        if not continuing:
            sys.exit(0)
    except ConfigurationError as e:
        logging.critical(f"Configuration error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logging.info("Initialization interrupted — exiting")
        sys.exit(130)

    asyncio.run(async_main(), debug=True if active_config.log_level == logging.DEBUG else False)


if __name__ == "__main__":
    main()
