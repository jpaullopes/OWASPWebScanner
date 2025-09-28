"""Compat package para o antigo módulo de XSS."""

from __future__ import annotations

from .scanner import XSSScanner
from owasp_scanner.scanners.xss.runner import run_xss_scanner as run_xss_scan

__all__ = ["XSSScanner", "run_xss_scan"]
