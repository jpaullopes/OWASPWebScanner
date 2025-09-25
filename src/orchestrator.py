
import argparse
import json
from .Recon.web_crawler import Spider
from .modules.SqlInjectionScanner.sql_injection import run_sqli_scan, format_cookies
from .modules.XssScanner.xss import run_xss_scan
from .modules.CallbackServer.xss_http_server import iniciar_servidor_ouvinte, obter_relatorio_detalhado
from playwright.sync_api import sync_playwright

def main():
    parser = argparse.ArgumentParser(description="OWASP Web Scanner")
    parser.add_argument("-u", "--url", required=True, help="URL do alvo para escanear")
    args = parser.parse_args()

    print(f"[*] Iniciando o escaneamento no alvo: {args.url}")

    # 1. Fase de Reconhecimento
    print("[*] Fase 1: Reconhecimento e Crawling")
    spider = Spider(args.url)
    spider.crawl()

    # 2. Fase de Análise de Vulnerabilidades
    print("[*] Fase 2: Análise de Vulnerabilidades")
    
    # Carrega o relatório do spider
    with open("relatorio_spider.json", 'r') as f:
        dados = json.load(f)
    
    alvos_sqli = dados.get("alvos_para_sqli", [])
    cookies = dados.get("cookies", [])
    
    # Executa o scan de SQL Injection
    if alvos_sqli and cookies:
        cookie_str = format_cookies(cookies)
        run_sqli_scan(alvos_sqli, cookie_str)
    else:
        print("[-] Nenhum alvo para SQL Injection encontrado ou cookies não disponíveis.")
        
    # Executa o scan de XSS
    print("[*] Iniciando o scan de XSS...")
    # Inicia o servidor de callback
    iniciar_servidor_ouvinte(8001)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        campos_interativos = dados.get("alvos_para_xss", [])
        if campos_interativos:
            run_xss_scan(page, browser, "http://localhost:8001", args.url, p, campos_interativos)
        else:
            print("[-] Nenhum alvo para XSS encontrado.")
            
        browser.close()
        
    # Obtém o relatório do servidor de callback
    relatorio_xss = obter_relatorio_detalhado()
    print("[*] Relatório do scan de XSS:")
    print(json.dumps(relatorio_xss, indent=4))
    
    print("[+] Escaneamento concluído.")

if __name__ == "__main__":
    main()
