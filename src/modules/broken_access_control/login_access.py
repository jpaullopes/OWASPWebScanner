import os

from dotenv import load_dotenv

from src.recon import close_modals_and_popups

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()
EMAIL_LOGIN = os.getenv("EMAIL_LOGIN")
PASSWORD_LOGIN = os.getenv("PASSWORD_LOGIN")


from playwright.sync_api import TimeoutError


def login_acess(page, url_login):
    """Realiza o login na página alvo com as credenciais que estão
    no arquivo environment."""

    try:
        # Navega para a página de login primeiro
        page.goto(url_login)

        # Chama a função para fechar modais e popups
        close_modals_and_popups(page)

        # Aguarda os campos estarem disponíveis
        page.wait_for_selector("input[name='email']", timeout=10000)

        # Simula o preenchimento e envio do formulário
        page.locator("input[name='email']").fill(EMAIL_LOGIN)
        page.locator("input[name='password']").fill(PASSWORD_LOGIN)
        page.locator("input[name='password']").press("Enter")

        # Aguarda a URL mudar, indicando que o login foi bem-sucedido
        try:
            # Espera a URL não ser mais a de login.
            # O timeout deve ser suficiente para a página carregar.
            page.wait_for_url(lambda url: url != url_login and "login" not in url, timeout=7000)
            print("Login realizado com sucesso!")
            return True
        except TimeoutError:
            print("Login falhou - A URL não mudou após a tentativa ou ainda contém 'login'.")
            return False

    except Exception as e:
        print(f"Erro durante o login: {e}")
        return False
