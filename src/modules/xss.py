from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

TAGS_TO_FIND = ['input', 'form', 'textarea', 'select']

def find_tags(html_content, tags):
    """Função responsável por encontrar as tags passadas como parâmetro"""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        found_tags = []

        for tag in tags:
            foud_tag_elements = soup.find_all(tag)
            for tag_elements in foud_tag_elements:
                if tag_elements:
                    tag_info = { "name" : tag_elements.get('name'),
                                "id" :  tag_elements.get('id'),
                                "type" : tag_elements.get('type'),
                                }
                    found_tags.append(tag_info)
        return found_tags
    except Exception as e:
        print(f"An error occurred while parsing HTML: {e}")
        return []

def get_rendered_html(url):
    """Captura HTML após renderização do JavaScript."""
    chrome_options = Options()
    #chrome_options.add_argument("--headless")  
    driver = webdriver.Chrome(options=chrome_options)

    try:
        driver.get(url)
        # Espera o carregamento completo da página
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body"))) 
        time.sleep(3)
        
        # Tenta fechar modal/popup comum
        try:
            # Procura botão de fechar (X)
            close_button = driver.find_element(By.XPATH, "//button[contains(@class, 'close') or contains(@aria-label, 'close') or text()='×']")
            close_button.click()
            time.sleep(1)
        except:
            try:
                # Procura botão "Dismiss" ou "OK"
                dismiss_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Dismiss') or contains(text(), 'OK') or contains(text(), 'Close')]")
                dismiss_button.click()
                time.sleep(1)
            except:
                try:
                    # Tenta clicar fora do modal (no backdrop)
                    backdrop = driver.find_element(By.CLASS_NAME, "cdk-overlay-backdrop")
                    backdrop.click()
                    time.sleep(1)
                except:
                    try:
                        # Pressiona ESC para fechar modal
                        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                        time.sleep(1)
                    except:
                        pass
        
        # Tenta clicar na lupa de busca para ativar o campo
        try:
            search_icon = driver.find_element(By.XPATH, "//mat-icon[text()='search']")
            search_icon.click()
            time.sleep(2)  
        except:
            try:
                search_button = driver.find_element(By.XPATH, "//button[contains(@aria-label, 'search')]")
                search_button.click()
                time.sleep(2)
            except:
                pass
                
        return driver
    except Exception as e:
        print(f"An error occurred while loading the page: {e}")
        driver.quit()
        return None

def eco_test(lista, driver, test_text):
    """Função de teste para enviar um texto nos campos de input."""
    results = []
    
    for element in lista:
        try:
            input_field = None
            
            # Pula checkboxes e outros tipos não-texto
            if element.get('type') in ['checkbox', 'radio', 'submit', 'button']:
                results.append({
                    'element': element,
                    'status': 'skipped',
                    'error': f"Skipped {element.get('type')} element"
                })
                continue
            
            # Tenta encontrar por ID primeiro
            if element['id']:
                try:
                    input_field = driver.find_element(By.ID, element['id'])
                    
                    # Para campos Angular Material, aguarda mais tempo
                    if 'mat-input' in element['id']:
                        time.sleep(2)
                    
                    # Rola até o elemento e clica nele para ativar
                    driver.execute_script("arguments[0].scrollIntoView();", input_field)
                    input_field.click()
                    time.sleep(0.5)  # Aguarda um pouco após o clique
                    # Aguarda o elemento ficar interagível
                    WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, element['id'])))
                except:
                    pass
            
            # Se não encontrou por ID, tenta por NAME
            if not input_field and element['name']:
                try:
                    input_field = driver.find_element(By.NAME, element['name'])
                    driver.execute_script("arguments[0].scrollIntoView();", input_field)
                    input_field.click()
                    time.sleep(0.5)
                    WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.NAME, element['name'])))
                except:
                    pass
                    
            if input_field:
                # Só tenta clear() se não for checkbox/radio
                try:
                    input_field.clear() 
                except:
                    pass  # Se clear() falhar, continua sem limpar
                
                input_field.send_keys(test_text)

                try:
                    # Procura pelo botão de submit
                    submit_button = driver.find_element(By.XPATH, "//button[@type='submit']")
                    submit_button.click()
                except:
                    # Procura por um botão de login específico
                    try:
                        login_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Log in')]")
                        login_button.click()
                    except:
                        # Preciona Enter 
                        input_field.send_keys(Keys.RETURN)
                
                results.append({
                    'element': element,
                    'status': 'success',
                    'payload_sent': test_text,
                    'eco_text': eco_verificator(driver, test_text)
                })
            else:
                results.append({
                    'element': element,
                    'status': 'failed',
                    'error': 'Element not found by ID or NAME'
                })
                
        except Exception as e:
            results.append({
                'element': element,
                'status': 'failed',
                'error': str(e)
            })
    
    return results

def eco_verificator(driver, eco_text):
    """Verifica se o texto enviado foi processado corretamente."""
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        body_text = driver.find_element(By.TAG_NAME, "body").text
        if eco_text in body_text:
            return True
        return False
    except Exception as e:
        print(f"An error occurred during verification: {e}")
        return False

driver = get_rendered_html("http://localhost:3000/#/search")
if driver:
    html = driver.page_source
    found_tags = find_tags(html, TAGS_TO_FIND)
    
    # Testa os campos encontrados
    test_results = eco_test(found_tags, driver,"TESTANDO")
    # Filtra apenas os sucessos
    successful_results = [result for result in test_results if result['status'] == 'success']
    print(test_results)
    print(f"Resultados do teste: {successful_results}")
    
    driver.quit()

