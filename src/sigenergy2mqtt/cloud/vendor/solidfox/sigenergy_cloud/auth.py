"""Authentication primitives for the Sigenergy Cloud app API."""

from __future__ import annotations

import base64
import time
from dataclasses import dataclass
from typing import Any

import aiohttp
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

from .errors import SigenergyCloudAuthError, SigenergyCloudTokenExpiredError

_PASSWORD_AES_KEY = "sigensigensigenp"
_PASSWORD_AES_IV = "sigensigensigenp"
_OAUTH_CLIENT_ID = "sigen"
_OAUTH_CLIENT_SECRET = "sigen"
_TOKEN_REFRESH_MARGIN_SECONDS = 60


def encrypt_password(password: str) -> str:
    """Return the AES-CBC password encoding expected by Sigenergy Cloud."""
    cipher = AES.new(
        _PASSWORD_AES_KEY.encode("utf-8"),
        AES.MODE_CBC,
        _PASSWORD_AES_IV.encode("latin1"),
    )
    encrypted = cipher.encrypt(pad(password.encode("utf-8"), AES.block_size))
    return base64.b64encode(encrypted).decode("utf-8")


@dataclass(frozen=True, slots=True)
class TokenBundle:
    """OAuth tokens plus their local expiry deadline."""

    access_token: str
    refresh_token: str
    expires_at: float

    @classmethod
    def from_api(cls, payload: dict[str, Any]) -> "TokenBundle":
        """Create a token bundle from Sigenergy's OAuth response shape."""
        expires_in = int(payload["expires_in"])
        return cls(
            access_token=str(payload["access_token"]),
            refresh_token=str(payload["refresh_token"]),
            expires_at=time.time() + max(0, expires_in - _TOKEN_REFRESH_MARGIN_SECONDS),
        )

    @property
    def expired(self) -> bool:
        """Return true when the token should be refreshed before use."""
        return time.time() >= self.expires_at


class OAuthSession:
    """Small state holder for Sigenergy's password-grant OAuth flow."""

    def __init__(self) -> None:
        self._tokens: TokenBundle | None = None

    @property
    def headers(self) -> dict[str, str]:
        """Return JSON headers for authenticated cloud requests."""
        if self._tokens is None:
            raise SigenergyCloudAuthError("Sigenergy Cloud is not authenticated")
        return {
            "Authorization": f"Bearer {self._tokens.access_token}",
            "Content-Type": "application/json",
        }

    async def authenticate(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        username: str,
        encrypted_password: str,
    ) -> None:
        """Authenticate with username/password and store access tokens."""
        self._tokens = await self._request_token(
            session,
            base_url,
            {
                "username": username,
                "password": encrypted_password,
                "grant_type": "password",
            },
            SigenergyCloudAuthError,
        )

    async def ensure_token(self, session: aiohttp.ClientSession, base_url: str) -> None:
        """Refresh the token if needed."""
        if self._tokens is None:
            raise SigenergyCloudAuthError("Sigenergy Cloud is not authenticated")
        if not self._tokens.expired:
            return
        self._tokens = await self._request_token(
            session,
            base_url,
            {
                "grant_type": "refresh_token",
                "refresh_token": self._tokens.refresh_token,
            },
            SigenergyCloudTokenExpiredError,
        )

    async def _request_token(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        form: dict[str, str],
        error_type: type[SigenergyCloudAuthError],
    ) -> TokenBundle:
        url = f"{base_url}auth/oauth/token"
        async with session.post(
            url,
            data=form,
            auth=aiohttp.BasicAuth(_OAUTH_CLIENT_ID, _OAUTH_CLIENT_SECRET),
        ) as response:
            body = await response.text()
            if response.status != 200:
                raise error_type(
                    f"Sigenergy Cloud authentication failed: HTTP {response.status}; {body}"
                )
            payload = await response.json()

        token_payload = payload.get("data", payload)
        if not isinstance(token_payload, dict):
            raise error_type(f"Unexpected Sigenergy Cloud token response: {payload!r}")
        try:
            return TokenBundle.from_api(token_payload)
        except KeyError as exc:
            raise error_type(
                f"Incomplete Sigenergy Cloud token response: {payload!r}"
            ) from exc
