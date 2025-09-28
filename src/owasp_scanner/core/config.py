"""Configuration loading and CLI parsing utilities."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

from dotenv import load_dotenv


@dataclass(slots=True)
class ScannerConfig:
    """Holds runtime options for a full scan execution."""

    target_url: str
    session_cookie: Optional[str]
    report_path: Path
    headless: bool = False
    auth_email: Optional[str] = None
    auth_password: Optional[str] = None

    @property
    def login_url(self) -> str:
        return urljoin(self.target_url, "/#/login")


def load_configuration(target_url: str, report_name: str = "relatorio_spider.json") -> ScannerConfig:
    """Builds a ``ScannerConfig`` from CLI input and environment variables."""

    load_dotenv()  # Loads .env values if present

    report_path = Path(report_name).resolve()
    session_cookie = os.getenv("SESSION_COOKIE") or None
    auth_email = os.getenv("EMAIL_LOGIN")
    auth_password = os.getenv("PASSWORD_LOGIN")

    return ScannerConfig(
        target_url=target_url.rstrip("/"),
        session_cookie=session_cookie,
        report_path=report_path,
        headless=os.getenv("HEADLESS", "false").lower() in {"1", "true", "yes"},
        auth_email=auth_email,
        auth_password=auth_password,
    )
