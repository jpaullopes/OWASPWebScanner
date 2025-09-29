"""Integration layer for running XSSStrike against discovered targets."""

from .runner import XSSStrikeRunResult, run_xssstrike_scanner

__all__ = ["XSSStrikeRunResult", "run_xssstrike_scanner"]
