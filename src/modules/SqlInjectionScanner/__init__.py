"""Compat package para o antigo módulo de SQL Injection."""

from __future__ import annotations

from .sql_injection import format_cookies, run_sqli_scan

__all__ = ["format_cookies", "run_sqli_scan"]
