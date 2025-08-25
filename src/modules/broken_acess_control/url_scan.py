import threading
import requests
from playwright.sync_api import sync_playwright
from login_acess import login_acess

def word_list_reader(word_list):
    """Responsavél por fazer a leitura do arquivo de wordlist e retornar uma lista de URLs."""
    url_list = []
    try:
        with open(word_list, 'r') as file:
            for word in file:
                url = word.strip()
                url_list.append(url)
        return url_list
    except FileNotFoundError:
        print(f"Wordlist file '{word_list}' not found.")
        return []
    
def check_url_status(url, page):
    """Verifica o status da URL usando requests e Playwright."""
    try:
        response = page.goto(url, timeout=5000)
        if response and response.status == 200:
            return True
        else:
            return False

    except Exception as e:
        print(f"Error accessing {url}: {e}")
        return False

def url_scanner(base_url, word_list):
    """Função principal para escanear URLs a partir de uma wordlist."""
    url_list = word_list_reader(word_list)
    if not url_list:
        print("No URLs to scan.")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Realiza o login na página alvo
        login_acess(page)

        threads = []
        for word in url_list:
            url = f"{base_url}/{word}"
            thread = threading.Thread(target=lambda u=url: check_url_status(u, page))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        browser.close()