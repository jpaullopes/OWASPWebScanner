from src.modules.sql_injection import bypass_sql_injection_list, sql_injection_test

url_login = "http://localhost:3000/#/login"
bypassed = sql_injection_test(bypass_sql_injection_list, url_login)
if bypassed:
    print("\n--- Possíveis Injeções SQL Encontradas ---")
    for field, payload, resp in bypassed:
        print(
            f"Campo: {field} <|> Payload: {payload} <|> Email: "
            f"{resp.get('authentication', {}).get('umail', 'Não encontrado')}"
        )
