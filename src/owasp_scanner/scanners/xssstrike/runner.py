"""Wrapper around the external ``xssstrike`` tool."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Iterable, List, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from ...core.config import ScannerConfig
from ...core.models import FieldAttributes, FieldInfo
from ...core.report import ReconReport

XSSSTRIKE_PARAM_VALUE = "__OWASP_XSSSTRIKE__"
DEFAULT_TIMEOUT = 120


@dataclass(frozen=True)
class XSSStrikeTarget:
    """Represents a single request that will be sent to XSSStrike."""

    target_url: str
    field_identifier: str
    parameter: str


@dataclass(frozen=True)
class XSSStrikeFinding:
    """Details about a single XSSStrike execution against a field."""

    field_identifier: str
    parameter: str
    url: str
    command: List[str]
    vulnerable: bool
    returncode: int
    output: str
    error: Optional[str] = None


@dataclass
class XSSStrikeRunResult:
    """Outcome of running the XSSStrike integration."""

    findings: List[XSSStrikeFinding] = field(default_factory=list)
    skipped_reason: Optional[str] = None


def _normalize_action_url(url: str) -> Optional[str]:
    if not url:
        return None

    parsed = urlsplit(url)
    path = parsed.path

    # SPA-style fragments like http://host/#/search are converted to /search
    fragment = parsed.fragment
    if fragment and fragment.startswith("/"):
        path = fragment
        fragment = ""

    parsed = parsed._replace(fragment="", path=path)
    if not parsed.scheme or not parsed.netloc:
        return None
    return urlunsplit(parsed)


def _resolve_parameter_name(field: FieldInfo) -> Optional[str]:
    attributes: FieldAttributes = field.get("attributes", {})  # type: ignore[assignment]
    candidates = (
        attributes.get("name"),
        attributes.get("id"),
        attributes.get("placeholder"),
        attributes.get("data_testid"),
    )
    for candidate in candidates:
        if isinstance(candidate, str) and candidate:
            return candidate

    identifier = field.get("identifier")
    if isinstance(identifier, str) and identifier:
        if "::" in identifier:
            return identifier.split("::", 1)[1]
        return identifier
    return None


def _build_target_url(action_url: str, parameter: str) -> Optional[str]:
    normalized = _normalize_action_url(action_url)
    if not normalized:
        return None

    parsed = urlsplit(normalized)
    query_items = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query_items[parameter] = XSSSTRIKE_PARAM_VALUE
    new_query = urlencode(query_items, doseq=True)
    return urlunsplit(parsed._replace(query=new_query))


def _build_targets(forms: Iterable[dict]) -> List[XSSStrikeTarget]:
    targets: List[XSSStrikeTarget] = []
    seen: set[tuple[str, str]] = set()

    for form in forms:
        action_url = form.get("url_de_envio")
        campos = form.get("campos", [])
        if not action_url or not campos:
            continue

        for field in campos:
            if not isinstance(field, dict):
                continue
            parameter = _resolve_parameter_name(field)
            if not parameter:
                continue
            target_url = _build_target_url(action_url, parameter)
            identifier = field.get("identifier")
            if not target_url or not isinstance(identifier, str):
                continue

            key = (target_url, parameter)
            if key in seen:
                continue
            seen.add(key)
            targets.append(XSSStrikeTarget(target_url, identifier, parameter))

    return targets


def _trim_output(output: str, limit: int = 2000) -> str:
    if len(output) <= limit:
        return output
    return f"{output[:limit]}\n...[truncated]..."


def _execute_xssstrike(command: List[str], *, timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def run_xssstrike_scanner(
    config: ScannerConfig,
    report: ReconReport,
    *,
    timeout: int = DEFAULT_TIMEOUT,
) -> XSSStrikeRunResult:
    """Runs XSSStrike for each discovered XSS target when available."""

    if not report.xss_forms:
        return XSSStrikeRunResult()

    executable = shutil.which("xssstrike")
    if not executable:
        return XSSStrikeRunResult(skipped_reason="xssstrike não encontrado no PATH.")

    targets = _build_targets(report.xss_forms)
    if not targets:
        return XSSStrikeRunResult(skipped_reason="Nenhum alvo compatível para XSSStrike.")

    findings: List[XSSStrikeFinding] = []

    for target in targets:
        command = [executable, "-u", target.target_url, "--crawl", "--skip-dom"]
        try:
            completed = _execute_xssstrike(command, timeout=timeout)
        except subprocess.TimeoutExpired:
            findings.append(
                XSSStrikeFinding(
                    field_identifier=target.field_identifier,
                    parameter=target.parameter,
                    url=target.target_url,
                    command=command,
                    vulnerable=False,
                    returncode=-1,
                    output="",
                    error=f"Tempo limite excedido após {timeout}s",
                )
            )
            continue
        except FileNotFoundError:
            return XSSStrikeRunResult(skipped_reason="xssstrike não pôde ser executado.")

        stdout = (completed.stdout or "").strip()
        stderr = (completed.stderr or "").strip()
        combined_output = stdout or stderr
        truncated_output = _trim_output(combined_output)
        vulnerable = "vulnerable" in combined_output.lower()
        error_message: Optional[str] = None
        if completed.returncode != 0 and stderr:
            error_message = _trim_output(stderr)

        findings.append(
            XSSStrikeFinding(
                field_identifier=target.field_identifier,
                parameter=target.parameter,
                url=target.target_url,
                command=command,
                vulnerable=vulnerable,
                returncode=completed.returncode,
                output=truncated_output,
                error=error_message,
            )
        )

    return XSSStrikeRunResult(findings=findings)
