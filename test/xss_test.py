from src.modules.server_ouvinte import iniciar_servidor_ouvinte, obter_status_tracking, obter_relatorio_detalhado,obter_payloads_executados,limpar_tracking
from pyngrok import ngrok
from src.modules.xss import get_rendered_html, find_tags, blind_xss_injection, eco_test
import time

# Configuração de Tags para encontrar campos de entrada
TAGS_TO_FIND = ['input', 'form', 'textarea', 'select']

# Configurações do servidor ouvinte
porta = 8000

print("OWASP WEB SCANNER - BLIND XSS TESTER")

# Inicia o servidor ouvinte em uma thread separada
print("Iniciando servidor ouvinte")
iniciar_servidor_ouvinte(porta)

# Cria o túnel ngrok para expor o servidor local
#print("Criando túnel ngrok")
#ngrok_tunnel = ngrok.connect(porta)
url_ouvinte = f'http://localhost:{porta}'
print(f"Servidor ouvinte exposto em: {url_ouvinte}")
print()

# Limpa dados anteriores de tracking
limpar_tracking()

# Exemplo de uso do Blind XSS
print("Iniciando teste de Blind XSS")
# Url de teste
url_teste = "http://localhost:3000/#/login"  
driver = get_rendered_html(url_teste)
if driver:
    print("Página carregada com sucesso")
    
    # Extrai campos da página
    html = driver.page_source
    found_tags = find_tags(html, TAGS_TO_FIND)
    print(f"{len(found_tags)} campos encontrados na página")
    
    # Teste de eco com os campos encontrados
    print("Executando teste de eco para validar campos")
    eco_results = eco_test(found_tags, driver, "TEXTPASSIVE")
    successful_results = [result for result in eco_results if result['status'] == 'success']
    print(f"{len(successful_results)} campos válidos identificados")
    
    if successful_results:
        # Mostra campos válidos
        print("\nCAMPOS VÁLIDOS PARA TESTE:")
        for i, result in enumerate(successful_results, 1):
            element = result['element']
            field_name = element.get('name') or element.get('id', 'sem-nome')
            print(f"{i}. {field_name} (tipo: {element.get('type', 'text')})")
        print()
        
        # Recarregar a pagina para a url de teste para evitar problemas de estado
        driver.quit()
        driver = get_rendered_html(url_teste)
        # Teste de Blind XSS com os campos validados
        print("Iniciando injeção de payloads Blind XSS")
        blind_xss_results = blind_xss_injection(successful_results, driver, url_ouvinte)
        
        # Mostra resultados imediatos
        print(f"{len(blind_xss_results)} payloads injetados com sucesso")
        
        # Aguarda um tempo para possíveis callbacks
        print("Aguardando callbacks de Blind XSS")
        print("Aguardando 30 segundos para detectar execuções")
        
        time.sleep(30)

        print("RELATÓRIO FINAL DE BLIND XSS")
        # Obtém relatório detalhado
        relatorio = obter_relatorio_detalhado()
        
        print(f"RESUMO:")
        print(f" Payloads injetados: {relatorio['resumo']['total_injetados']}")
        print(f" Callbacks recebidos: {relatorio['resumo']['total_recebidos']}")
        print(f" Payloads executados: {relatorio['resumo']['total_executados']}")
        print(f" Taxa de sucesso: {relatorio['resumo']['taxa_sucesso']}")
        print()
        
        # Mostra campos vulneráveis
        if relatorio['campos_vulneraveis']:
            print("CAMPOS VULNERÁVEIS A BLIND XSS:")
            for campo in relatorio['campos_vulneraveis']:
                print(f" {campo}")
            print()
        
        # Mostra payloads executados
        executados = relatorio['payloads_executados']
        if executados:
            print("PAYLOADS EXECUTADOS COM SUCESSO:")
            for payload_id, info in executados.items():
                print(f" {payload_id}: {info['campo_name']} ({info['payload']})")
                print(f"     Executado em: {info.get('executed_at', 'N/A')}")
            print()
        else:
            print("NENHUM PAYLOAD FOI EXECUTADO")
            print(" Possíveis causas: CSP, filtros, campos não vulneráveis")
            print()
    
    else:
        print("Nenhum campo válido encontrado para teste")
    
    driver.quit()
    print("Navegador fechado")

else:
    print("Erro ao carregar a página de teste")

print("\nMantendo servidor ouvinte ativo para callbacks tardios")
print("Pressione Ctrl+C para encerrar")

# Mantém o servidor ouvinte ativo para capturar requisições tardias
try:
    while True:
        time.sleep(5)
        status = obter_status_tracking()
        if status['total_executados'] > 0:
            pass
        
except KeyboardInterrupt:
    print("\nEncerrando servidor ouvinte")
    
    # Mostra relatório final antes de encerrar
    final_status = obter_status_tracking()
    if final_status['total_executados'] > 0:
        print(f"RESULTADO FINAL: {final_status['total_executados']} payload(s) executado(s)")
    #ngrok.disconnect(url_ouvinte)
    print("Sistema encerrado")


    