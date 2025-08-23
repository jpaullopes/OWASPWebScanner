import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup

async def find_tags(html_content, tags):
    """Função responsável por encontrar as tags passadas como parâmetro"""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        found_tags = []

        for tag in tags:
            foud_tag_elements = soup.find_all(tag)
            for tag_elements in foud_tag_elements:
                if tag_elements:
                    tag_info = { 
                        "name": tag_elements.get('name'),
                        "id": tag_elements.get('id'),
                        "type": tag_elements.get('type'),
                    }
                    found_tags.append(tag_info)
        return found_tags
    except Exception as e:
        print(f"An error occurred while parsing HTML: {e}")
        return []

async def close_modals_and_popups(page):
    """Tenta fechar modals e popups comuns que podem interferir nos testes"""
    try:
        # Tenta fechar o popup de boas-vindas
        await page.locator("button[aria-label='Close Welcome Banner']").click(timeout=2000)
        print("Banner de boas-vindas fechado.")
    except PlaywrightTimeoutError:
        pass # Ignora se não encontrar

    try:
        # Tenta fechar o popup de cookies
        await page.locator(".cc-btn.cc-dismiss").click(timeout=2000)
        print("Popup de cookies fechado.")
    except PlaywrightTimeoutError:
        pass # Ignora se não encontrar

    try:
        # Tenta pressionar ESC para fechar outros modais
        await page.keyboard.press("Escape")
    except Exception as e:
        print(f"Não foi possível pressionar ESC: {e}")


async def activate_search_bar(page):
    """Ativa a barra de pesquisa usando múltiplas estratégias com Playwright."""
    print("Procurando o ícone da lupa")
    
    # O Playwright espera automaticamente, então o código é mais simples
    search_icon_locator = page.locator("mat-icon[class*='mat-search_icon-search'], mat-icon[data-mat-icon-type='font']")
    
    try:
        await search_icon_locator.first.click(timeout=5000)
        print("Clicando na lupa")
        
        # Aguarda a barra de pesquisa (input) ficar visível e clicável
        search_input = page.locator("#mat-input-1")
        await search_input.wait_for(state="visible", timeout=10000)
        await search_input.wait_for(state="editable", timeout=10000)
        
        print("Barra de pesquisa ativada!")
        await page.wait_for_timeout(1000) # Pequena pausa para garantir a estabilização da UI
        return True
    except PlaywrightTimeoutError:
        print("Nenhum ícone de pesquisa encontrado ou a barra não ficou ativa a tempo.")
        return False
    except Exception as e:
        print(f"Erro inesperado ao ativar a barra de pesquisa: {e}")
        return False


async def get_rendered_page(p, url):
    """Navega para a URL e retorna o objeto da página após as interações iniciais."""
    browser = await p.chromium.launch(headless=False) # Mude para True para modo headless
    page = await browser.new_page()
    
    try:
        print(f"Navegando para {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        
        # Fecha modals e popups que podem atrapalhar
        await close_modals_and_popups(page)
        
        # Ativa a barra de pesquisa se disponível
        await activate_search_bar(page)
              
        return page, browser
    except Exception as e:
        print(f"Ocorreu um erro ao carregar a página: {e}")
        if 'browser' in locals() and browser.is_connected():
            await browser.close()
        return None, None

async def page_reload(page, browser, url_teste):
    """Fecha a página e o navegador atuais e abre uma nova instância."""
    print("Recarregando a página para limpar o estado...")
    try:
        if browser and browser.is_connected():
            await browser.close()
        
        async with async_playwright() as p:
            page, browser = await get_rendered_page(p, url_teste)
            return page, browser
    except Exception as e:
        print(f"Erro ao recarregar a página: {e}")
        return None, None