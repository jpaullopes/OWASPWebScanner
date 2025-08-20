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
        found_tags = {}

        for tag in tags:
            found_tags[tag] = [str(element) for element in soup.find_all(tag)]
        return found_tags
    except Exception as e:
        print(f"An error occurred while parsing HTML: {e}")
        return {tag: [] for tag in tags}

def get_rendered_html(url):
    """Captura HTML após renderização do JavaScript."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  
    driver = webdriver.Chrome(options=chrome_options)

    try:
        driver.get(url)
        # Espera o carregamento completo da página
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body"))) 
        return driver.page_source
    finally:
        driver.quit()


# Uso
html = get_rendered_html("http://localhost:3000/#/login/")
#print(html)

found_tags = find_tags(html, TAGS_TO_FIND)
print(found_tags)
