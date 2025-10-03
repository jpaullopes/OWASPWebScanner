"""Centralized imports for the OWASP scanner package used in tests."""

from owasp_scanner.access import analyzer  # type: ignore[import]
from owasp_scanner.core import dependencies  # type: ignore[import]
from owasp_scanner.core.config import (  # type: ignore[import]
    ScannerConfig,
    load_configuration,
)
from owasp_scanner.core.report import (  # type: ignore[import]
    AccessTargetsArtifact,
    ReconReport,
    XssTargetsArtifact,
    SqlTargetsArtifact,
)
from owasp_scanner.recon.utils import build_cookie_header  # type: ignore[import]
from owasp_scanner.scanners.sql import runner as sql_runner  # type: ignore[import]

__all__ = [
    "analyzer",
    "load_configuration",
    "ScannerConfig",
    "ReconReport",
    "SqlTargetsArtifact",
    "AccessTargetsArtifact",
    "XssTargetsArtifact",
    "dependencies",
    "build_cookie_header",
    "sql_runner",
]
