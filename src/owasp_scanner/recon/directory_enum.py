"""Directory enumeration helpers backed by ffuf."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Iterable, Optional

from .utils import build_cookie_header

RESOURCE_ROOT = Path(__file__).resolve().parent.parent / "resources"
DEFAULT_WORDLIST = RESOURCE_ROOT / "common_dirs.txt"


class DirectoryEnumerationError(RuntimeError):
    """Raised when ffuf fails to complete the enumeration."""


def run_ffuf(
    base_url: str,
    cookies: Optional[Iterable[dict]] = None,
    wordlist: Optional[Path] = None,
    threads: int = 15,
    timeout: int = 300,
) -> set[str]:
    """Executes ffuf and returns the set of discovered paths."""

    wordlist_path = wordlist or DEFAULT_WORDLIST
    if not wordlist_path.exists():
        raise FileNotFoundError(f"Wordlist not found: {wordlist_path}")

    headers: list[str] = []
    cookie_header = build_cookie_header(cookies)
    if cookie_header:
        headers.extend(["-H", f"Cookie: {cookie_header}"])

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp_file:
        tmp_path = Path(tmp_file.name)

    command = [
        "ffuf",
        "-w",
        str(wordlist_path),
        "-u",
        f"{base_url.rstrip('/')}/FUZZ",
        "-mc",
        "200,401,403",
        "-t",
        str(threads),
        "-of",
        "json",
        "-o",
        str(tmp_path),
        "-timeout",
        str(timeout),
    ]

    if headers:
        command.extend(headers)

    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as exc:  # pragma: no cover - relies on ffuf
        raise DirectoryEnumerationError(exc.stderr or exc.stdout) from exc

    try:
        data = json.loads(tmp_path.read_text(encoding="utf-8"))
    finally:
        tmp_path.unlink(missing_ok=True)

    discovered: set[str] = set()
    for entry in data.get("results", []):
        url = entry.get("url")
        status = entry.get("status")
        if not url or status is None:
            continue
        discovered.add(url)

    return discovered
