from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time


# Função responsável por encontrar as tags passadas como parâmetro
def find_tags(html_content, tags):
    soup = BeautifulSoup(html_content, 'html.parser')
    found_tags = {}

    for tag in tags:
        found_tags[tag] = [str(element) for element in soup.find_all(tag)]
    return found_tags

#Captura HTML após renderização do JavaScript.
def get_rendered_html(url):
    chrome_options = Options()
    chrome_options.add_argument("--headless")  
    driver = webdriver.Chrome(options=chrome_options)

    try:
        driver.get(url)
        # Aguarda carregamento completo
        time.sleep(3)  
        return driver.page_source
    finally:
        driver.quit()


# Uso
html = get_rendered_html("http://localhost:3000/#/login/")
#print(html)

TAGS_TO_FIND = ['input', 'form', 'textarea', 'select']
found_tags = find_tags(html, TAGS_TO_FIND)
print(found_tags)
