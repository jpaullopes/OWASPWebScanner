"""Compatibilidade para código legado que ainda importa ``src.Recon``.

O módulo real foi movido para ``owasp_scanner.recon``.
"""

from __future__ import annotations

from owasp_scanner.recon.crawler import Spider

__all__ = ["Spider"]
