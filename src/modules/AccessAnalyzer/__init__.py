"""Compat package para código que ainda importa ``src.modules.AccessAnalyzer``."""

from __future__ import annotations

from .url_scan import url_scanner

__all__ = ["url_scanner"]