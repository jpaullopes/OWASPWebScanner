from requests import get, exceptions
from bs4 import BeautifulSoup

def html_extractor(url):
    try:
        html = get(url)
        return BeautifulSoup(html.text, "html.parser")
    except exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return
