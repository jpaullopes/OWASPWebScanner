from bs4 import BeautifulSoup
import requests

# Função responsável por encontrar as tags passadas como parâmetro
def find_tags(html_content, tags):
    soup = BeautifulSoup(html_content, 'html.parser')
    found_tags = {}
    for tag in tags:
        found_tags[tag] = [str(element) for element in soup.find_all(tag)]
    return found_tags

html = requests.get("http://localhost:3000/#/login/").text
print(html)

# Exemplo de uso
tags_to_find = ['input', 'form', 'textarea', 'select']
found_tags = find_tags(html, tags_to_find)
print(found_tags)
