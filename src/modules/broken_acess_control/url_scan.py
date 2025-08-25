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
        response = page.goto(url, timeout=5000)
        if response and response.status == 200:
            return True
        else:
            return False

    except Exception as e:
        print(f"Error accessing {url}: {e}")
        return False