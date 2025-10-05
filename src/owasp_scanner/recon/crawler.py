"""High level crawler that populates targets for subsequent scanners."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup
from playwright.sync_api import Page, Request, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from ..core.config import ScannerConfig
from ..core.models import FieldInfo
from ..core.report import ReconReport
from .cookie_manager import CookieManager
from .directory_enum import DirectoryEnumerationError, run_ffuf
from .forms import FormCollector
from .link_collector import LinkCollector
from .state import CrawlerRuntimeState
from .targeting import TargetFilter

logger = logging.getLogger(__name__)

AUTO_CLICK_SELECTORS = (
    'a[href^="#/"]',
    '[routerlink]:not(a)',
    'button[routerlink]',
    'button[onclick*="location" i]',
    '[role="link"]',
)


@dataclass
class Spider:
    """Collects URLs, forms and cookies from the target application."""

    config: ScannerConfig
    report: ReconReport = field(default_factory=ReconReport)

    def __post_init__(self) -> None:
        self.report.seed_url = self.config.target_url
        parsed = urlparse(self.config.target_url)
        target_host = parsed.netloc.lower()
        target_hostname = (parsed.hostname or "").lower()

        self._target_filter = TargetFilter(
            target_host=target_host,
            target_hostname=target_hostname,
        )
        self._cookie_manager = CookieManager(
            self.config, self._target_filter.filter_cookies
        )
        self._state = CrawlerRuntimeState()
        self._form_collector = FormCollector(
            report=self.report,
            state=self._state,
            is_allowed_url=self._target_filter.is_allowed,
        )
        self._link_collector = LinkCollector(
            report=self.report,
            state=self._state,
            target_filter=self._target_filter,
        )

    @property
    def runtime_state(self) -> CrawlerRuntimeState:
        """Return the current mutable runtime state for observability tools."""

        return self._state

    # ------------------------------------------------------------------
    # Public helpers (kept for unit tests)
    # ------------------------------------------------------------------
    def _build_field_info_from_values(
        self,
        *,
        name: Optional[str],
        element_id: Optional[str],
        aria: Optional[str],
        placeholder: Optional[str],
        data_testid: Optional[str],
        field_type: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> Optional[FieldInfo]:
        return self._form_collector.build_field_info_from_values(
            name=name,
            element_id=element_id,
            aria=aria,
            placeholder=placeholder,
            data_testid=data_testid,
            field_type=field_type,
            tag=tag,
        )

    # ------------------------------------------------------------------
    # Core workflow
    # ------------------------------------------------------------------
    def run(self) -> ReconReport:
        self._reset_runtime_state()
        self._to_visit: set[str] = set()
        self._queue_url(self.config.target_url)

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=self.config.headless)
            context = browser.new_context()
            page = context.new_page()
            page.on("request", self._capture_request)

            try:
                self._cookie_manager.bootstrap(
                    page,
                    target_url=self.config.target_url,
                    report=self.report,
                    state=self._state,
                )
            except Exception:
                logger.debug(
                    "Cookie bootstrap failed; continuing without session context",
                    exc_info=True,
                )

            ffuf_ran = False

            try:
                while self._to_visit or not ffuf_ran:
                    while self._to_visit:
                        current_url = self._to_visit.pop()
                        if current_url in self._state.visited_urls:
                            continue
                        self._navigate_and_collect(page, current_url)

                    if ffuf_ran:
                        break

                    self._enumerate_directories()
                    ffuf_ran = True
            finally:
                browser.close()

        return self.report

    # ------------------------------------------------------------------
    # Runtime setup helpers
    # ------------------------------------------------------------------
    def _reset_runtime_state(self) -> None:
        self._state = CrawlerRuntimeState()
        initial_cookies = self._target_filter.filter_cookies(self.report.cookies or [])
        self._state.initial_cookies = list(initial_cookies)
        self._cookie_manager.initial_cookies = list(initial_cookies)
        self._form_collector.update_context(report=self.report, state=self._state)
        self._link_collector.update_context(report=self.report, state=self._state)

    def _queue_url(self, url: str) -> None:
        if not self._is_allowed_url(url):
            return
        if url in self._state.visited_urls:
            return
        if url not in self._state.seen_urls:
            self._state.seen_urls.add(url)
        self._to_visit.add(url)
        self.report.discovered_urls.add(url)

    def _is_allowed_url(self, url: str) -> bool:
        return self._target_filter.is_allowed(url)

    # ------------------------------------------------------------------
    # Crawling primitives
    # ------------------------------------------------------------------
    def _navigate_and_collect(self, page: Page, url: str) -> None:
        try:
            page.goto(url, timeout=8000)
        except PlaywrightTimeoutError:
            return
        except Exception:
            return

        self._wait_settled(page)
        self._state.visited_urls.add(url)
        self._state.visited_count += 1
        self._collect_page(page, auto_click=True)

    def _collect_page(self, page: Page, *, auto_click: bool) -> None:
        current_url = page.url
        if self._is_allowed_url(current_url):
            self.report.discovered_urls.add(current_url)
            self._state.seen_urls.add(current_url)
            self._link_collector.record_url(current_url)

        self._form_collector.collect_from_page(page, current_url)
        for url in self._link_collector.collect_from_page(page, current_url):
            self._queue_url(url)

        html = self._read_page_html(page)
        if html:
            soup = BeautifulSoup(html, "html.parser")
            self._form_collector.collect_from_soup(soup, current_url)
            for url in self._link_collector.gather_from_soup(soup, current_url):
                self._queue_url(url)

        self._cookie_manager.refresh_from_page(
            page, report=self.report, state=self._state
        )

        if auto_click:
            self._auto_click_navigations(page)

    def _auto_click_navigations(self, page: Page) -> None:
        for selector in AUTO_CLICK_SELECTORS:
            for element in self._safe_locator_list(page, selector):
                candidate = (
                    self._safe_attribute(element, "href")
                    or self._safe_attribute(element, "routerlink")
                    or self._safe_attribute(element, "onclick")
                )

                normalized = self._normalize_candidate(page.url, candidate)
                if not normalized:
                    continue
                if normalized in self._state.clicked_router_links:
                    continue

                self._state.clicked_router_links.add(normalized)

                try:
                    element.click(timeout=500)
                    try:
                        page.wait_for_load_state("networkidle", timeout=1500)
                    except Exception:
                        page.wait_for_timeout(150)
                except Exception:
                    continue

                self._collect_page(page, auto_click=False)

    def _enumerate_directories(self) -> None:
        try:
            discovered = run_ffuf(
                self.config.target_url,
                self.report.cookies,
                verbose=self.config.ffuf_verbose,
            )
        except DirectoryEnumerationError:
            return

        for url in discovered:
            if not self._is_allowed_url(url):
                continue
            self.report.access_targets.add(url)
            self._state.ffuf_urls.add(url)
            self._queue_url(url)

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    def _capture_request(self, request: Request) -> None:
        try:
            parsed = urlparse(request.url)
            if not parsed.netloc or parsed.netloc.lower() != self._target_filter.target_host:
                return
            if request.method.upper() != "GET" or not parsed.query:
                return

            params = parse_qsl(parsed.query, keep_blank_values=True)
            if not params:
                return

            mutated = [(name, "FUZZ") for name, _ in params]
            normalized_query = urlencode(mutated, doseq=True)
            target_url = urlunparse(parsed._replace(query=normalized_query))
            self.report.sqli_targets.add(target_url)
        except Exception:
            return

    @staticmethod
    def _wait_settled(page: Page) -> None:
        try:
            page.wait_for_load_state("networkidle", timeout=3000)
        except Exception:
            try:
                page.wait_for_load_state("domcontentloaded", timeout=1500)
            except Exception:
                page.wait_for_timeout(300)

    @staticmethod
    def _read_page_html(page: Page) -> str:
        try:
            return page.content()
        except Exception:
            return ""

    def _normalize_candidate(self, base_url: str, candidate: Optional[str]) -> Optional[str]:
        if not candidate:
            return None

        value = candidate
        if value.startswith("#"):
            value = value[1:]
        if value.startswith("/"):
            value = urljoin(self.config.target_url, value)

        return self._link_collector.normalize(base_url, value)

    @staticmethod
    def _safe_locator_list(locator_owner: Page, selector: str) -> list:
        try:
            return locator_owner.locator(selector).all()
        except Exception:
            return []

    @staticmethod
    def _safe_attribute(element, name: str) -> Optional[str]:
        try:
            return element.get_attribute(name)
        except Exception:
            return None
