"""Entry point for executing the XSS scan."""

from __future__ import annotations

from typing import List, Optional
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright

from ...core.config import ScannerConfig
from ...core.report import ReconReport, XssScanArtifact, XssTargetsArtifact
from ...recon.utils import build_field_info_from_values
from .scanner import XSSScanner


IGNORED_INPUT_TYPES = {"hidden", "submit", "button", "reset", "image"}


def _apply_cookies(context, cookies):
    if not cookies:
        return
    try:
        context.add_cookies(cookies)
    except Exception:
        pass


def _safe_get_attribute(element, attribute: str) -> Optional[str]:
    try:
        return element.get_attribute(attribute)
    except Exception:
        return None


def _collect_form_fields(form_handle) -> List[dict]:
    fields: List[dict] = []
    for element in form_handle.locator("input, textarea, select").all():
        try:
            tag_name = element.evaluate("el => el.tagName.toLowerCase()")
        except Exception:
            tag_name = None

        input_type = (_safe_get_attribute(element, "type") or "").lower()
        if tag_name == "input" and input_type in IGNORED_INPUT_TYPES:
            continue

        field_info = build_field_info_from_values(
            name=_safe_get_attribute(element, "name"),
            element_id=_safe_get_attribute(element, "id"),
            aria=_safe_get_attribute(element, "aria-label"),
            placeholder=_safe_get_attribute(element, "placeholder"),
            data_testid=_safe_get_attribute(element, "data-testid"),
            field_type=input_type,
            tag=tag_name,
        )

        if field_info:
            fields.append(field_info)

    return fields


def _gather_forms_for_page(page) -> List[dict]:
    forms_data: List[dict] = []
    seen: set[tuple[str, tuple[str, ...]]] = set()
    current_url = page.url

    for form_handle in page.locator("form").all():
        action = _safe_get_attribute(form_handle, "action") or current_url
        submit_url = urljoin(current_url, action)
        fields = _collect_form_fields(form_handle)
        if not fields:
            continue

        identifiers = tuple(field["identifier"] for field in fields if "identifier" in field)
        key = (submit_url, identifiers)
        if key in seen:
            continue
        seen.add(key)
        forms_data.append({"url_de_envio": submit_url, "campos": fields})

    return forms_data


def build_xss_targets_from_url(config: ScannerConfig, url: str) -> XssTargetsArtifact:
    """Discovers XSS targets for a single URL without running the full crawler."""

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=config.headless)
        context = browser.new_context()
        page = context.new_page()
        page.goto(url, timeout=15000)
        forms = _gather_forms_for_page(page)
        cookies = context.cookies()
        browser.close()

    return XssTargetsArtifact.from_forms(url, forms, cookies=cookies)


def run_xss_scanner(
    config: ScannerConfig,
    targets: XssTargetsArtifact | ReconReport,
    listener_url: str,
) -> XssScanArtifact:
    artifact = targets.as_xss_targets() if isinstance(targets, ReconReport) else targets

    origin_url: Optional[str] = artifact.origin_url or config.target_url
    if not artifact.forms:
        return XssScanArtifact(origin_url=origin_url or "", findings=[])

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=config.headless)
        context = browser.new_context()
        _apply_cookies(context, artifact.cookies)
        page = context.new_page()
        if origin_url:
            page.goto(origin_url, timeout=15000)

        scanner = XSSScanner(page, browser, listener_url, origin_url or config.target_url, playwright)
        results = scanner.run(list(artifact.forms))

        browser.close()

    return XssScanArtifact(origin_url=origin_url or "", findings=results)
