import threading
import requests
from playwright.sync_api import sync_playwright

def word_list_reader(word_list):
    """Responsavél por fazer a"""
    url_list = []

    with open(word_list, 'r') as file:
        for word in file:
            url = word.strip()
            url_list.append(url)

 