"""Compatibilidade para código legado usando ``src.Recon.web_crawler``.

Este módulo apenas reexporta ``owasp_scanner.recon.crawler.Spider``.
"""

from __future__ import annotations

from owasp_scanner.recon.crawler import Spider

__all__ = ["Spider"]