"""Regional Sigenergy Cloud API endpoints."""

from __future__ import annotations

REGION_BASE_URLS: dict[str, str] = {
    "aus": "https://api-aus.sigencloud.com/",
    "eu": "https://api-eu.sigencloud.com/",
    "cn": "https://api-cn.sigencloud.com/",
    "apac": "https://api-apac.sigencloud.com/",
    "us": "https://api-us.sigencloud.com/",
}


def base_url_for_region(region: str) -> str:
    """Return the API base URL for a Sigenergy Cloud region."""
    if region == "testing":
        # Import lazily to avoid a configuration-model import cycle.
        from sigenergy2mqtt.config import active_config

        testing_url = active_config.cloud.testing_url
        if testing_url:
            return testing_url
    try:
        return REGION_BASE_URLS[region]
    except KeyError as exc:
        supported = ", ".join(sorted(REGION_BASE_URLS))
        raise ValueError(
            f"Unsupported Sigenergy region {region!r}; use one of {supported}"
        ) from exc
