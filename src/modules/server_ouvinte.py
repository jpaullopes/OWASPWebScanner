import http.server
import socketserver
import threading
from pyngrok import ngrok
import time
import uuid
from datetime import datetime

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