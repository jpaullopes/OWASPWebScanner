"""Entry point for executing the XSS scan."""

from __future__ import annotations

from typing import List

from playwright.sync_api import sync_playwright

from ...core.config import ScannerConfig
from ...core.report import ReconReport
from .scanner import XSSScanner


def _apply_cookies(context, cookies):
    if not cookies:
        return
    try:
        context.add_cookies(cookies)
    except Exception:
        pass


def run_xss_scanner(config: ScannerConfig, report: ReconReport, listener_url: str) -> List[dict]:
    if not report.xss_forms:
        return []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=config.headless)
        context = browser.new_context()
        _apply_cookies(context, report.cookies)
        page = context.new_page()
        page.goto(config.target_url, timeout=15000)

        scanner = XSSScanner(page, browser, listener_url, config.target_url, playwright)
        results = scanner.run(report.xss_forms)

        browser.close()
    return results
