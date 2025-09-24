import os

from dotenv import load_dotenv

from src.Recon import close_modals_and_popups

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()
EMAIL_LOGIN = os.getenv("EMAIL_LOGIN")
PASSWORD_LOGIN = os.getenv("PASSWORD_LOGIN")


from playwright.sync_api import TimeoutError


def login_and_get_cookies(page, url_login):
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
