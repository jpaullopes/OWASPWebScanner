"""
Compat layer for the legacy Access Analyzer module.

Historically ``url_scanner`` lived here; now it proxies to
``owasp_scanner.access.analyzer.run_access_analyzer`` while preserving the old
return signature and console messages.
"""

from __future__ import annotations

from pathlib import Path

from owasp_scanner.access.analyzer import run_access_analyzer
from owasp_scanner.core.config import load_configuration
from owasp_scanner.core.report import ReconReport

__all__ = ["url_scanner"]


def url_scanner(login_url: str, base_url: str, report_path: str = "relatorio_spider.json", headless: bool = False):
    """Mantém compatibilidade com o antigo helper ``url_scanner``.

    Os parâmetros ``login_url`` e ``headless`` são ignorados, pois a nova
    implementação consulta credenciais e opções a partir da configuração e do
    relatório consolidado.
    """

    path = Path(report_path)
    if not path.exists():
        print(f"[!] Relatório '{report_path}' não encontrado. Execute o crawler primeiro.")
        return []

    config = load_configuration(base_url, report_path)
    report = ReconReport.load(path)

    accessible = run_access_analyzer(config, report)

    if accessible:
        print("[+] URLs acessíveis identificadas:")
        for url in accessible:
            print(f"    - {url}")
    else:
        print("[-] Nenhuma URL restrita acessível encontrada.")

    return accessible

