"""Dependency checks for external tooling required by the scanner."""

from __future__ import annotations

import shutil
import subprocess
from typing import Iterable

REQUIRED_TOOLS: Iterable[tuple[str, list[str]]] = (
    ("sqlmap", ["sqlmap", "--version"]),
    ("ffuf", ["ffuf", "-V"]),
    ("xssstrike", ["xssstrike", "--help"]),
)


def check_tool(command: list[str]) -> bool:
    """Returns ``True`` if the command completes successfully."""

    executable = command[0]
    if shutil.which(executable) is None:
        return False

    try:
        subprocess.run(command, capture_output=True, text=True, check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def verify_dependencies() -> dict[str, bool]:
    """Checks each required tool and returns a mapping with the result."""

    results: dict[str, bool] = {}
    for name, command in REQUIRED_TOOLS:
        results[name] = check_tool(command)
    return results
