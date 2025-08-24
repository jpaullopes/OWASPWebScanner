import sys
import os
import requests
from playwright.sync_api import sync_playwright
from src.modules.sql_injection.sql_injection import sql_injection_test, bypass_sql_injection_list

# Adiciona o diretório raiz ao sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


url_login = "http://localhost:3000/#/login"
bypassed = sql_injection_test(bypass_sql_injection_list, url_login)
if bypassed:
    print("\n--- Possíveis Injeções SQL Encontradas ---")
    for field, payload, resp in bypassed:
        print(f"Campo: {field} <|> Payload: {payload} <|> Email: {resp.get("authentication", {}).get("umail", "Não encontrado")}")