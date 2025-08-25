from playwright.sync_api import sync_playwright
from src.recon.web_crawler import close_modals_and_popups 
import os
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()
EMAIL_LOGIN = os.getenv("EMAIL_LOGIN")
PASSWORD_LOGIN = os.getenv("PASSWORD_LOGIN")


def login_acess(page):
    """Realiza o login na página alvo com as credenciais que estão no arquivo environment."""

    # Chama a função para fechar modais e popups
    close_modals_and_popups(page)
    
    # Simula o preenchimento e envio do formulário
    try:
        page.locator("input[name='email']").fill(EMAIL_LOGIN)
        page.locator("input[name='password']").fill(PASSWORD_LOGIN)
        page.locator("input[name='password']").press('Enter')
    except Exception as e:
        print(f"Não foi possível preencher o formulário automaticamente: {e}")
    