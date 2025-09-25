# spider.py
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError
from urllib.parse import urljoin, urlparse
import time
import json
import subprocess
import os
from src.modules.Auth.authentication import login_juice_shop

# --- AVISO ---
# Este script é para fins educacionais.
# Execute-o apenas em ambientes de teste autorizados, como o OWASP Juice Shop local.

class Spider:
    def __init__(self, base_url: str, session_cookie: str = None):
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.urls_to_visit = {base_url}  # Usamos um set para evitar duplicatas
        self.visited_urls = set()
        self.found_targets = {
            "alvos_para_sqli": set(),
            "alvos_para_xss": []
        }
        self.cookies = []
        if session_cookie:
            # Adiciona cookie de sessão se fornecido
            self.cookies = [{"name": "session", "value": session_cookie, "domain": self.domain}]

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

            # Se não há cookies, tenta login
            if not self.cookies:
                self.cookies = login_juice_shop(page, self.base_url)
                if self.cookies:
                    self.urls_to_visit.add(page.url)
            else:
                # Adiciona cookies ao contexto
                context.add_cookies(self.cookies)
                page.goto(self.base_url)
            
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
            self._enumerate_directories()
            self._save_report()

    def _enumerate_directories(self):
        """Executa enumeração de diretórios usando ffuf."""
        print("\n[*] Iniciando enumeração de diretórios com ffuf...")
        
        # Verifica se ffuf está instalado
        try:
            subprocess.run(["ffuf", "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("[!] ffuf não encontrado. Pule a enumeração de diretórios.")
            print("   Instale com: go install github.com/ffuf/ffuf@latest")
            return
        
        # Cria uma wordlist básica se não existir
        wordlist_path = "dir_wordlist.txt"
        if not os.path.exists(wordlist_path):
            basic_words = [
                "admin", "api", "backup", "config", "dashboard", "debug", "ftp", "login", "private", "test", "upload", "user"
            ]
            with open(wordlist_path, "w") as f:
                f.write("\n".join(basic_words))
            print(f"[*] Wordlist básica criada em {wordlist_path}")
        
        # Prepara cookies para ffuf
        cookie_header = ""
        if self.cookies:
            cookie_parts = [f"{c['name']}={c['value']}" for c in self.cookies]
            cookie_header = f"Cookie: {'; '.join(cookie_parts)}"
        
        # Comando ffuf
        cmd = [
            "ffuf",
            "-u", f"{self.base_url}/FUZZ",
            "-w", wordlist_path,
            "-mc", "200,403,401",  # Match codes: 200 (ok), 403 (forbidden), 401 (unauthorized)
            "-t", "10",  # Threads
            "-o", "ffuf_output.json",
            "-of", "json"
        ]
        if cookie_header:
            cmd.extend(["-H", cookie_header])
        
        try:
            print(f"[*] Executando: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                print("[+] Enumeração concluída. Processando resultados...")
                self._process_ffuf_results("ffuf_output.json")
            else:
                print(f"[-] ffuf falhou: {result.stderr}")
        except subprocess.TimeoutExpired:
            print("[-] Timeout na enumeração de diretórios.")
        except Exception as e:
            print(f"[-] Erro na enumeração: {e}")

    def _process_ffuf_results(self, output_file):
        """Processa os resultados do ffuf e adiciona ao relatório."""
        if not os.path.exists(output_file):
            return
        
        with open(output_file, "r") as f:
            data = json.load(f)
        
        for result in data.get("results", []):
            url = result["url"]
            status = result["status"]
            if url not in self.visited_urls:
                print(f"[+] Diretório encontrado: {url} (Status: {status})")
                # Adiciona como alvo para SQLi se tiver parâmetros (pode ser API)
                if '?' in url:
                    self.found_targets["alvos_para_sqli"].add(url)
                else:
                    # Adiciona como alvo geral, talvez para access control
                    if "alvos_para_access" not in self.found_targets:
                        self.found_targets["alvos_para_access"] = set()
                    self.found_targets["alvos_para_access"].add(url)
        
        # Limpa arquivo temporário
        os.remove(output_file)

    def _save_report(self):
        """Salva os alvos encontrados em um arquivo JSON."""
        # Converte os sets para listas para poder salvar em JSON
        self.found_targets["alvos_para_sqli"] = list(self.found_targets["alvos_para_sqli"])
        if "alvos_para_access" in self.found_targets:
            self.found_targets["alvos_para_access"] = list(self.found_targets["alvos_para_access"])
        
        # Adiciona os cookies capturados ao relatório
        self.found_targets["cookies"] = self.cookies
        print(f"[*] Salvando relatório com cookies: {self.found_targets['cookies']}")
        
        with open("relatorio_spider.json", "w") as f:
            json.dump(self.found_targets, f, indent=4)
        print("\n[+] Relatório de inteligência salvo em 'relatorio_spider.json'")


if __name__ == "__main__":
    # URL do alvo via env ou padrão
    target = os.getenv("TARGET_URL", "http://192.168.3.11:3000")
    session_cookie = os.getenv("SESSION_COOKIE")
    spider = Spider(target, session_cookie)
    spider.crawl()