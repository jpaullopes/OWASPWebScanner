import os
from src.modules.AccessAnalyzer.url_scan import url_scanner

# URL da página 
TARGET_LOGIN_URL = "http://localhost:8080/WebGoat/login" 

# URL base do seu alvo 
TARGET_BASE_URL = "http://localhost:3000/#/" 


def run_test():
    print("\n--- Iniciando Teste Manual do AccessAnalyzer ---")
    print(f"URL de Login: {TARGET_LOGIN_URL}")
    print(f"URL Base: {TARGET_BASE_URL}")

    base_url_formatted = TARGET_BASE_URL if TARGET_BASE_URL.endswith('/') else TARGET_BASE_URL + '/'

    try:
        url_scanner(TARGET_LOGIN_URL, base_url_formatted, headless=True)
        print("\n--- Teste do AccessAnalyzer Concluído ---")
    except Exception as e:
        print(f"\n--- Erro durante o Teste do AccessAnalyzer: {e} ---")


if __name__ == "__main__":
    run_test()
