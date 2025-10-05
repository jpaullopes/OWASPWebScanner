from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional, Sequence
from urllib.parse import urlparse

from playwright.sync_api import Page

from ..auth.login import login_juice_shop_demo, login_with_credentials
from ..core.config import ScannerConfig
from ..core.report import ReconReport
from .state import CrawlerRuntimeState


@dataclass(slots=True)
class CookieManager:
    """Handles crawler cookie bootstrapping and synchronization."""

    config: ScannerConfig
    filter_cookies: Callable[[Sequence[dict]], list[dict]]
    initial_cookies: list[dict] = field(default_factory=list)

    def bootstrap(
        self,
        page: Page,
        *,
        target_url: str,
        report: ReconReport,
        state: Optional[CrawlerRuntimeState] = None,
    ) -> None:
        """Prime the Playwright context with authentication cookies."""

        try:
            if self._apply_session_cookie(page, target_url):
                cookies = page.context.cookies()
                self._store(self.filter_cookies(cookies), report, state)
                return

            cookies = self._login_with_credentials(page)
            if cookies:
                self._store(self.filter_cookies(cookies), report, state)
                return

            cookies = login_juice_shop_demo(page, target_url)
            if cookies:
                self._store(self.filter_cookies(cookies), report, state)
                return
        except Exception:
            pass

        fallback = self.filter_cookies(report.cookies or [])
        self._store(fallback, report, state)

    def refresh_from_page(
        self,
        page: Page,
        *,
        report: ReconReport,
        state: Optional[CrawlerRuntimeState] = None,
    ) -> None:
        """Update stored cookies based on the current browser state."""

        try:
            cookies = page.context.cookies()
        except Exception:
            return

        filtered = self.filter_cookies(cookies)
        if filtered:
            self._store(filtered, report, state)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _apply_session_cookie(self, page: Page, target_url: str) -> bool:
        if not self.config.session_cookie:
            return False

        domain = urlparse(target_url).hostname
        if not domain:
            return False

        name, _, value = self.config.session_cookie.partition("=")
        if not name or not value:
            return False

        page.context.add_cookies(
            [
                {
                    "name": name.strip(),
                    "value": value.strip(),
                    "domain": domain,
                    "path": "/",
                }
            ]
        )

        page.goto(target_url, timeout=10000)
        return True

    def _login_with_credentials(self, page: Page) -> Optional[list[dict]]:
        if not self.config.auth_email or not self.config.auth_password:
            return None

        return login_with_credentials(
            page,
            self.config.login_url,
            self.config.auth_email,
            self.config.auth_password,
        )

    def _store(
        self,
        cookies: Sequence[dict],
        report: ReconReport,
        state: Optional[CrawlerRuntimeState],
    ) -> None:
        self.initial_cookies = list(cookies)
        report.cookies = list(cookies)
        if state is not None:
            state.initial_cookies = list(cookies)
