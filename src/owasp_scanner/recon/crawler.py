"""High level crawler that populates targets for subsequent scanners."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional
from urllib.parse import urljoin, urlparse

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, sync_playwright

from ..auth.login import login_with_credentials, login_juice_shop_demo
from ..core.config import ScannerConfig
from ..core.report import ReconReport
from .directory_enum import run_ffuf, DirectoryEnumerationError


@dataclass
class Spider:
    """Collects URLs, forms and cookies from the target application."""

    config: ScannerConfig
    report: ReconReport = field(default_factory=ReconReport)

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
                if "?" in full_url and "=" in full_url:
                    self.report.sqli_targets.add(full_url)
                self._queue_url(full_url)
            except Exception:
                continue

    def _extract_forms(self, page: Page) -> None:
        forms = page.locator("form").all()
        for form in forms:
            try:
                action = form.get_attribute("action") or page.url
                inputs = form.locator("input, textarea, select").all()
                fields = [element.get_attribute("name") for element in inputs if element.get_attribute("name")]
                self.report.xss_forms.append(
                    {
                        "url_de_envio": urljoin(self.config.target_url, action),
                        "campos": fields,
                    }
                )
            except Exception:
                continue

    def _queue_url(self, url: str) -> None:
        if url not in self._visited:
            self._to_visit.add(url)

    def run(self) -> ReconReport:
        self._visited: set[str] = set()
        self._to_visit: set[str] = {self.config.target_url}

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=self.config.headless)
            context = browser.new_context()
            page = context.new_page()

            try:
                self._bootstrap_session(page)
            except Exception:
                pass

            while self._to_visit:
                current_url = self._to_visit.pop()
                if current_url in self._visited:
                    continue
                try:
                    page.goto(current_url, timeout=8000)
                    self._visited.add(current_url)
                    self._extract_links(page, current_url)
                    self._extract_forms(page)
                    self._record_cookies(page)
                except PlaywrightTimeoutError:
                    continue
                except Exception:
                    continue

            browser.close()

        try:
            discovered = run_ffuf(self.config.target_url, self.report.cookies)
            self.report.access_targets.update(discovered)
        except DirectoryEnumerationError:
            pass

        return self.report
