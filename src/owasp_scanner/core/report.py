"""Backwards-compatible exports for artifact data structures."""

from __future__ import annotations

from .artifacts import (
    AccessAnalysisArtifact,
    AccessTargetsArtifact,
    DalfoxScanArtifact,
    ReconReport,
    SqlScanArtifact,
    SqlScanResult,
    SqlTargetsArtifact,
    XssScanArtifact,
    XssTargetsArtifact,
)

__all__ = [
    "AccessAnalysisArtifact",
    "AccessTargetsArtifact",
    "DalfoxScanArtifact",
    "ReconReport",
    "SqlScanArtifact",
    "SqlScanResult",
    "SqlTargetsArtifact",
    "XssScanArtifact",
    "XssTargetsArtifact",
]
