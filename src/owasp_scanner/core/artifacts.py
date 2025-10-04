"""Shared artifact data structures for modular scanner stages."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
)

if TYPE_CHECKING:  # pragma: no cover - import-time type checking only
    from ..scanners.dalfox.runner import DalfoxFinding


def _freeze_cookies(cookies: Iterable[Dict[str, Any]]) -> Tuple[Dict[str, Any], ...]:
    return tuple(dict(cookie) for cookie in cookies)


def _freeze_targets(targets: Iterable[str]) -> Tuple[str, ...]:
    return tuple(sorted(set(targets)))


@dataclass
class ReconReport:
    """Structured data produced by reconnaissance stages."""

    seed_url: str = ""
    discovered_urls: Set[str] = field(default_factory=set)
    sqli_targets: Set[str] = field(default_factory=set)
    xss_forms: List[Dict[str, Any]] = field(default_factory=list)
    access_targets: Set[str] = field(default_factory=set)
    cookies: List[Dict[str, Any]] = field(default_factory=list)

    def to_json(self) -> str:
        data = {
            "seed_url": self.seed_url,
            "urls_descobertas": sorted(self.discovered_urls),
            "alvos_para_sqli": sorted(self.sqli_targets),
            "alvos_para_xss": self.xss_forms,
            "alvos_para_access": sorted(self.access_targets),
            "cookies": self.cookies,
        }
        return json.dumps(data, indent=4)

    def save(self, path: Path) -> None:
        path.write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "ReconReport":
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            seed_url=raw.get("seed_url", ""),
            discovered_urls=set(raw.get("urls_descobertas", [])),
            sqli_targets=set(raw.get("alvos_para_sqli", [])),
            xss_forms=list(raw.get("alvos_para_xss", [])),
            access_targets=set(raw.get("alvos_para_access", [])),
            cookies=list(raw.get("cookies", [])),
        )

    # ------------------------------------------------------------------
    # Artifact projections for specific modules
    # ------------------------------------------------------------------
    def as_sql_targets(self) -> "SqlTargetsArtifact":
        return SqlTargetsArtifact(
            targets=_freeze_targets(self.sqli_targets),
            cookies=_freeze_cookies(self.cookies),
        )

    def as_xss_targets(self) -> "XssTargetsArtifact":
        return XssTargetsArtifact(
            origin_url=self.seed_url,
            forms=tuple(self.xss_forms),
            cookies=_freeze_cookies(self.cookies),
        )

    def as_access_targets(self) -> "AccessTargetsArtifact":
        return AccessTargetsArtifact(
            urls=_freeze_targets(self.access_targets),
            cookies=_freeze_cookies(self.cookies),
        )


@dataclass(frozen=True)
class SqlTargetsArtifact:
    """Input data required to execute SQL Injection scanning."""

    targets: Tuple[str, ...]
    cookies: Tuple[Dict[str, Any], ...] = ()

    @classmethod
    def from_iterable(
        cls,
        targets: Iterable[str],
        cookies: Optional[Iterable[Dict[str, Any]]] = None,
    ) -> "SqlTargetsArtifact":
        return cls(
            targets=_freeze_targets(targets),
            cookies=_freeze_cookies(cookies or ()),
        )


@dataclass(frozen=True)
class AccessTargetsArtifact:
    """Input data for the access control analyzer."""

    urls: Tuple[str, ...]
    cookies: Tuple[Dict[str, Any], ...] = ()

    @classmethod
    def from_iterable(
        cls,
        urls: Iterable[str],
        cookies: Optional[Iterable[Dict[str, Any]]] = None,
    ) -> "AccessTargetsArtifact":
        return cls(
            urls=_freeze_targets(urls),
            cookies=_freeze_cookies(cookies or ()),
        )


@dataclass(frozen=True)
class XssTargetsArtifact:
    """Information required to run XSS scanners."""

    origin_url: str
    forms: Tuple[Dict[str, Any], ...]
    cookies: Tuple[Dict[str, Any], ...] = ()

    @classmethod
    def from_forms(
        cls,
        origin_url: str,
        forms: Sequence[Dict[str, Any]],
        cookies: Optional[Iterable[Dict[str, Any]]] = None,
    ) -> "XssTargetsArtifact":
        return cls(
            origin_url=origin_url,
            forms=tuple(forms),
            cookies=_freeze_cookies(cookies or ()),
        )


@dataclass(frozen=True)
class SqlScanResult:
    """Outcome for a single SQL Injection target."""

    target: str
    vulnerable: bool
    raw_output: str


@dataclass
class SqlScanArtifact:
    """Container returned by the SQL Injection scanner."""

    targets: Tuple[str, ...]
    results: List[SqlScanResult]

    @property
    def vulnerable_targets(self) -> Tuple[str, ...]:
        return tuple(result.target for result in self.results if result.vulnerable)


@dataclass
class XssScanArtifact:
    """Container returned by the Playwright-based XSS scanner."""

    origin_url: str
    findings: List[Dict[str, Any]]

    @property
    def has_findings(self) -> bool:
        return bool(self.findings)


@dataclass
class DalfoxScanArtifact:
    """Container for Dalfox scan results."""

    origin_url: str
    findings: List["DalfoxFinding"]
    skipped_reason: Optional[str] = None

    @property
    def has_findings(self) -> bool:
        return bool(self.findings)

    @property
    def skipped(self) -> bool:
        return self.skipped_reason is not None


@dataclass
class AccessAnalysisArtifact:
    """Container for access control analysis results."""

    checked_urls: Tuple[str, ...]
    accessible_urls: List[str]

    @property
    def has_accessible(self) -> bool:
        return bool(self.accessible_urls)