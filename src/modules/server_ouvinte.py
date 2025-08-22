import http.server
import socketserver
import threading
from pyngrok import ngrok
import time
import uuid
from datetime import datetime
from urllib.parse import urlparse, parse_qs

# Sistema de Tracking de Payloads
payload_tracker = {
    'injected': {},  # Payloads injetados: {id: {info}}
    'received': {}   # Callbacks recebidos: {id: {info}}
}


# Ela define o que acontece quando um pedido do nosso payload chega.
class XSSRequestHandler(http.server.BaseHTTPRequestHandler):
    # Esta função é chamada automaticamente quando chega um pedido GET (como o do fetch).
    def do_GET(self):
        print("\n[!!!] BLIND XSS CONFIRMADO! Chamada recebida!")
        print(f"[+] O pedido veio de: {self.client_address[0]}")
        print(f"[+] Alvo do pedido: {self.path}") # Podemos até passar info no URL
        
        # Enviamos uma resposta OK para o navegador da vítima.
        self.send_response(200)
        self.end_headers()

# Esta função prepara e inicia o nosso servidor numa thread separada.
def iniciar_servidor_ouvinte(porta):
    # Criamos o servidor com o nosso "atendedor de chamadas".
    servidor = socketserver.TCPServer(("", porta), XSSRequestHandler)
    print(f"[*] Servidor ouvinte iniciado na porta {porta}.")
    
    # Colocamos o servidor para correr numa thread.
    thread_servidor = threading.Thread(target=servidor.serve_forever)
    thread_servidor.daemon = True
    thread_servidor.start()


# Executando a criação do servidor
porta = 8000
iniciar_servidor_ouvinte(porta)
# Criando túnel ngrok para expor o servidor local
ngrok_tunnel = ngrok.connect(porta)
print(ngrok_tunnel)
time.sleep(30)
ngrok.disconnect(ngrok_tunnel.public_url)

def gerar_id_payload():
    """Gera um ID único para cada payload injetado."""
    return str(uuid.uuid4())[:8] 

def registrar_payload_injetado(campo_id, campo_name, payload, url_origem):
    """Registra um payload que foi injetado em um campo."""
    payload_id = gerar_id_payload()
    
    payload_tracker['injected'][payload_id] = {
        'id': payload_id,
        'timestamp': datetime.now().isoformat(),
        'campo_id': campo_id,
        'campo_name': campo_name,
        'payload': payload,
        'url_origem': url_origem,
        'status': 'injected'
    }
    
    print(f"[+] Payload registrado: {payload_id} no campo {campo_name or campo_id}")
    return payload_id

def obter_payloads_injetados():
    """Retorna todos os payloads que foram injetados."""
    return payload_tracker['injected'].copy()

def obter_payloads_recebidos():
    """Retorna todos os callbacks que foram recebidos."""
    return payload_tracker['received'].copy()

def obter_status_tracking():
    """Retorna estatísticas do tracking."""
    total_injetados = len(payload_tracker['injected'])
    total_recebidos = len(payload_tracker['received'])
    
    return {
        'total_injetados': total_injetados,
        'total_recebidos': total_recebidos
        }