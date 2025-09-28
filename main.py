#!/usr/bin/env python3
"""Compatibility entry point that proxies to ``owasp_scanner.cli``."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SRC_PATH = ROOT / "src"
if SRC_PATH.exists():  # allow execution without installation in editable mode
    sys.path.insert(0, str(SRC_PATH))


def main() -> None:
    cli = importlib.import_module("owasp_scanner.cli")
    cli.main()


if __name__ == "__main__":
    main()
