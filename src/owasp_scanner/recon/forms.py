from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..core.models import FieldInfo
from ..core.report import ReconReport
from .state import CrawlerRuntimeState
from .utils import (build_field_info_from_values as util_build_field_info_from_values,)


IGNORED_INPUT_TYPES = {"hidden", "submit", "button", "reset", "image"}


@dataclass(slots=True)
class FormCollector:
    """Extracts form and input metadata for SQLi and XSS scanners."""

    report: ReconReport
    state: CrawlerRuntimeState
    is_allowed_url: Callable[[str], bool]

    def update_context(self, *, report: ReconReport, state: CrawlerRuntimeState) -> None:
        self.report = report
        self.state = state

    # ------------------------------------------------------------------
    # Public helpers reused by unit tests
    # ------------------------------------------------------------------
    def build_field_info_from_values(
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
        return util_build_field_info_from_values(
            name=name,
            element_id=element_id,
            aria=aria,
            placeholder=placeholder,
            data_testid=data_testid,
            field_type=field_type,
            tag=tag,
        )

    # ------------------------------------------------------------------
    # Collection routines
    # ------------------------------------------------------------------
    def collect_from_page(self, page: Any, base_url: str) -> None:
        for form in self._safe_locator_list(page, "form"):
            self._collect_form_from_locator(form, base_url)

        self._collect_loose_inputs_from_page(page, base_url)

    def collect_from_soup(self, soup: BeautifulSoup, base_url: str) -> None:
        for form in soup.find_all("form"):
            self._collect_form_from_soup(form, base_url)

        for element in soup.find_all(["input", "textarea", "select"]):
            if element.find_parent("form"):
                continue

            field_info = self.build_field_info_from_values(
                name=element.get("name"),
                element_id=element.get("id"),
                aria=element.get("aria-label"),
                placeholder=element.get("placeholder"),
                data_testid=element.get("data-testid"),
                field_type=(element.get("type") or "").lower(),
                tag=(element.name or "").lower(),
            )

            if field_info:
                self.register_field_identifier(base_url, field_info)

    def register_field_identifier(self, url: str, field_info: FieldInfo) -> None:
        if not field_info:
            return
        self._add_xss_form(url, [field_info])
        self._register_sqli_candidates(url, [field_info])

    def _collect_form_from_locator(self, form: Any, base_url: str) -> None:
        try:
            action = form.get_attribute("action")
        except Exception:
            action = None

        submit_base = self._normalize_submit_url(base_url, action)
        fields: list[FieldInfo] = []

        for element in self._safe_locator_list(form, "input, textarea, select"):
            field_info = self._build_field_info_from_locator(element)
            if not field_info:
                continue

            attributes = field_info.get("attributes", {})
            tag_name = (attributes.get("tag") or "").lower()
            input_type = (attributes.get("type") or "").lower()

            if tag_name == "input" and input_type in IGNORED_INPUT_TYPES:
                continue

            fields.append(field_info)

        if not fields:
            return

        submit_url = submit_base if submit_base else base_url
        self._add_xss_form(submit_url, fields)
        self._register_sqli_candidates(submit_url, fields)

    def _collect_form_from_soup(self, form, base_url: str) -> None:
        action = form.get("action") or base_url
        fields: List[FieldInfo] = []

        for element in form.find_all(["input", "textarea", "select"]):
            tag_name = element.name.lower() if element.name else None
            input_type = (element.get("type") or "").lower()
            if tag_name == "input" and input_type in IGNORED_INPUT_TYPES:
                continue

            field_info = self.build_field_info_from_values(
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
            return

        submit_url = self._normalize_submit_url(base_url, action)
        self._add_xss_form(submit_url, fields)
        self._register_sqli_candidates(submit_url, fields)

    def _collect_loose_inputs_from_page(self, page: Any, page_url: str) -> None:
        for element in self._safe_locator_list(page, "input, textarea, select"):
            try:
                inside_form = element.evaluate("(el) => el.closest('form') !== null")
            except Exception:
                inside_form = True

            if inside_form:
                continue

            field_info = self._build_field_info_from_locator(element)
            if not field_info:
                continue

            attributes = field_info.get("attributes", {})
            tag_name = (attributes.get("tag") or "").lower()
            input_type = (attributes.get("type") or "").lower()

            if tag_name == "input" and input_type in IGNORED_INPUT_TYPES:
                continue

            self.register_field_identifier(page_url, field_info)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _add_xss_form(self, url: str, fields: Iterable[FieldInfo]) -> None:
        if not self.is_allowed_url(url):
            return

        unique_fields: list[FieldInfo] = []
        identifiers_order: list[str] = []
        seen_identifiers: set[str] = set()

        for field_item in fields:
            identifier = field_item.get("identifier")
            if not identifier or identifier in seen_identifiers:
                continue
            unique_fields.append(field_item)
            identifiers_order.append(identifier)
            seen_identifiers.add(identifier)

        if not unique_fields:
            return

        key = (url, tuple(identifiers_order))
        if key in self.state.xss_seen:
            return

        self.state.xss_seen.add(key)
        self.report.xss_forms.append({"url_de_envio": url, "campos": unique_fields})

    def _register_sqli_candidates(
        self, submit_url: str, fields: Sequence[FieldInfo]
    ) -> None:
        param_names = self._derive_param_names(fields)
        if not param_names:
            return
        base_url = submit_url.split("#", 1)[0]
        if not self.is_allowed_url(base_url):
            return
        join_char = "&" if "?" in base_url else "?"
        query = "&".join(f"{name}=FUZZ" for name in param_names)
        self.report.sqli_targets.add(f"{base_url}{join_char}{query}")

    def _derive_param_names(self, fields: Sequence[FieldInfo]) -> Tuple[str, ...]:
        ordered: dict[str, None] = {}
        for field_item in fields:
            attributes = field_item.get("attributes", {})
            name = attributes.get("name")
            if name:
                ordered.setdefault(name, None)
        return tuple(ordered.keys())

    def _build_field_info_from_locator(self, element: Any) -> Optional[FieldInfo]:
        try:
            tag = element.evaluate("(el) => el.tagName.toLowerCase()")
        except Exception:
            tag = None

        def _safe_attr(attribute: str) -> Optional[str]:
            try:
                return element.get_attribute(attribute)
            except Exception:
                return None

        return self.build_field_info_from_values(
            name=_safe_attr("name"),
            element_id=_safe_attr("id"),
            aria=_safe_attr("aria-label"),
            placeholder=_safe_attr("placeholder"),
            data_testid=_safe_attr("data-testid"),
            field_type=_safe_attr("type"),
            tag=tag,
        )

    def _normalize_submit_url(self, base_url: str, action: Optional[str]) -> str:
        if not action:
            return base_url
        return urljoin(base_url, action)

    @staticmethod
    def _safe_locator_list(locator_owner: Any, selector: str) -> list[Any]:
        try:
            locator = locator_owner.locator(selector)
            return locator.all()
        except Exception:
            return []