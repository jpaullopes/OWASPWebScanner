"""Wrapper around the external ``dalfox`` tool."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from ...core.config import ScannerConfig
from ...core.models import FieldAttributes, FieldInfo
from ...core.report import DalfoxScanArtifact, ReconReport, XssTargetsArtifact

DALFOX_PLACEHOLDER = "FUZZ"
DEFAULT_TIMEOUT = 120


@dataclass(frozen=True)
class DalfoxTarget:
    """Represents a single HTTP target that will be fuzzed by Dalfox."""

    url: str
    field_identifier: str
    parameter: str


@dataclass(frozen=True)
class DalfoxFinding:
    """Result details for an executed Dalfox scan."""

    field_identifier: str
    parameter: str
    url: str
    command: Tuple[str, ...]
    returncode: int
    output: str
    vulnerabilities: Tuple[dict, ...] = ()
    error: Optional[str] = None

    @property
    def vulnerable(self) -> bool:
        return bool(self.vulnerabilities)


def _normalize_action_url(url: str) -> Optional[str]:
    if not url:
        return None

    parsed = urlsplit(url)
    path = parsed.path

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
    query_items[parameter] = DALFOX_PLACEHOLDER
    new_query = urlencode(query_items, doseq=True)
    return urlunsplit(parsed._replace(query=new_query))


def _build_targets(forms: Iterable[dict]) -> List[DalfoxTarget]:
    targets: List[DalfoxTarget] = []
    seen: set[tuple[str, str]] = set()

    for form in forms:
        action_url = form.get("url_de_envio")
        campos = form.get("campos", [])
        if not action_url or not campos:
            continue

        for field_item in campos:
            if not isinstance(field_item, dict):
                continue
            parameter = _resolve_parameter_name(field_item)
            if not parameter:
                continue
            target_url = _build_target_url(action_url, parameter)
            identifier = field_item.get("identifier")
            if not target_url or not isinstance(identifier, str):
                continue

            key = (target_url, parameter)
            if key in seen:
                continue
            seen.add(key)
            targets.append(DalfoxTarget(target_url, identifier, parameter))

    return targets


def _trim_output(output: str, limit: int = 2000) -> str:
    if len(output) <= limit:
        return output
    return f"{output[:limit]}\n...[truncated]..."


def _parse_vulnerabilities(raw_output: str) -> Tuple[dict, ...]:
    if not raw_output:
        return ()

    try:
        data = json.loads(raw_output)
    except json.JSONDecodeError:
        return ()

    if isinstance(data, dict):
        candidates = [data]
    elif isinstance(data, list):
        candidates = data
    else:
        return ()

    valid_items: List[dict] = []
    for item in candidates:
        if isinstance(item, dict):
            valid_items.append(item)
    return tuple(valid_items)


def _execute_dalfox(command: Sequence[str], *, timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def run_dalfox_scanner(
    config: ScannerConfig,
    targets: XssTargetsArtifact | ReconReport,
    *,
    timeout: int = DEFAULT_TIMEOUT,
) -> DalfoxScanArtifact:
    """Runs Dalfox for each discovered XSS target when available."""

    artifact = targets.as_xss_targets() if isinstance(targets, ReconReport) else targets
    origin_url = artifact.origin_url or config.target_url

    if not artifact.forms:
        return DalfoxScanArtifact(origin_url=origin_url or "", findings=[])

    executable = shutil.which("dalfox")
    if not executable:
        return DalfoxScanArtifact(
            origin_url=origin_url or "",
            findings=[],
            skipped_reason="dalfox não encontrado no PATH.",
        )

    targets_to_scan = _build_targets(artifact.forms)
    if not targets_to_scan:
        return DalfoxScanArtifact(
            origin_url=origin_url or "",
            findings=[],
            skipped_reason="Nenhum alvo compatível para o Dalfox.",
        )

    findings: List[DalfoxFinding] = []

    for target in targets_to_scan:
        command = (
            executable,
            "url",
            target.url,
            "-p",
            target.parameter,
            "--format",
            "json",
            "--no-color",
        )
        try:
            completed = _execute_dalfox(command, timeout=timeout)
        except subprocess.TimeoutExpired:
            findings.append(
                DalfoxFinding(
                    field_identifier=target.field_identifier,
                    parameter=target.parameter,
                    url=target.url,
                    command=command,
                    returncode=-1,
                    output="",
                    vulnerabilities=(),
                    error=f"Tempo limite excedido após {timeout}s",
                )
            )
            continue
        except FileNotFoundError:
            return DalfoxScanArtifact(
                origin_url=origin_url or "",
                findings=[],
                skipped_reason="dalfox não pôde ser executado.",
            )

        stdout = (completed.stdout or "").strip()
        stderr = (completed.stderr or "").strip()
        primary_output = stdout or stderr
        vulnerabilities = _parse_vulnerabilities(stdout)
        truncated_output = _trim_output(primary_output)

        error_message: Optional[str] = None
        if completed.returncode != 0 and stderr:
            error_message = _trim_output(stderr)

        findings.append(
            DalfoxFinding(
                field_identifier=target.field_identifier,
                parameter=target.parameter,
                url=target.url,
                command=command,
                returncode=completed.returncode,
                output=truncated_output,
                vulnerabilities=vulnerabilities,
                error=error_message,
            )
        )

    return DalfoxScanArtifact(origin_url=origin_url or "", findings=findings)
