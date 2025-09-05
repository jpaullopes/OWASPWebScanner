import time

from playwright.sync_api import sync_playwright

from src.modules.server import iniciar_servidor_ouvinte, obter_relatorio_detalhado
from src.modules.xss import blind_xss_injection, eco_test
from src.recon import find_tags, get_rendered_page

# --- Configurações ---
URL_ALVO = "http://localhost:8000"
TAGS_PARA_BUSCAR = ["input", "textarea", "select"]
TEXTO_ECO_TEST = "TEXTO!@#$%"
PORTA_OUVINTE = 8080
URL_OUVINTE = f"http://localhost:{PORTA_OUVINTE}"


def main():
    """Função principal para orquestrar o scanner."""
    page = None
    browser = None

    try:
        # 1. Iniciar o servidor ouvinte em uma thread separada
        iniciar_servidor_ouvinte(PORTA_OUVINTE)
        print(f"Servidor ouvinte iniciado em {URL_OUVINTE}")
        time.sleep(1)  # Dá um tempo para o servidor iniciar

        # 2. Iniciar o Playwright e navegar para a página
        with sync_playwright() as p:
            page, browser = get_rendered_page(p, URL_ALVO)
            if not page:
                print("Falha ao carregar a página. Encerrando.")
                return

            # 3. Extrair o HTML renderizado e encontrar campos
            html_content = page.content()
            campos_encontrados = find_tags(html_content, TAGS_PARA_BUSCAR)
            print(f"Encontrados {len(campos_encontrados)} campos para teste.")

            # 4. Executar o teste de eco para validar os campos
            print("Executando teste de eco para validar campos...")
            resultados_eco = eco_test(campos_encontrados, page, TEXTO_ECO_TEST)
            campos_validos = [
                res
                for res in resultados_eco
                if res.get("status") == "success" and res.get("eco_text", False)
            ]
            print(
                f"Encontrados {len(campos_validos)} campos que refletem o input"
                "(vulneráveis a eco)."
            )

            # 5. Injetar payloads de Blind XSS
            if campos_validos:
                print("\n--- Iniciando injeção de Blind XSS ---")
                injected_payloads = blind_xss_injection(
                    campos_validos, page, browser, URL_OUVINTE, URL_ALVO, p
                )
                print(f"Total de {len(injected_payloads)} payloads injetados.")
            else:
                print("Nenhum campo válido para injeção de Blind XSS encontrado.")
                print("Resultados do eco test:")
                for res in resultados_eco:
                    print(
                        f"  - Status: {res.get('status')}, Eco: {res.get('eco_text')}" 
                        f"Erro: {res.get('error', 'N/A')}"
                    )

            # 6. Aguardar um tempo para possíveis callbacks
            print("\nAguardando 15 segundos por callbacks de Blind XSS...")
            time.sleep(15)

    except Exception as e:
        print(f"Ocorreu um erro na execução principal: {e}")

    finally:
        # 7. Gerar o relatório final
        print("\n--- Relatório Final de Blind XSS ---")
        relatorio = obter_relatorio_detalhado()
        if not relatorio["payloads_executados"]:
            print("Nenhum payload foi executado com sucesso.")
        else:
            print("Payloads executados com sucesso:")
            for payload_id, info in relatorio["payloads_executados"].items():
                print(f"  - ID: {payload_id}")
                print(f"    Campo: {info['campo_name']} ({info['campo_id']})")
                print(f"    URL: {info['url_origem']}")
                print(f"    Executado em: {info['executed_at']}")

        if browser and browser.is_connected():
            browser.close()
            print("\nNavegador fechado.")


main()
