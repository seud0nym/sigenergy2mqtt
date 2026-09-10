"""Diagnostics web UI, WebSocket feed, JSON export, and Docker health endpoint.

Public surface:
    diagnostics_registry  Register a provider: diagnostics_registry.register(name, collect_fn)
    diagnostics_server     The DiagnosticsServer instance; hosted by DiagnosticsService
    DiagnosticsService     Device wrapper — attach via ThreadConfig.add_device() in setup_services()
"""

from .registry import DiagnosticsProvider, diagnostics_registry
from .server import DiagnosticsServer, diagnostics_server
from .service import DiagnosticsService

__all__ = ["DiagnosticsProvider", "DiagnosticsServer", "DiagnosticsService", "diagnostics_registry", "diagnostics_server"]
