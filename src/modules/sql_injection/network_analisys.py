from playwright.async_api import async_playwright
import asyncio
from src.recon.web_crawler import close_modals_and_popups  


async def find_login_api_url(target_url):
    """
    Navega até uma página de login, tenta logar com dados falsos e 
    captura o URL da API e o formato do JSON usado.
    """
    
    api_info = {"url": None, "json_format": None}

    async def espionar_requisicao(request):
        # 1. Filtra por requisições do tipo POST
        if request.method == "POST":
            # 2. Filtra por URLs que parecem ser de login
            if "login" in request.url or "signin" in request.url or "auth" in request.url:
                print(f"[!] Alvo encontrado: {request.method} {request.url}")
                
                # 3. Captura a URL e o formato do JSON
                api_info["url"] = request.url
                api_info["json_format"] = request.post_data_json
                
                # Para o listener para não capturar mais nada
                await page.unroute("**", espionar_requisicao)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False) 
        page = await browser.new_page()

        # Liga o espião ANTES de qualquer ação
        page.on("request", espionar_requisicao)

        # Navega para a página
        await page.goto(target_url)
        
        # Chama a função assíncrona para fechar modais e popups
        await close_modals_and_popups(page)
        
        # Simula o preenchimento e envio do formulário
        # Usamos try/except pois os campos podem não existir
        try:
            await page.locator("input[name='email']").fill("isca123@gmail.com")
            await page.locator("input[name='password']").fill("isca123")
            await page.locator("input[name='password']").press('Enter')
            #await page.locator("button[class='login-button']").press('Enter')
        except Exception as e:
            print(f"Não foi possível preencher o formulário automaticamente: {e}")
        
        # Espera um pouco para a requisição ser capturada
        await asyncio.sleep(5) 
        
        await browser.close()
    
    return api_info


url_alvo = "http://localhost:3000/#/login"
informacao_api = asyncio.run(find_login_api_url(url_alvo))

if informacao_api["url"]:
    print("\n--- Descoberta Sucedida ---")
    print(f"URL da API de Login: {informacao_api['url']}")
    print(f"Formato do JSON: {informacao_api['json_format']}")
else:
    print("\n--- Descoberta Falhou ---")

    print("Não foi possível encontrar a API de login.")