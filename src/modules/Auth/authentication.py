# authentication.py

import os
from dotenv import load_dotenv
from playwright.sync_api import Page, TimeoutError
from urllib.parse import urljoin

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()
EMAIL_LOGIN = os.getenv("EMAIL_LOGIN")
PASSWORD_LOGIN = os.getenv("PASSWORD_LOGIN")

def close_modals_and_popups(page: Page):
    """Tenta fechar modals, popups e aba lateral que podem interferir nos testes"""
    try:
        # Tenta fechar o popup de boas-vindas
        page.locator("button[aria-label='Close Welcome Banner']").click(timeout=2000)
    except TimeoutError:
        pass

    try:
        # Tenta fechar o popup de cookies
        page.locator(".cc-btn.cc-dismiss").click(timeout=2000)
    except TimeoutError:
        pass

    try:
        # Tenta fechar aba lateral (sidenav) se estiver aberta
        sidebar_backdrop = page.locator(
            ".cdk-overlay-backdrop, mat-sidenav-container .mat-drawer-backdrop"
        )
        if sidebar_backdrop.count() > 0:
            sidebar_backdrop.first.click(timeout=2000)
    except TimeoutError:
        pass

    try:
        # Tenta pressionar ESC para fechar outros modais
        page.keyboard.press("Escape")
    except Exception as e:
        print(f"Não foi possível pressionar ESC: {e}")

def login_and_get_cookies(page: Page, url_login: str):
    """
    Realiza o login e, se for bem-sucedido, retorna os cookies da sessão.
    Retorna:
        list: Uma lista de dicionários de cookies em caso de sucesso.
        None: Em caso de falha.
    """
    try:
        # Navega para a página de login
        page.goto(url_login)
        close_modals_and_popups(page)

        # Preenche o formulário de login
        page.wait_for_selector("input[name='email']", timeout=10000)
        page.locator("input[name='email']").fill(EMAIL_LOGIN)
        page.locator("input[name='password']").fill(PASSWORD_LOGIN)
        page.locator("input[name='password']").press("Enter")

        # Aguarda a navegação pós-login
        try:
            page.wait_for_url(lambda url: url != url_login and "login" not in url, timeout=7000)
            print("Login realizado com sucesso!")

            # Extrai os cookies do contexto do navegador
            cookies = page.context.cookies()
            print(f"Cookies extraídos: {[cookie['name'] for cookie in cookies]}")
            return cookies
        except TimeoutError:
            print("Login falhou - A URL não mudou após a tentativa.")
            return None

    except Exception as e:
        print(f"Erro durante o login: {e}")
        return None

def login_juice_shop(page: Page, base_url: str):
    """Faz login na aplicação para obter uma sessão autenticada."""
    print("[*] Tentando fazer login no Juice Shop...")
    try:
        login_url = urljoin(base_url, "/#/login")
        page.goto(login_url)
        close_modals_and_popups(page)  # Fecha modals e popups antes de interagir
        page.get_by_label("Email").fill("admin@juice-sh.op") # Use credenciais de teste
        page.get_by_label("Text field for the login password").fill("admin123")  # Locator mais específico para evitar conflito
        page.get_by_role("button", name="Login").click()
        
        # Espera a navegação para a página principal após o login
        page.wait_for_url(lambda url: "search" in url, timeout=5000)
        
        # Captura os cookies de sessão para usar depois
        cookies = page.context.cookies()
        print(f"[+] Login bem-sucedido. Cookies de sessão capturados: {len(cookies) if cookies else 0} cookies")
        return cookies
    except Exception as e:
        print(f"[-] Falha no login: {e}. O spider continuará sem autenticação.")
        return None
