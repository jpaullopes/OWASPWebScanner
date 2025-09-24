from src.modules.SqlInjectionScanner.sql_injection import SQLInjectionScanner

# Define a URL da página de login do WebGoat que será o alvo do teste.
# O scanner irá navegar para esta página para encontrar o endpoint da API de login.
URL_ALVO = "http://localhost:8080/WebGoat/login"

def run_sql_injection_test():
    """
    Configura e executa a varredura de injeção de SQL usando a nova classe SQLInjectionScanner.
    """
    print(f"--- Iniciando Teste de SQL Injection no Alvo: {URL_ALVO} ---")
    
    # A classe é um gerenciador de contexto para garantir que o navegador seja iniciado e fechado corretamente.
    with SQLInjectionScanner(login_page_url=URL_ALVO) as scanner:
        # O método run_scan executa todo o processo: 
        # 1. Descobre a API de login.
        # 2. Testa os payloads.
        # 3. Imprime os resultados.
        scanner.run_scan()

    print("\n--- Teste de SQL Injection Concluído ---")


if __name__ == "__main__":
    run_sql_injection_test()