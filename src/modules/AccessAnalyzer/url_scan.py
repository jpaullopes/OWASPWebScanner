import os
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright

from .login_access import login_acess


def word_list_reader(word_list_path):
    """Lê uma wordlist de um arquivo e retorna uma lista de caminhos."""
    try:
        with open(word_list_path, "r", encoding="utf-8") as file:
            return [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        print(f"Erro: Arquivo de wordlist não encontrado em '{word_list_path}'")
        return []


def check_url_status(page, url, login_url):
    """
    Verifica o status de uma URL, garantindo que não houve redirecionamento para a página de login.
    """
    try:
        response = page.goto(url, timeout=5000, wait_until="domcontentloaded")
        # Garante que a URL final não seja a de login
        final_url = page.url
        if login_url in final_url and url != login_url:
            print(f"[-] Acesso negado a {url} (redirecionado para login)")
            return False

        if response and response.status == 200:
            print(f"[+] URL acessível encontrada: {url} (Status: {response.status})")
            return True
        else:
            status = response.status if response else "N/A"
            print(f"[-] URL retornou status diferente de 200: {url} (Status: {status})")
            return False

    except Exception as e:
        print(f"[!] Erro ao acessar {url}: {e}")
        return False


def url_scanner(login_url, base_url, word_list_path, headless=True):
    """Função principal para escanear URLs a partir de uma wordlist após o login."""
    paths = word_list_reader(word_list_path)
    if not paths:
        print("Nenhuma URL para escanear.")
        return

    print(f"Iniciando scanner com {len(paths)} caminhos.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()

        # Realiza o login
        if not login_acess(page, login_url):
            print("Falha no login. Abortando o scan.")
            browser.close()
            return

        print("\n--- Iniciando varredura de URLs ---\n")
        found_urls = []
        for path in paths:
            # Constrói a URL completa de forma segura
            url = urljoin(base_url, path.lstrip('/'))
            print(f"[*] Testando URL: {url}")
            if check_url_status(page, url, login_url):
                found_urls.append(url)

        print(f"\n--- Scan concluído! ---")
        if found_urls:
            print(f"Encontradas {len(found_urls)} URLs acessíveis:")
            for url in found_urls:
                print(f"  - {url}")
        else:
            print("Nenhuma URL restrita foi acessada com sucesso.")

        browser.close()

# # Exemplo de como chamar esta função a partir de outro arquivo:
# if __name__ == "__main__":
#     # Defina as configurações do alvo aqui
#     target_login_url = "http://localhost:3000/#/login"
#     target_base_url = "http://localhost:3000/#/"
#
#     # O caminho para a wordlist é relativo a este arquivo
#     wordlist_path = os.path.join(os.path.dirname(__file__), "url_list.txt")
#
#     # Garante que a URL base termina com /
#     base_url = target_base_url if target_base_url.endswith('/') else target_base_url + '/'
#
#     # Chama o scanner
#     url_scanner(target_login_url, base_url, wordlist_path, headless=False)