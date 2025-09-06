import os
from src.modules.AccessAnalyzer.url_scan import url_scanner

# --- Configurações para o Teste ---
# ATENÇÃO: Para este teste funcionar, você precisa ter um servidor web rodando
# com uma página de login e algumas URLs que simulem controle de acesso.
# O Juice Shop (https://github.com/juice-shop/juice-shop) é uma ótima opção.

# URL da página de login do seu alvo
TARGET_LOGIN_URL = "http://localhost:3000/#/login" # Exemplo: Juice Shop

# URL base do seu alvo (onde as URLs da wordlist serão anexadas)
TARGET_BASE_URL = "http://localhost:3000/#/" # Exemplo: Juice Shop

# Caminho para a wordlist de URLs a serem testadas
# Certifique-se de que este arquivo exista e contenha URLs (uma por linha)
# que você deseja testar para controle de acesso.
# Exemplo de conteúdo para url_list.txt:
# /admin
# /ftp
# /secret_page
WORDLIST_FILE = os.path.join(os.path.dirname(__file__), "../src/modules/AccessAnalyzer/url_list.txt")


def run_test():
    print("\n--- Iniciando Teste Manual do AccessAnalyzer ---")
    print(f"URL de Login: {TARGET_LOGIN_URL}")
    print(f"URL Base: {TARGET_BASE_URL}")
    print(f"Wordlist: {WORDLIST_FILE}")

    # Garante que a URL base termina com / para urljoin funcionar corretamente
    base_url_formatted = TARGET_BASE_URL if TARGET_BASE_URL.endswith('/') else TARGET_BASE_URL + '/'

    try:
        # Chama a função url_scanner com headless=False para que você possa ver o navegador
        url_scanner(TARGET_LOGIN_URL, base_url_formatted, WORDLIST_FILE, headless=False)
        print("\n--- Teste do AccessAnalyzer Concluído ---")
    except Exception as e:
        print(f"\n--- Erro durante o Teste do AccessAnalyzer: {e} ---")


if __name__ == "__main__":
    run_test()
