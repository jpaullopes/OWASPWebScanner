import http.server
import socketserver
import threading
import uuid
from datetime import datetime
from urllib.parse import parse_qs, urlparse

# Sistema de Tracking de Payloads
payload_tracker = {
    "injected": {},  # Payloads injetados: {id: {info}}
    "received": {},  # Callbacks recebidos: {id: {info}}
}


# Ela define o que acontece quando um pedido do nosso payload chega.
class XSSRequestHandler(http.server.BaseHTTPRequestHandler):
    # Esta função é chamada automaticamente quando chega um pedido GET.
    def do_GET(self):
        try:
            # Analisa a URL e extrai parâmetros
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)

            print("\n[!!!] BLIND XSS CONFIRMADO! Chamada recebida!")
            print(f"[+] O pedido veio de: {self.client_address[0]}")
            print(f"[+] Caminho completo: {self.path}")
            print(f"[+] Timestamp: {datetime.now().isoformat()}")

            # Extrai o ID do payload se presente
            payload_id = None
            if "id" in query_params:
                payload_id = query_params["id"][0]
                print(f"[+] Payload ID identificado: {payload_id}")

                # Correlaciona com payload injetado
                if payload_id in payload_tracker["injected"]:
                    payload_info = payload_tracker["injected"][payload_id]
                    print("[+] Correlação encontrada!")
                    print(
                        f"    Campo alvo: {payload_info['campo_name']}" 
                        f"({payload_info['campo_id']})"
                    )
                    print(f"    URL origem: {payload_info['url_origem']}")
                    print(f"    Payload: {payload_info['payload']}")
                    print(f"    Injetado em: {payload_info['timestamp']}")
                else:
                    print("[!] Payload ID não encontrado no tracker")

            # Registra o callback recebido
            self._registrar_callback_recebido(payload_id, parsed_url, query_params)

        except Exception as e:
            print(f"[!] Erro ao processar callback: {e}")

        # Enviamos uma resposta OK para o navegador da vítima.
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"OK")

    def _registrar_callback_recebido(self, payload_id, parsed_url, query_params):
        """Registra informações detalhadas do callback recebido."""
        callback_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().isoformat()

        callback_info = {
            "callback_id": callback_id,
            "timestamp": timestamp,
            "payload_id": payload_id,
            "client_ip": self.client_address[0],
            "client_port": self.client_address[1],
            "path": parsed_url.path,
            "query_params": dict(query_params),
            "full_url": self.path,
            "user_agent": self.headers.get("User-Agent", "Unknown"),
            "referer": self.headers.get("Referer", "Unknown"),
            "status": "received",
        }

        # Armazena no tracker
        payload_tracker["received"][callback_id] = callback_info

        # Se payload_id existe, marca como executado
        if payload_id and payload_id in payload_tracker["injected"]:
            payload_tracker["injected"][payload_id]["status"] = "executed"
            payload_tracker["injected"][payload_id]["callback_id"] = callback_id
            payload_tracker["injected"][payload_id]["executed_at"] = timestamp

        print(f"[+] Callback registrado: {callback_id}")

    def log_message(self, format, *args):
        """Suprime logs padrão do servidor HTTP para manter saída limpa."""
        pass


# Esta função prepara e inicia o nosso servidor numa thread separada.
def iniciar_servidor_ouvinte(porta):
    # Criamos o servidor com o nosso "atendedor de chamadas".
    servidor = socketserver.TCPServer(("", porta), XSSRequestHandler)
    print(f"[*] Servidor ouvinte iniciado na porta {porta}.")

    # Colocamos o servidor para correr numa thread.
    thread_servidor = threading.Thread(target=servidor.serve_forever)
    thread_servidor.daemon = True
    thread_servidor.start()


def gerar_id_payload():
    """Gera um ID único para cada payload injetado."""
    return str(uuid.uuid4())[:8]


def registrar_payload_injetado(campo_id, campo_name, payload, url_origem):
    """Registra um payload que foi injetado em um campo."""
    payload_id = gerar_id_payload()

    payload_tracker["injected"][payload_id] = {
        "id": payload_id,
        "timestamp": datetime.now().isoformat(),
        "campo_id": campo_id,
        "campo_name": campo_name,
        "payload": payload,
        "url_origem": url_origem,
        "status": "injected",
    }

    print(f"[+] Payload registrado: {payload_id} no campo {campo_name or campo_id}")
    return payload_id


def obter_payloads_injetados():
    """Retorna todos os payloads que foram injetados."""
    return payload_tracker["injected"].copy()


def obter_payloads_recebidos():
    """Retorna todos os callbacks que foram recebidos."""
    return payload_tracker["received"].copy()


def obter_status_tracking():
    """Retorna estatísticas do tracking."""
    total_injetados = len(payload_tracker["injected"])
    total_recebidos = len(payload_tracker["received"])

    # Conta quantos payloads foram executados com sucesso
    executados = sum(
        1 for p in payload_tracker["injected"].values() if p["status"] == "executed"
    )

    return {
        "total_injetados": total_injetados,
        "total_recebidos": total_recebidos,
        "total_executados": executados,
    }


def obter_payloads_executados():
    """Retorna apenas os payloads que foram executados com sucesso."""
    return {
        k: v
        for k, v in payload_tracker["injected"].items()
        if v["status"] == "executed"
    }


def obter_relatorio_detalhado():
    """Retorna relatório completo do teste de Blind XSS."""
    status = obter_status_tracking()
    executados = obter_payloads_executados()

    relatorio = {
        "resumo": status,
        "payloads_injetados": payload_tracker["injected"].copy(),
        "callbacks_recebidos": payload_tracker["received"].copy(),
        "payloads_executados": executados,
        "campos_vulneraveis": list(set(p["campo_name"]
        for p in executados.values())),
    }

    return relatorio


def limpar_tracking():
    """Limpa todos os dados de tracking."""
    payload_tracker["injected"].clear()
    payload_tracker["received"].clear()
    print("[*] Dados de tracking limpos.")
