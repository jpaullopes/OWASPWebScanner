from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

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

def setup_chrome_driver():
    """Configura e retorna um driver Chrome otimizado"""
    chrome_options = Options()
    #chrome_options.add_argument("--headless")  
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=chrome_options)

def close_modals_and_popups(driver):
    """Tenta fechar modals e popups comuns que podem interferir nos testes"""
    try:
        # Procura botão de fechar
        close_button = driver.find_element(By.XPATH, "//button[contains(@class, 'close') or contains(@aria-label, 'close') or text()='×']")
        close_button.click()
        WebDriverWait(driver, 5).until(EC.invisibility_of_element(close_button))
    except:
        try:
            # Procura por dismiss ou OK
            dismiss_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Dismiss') or contains(text(), 'OK')]")
            dismiss_button.click()
        except:
            try:
                # Tenta clica no backdrop para fechar modals
                backdrop = driver.find_element(By.CLASS_NAME, "cdk-overlay-backdrop")
                backdrop.click()
                WebDriverWait(driver, 5).until(EC.invisibility_of_element(backdrop))
            except:
                try:
                    # Pressiona ESC 
                    driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                except:
                    pass

def close_sidebar_generic(driver):
    """Tenta fechar sidebars/menus laterais em sites diversos"""
    print("Verificando e fechando sidebars...")
    
    sidebar_selectors = [
        # OWASP Juice Shop específico
        "mat-sidenav.mat-drawer-opened",
        ".mat-drawer-opened",
        
        # Sidebars genéricas
        ".sidebar.open",
        ".side-menu.open", 
        ".drawer.open",
        ".offcanvas.show",
        ".nav-drawer.open",
        ".side-panel.active",
        
        # Bootstrap e frameworks populares
        ".navbar-collapse.show",
        ".navbar-toggler[aria-expanded='true']",
        ".offcanvas-backdrop",
        
        # Angular Material
        ".mat-drawer-backdrop",
        ".cdk-overlay-backdrop",
        
        # Outros padrões comuns
        "[class*='sidebar'][class*='open']",
        "[class*='menu'][class*='open']",
        "[class*='drawer'][class*='open']"
    ]
    
    for selector in sidebar_selectors:
        try:
            sidebar = driver.find_element(By.CSS_SELECTOR, selector)
            if sidebar.is_displayed():
                print(f"Encontrou sidebar ativa: {selector}")
                
                # Tenta diferentes formas de fechar
                # 1. Clica no próprio sidebar (alguns fecham assim)
                try:
                    sidebar.click()
                    time.sleep(0.5)
                    if not sidebar.is_displayed():
                        print("Sidebar fechada clicando nela")
                        continue
                except:
                    pass
                
                # 2. Procura botão de fechar dentro da sidebar
                try:
                    close_btn = sidebar.find_element(By.CSS_SELECTOR, 
                        "button[aria-label*='close'], button[aria-label*='Close'], .close, [class*='close']")
                    close_btn.click()
                    print("Sidebar fechada via botão close")
                    time.sleep(0.5)
                    continue
                except:
                    pass
                
                # 3. Clica fora da sidebar (backdrop)
                try:
                    driver.execute_script("arguments[0].click();", 
                        driver.find_element(By.TAG_NAME, "body"))
                    time.sleep(0.5)
                    if not sidebar.is_displayed():
                        print("Sidebar fechada clicando fora")
                        continue
                except:
                    pass
                    
        except:
            continue
    
    # Pressiona ESC como último recurso
    try:
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        time.sleep(0.5)
    except:
        pass

def activate_search_bar(driver):
    """Ativa a barra de pesquisa usando múltiplas estratégias"""
    print("Procurando o ícone da lupa")
    search_icon = None
    
    # Estratégia 1: mat-icon com classe mat-search_icon-search 
    try:
        search_icon = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "mat-icon[class*='mat-search_icon-search']"))
        )
        print("Encontrou mat-icon com classe mat-search_icon-search")
    except:
        pass
    
    # Estratégia 2: mat-icon que contém texto "search" 
#    if not search_icon:
#       try:
#            search_icon = WebDriverWait(driver, 3).until(
#                EC.element_to_be_clickable((By.XPATH, "//mat-icon[contains(text(), 'search')]"))
#            )
#            print("Encontrou mat-icon com texto 'search'")
#        except:
#            pass
    
    # Estratégia 3: qualquer mat-icon na barra superior (toolbar)
#    if not search_icon:
#        try:
#            search_icon = WebDriverWait(driver, 3).until(
#                EC.element_to_be_clickable((By.CSS_SELECTOR, "mat-toolbar mat-icon"))
#            )
#            print("Encontrou mat-icon genérico na toolbar")
#        except:
#            pass
    
    # Estratégia 4: busca por data-mat-icon-type="font"
    if not search_icon:
        try:
            search_icon = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "mat-icon[data-mat-icon-type='font']"))
            )
            print("Encontrou mat-icon com data-mat-icon-type")
        except:
            pass
    
    # Se encontrou, clica e aguarda
    if search_icon:
        print("Clicando na lupa")
        search_icon.click()
        print("Aguardando barra de pesquisa ficar ativa")
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "mat-input-1"))
        )
        print("Barra de pesquisa ativada!")
        time.sleep(1)
        return True
    else:
        print("Nenhum ícone encontrado")
        return False

def get_rendered_html(url):
    """Captura HTML após renderização do JavaScript."""
    driver = setup_chrome_driver()

    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body"))) 

        # Fecha modals e popups
        close_modals_and_popups(driver)
        
        # Ativa a barra de pesquisa se disponível
        try:
            activate_search_bar(driver)
        except Exception as e:
            print(f"Erro ao ativar busca: {e}")
              
        return driver
    except Exception as e:
        print(f"An error occurred while loading the page: {e}")
        driver.quit()
        return None

def complete_session_reset(driver, url_teste):
    """Reset COMPLETO da sessão do navegador - limpa TUDO mantendo o navegador ativo"""
    try:
        print("🔄 Iniciando reset completo da sessão...")
        
        # 1. Limpa TUDO do navegador
        print("   • Limpando cookies, localStorage, sessionStorage...")
        driver.execute_script("window.localStorage.clear();")
        driver.execute_script("window.sessionStorage.clear();")
        driver.delete_all_cookies()
        
        # 2. Limpa cache e histórico (quando possível)
        try:
            driver.execute_script("window.caches.keys().then(names => names.forEach(name => caches.delete(name)));")
        except:
            pass
            
        # 3. Navega para página limpa
        print("   • Navegando para página limpa...")
        driver.get(url_teste)
        
        # 4. Aguarda carregar completamente
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(1)
        
        # 5. Fecha tudo que pode interferir
        print("   • Fechando modals e interferências...")
        close_modals_and_popups(driver)
        close_sidebar_generic(driver)
        
        # 6. Aguarda estabilizar
        time.sleep(2)
        
        print("✅ Reset completo da sessão finalizado!")
        return driver
        
    except Exception as e:
        print(f"❌ Erro no reset completo: {e}")
        return None

def page_reload(driver, url_teste, campo_id=None):
    """Recarrega a página com reset de sessão - versão eficiente e completa"""
    try:
        print(f"🔄 Reset de página para campo: {campo_id or 'genérico'}")
        
        # Usa reset completo de sessão
        driver = complete_session_reset(driver, url_teste)
        if not driver:
            return None
            
        # Ativa barra de pesquisa APENAS se necessário
        if campo_id == 'mat-input-1':
            print("   • Ativando barra de pesquisa...")
            try:
                activate_search_bar(driver)
            except Exception as e:
                print(f"   ⚠️ Erro ao ativar busca: {e}")
        
        return driver
        
    except Exception as e:
        print(f"❌ Erro no page_reload: {e}")
        return None