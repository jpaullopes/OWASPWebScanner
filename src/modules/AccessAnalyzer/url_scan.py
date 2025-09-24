import os
import requests
import concurrent.futures
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright
from .login_access import login_and_get_cookies

# Número de threads para a varredura concorrente
MAX_THREADS = 20

def word_list_reader(word_list_path):
    """Lê uma wordlist de um arquivo e retorna uma lista de caminhos."""
    try:
        with open(word_list_path, "r", encoding="utf-8") as file:
            return [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        print(f"Erro: Arquivo de wordlist não encontrado em '{word_list_path}'")
        return []

def check_url_fast(session, url):
    """
    Verifica uma única URL usando uma sessão de requests.
    Retorna a URL se o acesso for bem-sucedido (status 200), senão None.
    """
    try:
        # Usamos stream=True e um timeout para não baixar corpos de resposta grandes
        # e para evitar que uma requisição lenta prenda a thread.
        with session.get(url, timeout=5, allow_redirects=False, stream=True) as response:
            # Consideramos sucesso apenas um status 200 OK.
            # Outros status como 302 (redirecionamento) são ignorados aqui,
            # pois a sessão já está autenticada.
            if response.status_code == 200:
                print(f"[+] URL acessível: {url} (Status: 200)")
                return url
            else:
                # Imprime silenciosamente para não poluir a saída
                # print(f"[-] URL: {url} (Status: {response.status_code})")
                return None
    except requests.RequestException as e:
        # Ignora erros de conexão, timeout, etc.
        # print(f"[!] Erro ao acessar {url}: {e}")
        return None

def url_scanner(login_url, base_url, word_list_path, headless=False):
    """Função principal para escanear URLs usando a abordagem híbrida."""
    paths = word_list_reader(word_list_path)
    if not paths:
        print("Nenhuma URL para escanear.")
        return

    print("--- Iniciando Fase 1: Autenticação com Playwright ---")
    cookies = None
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        cookies = login_and_get_cookies(page, login_url)
        browser.close()

    if not cookies:
        print("Falha na autenticação. Abortando a varredura.")
        return

    print("--- Iniciando Fase 2: Varredura Rápida com Requests ---")
    
    # Configura a sessão de requests com os cookies obtidos
    session = requests.Session()
    for cookie in cookies:
        session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])
    
    # Prepara a lista de URLs completas
    full_urls = [urljoin(base_url, path.lstrip('/')) for path in paths]
    found_urls = []

    print(f"Iniciando varredura de {len(full_urls)} URLs com {MAX_THREADS} threads...")

    # Executa a varredura concorrente
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        # Mapeia a função check_url_fast para cada URL
        future_to_url = {executor.submit(check_url_fast, session, url): url for url in full_urls}
        for future in concurrent.futures.as_completed(future_to_url):
            result = future.result()
            if result:
                found_urls.append(result)

    print("\n--- Scan concluído! ---")
    if found_urls:
        print(f"Encontradas {len(found_urls)} URLs acessíveis:")
        # Ordena para uma saída consistente
        for url in sorted(found_urls):
            print(f"  - {url}")
    else:
        print("Nenhuma URL restrita foi acessada com sucesso.")

