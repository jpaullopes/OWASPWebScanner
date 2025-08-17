import requests
from src.recon.spider import html_extractor
from bs4 import BeautifulSoup

session = requests.Session()

def login_test(url, dictionary_login, session):
    try:
        response = session.post(url, data=dictionary_login)
        return response
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return

def token_extractor(url, token_name, session):
    soup = html_extractor(url, session)
    token = soup.find("input", {"name": token_name})['value']
    return token

user_token = token_extractor("http://localhost/login.php", "user_token")

resposta = login_test("http://localhost/login.php", {"username": "admin", "password": "password", "user_token" : f"{user_token}"})

print(resposta.text)
