from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional
from urllib.parse import urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup

from ..core.report import ReconReport
from .state import CrawlerRuntimeState
from .targeting import TargetFilter


@dataclass(slots=True)
class LinkCollector:
    """Normalizes crawl links and surfaces URL-based SQLi targets."""

    report: ReconReport
    state: CrawlerRuntimeState
    target_filter: TargetFilter

    def update_context(self, *, report: ReconReport, state: CrawlerRuntimeState) -> None:
        self.report = report
        self.state = state

    def record_url(self, url: str) -> None:
        if "?" in url and "=" in url and self.target_filter.is_allowed(url):
            self.report.sqli_targets.add(url)

    def collect_from_page(self, page: Any, current_url: str) -> List[str]:
        """Collect anchor and router-link URLs from a Playwright page."""

        new_links: List[str] = []

        for anchor in self._safe_locator_list(page, "a"):
            href = self._safe_attribute(anchor, "href") or self._safe_attribute(anchor, "routerlink")
            normalized = self.normalize_link(current_url, href)
            if not normalized:
                continue
            self.record_url(normalized)
            if normalized not in self.state.seen_urls:
                self.state.seen_urls.add(normalized)
                self.report.discovered_urls.add(normalized)
                new_links.append(normalized)

        for element in self._safe_locator_list(page, "[routerlink]"):
            href = self._safe_attribute(element, "routerlink")
            normalized = self.normalize_link(current_url, href)
            if not normalized:
                continue
            if normalized not in self.state.seen_urls:
                self.state.seen_urls.add(normalized)
                self.report.discovered_urls.add(normalized)
                new_links.append(normalized)

        return new_links

    def gather_from_soup(self, soup: BeautifulSoup, current_url: str) -> List[str]:
        new_links: List[str] = []
        for anchor in soup.find_all("a"):
            href = anchor.get("href") or anchor.get("routerlink")
            normalized = self.normalize_link(current_url, href)
            if not normalized:
                continue
            self.record_url(normalized)
            if normalized not in self.state.seen_urls:
                self.state.seen_urls.add(normalized)
                self.report.discovered_urls.add(normalized)
                new_links.append(normalized)
        return new_links

    def normalize_link(self, base_url: str, href: Optional[str]) -> Optional[str]:
        if not href:
            return None

        # Para SPAs, usar lógica especial para fragmentos e caminhos absolutos
        if href.startswith("#/"):
            # Usar URL base sem fragmentos para SPAs
            parsed = urlparse(base_url)
            # Pegar a URL raiz e adicionar o fragmento manualmente
            root_url = f"{parsed.scheme}://{parsed.netloc}/"
            joined = root_url + href
        elif href.startswith("/"):
            # Para caminhos absolutos, usar URL raiz
            parsed = urlparse(base_url)
            root_url = f"{parsed.scheme}://{parsed.netloc}"
            joined = urljoin(root_url, href)
        else:
            joined = urljoin(base_url, href)
            
        if not self.target_filter.is_allowed(joined):
            return None

        parsed = urlparse(joined)
        keep_fragment = bool(parsed.fragment and parsed.fragment.startswith("/"))
        sanitized = parsed if keep_fragment else parsed._replace(fragment="")
        return urlunparse(sanitized)

    @staticmethod
    def _safe_locator_list(locator_owner: Any, selector: str) -> list[Any]:
        try:
            locator = locator_owner.locator(selector)
            return locator.all()
        except Exception:
            return []

    @staticmethod
    def _safe_attribute(element: Any, name: str) -> Optional[str]:
        try:
            return element.get_attribute(name)
        except Exception:
            return None
