# maestro.py
import json
import subprocess
import os

def format_cookies(cookies_list: list) -> str:
    """Converte a lista de cookies do Playwright para uma string para o sqlmap."""
    partes_do_cookie = []
    for cookie in cookies_list:
        partes_do_cookie.append(f"{cookie['name']}={cookie['value']}")
    return "; ".join(partes_do_cookie)

def run_sqli_scan(targets: list, cookie_string: str):
    """Executa o sqlmap contra uma lista de alvos usando os cookies de sessão."""
    
    print("\n--- [ MAESTRO ] ---")
    print("Iniciando varredura de SQL Injection nos alvos encontrados...")
    
    for url in targets:
        print(f"\n[*] Alvo: {url}")
        
        # Monta o comando final para o subprocess
        comando = [
            "sqlmap",
            "-u", url,
            "--cookie", cookie_string,
            "--batch",         # Responde 'sim' para as perguntas
            "--level=5",       # Nível de teste (1 é o mais rápido)
            "--risk=3"         # Risco (1 é o mais seguro)
        ]
        
        try:
            print(f"[*] Executando sqlmap...")
            resultado = subprocess.run(comando, capture_output=True, text=True, timeout=300) # Timeout de 5 minutos
            
            # Verifica se o sqlmap encontrou algo
            if "the back-end DBMS is" in resultado.stdout or "is vulnerable" in resultado.stdout:
                print(f"[!!!] SUCESSO! Alvo parece ser vulnerável a SQL Injection.")
                # Em um cenário real, poderíamos salvar o output completo em um log
                print("--- Início do Relatório sqlmap ---")
                print(resultado.stdout)
                print("--- Fim do Relatório sqlmap ---")
            else:
                print("[-] Alvo não parece ser vulnerável (com base nos testes rápidos).")

        except FileNotFoundError:
            print("[!!!] ERRO: O comando 'sqlmap' não foi encontrado. Verifique se ele está instalado e no PATH do sistema.")
            return # Sai da função se o sqlmap não for encontrado
        except subprocess.TimeoutExpired:
            print(f"[-] TEMPO ESGOTADO: O scan para {url} demorou mais de 5 minutos.")
        except Exception as e:
            print(f"[!!!] ERRO inesperado ao executar o sqlmap: {e}")


if __name__ == "__main__":
    # Constrói o caminho para o relatório
    caminho_relatorio = "relatorio_spider.json" # Assumindo que está na mesma pasta
    
    if not os.path.exists(caminho_relatorio):
        print(f"ERRO: Arquivo de relatório '{caminho_relatorio}' não encontrado.")
        print("Execute o spider.py primeiro.")
    else:
        # Carrega os dados do relatório do Spider
        with open(caminho_relatorio, 'r') as f:
            dados = json.load(f)
        
        # Prepara os dados para o ataque
        alvos_sqli = dados.get("alvos_para_sqli", [])
        cookies = dados.get("cookies", [])
        
        if not alvos_sqli:
            print("Nenhum alvo para SQL Injection encontrado no relatório.")
        else:
            cookie_str = format_cookies(cookies)
            # Executa o scan
            run_sqli_scan(alvos_sqli, cookie_str)