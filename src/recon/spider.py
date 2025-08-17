from requests import get, exceptions
from bs4 import BeautifulSoup

def html_extractor(url):
    try:
        html = get(url)
        return html.text
    except exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return

def 