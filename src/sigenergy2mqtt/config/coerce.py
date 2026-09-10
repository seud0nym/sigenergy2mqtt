"""
None-safe coercion helpers for environment variable strings.
All functions return None when the input is None, preserving the
"not set" sentinel so callers can skip absent env vars cleanly.
"""

from __future__ import annotations

from typing import Any


def _set(d: dict, key: str, val: Any) -> None:
    """Write to dict only if val is not None."""
    if val is not None:
        d[key] = val


def _bool(v: str | None) -> bool | None:
    if v is None:
        return None
    return v.strip().lower() in ("1", "true", "yes", "on", "y")


def _invert_bool(v: str | None) -> bool | None:
    """Parse boolean env var and invert it (for no-* flags stored as positive attributes)."""
    result = _bool(v)
    return None if result is None else not result


def _int(v: str | None) -> int | None:
    return int(v) if v is not None else None


def _float(v: str | None) -> float | None:
    return float(v) if v is not None else None


def _int_list(v: str | None) -> list[int] | None:
    """'1,2,3' → [1, 2, 3]"""
    if v is None:
        return None
    return [int(x.strip()) for x in v.split(",") if x.strip()]


def _str_list(v: str | None) -> list[str] | None:
    """'a,b,c' → ['a', 'b', 'c']"""
    if v is None:
        return None
    return [x.strip() for x in v.split(",") if x.strip()]
