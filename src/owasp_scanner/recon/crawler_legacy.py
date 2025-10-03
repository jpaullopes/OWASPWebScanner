"""High level crawler that populates targets for subsequent scanners."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional, Sequence, Set, Tuple
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse
import logging

from bs4 import BeautifulSoup
from playwright.sync_api import Page, Request, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from ..auth.login import login_juice_shop_demo, login_with_credentials
from ..core.config import ScannerConfig
from ..core.models import FieldAttributes, FieldInfo
from ..core.report import ReconReport
from .directory_enum import DirectoryEnumerationError, run_ffuf

IGNORED_INPUT_TYPES = {"hidden", "submit", "button", "reset", "image"}
EXCLUDED_HOST_KEYWORDS = {"github"}

logger = logging.getLogger(__name__)


@dataclass
class Spider:
    """Collects URLs, forms and cookies from the target application."""

    config: ScannerConfig
    report: ReconReport = field(default_factory=ReconReport)

    def __post_init__(self) -> None:
        parsed = urlparse(self.config.target_url)
        self._target_host: str = parsed.netloc
        self._target_hostname: str = (parsed.hostname or "").lower()
        self._xss_seen: Set[Tuple[str, Tuple[str, ...]]] = set()
        self._clicked_router_links: Set[str] = set()
        self.report.seed_url = self.config.target_url

    def _filter_cookies(self, cookies: Sequence[dict]) -> list[dict]:
        if not cookies:
            return []
        allowed: list[dict] = []
        allowed_domains = {value for value in (self._target_host, self._target_hostname) if value}
        suffix = f".{self._target_hostname}" if self._target_hostname else None
        for cookie in cookies:
            domain = (cookie.get("domain") or "").lstrip(".").lower()
            if not domain:
                continue
            if domain in allowed_domains or (suffix and domain.endswith(suffix)):
                allowed.append(cookie)
        return allowed

    def _record_cookies(self, page: Page) -> None:
        try:
            cookies = page.context.cookies()
            self.report.cookies = self._filter_cookies(cookies)
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
            cookies = login_with_credentials(
                page,
                self.config.login_url,
                self.config.auth_email,
                self.config.auth_password,
            )
            if cookies:
                self.report.cookies = cookies
                return

        cookies = login_juice_shop_demo(page, self.config.target_url)
        if cookies:
            self.report.cookies = cookies

    def _is_allowed_url(self, url: str) -> bool:
        try:
            parsed_url = urlparse(url)
        except Exception:
            return False
        host = parsed_url.netloc.lower()
        hostname = (parsed_url.hostname or "").lower()
        if parsed_url.scheme and parsed_url.scheme not in {"http", "https", ""}:
            return False
        if host:
            if host.lower() != self._target_host.lower() and (
                not hostname or hostname != self._target_hostname
            ):
                return False
        elif hostname:
            if hostname != self._target_hostname:
                return False
        candidate = host or hostname
        if candidate and any(keyword in candidate for keyword in EXCLUDED_HOST_KEYWORDS):
            return False
        return True

    def _normalize_link(self, base_url: str, href: Optional[str]) -> Optional[str]:
        if not href:
            return None
        joined = urljoin(base_url, href)
        if not self._is_allowed_url(joined):
            return None
        parsed = urlparse(joined)
        keep_fragment = bool(parsed.fragment and parsed.fragment.startswith("/"))
        sanitized = parsed if keep_fragment else parsed._replace(fragment="")
        return urlunparse(sanitized)

    def _record_link_targets(self, url: str) -> None:
        if "?" in url and "=" in url and self._is_allowed_url(url):
            self.report.sqli_targets.add(url)

    def _extract_links(self, page: Page, url: str) -> None:
        # Traditional anchors
        anchors = page.locator("a").all()
        for anchor in anchors:
            try:
                href = anchor.get_attribute("href") or anchor.get_attribute("routerlink")
                normalized = self._normalize_link(url, href)
                if not normalized:
                    continue
                self._record_link_targets(normalized)
                self._queue_url(normalized)
            except Exception:
                continue
        # Elements with routerLink attribute (Angular) not using <a>
        router_candidates = page.locator('[routerlink]').all()
        for el in router_candidates:
            try:
                href = el.get_attribute('routerlink')
                normalized = self._normalize_link(url, href)
                if not normalized:
                    continue
                self._queue_url(normalized)
            except Exception:
                continue

    def _install_history_hook(self, page: Page) -> None:
        try:
            page.add_init_script(
                """
                (() => {
                  function wrap(fnName){
                    const orig = history[fnName];
                    history[fnName] = function(){
                      const ret = orig.apply(this, arguments);
                      window.dispatchEvent(new Event('owasp_history_change'));
                      return ret;
                    }
                  }
                  wrap('pushState');
                  wrap('replaceState');
                  window.addEventListener('hashchange', () => {
                    window.dispatchEvent(new Event('owasp_history_change'));
                  });
                })();
                """
            )
        except Exception:
            pass

    def _auto_click_navigations(self, page: Page) -> None:
        # Click elements that likely trigger client-side route changes (SPA)
        selectors = [
            'a[href^="#/"]',
            '[routerlink]:not(a)',
            'button[routerlink]',
            'button[onclick*="location" i]',
            '[role="link"]',
        ]
        for sel in selectors:
            try:
                elements = page.locator(sel).all()
            except Exception:
                continue
            for el in elements:
                try:
                    href = el.get_attribute('href') or el.get_attribute('routerlink') or el.get_attribute('onclick')
                    if not href:
                        continue
                    # Normalize routerlink style hrefs
                    candidate = href
                    if candidate.startswith('#'):
                        candidate = candidate[1:]
                    if candidate.startswith('/'):
                        candidate = urljoin(self.config.target_url, candidate)
                    normalized = self._normalize_link(page.url, candidate)
                    if not normalized:
                        continue
                    if normalized in self._clicked_router_links:
                        continue
                    self._clicked_router_links.add(normalized)
                    # Perform click and allow rendering
                    el.click(timeout=500)
                    try:
                        page.wait_for_load_state('networkidle', timeout=1500)
                    except Exception:
                        page.wait_for_timeout(150)
                    # Re-collect after navigation
                    self._extract_forms(page)
                    self._extract_loose_inputs(page)
                    self._extract_links(page, page.url)
                except Exception:
                    continue

    def _register_field_identifier(self, url: str, field_info: FieldInfo) -> None:
        if not field_info:
            return
        self._add_xss_form(url, [field_info])
        self._register_sqli_candidates(url, [field_info])

    def _identifier_from_attributes(
        self,
        *,
        name: Optional[str],
        element_id: Optional[str],
        aria: Optional[str],
        placeholder: Optional[str],
        data_testid: Optional[str],
    ) -> Optional[str]:
        if name:
            return name

        priority_attributes = (
            (data_testid, "data-testid::"),
            (placeholder, "placeholder::"),
            (aria, "aria::"),
        )

        for value, prefix in priority_attributes:
            if value:
                return f"{prefix}{value}"

        if element_id:
            return f"id::{element_id}"

        return None

    def _build_field_info_from_values(
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
        identifier = self._identifier_from_attributes(
            name=name,
            element_id=element_id,
            aria=aria,
            placeholder=placeholder,
            data_testid=data_testid,
        )
        if not identifier:
            return None

        attributes: FieldAttributes = {}
        if name is not None:
            attributes["name"] = name
        if element_id is not None:
            attributes["id"] = element_id
        if aria is not None:
            attributes["aria_label"] = aria
        if placeholder is not None:
            attributes["placeholder"] = placeholder
        if data_testid is not None:
            attributes["data_testid"] = data_testid
        if field_type:
            attributes["type"] = field_type.lower()
        if tag:
            attributes["tag"] = tag.lower()

        return {"identifier": identifier, "attributes": attributes}

    def _build_field_info(self, element) -> Optional[FieldInfo]:
        try:
            tag = element.evaluate("el => el.tagName.toLowerCase()")
        except Exception:
            tag = None

        def _safe_attr(attr: str) -> Optional[str]:
            try:
                return element.get_attribute(attr)
            except Exception:
                return None

        return self._build_field_info_from_values(
            name=_safe_attr("name"),
            element_id=_safe_attr("id"),
            aria=_safe_attr("aria-label"),
            placeholder=_safe_attr("placeholder"),
            data_testid=_safe_attr("data-testid"),
            field_type=_safe_attr("type"),
            tag=tag,
        )

    def _add_xss_form(self, url: str, fields: Iterable[FieldInfo]) -> None:
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
        if key in self._xss_seen:
            return
        self._xss_seen.add(key)
        self.report.xss_forms.append({"url_de_envio": url, "campos": unique_fields})

    def _derive_param_names(self, fields: Sequence[FieldInfo]) -> Tuple[str, ...]:
        ordered: dict[str, None] = {}
        for field_item in fields:
            attributes = field_item.get("attributes", {})
            name = attributes.get("name")
            if name:
                ordered.setdefault(name, None)
        return tuple(ordered.keys())

    def _register_sqli_candidates(
        self, submit_url: str, fields: Sequence[FieldInfo]
    ) -> None:
        param_names = self._derive_param_names(fields)
        if not param_names:
            return
        base_url = submit_url.split("#", 1)[0]
        join_char = "&" if "?" in base_url else "?"
        query = "&".join(f"{name}=FUZZ" for name in param_names)
        self.report.sqli_targets.add(f"{base_url}{join_char}{query}")

    def _extract_forms(self, page: Page) -> None:
        forms = page.locator("form").all()
        for form in forms:
            try:
                action = form.get_attribute("action") or page.url
                inputs = form.locator("input, textarea, select").all()
                fields: list[FieldInfo] = []

                for element in inputs:
                    field_info = self._build_field_info(element)
                    if not field_info:
                        continue

                    attributes = field_info.get("attributes", {})
                    tag = (attributes.get("tag") or "").lower()
                    input_type = (attributes.get("type") or "").lower()

                    if tag == "input" and input_type in IGNORED_INPUT_TYPES:
                        continue

                    fields.append(field_info)

                if not fields:
                    continue

                submit_url = urljoin(self.config.target_url, action)
                self._add_xss_form(submit_url, fields)
                self._register_sqli_candidates(submit_url, fields)
            except Exception:
                continue

    def _extract_loose_inputs(self, page: Page) -> None:
        try:
            elements = page.locator("input, textarea, select").element_handles()
        except Exception:
            elements = []

        for element in elements:
            try:
                if element.evaluate("(el) => el.closest('form') !== null"):
                    continue
            except Exception:
                continue

            field_info = self._build_field_info(element)
            if not field_info:
                continue

            attributes = field_info.get("attributes", {})
            tag = (attributes.get("tag") or "").lower()
            input_type = (attributes.get("type") or "").lower()

            if tag == "input" and input_type in IGNORED_INPUT_TYPES:
                continue

            self._register_field_identifier(page.url, field_info)

        # Static parsing fallback using BeautifulSoup for dynamically rendered inputs
        try:
            html = page.content()
        except Exception:
            return

        soup = BeautifulSoup(html, "html.parser")
        for tag in soup.find_all(["input", "textarea", "select"]):
            if tag.find_parent("form"):
                continue

            tag_name = tag.name.lower() if tag.name else None
            input_type = (tag.get("type") or "").lower()
            if tag_name == "input" and input_type in IGNORED_INPUT_TYPES:
                continue

            field_info = self._build_field_info_from_values(
                name=tag.get("name"),
                element_id=tag.get("id"),
                aria=tag.get("aria-label"),
                placeholder=tag.get("placeholder"),
                data_testid=tag.get("data-testid"),
                field_type=input_type,
                tag=tag_name,
            )

            if field_info:
                self._register_field_identifier(page.url, field_info)

    def _queue_url(self, url: str) -> None:
        if not self._is_allowed_url(url):
            return
        if url not in self._visited:
            self._to_visit.add(url)
            self.report.discovered_urls.add(url)

    def _capture_request(self, request: Request) -> None:
        try:
            parsed = urlparse(request.url)
            if not parsed.netloc or parsed.netloc != self._target_host:
                return
            if request.method.upper() != "GET" or not parsed.query:
                return

            params = parse_qsl(parsed.query, keep_blank_values=True)
            if not params:
                return

            mutated = [(name, "FUZZ") for name, _ in params]
            normalized_query = urlencode(mutated, doseq=True)
            target_url = urlunparse(parsed._replace(query=normalized_query))
            self.report.sqli_targets.add(target_url)
        except Exception:
            return

    def run(self) -> ReconReport:
        self._visited: set[str] = set()
        self._to_visit: set[str] = {self.config.target_url}

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=self.config.headless)
            context = browser.new_context()
            page = context.new_page()
            page.on("request", self._capture_request)
            self._install_history_hook(page)
            try:
                self._bootstrap_session(page)
            except Exception:
                pass
            # Listener para mudanças de histórico gerando nova coleta leve
            try:
                page.expose_function("__owasp_history_ping", lambda: None)
            except Exception:
                pass

            ffuf_ran = False

            while self._to_visit or not ffuf_ran:
                while self._to_visit:
                    current_url = self._to_visit.pop()
                    if current_url in self._visited:
                        continue
                    try:
                        page.goto(current_url, timeout=8000)
                        try:
                            page.wait_for_load_state("networkidle", timeout=3000)
                        except Exception:
                            page.wait_for_timeout(300)
                        self._visited.add(current_url)
                        self.report.discovered_urls.add(current_url)
                        self._extract_links(page, current_url)
                        self._extract_forms(page)
                        self._extract_loose_inputs(page)
                        self._record_cookies(page)
                        # Auto-click pass para descobrir rotas internas SPA
                        self._auto_click_navigations(page)
                    except PlaywrightTimeoutError:
                        continue
                    except Exception:
                        continue

                if ffuf_ran:
                    break

                try:
                    discovered = run_ffuf(
                        self.config.target_url,
                        self.report.cookies,
                        verbose=self.config.ffuf_verbose,
                    )
                    # Filter & queue only allowed
                    for url in discovered:
                        if self._is_allowed_url(url):
                            self.report.access_targets.add(url)
                            self._queue_url(url)
                except DirectoryEnumerationError:
                    pass

                ffuf_ran = True

            browser.close()

        return self.report
