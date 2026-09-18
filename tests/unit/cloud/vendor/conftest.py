"""Compatibility helpers for the vendored upstream test suite."""

import aiohttp
import aioresponses.core
from types import SimpleNamespace


class _CompatibleClientResponse(aiohttp.ClientResponse):
    """Bridge aioresponses to aiohttp 3.14's new stream_writer argument."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("stream_writer", SimpleNamespace(output_size=0))
        super().__init__(*args, **kwargs)


aioresponses.core.ClientResponse = _CompatibleClientResponse
