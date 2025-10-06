from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence
from urllib.parse import urlparse

DEFAULT_EXCLUDED_HOST_KEYWORDS = frozenset({"github"})


@dataclass(slots=True)
class TargetFilter:
    """Encapsulates host allow-listing and cookie filtering rules."""

    target_host: str
    target_hostname: str
    excluded_keywords: frozenset[str] = field(
        default_factory=lambda: DEFAULT_EXCLUDED_HOST_KEYWORDS
    )

    def is_allowed(self, url: str) -> bool:
        try:
            parsed_url = urlparse(url)
        except Exception:
            return False

        host = parsed_url.netloc.lower()
        hostname = (parsed_url.hostname or "").lower()

        if parsed_url.scheme and parsed_url.scheme not in {"http", "https", ""}:
            return False

        if host:
            if host != self.target_host and (
                not hostname or hostname != self.target_hostname
            ):
                return False
        elif hostname:
            if hostname != self.target_hostname:
                return False

        candidate = host or hostname
        #usando a abstração lá de baixo para evitar repetição
        if candidate and self._has_excluded_keyword(candidate):
            return False

        return True

    # mesma coisa
    def contains_excluded_keyword(self, value: str) -> bool:
        return self._has_excluded_keyword(value)

    # A modificação foi feita aqui
    def _has_excluded_keyword(self, value: str) -> bool:
        if not value:
            return False
        normalized = value.lower()
        return any(keyword in normalized for keyword in self.excluded_keywords)

    def filter_cookies(self, cookies: Sequence[dict]) -> list[dict]:
        if not cookies:
            return []

        allowed: list[dict] = []
        allowed_domains = {value for value in (self.target_host, self.target_hostname) if value}
        suffix = f".{self.target_hostname}" if self.target_hostname else None

        for cookie in cookies:
            domain = (cookie.get("domain") or "").lstrip(".").lower()
            if not domain:
                continue

            if domain in allowed_domains or (suffix and domain.endswith(suffix)):
                allowed.append(cookie)

        return allowed
