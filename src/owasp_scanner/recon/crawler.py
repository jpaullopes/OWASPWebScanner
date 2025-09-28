"""High level crawler that populates targets for subsequent scanners."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional, Sequence, Set, Tuple
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup

from playwright.sync_api import Page, Request, TimeoutError as PlaywrightTimeoutError, sync_playwright

from ..auth.login import login_with_credentials, login_juice_shop_demo
from ..core.config import ScannerConfig
from ..core.report import ReconReport
from .directory_enum import run_ffuf, DirectoryEnumerationError


IGNORED_INPUT_TYPES = {"hidden", "submit", "button", "reset", "image"}


@dataclass
class Spider:
    """Collects URLs, forms and cookies from the target application."""

    config: ScannerConfig
    report: ReconReport = field(default_factory=ReconReport)

    def __post_init__(self) -> None:
        parsed = urlparse(self.config.target_url)
        self._target_host: str = parsed.netloc
        self._xss_seen: Set[Tuple[str, Tuple[str, ...]]] = set()

    def _record_cookies(self, page: Page) -> None:
        try:
            self.report.cookies = page.context.cookies()
        except Exception:
            self.report.cookies = []

    def _bootstrap_session(self, page: Page) -> None:
        domain = urlparse(self.config.target_url).hostname
        if self.config.session_cookie and domain:
            name, _, value = self.config.session_cookie.partition("=")
            page.context.add_cookies([
                {
                    "name": name.strip(),
                    "value": value.strip(),
                    "domain": domain,
                    "path": "/",
                }
            ])
            page.goto(self.config.target_url, timeout=10000)
            self._record_cookies(page)
            return

        if self.config.auth_email and self.config.auth_password:
            cookies = login_with_credentials(page, self.config.login_url, self.config.auth_email, self.config.auth_password)
            if cookies:
                self.report.cookies = cookies
                return

        cookies = login_juice_shop_demo(page, self.config.target_url)
        if cookies:
            self.report.cookies = cookies

    def _extract_links(self, page: Page, url: str) -> None:
        anchors = page.locator("a").all()
        for anchor in anchors:
            try:
                href = anchor.get_attribute("href")
                if not href:
                    continue
                full_url = urljoin(self.config.target_url, href)
                if urlparse(full_url).netloc != urlparse(self.config.target_url).netloc:
                    continue
                if "commit" in full_url or "github" in full_url:
                    continue
                if "?" in full_url and "=" in full_url:
                    self.report.sqli_targets.add(full_url)
                self._queue_url(full_url)
            except Exception:
                continue

    def _register_field_identifier(self, url: str, identifier: str) -> None:
        self._add_xss_form(url, [identifier])
        self._register_sqli_candidates(url, [identifier])

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

        for value, prefix in ((element_id, "id::"), (aria, "aria::"), (placeholder, "placeholder::")):
            if value:
                return f"{prefix}{value}"

        if data_testid:
            return f"data-testid::{data_testid}"

        return None

    def _identify_field(self, element) -> Optional[str]:
        try:
            name_attr = element.get_attribute("name")
            element_id = element.get_attribute("id")
            aria = element.get_attribute("aria-label")
            placeholder = element.get_attribute("placeholder")
            data_testid = element.get_attribute("data-testid")

            return self._identifier_from_attributes(
                name=name_attr,
                element_id=element_id,
                aria=aria,
                placeholder=placeholder,
                data_testid=data_testid,
            )
        except Exception:
            return None
        return None

    def _add_xss_form(self, url: str, fields: Iterable[str]) -> None:
        unique_fields = tuple(dict.fromkeys(f for f in fields if f))
        if not unique_fields:
            return
        key = (url, unique_fields)
        if key in self._xss_seen:
            return
        self._xss_seen.add(key)
        self.report.xss_forms.append({"url_de_envio": url, "campos": list(unique_fields)})

    def _derive_param_names(self, fields: Sequence[str]) -> Tuple[str, ...]:
        ordered: dict[str, None] = {}
        for field in fields:
            if not field:
                continue
            if "::" in field:
                continue
            ordered.setdefault(field, None)
        return tuple(ordered.keys())

    def _register_sqli_candidates(self, submit_url: str, fields: Sequence[str]) -> None:
        param_names = self._derive_param_names(fields)
        if not param_names:
            return
        base_url = submit_url.split("#", 1)[0]
        join_char = "&" if "?" in base_url else "?"
        query = "&".join(f"{name}=FUZZ" for name in param_names)
        self.report.sqli_targets.add(f"{base_url}{join_char}{query}")

    def _extract_forms(self, page: Page) -> None:
        forms = page.locator("form").all()
        for form in forms:
            try:
                action = form.get_attribute("action") or page.url
                method = (form.get_attribute("method") or "get").lower()

                inputs = form.locator("input, textarea, select").all()
                fields: list[str] = []
                query_param_names: list[str] = []

                for element in inputs:
                    name_attr = element.get_attribute("name")
                    if name_attr:
                        fields.append(name_attr)
                        query_param_names.append(name_attr)
                        continue

                    identifier = self._identify_field(element)
                    if identifier:
                        fields.append(identifier)

                if not fields:
                    continue

                submit_url = urljoin(self.config.target_url, action)
                self._add_xss_form(submit_url, fields)
                self._register_sqli_candidates(submit_url, fields)

                if method == "get" and query_param_names:
                    base_url = submit_url.split("#", 1)[0]
                    join_char = "&" if "?" in base_url else "?"
                    query = "&".join(f"{name}=FUZZ" for name in query_param_names)
                    self.report.sqli_targets.add(f"{base_url}{join_char}{query}")
            except Exception:
                continue

    def _extract_loose_inputs(self, page: Page) -> None:
        try:
            elements = page.locator("input, textarea, select").element_handles()
        except Exception:
            elements = []

        for element in elements:
            try:
                if element.evaluate("(el) => el.closest('form') !== null"):
                    continue
            except Exception:
                continue

            try:
                input_type = (element.get_attribute("type") or "").lower()
            except Exception:
                input_type = ""

            if input_type in IGNORED_INPUT_TYPES:
                continue

            identifier = self._identify_field(element)
            if identifier:
                self._register_field_identifier(page.url, identifier)

        # Static parsing fallback using BeautifulSoup for dynamically rendered inputs
        try:
            html = page.content()
        except Exception:
            return

        soup = BeautifulSoup(html, "html.parser")
        for tag in soup.find_all(["input", "textarea", "select"]):
            if tag.find_parent("form"):
                continue

            input_type = (tag.get("type") or "").lower()
            if input_type in IGNORED_INPUT_TYPES:
                continue

            identifier = self._identifier_from_attributes(
                name=tag.get("name"),
                element_id=tag.get("id"),
                aria=tag.get("aria-label"),
                placeholder=tag.get("placeholder"),
                data_testid=tag.get("data-testid"),
            )

            if identifier:
                self._register_field_identifier(page.url, identifier)

    def _queue_url(self, url: str) -> None:
        if url not in self._visited:
            self._to_visit.add(url)

    def _capture_request(self, request: Request) -> None:
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

    def run(self) -> ReconReport:
        self._visited: set[str] = set()
        self._to_visit: set[str] = {self.config.target_url}

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=self.config.headless)
            context = browser.new_context()
            page = context.new_page()
            page.on("request", self._capture_request)

            try:
                self._bootstrap_session(page)
            except Exception:
                pass

            ffuf_ran = False

            while self._to_visit or not ffuf_ran:
                while self._to_visit:
                    current_url = self._to_visit.pop()
                    if current_url in self._visited:
                        continue
                    try:
                        page.goto(current_url, timeout=8000)
                        page.wait_for_timeout(500)
                        self._visited.add(current_url)
                        self._extract_links(page, current_url)
                        self._extract_forms(page)
                        self._extract_loose_inputs(page)
                        self._record_cookies(page)
                    except PlaywrightTimeoutError:
                        continue
                    except Exception:
                        continue

                if ffuf_ran:
                    break

                try:
                    discovered = run_ffuf(
                        self.config.target_url,
                        self.report.cookies,
                        verbose=self.config.ffuf_verbose,
                    )
                    self.report.access_targets.update(discovered)
                    for url in discovered:
                        self._queue_url(url)
                except DirectoryEnumerationError:
                    pass

                ffuf_ran = True

            browser.close()

        return self.report
