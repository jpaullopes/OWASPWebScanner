from playwright.sync_api import sync_playwright
import time
import sys
import os

# Adiciona o diretório raiz ao sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.recon.web_crawler import close_modals_and_popups  # Importação corrigida

def espionar_requisicao(request, api_info):
    """Listener que espiona requisições para capturar a URL da API de login e o formato do JSON"""
    # 1. Filtra por requisições do tipo POST
    if request.method == "POST":
        # 2. Filtra por URLs que parecem ser de login
        if "login" in request.url or "signin" in request.url or "auth" in request.url:
            print(f"[!] Alvo encontrado: {request.method} {request.url}")
            
            # 3. Captura a URL e o formato do JSON
            api_info["url"] = request.url
            api_info["json_format"] = request.post_data_json

def find_login_api_url(target_url):
    """
    Navega até uma página de login, tenta logar com dados falsos e 
    captura o URL da API e o formato do JSON usado. Retorna um dicionário com 'url' e 'json_format'.
    """
    
    api_info = {"url": None, "json_format": None}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False) 
        page = browser.new_page()

        # Liga o espião ANTES de qualquer ação
        page.on("request", lambda request: espionar_requisicao(request, api_info))

        # Navega para a página
        page.goto(target_url)
        
        # Chama a função para fechar modais e popups
        close_modals_and_popups(page)
        
        # Simula o preenchimento e envio do formulário
        try:
            page.locator("input[name='email']").fill("isca123@gmail.com")
            page.locator("input[name='password']").fill("isca123")
            page.locator("input[name='password']").press('Enter')
        except Exception as e:
            print(f"Não foi possível preencher o formulário automaticamente: {e}")
        
        # Espera um pouco para a requisição ser capturada
        time.sleep(5) 
        
        browser.close()
    
    return api_info

