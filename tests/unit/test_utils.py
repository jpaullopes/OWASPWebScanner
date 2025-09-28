import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from owasp_scanner.recon.utils import build_cookie_header  # type: ignore[import]


def test_build_cookie_header_formats_values():
    cookies = [
        {"name": "session", "value": "abc"},
        {"name": "token", "value": "xyz"},
    ]

    header = build_cookie_header(cookies)

    assert header == "session=abc; token=xyz"


def test_build_cookie_header_skips_invalid_entries():
    header = build_cookie_header([
        {"name": "", "value": ""},
        {"value": "missing-name"},
        {"name": "session", "value": "abc"},
    ])

    assert header == "session=abc"


def test_build_cookie_header_handles_none():
    assert build_cookie_header(None) == ""
