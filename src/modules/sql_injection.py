import requests
from recon.spider import html_extractor
from bs4 import BeautifulSoup

def login_test(url, dictionary_login):
    try:
        response = requests.post(url, data=dictionary_login)
        return response
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return

def token_extractor(url, token_name):
    soup = html_extractor(url)
    token = soup.find("input", {"name": token_name})['value']
    return token

user_token = token_extractor("http://localhost/login.php", "user_token")

resposta = login_test("http://localhost/login.php", {"username": "admin", "password": "password", "user_token" : user_token})

print(resposta.text)
