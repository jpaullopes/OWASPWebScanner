import threading
import requests
from playwright.sync_api import sync_playwright

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
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print(f"[Requests] URL found: {url} (Status: {response.status_code})")
            return

        page.goto(url, timeout=5000)
        if page.status == 200:
            print(f"[Playwright] URL found: {url} (Status: {page.status})")

    except Exception as e:
        print(f"Error accessing {url}: {e}")