from bs4 import BeautifulSoup

# Função responsável por encontrar as tags passadas como parâmetro
def find_tags(html_content, tags):
    soup = BeautifulSoup(html_content, 'html.parser')
    found_tags = {}
    for tag in tags:
        found_tags[tag] = [str(element) for element in soup.find_all(tag)]
    return found_tags

