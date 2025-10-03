"""Integration with the Dalfox XSS scanner."""

from .runner import DalfoxRunResult, run_dalfox_scanner

__all__ = ["DalfoxRunResult", "run_dalfox_scanner"]
