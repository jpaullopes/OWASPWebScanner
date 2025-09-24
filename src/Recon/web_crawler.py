# spider.py
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError
from urllib.parse import urljoin, urlparse
import time
import json

# --- AVISO ---
# Este script é para fins educacionais.
# Execute-o apenas em ambientes de teste autorizados, como o OWASP Juice Shop local.

class Spider:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.urls_to_visit = {base_url}  # Usamos um set para evitar duplicatas
        self.visited_urls = set()
        self.found_targets = {
            "alvos_para_sqli": set(),
            "alvos_para_xss": []
        }
        self.cookies = None

    def close_modals_and_popups(self, page):
        """Tenta fechar modals, popups e aba lateral que podem interferir nos testes"""
        try:
            # Tenta fechar o popup de boas-vindas
            page.locator("button[aria-label='Close Welcome Banner']").click(timeout=2000)
        except PlaywrightTimeoutError:
            pass

        try:
            # Tenta fechar o popup de cookies
            page.locator(".cc-btn.cc-dismiss").click(timeout=2000)
        except PlaywrightTimeoutError:
            pass

        try:
            # Tenta fechar aba lateral (sidenav) se estiver aberta
            sidebar_backdrop = page.locator(
                ".cdk-overlay-backdrop, mat-sidenav-container .mat-drawer-backdrop"
            )
            if sidebar_backdrop.count() > 0:
                sidebar_backdrop.first.click(timeout=2000)
        except PlaywrightTimeoutError:
            pass

        try:
            # Tenta pressionar ESC para fechar outros modais
            page.keyboard.press("Escape")
        except Exception as e:
            print(f"Não foi possível pressionar ESC: {e}")

    def _login(self, page: Page):
        """Faz login na aplicação para obter uma sessão autenticada."""
        print("[*] Tentando fazer login...")
        try:
            login_url = urljoin(self.base_url, "/#/login")
            page.goto(login_url)
            self.close_modals_and_popups(page)  # Fecha modals e popups antes de interagir
            page.get_by_label("Email").fill("admin@juice-sh.op") # Use credenciais de teste
            page.get_by_label("Text field for the login password").fill("admin123")  # Locator mais específico para evitar conflito
            page.get_by_role("button", name="Login").click()
            
            # Espera a navegação para a página principal após o login
            page.wait_for_url(lambda url: "search" in url, timeout=5000)
            
            # Captura os cookies de sessão para usar depois
            self.cookies = page.context.cookies()
            print(f"[+] Login bem-sucedido. Cookies de sessão capturados: {len(self.cookies) if self.cookies else 0} cookies")
            # Adiciona a URL atual à lista de visita, já que estamos logados
            self.urls_to_visit.add(page.url)
        except Exception as e:
            print(f"[-] Falha no login: {e}. O spider continuará sem autenticação.")

    def _extract_data(self, page: Page):
        """Extrai links e formulários da página atual."""
        
        # --- 1. Extrai todos os links ---
        links = page.locator('a').all()
        for link in links:
            try:
                href = link.get_attribute('href')
                if href:
                    # Converte o link relativo (ex: /sobre) para um link absoluto
                    full_url = urljoin(self.base_url, href)
                    
                    # Garante que o spider não saia do domínio alvo
                    if urlparse(full_url).netloc == self.domain:
                        
                        # Se a URL tem parâmetros, é um alvo de alta prioridade para SQLi
                        if '?' in full_url and '=' in full_url:
                            self.found_targets["alvos_para_sqli"].add(full_url)
                        
                        # Adiciona o link à lista de URLs para visitar
                        if full_url not in self.visited_urls:
                            self.urls_to_visit.add(full_url)
            except Exception:
                continue # Ignora links problemáticos

        # --- 2. Extrai todos os formulários ---
        forms = page.locator('form').all()
        for form in forms:
            try:
                action = form.get_attribute('action') or page.url
                form_url = urljoin(self.base_url, action)
                inputs = form.locator('input, textarea, select').all()
                field_names = [i.get_attribute('name') for i in inputs if i.get_attribute('name')]
                
                # Formulários são alvos de alta prioridade para XSS
                self.found_targets["alvos_para_xss"].append({
                    "url_de_envio": form_url,
                    "campos": field_names
                })
            except Exception:
                continue # Ignora formulários problemáticos

    def crawl(self):
        """Executa o processo de crawling."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False) # Mude para True para rodar em background
            context = browser.new_context()
            page = context.new_page()

            # Tenta fazer o login primeiro para ter acesso a mais páginas
            self._login(page)
            
            # Loop principal: continua enquanto houver URLs para visitar
            while self.urls_to_visit:
                url = self.urls_to_visit.pop()
                if url in self.visited_urls:
                    continue

                print(f"[*] Explorando: {url}")
                try:
                    page.goto(url, timeout=5000)
                    self.visited_urls.add(url)
                    self._extract_data(page)
                except Exception as e:
                    print(f"[-] Não foi possível acessar {url}: {e}")

            browser.close()
            self._save_report()

    def _save_report(self):
        """Salva os alvos encontrados em um arquivo JSON."""
        # Converte os sets para listas para poder salvar em JSON
        self.found_targets["alvos_para_sqli"] = list(self.found_targets["alvos_para_sqli"])
        
        # Adiciona os cookies capturados ao relatório
        self.found_targets["cookies"] = self.cookies
        print(f"[*] Salvando relatório com cookies: {self.found_targets['cookies']}")
        
        with open("relatorio_spider.json", "w") as f:
            json.dump(self.found_targets, f, indent=4)
        print("\n[+] Relatório de inteligência salvo em 'relatorio_spider.json'")


if __name__ == "__main__":
    # URL do nosso laboratório
    target = "http://192.168.3.11:3000"
    spider = Spider(target)
    spider.crawl()