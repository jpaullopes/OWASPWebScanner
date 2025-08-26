from playwright.sync_api import sync_playwright
from login_acess import login_acess
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
    """Verifica o status da URL usando Playwright."""
    try:
        response = page.goto(url, timeout=5000)
        if response and response.status == 200:
            # Se a URL for acessível, imprime a URL
            print(f"[Playwright] URL found: {url} (Status: {response.status})")
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
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        # Realiza o login na página alvo
        login_success = login_acess(page)
        
        if not login_success:
            print("Não foi possível fazer login. Abortando scan.")
            browser.close()
            return
        
        # Escaneia URLs sequencialmente para evitar problemas de concorrência
        found_urls = []
        for word in url_list:
            url = f"{base_url}/{word}"
            if check_url_status(url, page):
                found_urls.append(url)
        
        print(f"Scan concluído! Encontradas {len(found_urls)} URLs acessíveis.")
        browser.close()

# Exemplo de uso
target_base_url = "http://localhost:3000/#/login"
wordlist_path = os.path.join(os.path.dirname(__file__), "url_list.txt")
url_scanner(target_base_url, wordlist_path)