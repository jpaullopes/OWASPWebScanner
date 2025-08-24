from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup

def find_tags(html_content, tags):
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

def close_modals_and_popups(page):
    """Tenta fechar modals, popups e aba lateral que podem interferir nos testes"""
    try:
        # Tenta fechar o popup de boas-vindas
        page.locator("button[aria-label='Close Welcome Banner']").click(timeout=2000)
    except PlaywrightTimeoutError:
        pass 

    try:
        # Tenta fechar o popup de cookies
        page.locator(".cc-btn.cc-dismiss").click(timeout=2000)
    except PlaywrightTimeoutError:
        pass 

    try:
        # Tenta fechar aba lateral (sidenav) se estiver aberta
        sidebar_backdrop = page.locator(".cdk-overlay-backdrop, mat-sidenav-container .mat-drawer-backdrop")
        if sidebar_backdrop.count() > 0:
            sidebar_backdrop.first.click(timeout=2000)
    except PlaywrightTimeoutError:
        pass

    try:
        # Tenta pressionar ESC para fechar outros modais
        page.keyboard.press("Escape")
    except Exception as e:
        print(f"Não foi possível pressionar ESC: {e}")


def activate_search_bar(page):
    """Ativa a barra de pesquisa usando múltiplas estratégias com Playwright."""

    # Fechar modais e popups
    close_modals_and_popups(page)
    search_selectors = [
        "mat-icon.mat-search_icon-search",  
        ".mat-search_icons mat-icon:has-text('search')",  #
        "span.mat-search_icons mat-icon[class*='search']",  
        "mat-icon:has-text('search'):not([class*='menu'])",
    ]
    
    for selector in search_selectors:
        try:
            search_icon = page.locator(selector).first
            # Verifica se o elemento existe antes de tentar clicar
            if search_icon.count() > 0:
                search_icon.click(timeout=3000)
                
                # Aguarda a barra de pesquisa ficar visível
                search_input = page.locator("#mat-input-1")
                
                # Espera a barra ficar visível
                search_input.wait_for(state="visible", timeout=5000)
                print("Campo de pesquisa agora está visível")
                
                # Verifica se realmente é um campo editável
                if search_input.is_editable():
                    page.wait_for_timeout(1000)
                    
                    # Fecha qualquer aba latera
                    close_modals_and_popups(page)
                    return True
                else:
                    page.wait_for_timeout(1000)
                    if search_input.is_editable():
                        close_modals_and_popups(page)
                        return True
        except PlaywrightTimeoutError:
            print(f"Timeout com seletor {selector}")
            continue
        except Exception as e:
            print(f"Erro com seletor {selector}: {e}")
            continue
    
    print("Nenhum ícone de pesquisa encontrado com os seletores disponíveis")
    return False


def get_rendered_page(p, url):
    """Navega para a URL e retorna o objeto da página após as interações iniciais."""
    browser = p.chromium.launch(headless=True) 
    page = browser.new_page()
    
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=15000)
        # Fecha modals e popups 
        close_modals_and_popups(page)
        # Ativa a barra de pesquisa se disponível
        activate_search_bar(page)
              
        return page, browser
    except Exception as e:
        print(f"Ocorreu um erro ao carregar a página: {e}")
        if 'browser' in locals() and browser.is_connected():
            browser.close()
        return None, None

def page_reload(page, browser, url_teste, playwright_instance):
    """Fecha a página e o navegador atuais e abre uma nova instância dentro do mesmo contexto do Playwright."""
    try:
        # Fecha o navegador atual
        if browser and browser.is_connected():
            browser.close()
        
        # Cria um novo navegador e página dentro do mesmo contexto
        page, browser = get_rendered_page(playwright_instance, url_teste)
        return page, browser
    except Exception as e:
        print(f"Erro ao recarregar a página: {e}")
        return None, None