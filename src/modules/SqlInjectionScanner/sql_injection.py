# maestro.py
"""
SQL Injection Scanner Module

Este módulo detecta vulnerabilidades de Injeção SQL em aplicações web.
Utiliza sqlmap para executar testes automatizados em URLs alvo.

Funcionalidades:
- Leitura de alvos do relatório do crawler
- Execução de sqlmap com cookies de sessão
- Detecção baseada em indicadores de saída

Limitações:
- Depende de sqlmap instalado
- Pode gerar falsos positivos/negativos
- Timeout fixo de 5 minutos por alvo

Exemplo de Uso:
    python sql_injection.py  # Executa após crawler gerar relatório
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List

from owasp_scanner.core.report import ReconReport
from owasp_scanner.recon.utils import build_cookie_header
from owasp_scanner.scanners.sql.runner import SqlScanResult, run_sql_scanner

__all__ = ["format_cookies", "run_sqli_scan"]


def format_cookies(cookies_list: Iterable[dict]) -> str:
    """Mantém a função utilitária utilizada pelos scripts antigos."""

    return build_cookie_header(cookies_list)


def _string_to_cookies(cookie_string: str) -> List[dict]:
    cookies: List[dict] = []
    for part in cookie_string.split(";"):
        name, sep, value = part.strip().partition("=")
        if sep and name and value:
            cookies.append({"name": name, "value": value})
    return cookies


def run_sqli_scan(targets: Iterable[str], cookie_string: str):  # pragma: no cover - legacy helper
    report = ReconReport(sqli_targets=set(targets))
    if cookie_string:
        report.cookies = _string_to_cookies(cookie_string)

    results = run_sql_scanner(report)
    for result in results:
        status = "VULNERÁVEL" if result.vulnerable else "OK"
        print(f" - {status} :: {result.target}")

    return results


if __name__ == "__main__":  # pragma: no cover - legacy helper
    report_path = Path("relatorio_spider.json")
    if not report_path.exists():
        print("ERRO: Arquivo de relatório 'relatorio_spider.json' não encontrado.")
    else:
        data = json.loads(report_path.read_text(encoding="utf-8"))
        targets = data.get("alvos_para_sqli", [])
        cookies = data.get("cookies", [])
        if not targets:
            print("Nenhum alvo para SQL Injection encontrado no relatório.")
        else:
            cookie_str = format_cookies(cookies)
            run_sqli_scan(targets, cookie_str)