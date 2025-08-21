from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

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
            # Verifica se o elemento existe
            if element['name'] and driver.find_element(By.NAME, element['name']):
                input_field = driver.find_element(By.NAME, element['name'])
                input_field.clear() 
                input_field.send_keys(test_text)
                
                results.append({
                    'element': element,
                    'status': 'success',
                    'payload_sent': test_text
                })
                
        except Exception as e:
            results.append({
                'element': element,
                'status': 'failed',
                'error': str(e)
            })
    
    return results


# Uso
html = get_rendered_html("http://localhost:3000/#/login/")
if html:
    html = html.page_source
    found_tags = find_tags(html, TAGS_TO_FIND)
    print(found_tags)
    
