
import subprocess

def run_xss_scan(targets: list):
    """Executa o xssstrike contra uma lista de alvos."""
    
    print("\n--- [ XSS SCANNER ] ---")
    print("Iniciando varredura de XSS nos alvos encontrados...")
    
    for url in targets:
        print(f"\n[*] Alvo: {url}")
        
        # Monta o comando final para o subprocess
        comando = [
            "xssstrike",
            "-u", url,
            "--level=3",
            "--threads=10"
        ]
        
        try:
            print(f"[*] Executando xssstrike...")
            resultado = subprocess.run(comando, capture_output=True, text=True, timeout=300) # Timeout de 5 minutos
            
            # Verifica se o xssstrike encontrou algo
            if "Payloads found:" in resultado.stdout:
                print(f"[!!!] SUCESSO! Alvo parece ser vulnerável a XSS.")
                print("--- Início do Relatório xssstrike ---")
                print(resultado.stdout)
                print("--- Fim do Relatório xssstrike ---")
            else:
                print("[-] Alvo não parece ser vulnerável (com base nos testes rápidos).")

        except FileNotFoundError:
            print("[!!!] ERRO: O comando 'xssstrike' não foi encontrado. Verifique se ele está instalado e no PATH do sistema.")
            return # Sai da função se o xssstrike não for encontrado
        except subprocess.TimeoutExpired:
            print(f"[-] TEMPO ESGOTADO: O scan para {url} demorou mais de 5 minutos.")
        except Exception as e:
            print(f"[!!!] ERRO inesperado ao executar o xssstrike: {e}")
