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
            
            # Tenta encontrar por ID primeiro
            if element['id']:
                try:
                    input_field = driver.find_element(By.ID, element['id'])
                    # Rola até o elemento e clica nele para ativar
                    driver.execute_script("arguments[0].scrollIntoView();", input_field)
                    input_field.click()
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
                    WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.NAME, element['name'])))
                except:
                    pass
                    
            if input_field:
                input_field.clear() 
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
    print(f"Resultados do teste: {test_results}")
    
    driver.quit()
    
