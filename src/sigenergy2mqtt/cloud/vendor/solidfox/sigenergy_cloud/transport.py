"""Internal HTTP transport for the Sigenergy Cloud app API."""

from __future__ import annotations

import json
from typing import Any

import aiohttp

from .auth import OAuthSession
from .errors import (
    SigenergyCloudAPIError,
    SigenergyCloudAuthError,
    SigenergyCloudRateLimitError,
)

_SUCCESS_CODES = {0, "0", None}
_AUTH_CODES = {401, 403, "401", "403"}


def _error_message(payload: Any, fallback: str) -> str:
    if not isinstance(payload, dict):
        return fallback
    return (
        payload.get("msg")
        or payload.get("message")
        or payload.get("error_description")
        or payload.get("error")
        or fallback
    )


class CloudTransport:
    """Authenticated request helper shared by the high-level client."""

    def __init__(self, base_url: str, auth: OAuthSession) -> None:
        self._base_url = base_url
        self._auth = auth

    async def envelope(
        self,
        session: aiohttp.ClientSession,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute a request and return Sigenergy's full JSON envelope."""
        await self._auth.ensure_token(session, self._base_url)
        url = f"{self._base_url}{path.lstrip('/')}"
        async with session.request(
            method, url, headers=self._auth.headers, **kwargs
        ) as response:
            return await self._parse_response(response)

    async def data(
        self,
        session: aiohttp.ClientSession,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> Any:
        """Execute a request and return only the envelope's data member."""
        return (await self.envelope(session, method, path, **kwargs)).get("data")

    async def _parse_response(self, response: aiohttp.ClientResponse) -> dict[str, Any]:
        body = await response.text()
        try:
            payload: Any = json.loads(body) if body else {}
        except json.JSONDecodeError as exc:
            raise SigenergyCloudAPIError(
                f"Invalid JSON from Sigenergy Cloud: HTTP {response.status}",
                status_code=response.status,
                response_body=body,
            ) from exc

        if response.status == 401:
            raise SigenergyCloudAuthError(
                _error_message(payload, "Sigenergy Cloud authentication failed")
            )
        if response.status == 429:
            raise SigenergyCloudRateLimitError(
                _error_message(payload, "Sigenergy Cloud rate limit exceeded"),
                status_code=response.status,
                response_body=body,
            )
        if response.status >= 400:
            raise SigenergyCloudAPIError(
                _error_message(
                    payload, f"Sigenergy Cloud HTTP error {response.status}"
                ),
                status_code=response.status,
                response_body=body,
            )
        if not isinstance(payload, dict):
            raise SigenergyCloudAPIError(
                "Unexpected non-object response from Sigenergy Cloud",
                status_code=response.status,
                response_body=body,
            )

        code = payload.get("code")
        if code in _AUTH_CODES:
            raise SigenergyCloudAuthError(
                _error_message(payload, "Sigenergy Cloud authentication failed")
            )
        if code == 429 or code == "429":
            raise SigenergyCloudRateLimitError(
                _error_message(payload, "Sigenergy Cloud rate limit exceeded"),
                status_code=response.status,
                response_body=body,
            )
        if code not in _SUCCESS_CODES:
            raise SigenergyCloudAPIError(
                _error_message(payload, f"Sigenergy Cloud returned code {code}"),
                status_code=response.status,
                response_body=body,
            )
        return payload
