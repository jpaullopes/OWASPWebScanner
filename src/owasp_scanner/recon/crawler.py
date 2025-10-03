"""High level crawler that populates targets for subsequent scanners."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Sequence, Set, Tuple
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import scrapy
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from scrapy.crawler import CrawlerProcess
from scrapy.http import Response
from scrapy.utils.reactor import install_reactor
from twisted.internet.error import ReactorAlreadyInstalledError

from ..auth.login import login_with_credentials, login_juice_shop_demo
from ..core.config import ScannerConfig
from ..core.models import FieldAttributes, FieldInfo
from ..core.report import ReconReport
from .directory_enum import DirectoryEnumerationError, run_ffuf


IGNORED_INPUT_TYPES = {"hidden", "submit", "button", "reset", "image"}


@dataclass
class Spider:
    """Collects URLs, forms and cookies from the target application."""

    config: ScannerConfig
    report: ReconReport = field(default_factory=ReconReport)

    def __post_init__(self) -> None:
        parsed = urlparse(self.config.target_url)
        self._target_host = parsed.netloc
        self._reset_runtime_state(preserve_report=True)

    def _reset_runtime_state(self, *, preserve_report: bool = False) -> None:
        if not preserve_report:
            self.report = ReconReport()
        self._xss_seen = set()
        self._seen_urls = set()
        self._initial_cookies = []
        self._ffuf_urls = set()

    # ------------------------------------------------------------------
    # Session preparation
    # ------------------------------------------------------------------
    def _prepare_initial_cookies(self) -> None:
        """Bootstrap cookies using the existing Playwright helpers."""

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=self.config.headless)
                context = browser.new_context()
                page = context.new_page()
                domain = urlparse(self.config.target_url).hostname

                cookies: Optional[List[dict]] = None

                if self.config.session_cookie and domain:
                    name, _, value = self.config.session_cookie.partition("=")
                    if name and value:
                        context.add_cookies(
                            [
                                {
                                    "name": name.strip(),
                                    "value": value.strip(),
                                    "domain": domain,
                                    "path": "/",
                                }
                            ]
                        )
                        page.goto(self.config.target_url, timeout=10000)
                        cookies = context.cookies()
                elif self.config.auth_email and self.config.auth_password:
                    cookies = login_with_credentials(
                        page,
                        self.config.login_url,
                        self.config.auth_email,
                        self.config.auth_password,
                    )
                else:
                    cookies = login_juice_shop_demo(page, self.config.target_url)

                if cookies:
                    self._initial_cookies = list(cookies)
                    self.report.cookies = list(cookies)

                browser.close()
        except Exception:
            # Fallback gracefully when Playwright login is not available.
            self._initial_cookies = self.report.cookies or []

    def _maybe_run_ffuf(self) -> None:
        try:
            discovered = run_ffuf(
                self.config.target_url,
                self.report.cookies,
                verbose=self.config.ffuf_verbose,
            )
            self.report.access_targets.update(discovered)
            self._ffuf_urls = set(discovered)
        except DirectoryEnumerationError:
            self._ffuf_urls = set()

    # ------------------------------------------------------------------
    # Helper builders reused by unit tests
    # ------------------------------------------------------------------
    def _register_field_identifier(self, url: str, field_info: FieldInfo) -> None:
        if not field_info:
            return
        self._add_xss_form(url, [field_info])
        self._register_sqli_candidates(url, [field_info])

    def _identifier_from_attributes(
        self,
        *,
        name: Optional[str],
        element_id: Optional[str],
        aria: Optional[str],
        placeholder: Optional[str],
        data_testid: Optional[str],
    ) -> Optional[str]:
        if name:
            return name

        priority_attributes = (
            (data_testid, "data-testid::"),
            (placeholder, "placeholder::"),
            (aria, "aria::"),
        )

        for value, prefix in priority_attributes:
            if value:
                return f"{prefix}{value}"

        if element_id:
            return f"id::{element_id}"

        return None

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
        identifier = self._identifier_from_attributes(
            name=name,
            element_id=element_id,
            aria=aria,
            placeholder=placeholder,
            data_testid=data_testid,
        )
        if not identifier:
            return None

        attributes: FieldAttributes = {}
        if name is not None:
            attributes["name"] = name
        if element_id is not None:
            attributes["id"] = element_id
        if aria is not None:
            attributes["aria_label"] = aria
        if placeholder is not None:
            attributes["placeholder"] = placeholder
        if data_testid is not None:
            attributes["data_testid"] = data_testid
        if field_type:
            attributes["type"] = field_type.lower()
        if tag:
            attributes["tag"] = tag.lower()

        return {"identifier": identifier, "attributes": attributes}

    def _add_xss_form(self, url: str, fields: Iterable[FieldInfo]) -> None:
        unique_fields: list[FieldInfo] = []
        identifiers_order: list[str] = []
        seen_identifiers: set[str] = set()

        for field in fields:
            identifier = field.get("identifier")
            if not identifier or identifier in seen_identifiers:
                continue
            unique_fields.append(field)
            identifiers_order.append(identifier)
            seen_identifiers.add(identifier)

        if not unique_fields:
            return

        key = (url, tuple(identifiers_order))
        if key in self._xss_seen:
            return
        self._xss_seen.add(key)
        self.report.xss_forms.append({"url_de_envio": url, "campos": unique_fields})

    def _derive_param_names(self, fields: Sequence[FieldInfo]) -> Tuple[str, ...]:
        ordered: dict[str, None] = {}
        for field in fields:
            attributes = field.get("attributes", {})
            name = attributes.get("name")
            if name:
                ordered.setdefault(name, None)
        return tuple(ordered.keys())

    def _register_sqli_candidates(self, submit_url: str, fields: Sequence[FieldInfo]) -> None:
        param_names = self._derive_param_names(fields)
        if not param_names:
            return
        base_url = submit_url.split("#", 1)[0]
        join_char = "&" if "?" in base_url else "?"
        query = "&".join(f"{name}=FUZZ" for name in param_names)
        self.report.sqli_targets.add(f"{base_url}{join_char}{query}")

    # ------------------------------------------------------------------
    # HTML parsing utilities
    # ------------------------------------------------------------------
    def _normalize_link(self, base_url: str, href: str) -> Optional[str]:
        if not href:
            return None
        joined = urljoin(base_url, href)
        parsed = urlparse(joined)
        if parsed.netloc != self._target_host:
            return None
        sanitized = parsed._replace(fragment="")
        return urlunparse(sanitized)

    def _record_link_targets(self, url: str) -> None:
        if "?" in url and "=" in url:
            self.report.sqli_targets.add(url)

    def _extract_forms_from_soup(self, soup: BeautifulSoup, base_url: str) -> None:
        for form in soup.find_all("form"):
            action = form.get("action") or base_url
            fields: List[FieldInfo] = []

            for element in form.find_all(["input", "textarea", "select"]):
                tag_name = element.name.lower() if element.name else None
                input_type = (element.get("type") or "").lower()

                if tag_name == "input" and input_type in IGNORED_INPUT_TYPES:
                    continue

                field_info = self._build_field_info_from_values(
                    name=element.get("name"),
                    element_id=element.get("id"),
                    aria=element.get("aria-label"),
                    placeholder=element.get("placeholder"),
                    data_testid=element.get("data-testid"),
                    field_type=input_type,
                    tag=tag_name,
                )

                if field_info:
                    fields.append(field_info)

            if not fields:
                continue

            submit_url = urljoin(base_url, action)
            self._add_xss_form(submit_url, fields)
            self._register_sqli_candidates(submit_url, fields)

    def _extract_loose_inputs_from_soup(self, soup: BeautifulSoup, page_url: str) -> None:
        for element in soup.find_all(["input", "textarea", "select"]):
            if element.find_parent("form"):
                continue

            tag_name = element.name.lower() if element.name else None
            input_type = (element.get("type") or "").lower()
            if tag_name == "input" and input_type in IGNORED_INPUT_TYPES:
                continue

            field_info = self._build_field_info_from_values(
                name=element.get("name"),
                element_id=element.get("id"),
                aria=element.get("aria-label"),
                placeholder=element.get("placeholder"),
                data_testid=element.get("data-testid"),
                field_type=input_type,
                tag=tag_name,
            )

            if field_info:
                self._register_field_identifier(page_url, field_info)

    def _capture_request(self, request) -> None:
        try:
            parsed = urlparse(request.url)
            if not parsed.netloc or parsed.netloc != self._target_host:
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

    async def _page_init_callback(self, page, request) -> None:
        if self._initial_cookies:
            try:
                await page.context.add_cookies(self._initial_cookies)
            except Exception:
                pass
        page.on("request", self._capture_request)

    async def _handle_response(self, response: Response) -> List[str]:
        url = response.url
        self._seen_urls.add(url)
        self._record_link_targets(url)

        html = response.text or ""
        soup = BeautifulSoup(html, "html.parser")
        self._extract_forms_from_soup(soup, url)
        self._extract_loose_inputs_from_soup(soup, url)
        new_links: List[str] = []
        for anchor in soup.find_all("a"):
            href = anchor.get("href")
            normalized = self._normalize_link(url, href)
            if not normalized:
                continue
            self._record_link_targets(normalized)
            if normalized not in self._seen_urls:
                self._seen_urls.add(normalized)
                new_links.append(normalized)

        page = response.meta.get("playwright_page")
        if page:
            try:
                cookies = await page.context.cookies()
                if cookies:
                    self.report.cookies = cookies
            except Exception:
                pass

        return new_links

    # ------------------------------------------------------------------
    # Orchestration
    # ------------------------------------------------------------------
    def _build_playwright_meta(self) -> dict:
        return {
            "playwright": True,
            "playwright_include_page": True,
            "playwright_page_init_callback": self._page_init_callback,
        }

    def _build_start_urls(self) -> List[str]:
        ordered = [self.config.target_url]
        for url in sorted(self._ffuf_urls):
            if url not in ordered:
                ordered.append(url)
        return ordered

    def run(self, *, preserve_report: bool = False) -> ReconReport:
        self._reset_runtime_state(preserve_report=preserve_report)

        self._prepare_initial_cookies()
        self._maybe_run_ffuf()

        start_urls = self._build_start_urls()
        self._seen_urls.update(start_urls)

        try:
            install_reactor("twisted.internet.asyncioreactor.AsyncioSelectorReactor")
        except ReactorAlreadyInstalledError:
            pass

        settings = {
            "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
            "DOWNLOAD_HANDLERS": {
                "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
                "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            },
            "PLAYWRIGHT_BROWSER_TYPE": "chromium",
            "PLAYWRIGHT_LAUNCH_OPTIONS": {"headless": self.config.headless},
            "LOG_ENABLED": False,
            "ROBOTSTXT_OBEY": False,
            "USER_AGENT": "OWASPWebScanner/1.0",
        }

        process = CrawlerProcess(settings=settings)
        process.crawl(_ScrapyReconSpider, state=self, start_urls=start_urls)
        process.start()

        return self.report


class _ScrapyReconSpider(scrapy.Spider):
    name = "owasp_recon"

    def __init__(self, state: Spider, start_urls: Sequence[str], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state = state
        self.start_urls = list(start_urls)

    def start_requests(self):
        for url in self.start_urls:
            meta = dict(self.state._build_playwright_meta())
            yield scrapy.Request(url, callback=self.parse, meta=meta, dont_filter=True)

    async def parse(self, response: Response):
        new_links = await self.state._handle_response(response)

        page = response.meta.get("playwright_page")
        if page:
            try:
                await page.close()
            except Exception:
                pass

        for url in new_links:
            meta = dict(self.state._build_playwright_meta())
            yield scrapy.Request(url, callback=self.parse, meta=meta, dont_filter=True)
