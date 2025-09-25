#!/usr/bin/env python3
"""
OWASP Web Scanner - Orquestrador Principal

Este script coordena a execução de todos def main():
    Função principal.
    parser = argparse.ArgumentParser(description="OWASP Web Scanner")
    parser.add_argument("-u", "--url", required=True, help="URL do alvo (ex.: http://site.com)")
    args = parser.parse_args()

    print("OWASP Web Scanner - Iniciando...")
    config = load_config(args)

    if not check_dependencies():
        return

    try:
        run_crawler(config)
        server_process = run_callback_server(config)
        run_scanners(config, server_process)
        print("\n[+] Todos os módulos executados com sucesso!")
    except KeyboardInterrupt:
        print("\n[!] Execução interrompida pelo usuário.")
    except Exception as e:
        print(f"\n[!] Erro durante execução: {e}")nner em ordem.
Fluxo:
1. Crawler (descoberta de alvos)
2. CallbackServer (para XSS, em background)
3. Scanners (SQLi, XSS, Access)
"""

import os
import sys
import subprocess
import threading
import time
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Adiciona src ao path para imports
sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent / "src" / "modules"))

# Importa os módulos diretamente
from src.Recon.web_crawler import Spider
from src.modules.SqlInjectionScanner.sql_injection import run_sqli_scan, format_cookies
from src.modules.AccessAnalyzer.url_scan import url_scanner

def check_dependencies():
    """Verifica se dependências externas estão instaladas."""
    print("[*] Verificando dependências...")
    missing = []

    # Verifica sqlmap
    try:
        subprocess.run(["sqlmap", "--version"], capture_output=True, check=True)
        print("[+] sqlmap encontrado")
    except (subprocess.CalledProcessError, FileNotFoundError):
        missing.append("sqlmap (instale com: apt install sqlmap ou pip install sqlmap)")

    # Verifica ffuf
    try:
        result = subprocess.run(["ffuf", "-V"], capture_output=True, text=True)
        if "ffuf" in result.stdout.lower() or "fuzz faster u fool" in result.stdout.lower():
            print("[+] ffuf encontrado")
        else:
            missing.append("ffuf (instale com: go install github.com/ffuf/ffuf@latest)")
    except FileNotFoundError:
        missing.append("ffuf (instale com: go install github.com/ffuf/ffuf@latest)")

    if missing:
        print(f"[!] Dependências faltando: {', '.join(missing)}")
        print("Instale-as antes de continuar.")
        return False
    return True

def load_config(args):
    """Carrega configuração do projeto."""
    return {
        "target_url": args.url,
        "report_file": "relatorio_spider.json",
        "callback_port": 8000,
        "session_cookie": os.getenv("SESSION_COOKIE")  # Cookie do .env
    }

def run_crawler(config):
    """Executa o crawler."""
    print("\n=== [1/4] Executando Crawler ===")
    try:
        spider = Spider(config["target_url"], config["session_cookie"])
        spider.crawl()
        print("[+] Crawler concluído. Relatório salvo.")
    except Exception as e:
        print(f"[!] Erro no crawler: {e}")

def run_callback_server(config):
    """Inicia o servidor de callback em background."""
    print("\n=== [2/4] Iniciando Callback Server ===")
    try:
        # Inicia em background
        server_process = subprocess.Popen([sys.executable, "src/modules/CallbackServer/xss_http_server.py"])
        time.sleep(2)  # Aguarda inicialização
        print(f"[+] Callback Server iniciado (PID: {server_process.pid})")
        return server_process
    except Exception as e:
        print(f"[!] Erro no callback server: {e}")
        return None

def run_scanners(config, server_process):
    """Executa os scanners."""
    report_file = config["report_file"]
    if not os.path.exists(report_file):
        print(f"[!] Relatório {report_file} não encontrado. Execute o crawler primeiro.")
        return

    with open(report_file, "r") as f:
        report = json.load(f)

    cookies = report.get("cookies", [])
    cookie_str = format_cookies(cookies) if cookies else ""

    # SQL Injection
    print("\n=== [3/4] Executando SQL Injection Scanner ===")
    try:
        alvos_sqli = report.get("alvos_para_sqli", [])
        if alvos_sqli:
            run_sqli_scan(alvos_sqli, cookie_str)
        else:
            print("[-] Nenhum alvo SQLi encontrado.")
    except Exception as e:
        print(f"[!] Erro no SQLi scanner: {e}")

    # Access Analyzer
    print("\n=== [3/4] Executando Access Analyzer ===")
    try:
        url_scanner(config["target_url"] + "/#/login", config["target_url"], report_file)
    except Exception as e:
        print(f"[!] Erro no Access Analyzer: {e}")

    # Para o servidor
    if server_process:
        server_process.terminate()
        print("[+] Callback Server parado.")

def main():
    """Função principal."""
    parser = argparse.ArgumentParser(description="OWASP Web Scanner")
    parser.add_argument("-u", "--url", required=True, help="URL do alvo (ex.: http://site.com)")
    args = parser.parse_args()

    print("OWASP Web Scanner - Iniciando...")
    config = load_config(args)

    if not check_dependencies():
        return

    try:
        run_crawler(config)
        server_process = run_callback_server(config)
        run_scanners(config, server_process)
        print("\n[+] Todos os módulos executados com sucesso!")
    except KeyboardInterrupt:
        print("\n[!] Execução interrompida pelo usuário.")
    except Exception as e:
        print(f"\n[!] Erro durante execução: {e}")

if __name__ == "__main__":
    main()
