"""Integration with the Dalfox XSS scanner."""

from ...core.report import DalfoxScanArtifact
from .runner import DalfoxFinding, run_dalfox_scanner

__all__ = ["DalfoxFinding", "DalfoxScanArtifact", "run_dalfox_scanner"]
