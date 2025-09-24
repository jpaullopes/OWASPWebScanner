import subprocess

# Comando para rodar um scan simples no modo "batch" (não interativo)
# Alvo: um site de testes conhecido por ser vulnerável
comando_scan = [
    "sqlmap",
    "-u", "http://testphp.vulnweb.com/listproducts.php?cat=1",
    "--batch" # Responde "sim" para todas as perguntas do sqlmap
]

print(f"Iniciando scan com o comando: {' '.join(comando_scan)}")

resultado_scan = subprocess.run(comando_scan, capture_output=True, text=True)

print("\n--- Resultado do Scan (Resumido) ---")
# A saída do sqlmap é longa, vamos mostrar só as primeiras linhas
print(resultado_scan.stdout[:500] + "...")
