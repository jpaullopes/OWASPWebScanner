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
    """Tenta fechar modals, popups e aba lateral que podem interferir nos testes"""
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
        # Tenta fechar aba lateral (sidenav) se estiver aberta
        sidebar_backdrop = page.locator(".cdk-overlay-backdrop, mat-sidenav-container .mat-drawer-backdrop")
        if await sidebar_backdrop.count() > 0:
            await sidebar_backdrop.first.click(timeout=2000)
            print("Aba lateral fechada.")
    except PlaywrightTimeoutError:
        pass

    try:
        # Tenta pressionar ESC para fechar outros modais
        await page.keyboard.press("Escape")
    except Exception as e:
        print(f"Não foi possível pressionar ESC: {e}")


async def activate_search_bar(page):
    """Ativa a barra de pesquisa usando múltiplas estratégias com Playwright."""
    print("Procurando o ícone da lupa")
    
    # Primeiro, tenta fechar qualquer aba lateral que possa estar aberta
    await close_modals_and_popups(page)
    
    # Seletores MUITO específicos baseados no debug - o ícone correto é o #8
    search_selectors = [
        "mat-icon.mat-search_icon-search",  # Classe específica do ícone correto
        ".mat-search_icons mat-icon:has-text('search')",  # Container específico
        "span.mat-search_icons mat-icon[class*='search']",  # Ainda mais específico
        # Fallbacks mais genéricos mas ainda evitando o menu
        "mat-icon:has-text('search'):not([class*='menu'])",
    ]
    
    for selector in search_selectors:
        try:
            search_icon = page.locator(selector).first
            # Verifica se o elemento existe antes de tentar clicar
            if await search_icon.count() > 0:
                print(f"Tentando clicar no ícone com seletor: {selector}")
                await search_icon.click(timeout=3000)
                print(f"Ícone clicado com sucesso!")
                
                # Aguarda a barra de pesquisa ficar visível
                search_input = page.locator("#mat-input-1")
                
                # Espera até 5 segundos pela barra ficar visível
                await search_input.wait_for(state="visible", timeout=5000)
                print("Campo de pesquisa agora está visível")
                
                # Verifica se realmente é um campo editável
                if await search_input.is_editable():
                    print("Barra de pesquisa ativada com sucesso!")
                    await page.wait_for_timeout(1000)
                    
                    # Fecha qualquer aba lateral que tenha aberto acidentalmente
                    await close_modals_and_popups(page)
                    return True
                else:
                    print("Campo visível mas ainda não editável, aguardando...")
                    await page.wait_for_timeout(1000)
                    if await search_input.is_editable():
                        print("Agora o campo está editável!")
                        await close_modals_and_popups(page)
                        return True
                    else:
                        print("Campo continua não editável")
        except PlaywrightTimeoutError:
            print(f"Timeout com seletor {selector}")
            continue
        except Exception as e:
            print(f"Erro com seletor {selector}: {e}")
            continue
    
    print("Nenhum ícone de pesquisa encontrado com os seletores disponíveis.")
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

async def page_reload(page, browser, url_teste, playwright_instance):
    """Fecha a página e o navegador atuais e abre uma nova instância dentro do mesmo contexto do Playwright."""
    print("Recarregando a página para limpar o estado...")
    try:
        # Fecha o navegador atual
        if browser and browser.is_connected():
            await browser.close()
        
        # Cria um novo navegador e página dentro do mesmo contexto do Playwright
        page, browser = await get_rendered_page(playwright_instance, url_teste)
        return page, browser
    except Exception as e:
        print(f"Erro ao recarregar a página: {e}")
        return None, None