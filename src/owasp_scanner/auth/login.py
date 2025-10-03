"""Authentication helpers shared by crawler and scanners."""

from __future__ import annotations

from typing import Optional
from urllib.parse import urljoin

from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


def _close_overlays(page: Page) -> None:
    """Best-effort dismissal for the common Juice Shop overlays."""

    selectors = (
        "button[aria-label='Close Welcome Banner']",
        ".cc-btn.cc-dismiss",
        ".cdk-overlay-backdrop",
    )
    for selector in selectors:
        try:
            locator = page.locator(selector)
            if locator.count() > 0:
                locator.first.click(timeout=2000)
        except PlaywrightTimeoutError:
            continue

    try:
        page.keyboard.press("Escape")
    except Exception:
        pass


def login_with_credentials(page: Page, login_url: str, email: str, password: str) -> Optional[list[dict]]:
    """Attempts a login using the provided credentials and returns cookies."""

    try:
        page.goto(login_url)
        _close_overlays(page)

        page.wait_for_selector("input[name='email']", timeout=10000)
        page.locator("input[name='email']").fill(email)
        page.locator("input[name='password']").fill(password)
        page.locator("input[name='password']").press("Enter")

        page.wait_for_url(lambda current: current != login_url and "login" not in current, timeout=7000)
        return page.context.cookies()
    except PlaywrightTimeoutError:
        return None
    except Exception:
        return None


def login_juice_shop_demo(page: Page, base_url: str) -> Optional[list[dict]]:
    """Performs the default Juice Shop login used for demos."""

    login_url = urljoin(base_url, "/#/login")
    return login_with_credentials(page, login_url, "admin@juice-sh.op", "admin123")
