from .scanner import XSSScanner

# Configurações padrão
TAGS_TO_FIND = ["input", "form", "textarea", "select"]


def run_xss_scan(
    page, browser, url_ouvinte, url_original, playwright_instance, campos_interativos
):
    """Executa o scan de XSS completo"""
    scanner = XSSScanner(
        page, browser, url_ouvinte, url_original, playwright_instance
    )
    return scanner.run_scan(campos_interativos)
