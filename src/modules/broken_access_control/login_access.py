import os

from dotenv import load_dotenv

from src.recon import close_modals_and_popups

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()
EMAIL_LOGIN = os.getenv("EMAIL_LOGIN")
PASSWORD_LOGIN = os.getenv("PASSWORD_LOGIN")


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

        # Aguarda um pouco para o login processar
        page.wait_for_timeout(3000)

        # Verifica se o login foi bem-sucedido checando se ainda está na página de login
        current_url = page.url
        if "login" not in current_url:
            print("Login realizado com sucesso!")
            return True
        else:
            print("Login falhou - ainda na página de login")
            return False

    except Exception as e:
        print(f"Erro durante o login: {e}")
        return False
