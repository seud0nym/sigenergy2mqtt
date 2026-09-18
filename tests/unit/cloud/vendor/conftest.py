"""Compatibility helpers for the vendored upstream test suite."""

from inspect import signature
from types import SimpleNamespace

import aiohttp
import aioresponses.core


if "stream_writer" in signature(aiohttp.ClientResponse).parameters:
    # Remove when https://github.com/pnuckowski/aioresponses/pull/288 is released.
    class _CompatibleClientResponse(aiohttp.ClientResponse):
        """Supply the stream writer required by aiohttp 3.14 and later."""

        def __init__(self, *args, **kwargs):
            kwargs.setdefault("stream_writer", SimpleNamespace(output_size=0))
            super().__init__(*args, **kwargs)

    aioresponses.core.ClientResponse = _CompatibleClientResponse
