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
    chrome_options.add_argument("--headless")  
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
    if not search_icon:
        try:
            search_icon = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, "//mat-icon[contains(text(), 'search')]"))
            )
            print("Encontrou mat-icon com texto 'search'")
        except:
            pass
    
    # Estratégia 3: qualquer mat-icon na barra superior (toolbar)
    if not search_icon:
        try:
            search_icon = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "mat-toolbar mat-icon"))
            )
            print("Encontrou mat-icon genérico na toolbar")
        except:
            pass
    
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
