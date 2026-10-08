"""Typed exceptions raised by sigenergy-cloud."""

from __future__ import annotations


class SigenergyCloudError(Exception):
    """Base error for all sigenergy-cloud failures."""


class SigenergyCloudAuthError(SigenergyCloudError):
    """Authentication failed or the cloud rejected the current token."""


class SigenergyCloudTokenExpiredError(SigenergyCloudAuthError):
    """The refresh token no longer produced a valid access token."""


class SigenergyCloudAPIError(SigenergyCloudError):
    """The cloud API returned an unsuccessful response."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response_body: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class SigenergyCloudRateLimitError(SigenergyCloudAPIError):
    """The cloud API rate-limited the request."""
