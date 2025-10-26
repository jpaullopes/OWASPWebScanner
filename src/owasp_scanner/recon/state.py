from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class CrawlerRuntimeState:
    """Mutable runtime bookkeeping for the hybrid crawler."""

    seen_urls: set[str] = field(default_factory=set)
    xss_seen: set[tuple[str, tuple[str, ...]]] = field(default_factory=set)
    ffuf_urls: set[str] = field(default_factory=set)
    initial_cookies: list[dict] = field(default_factory=list)
    fallback_used: bool = False
    visited_count: int = 0
    visited_urls: set[str] = field(default_factory=set)
    clicked_router_links: set[str] = field(default_factory=set)
