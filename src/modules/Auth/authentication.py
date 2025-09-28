"""Compatibilidade para código legado que usa ``src.modules.Auth``.

As funções aqui chamam os novos utilitários em ``owasp_scanner.auth.login``.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from playwright.sync_api import Page

from owasp_scanner.auth.login import login_juice_shop_demo, login_with_credentials

load_dotenv()

EMAIL_LOGIN = os.getenv("EMAIL_LOGIN")
PASSWORD_LOGIN = os.getenv("PASSWORD_LOGIN")

__all__ = ["close_modals_and_popups", "login_and_get_cookies", "login_juice_shop"]


def close_modals_and_popups(page: Page) -> None:  # pragma: no cover - legacy helper
    """Compat wrapper – mantido por motivos históricos."""
    return None

def login_and_get_cookies(page: Page, url_login: str):  # pragma: no cover - legacy helper
    creds_available = EMAIL_LOGIN and PASSWORD_LOGIN
    if not creds_available:
        print("[!] Variáveis EMAIL_LOGIN/PASSWORD_LOGIN não definidas. Configure o .env.")
        return None

    return login_with_credentials(page, url_login, EMAIL_LOGIN, PASSWORD_LOGIN)


def login_juice_shop(page: Page, base_url: str):  # pragma: no cover - legacy helper
    return login_juice_shop_demo(page, base_url)
