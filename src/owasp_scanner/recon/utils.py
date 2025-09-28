"""Helper utilities used by recon modules."""

from __future__ import annotations

from typing import Iterable, Optional


def build_cookie_header(cookies: Optional[Iterable[dict]]) -> str:
    if not cookies:
        return ""
    pieces = []
    for cookie in cookies:
        name = cookie.get("name")
        value = cookie.get("value")
        if name and value:
            pieces.append(f"{name}={value}")
    return "; ".join(pieces)
