"""Command line interface for the OWASP Web Scanner."""

from __future__ import annotations

import argparse
from pathlib import Path

from .access.analyzer import run_access_analyzer
from .callback.server import CallbackServer, tracker
from .core.config import load_configuration
from .core.dependencies import verify_dependencies
# O crawler baseado em Scrapy foi descontinuado em favor de uma abordagem Playwright direta.
from .recon.crawler import Spider as PlaywrightSpider
from .scanners.dalfox import run_dalfox_scanner
from .scanners.sql.runner import run_sql_scanner
from .scanners.xss.runner import run_xss_scanner


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OWASP Web Scanner")
    parser.add_argument("-u", "--url", required=True, help="URL do alvo")
    parser.add_argument("--callback-port", type=int, default=8080, help="Porta do servidor de callback")
    parser.add_argument("--report", default="relatorio_spider.json", help="Arquivo de saída do relatório")
    parser.add_argument("--verbose-ffuf", action="store_true", help="Mostra a execução detalhada do ffuf")
    parser.add_argument("--verbose-sql", action="store_true", help="Exibe a saída completa do sqlmap")
    parser.add_argument("--sql-timeout", type=int, default=10, help="Tempo máximo (s) por alvo do sqlmap")
    return parser.parse_args()


def print_dependency_status() -> bool:
    status = verify_dependencies()
    missing = [name for name, ok in status.items() if not ok]
    for name, ok in status.items():
        print(f"[{'+' if ok else '!'}] {name} {'encontrado' if ok else 'não encontrado'}")
    if missing:
        print("[!] Instale as dependências acima antes de continuar.")
        return False
    return True


def run_cli() -> None:
    args = parse_arguments()
    config = load_configuration(
        args.url,
        args.report,
        ffuf_verbose=args.verbose_ffuf,
        sql_verbose=args.verbose_sql,
        sql_timeout=args.sql_timeout,
    )

    print("[*] Verificando dependências...")
    if not print_dependency_status():
        return

    print("\n=== [1/5] Reconhecimento ===")
    print("[+] Utilizando o crawler Playwright (SPA-friendly).")
    spider = PlaywrightSpider(config)
    report = spider.run()
    report_path = Path(config.report_path)
    report.save(report_path, deduplicate_spa=getattr(config, 'deduplicate_spa_urls', False))
    print(f"[+] Relatório salvo em {report_path}")

    sql_targets = report.as_sql_targets()
    xss_targets = report.as_xss_targets()
    access_targets = report.as_access_targets()

    callback_server = CallbackServer(args.callback_port, tracker)
    callback_url = f"http://localhost:{args.callback_port}"

    print("\n=== [2/5] Servidor de Callback ===")
    callback_server.start()
    print(f"[+] Servidor ouvindo em {callback_url}")

    print("\n=== [3/5] SQL Injection ===")
    sql_results = run_sql_scanner(sql_targets, verbose=config.sql_verbose, timeout=config.sql_timeout)
    if sql_results.results:
        for result in sql_results.results:
            status = "VULNERÁVEL" if result.vulnerable else "OK"
            print(f" - {status} :: {result.target}")
    else:
        print(" - Nenhum alvo de SQL Injection identificado.")

    print("\n=== [4/5] XSS (Playwright) ===")
    xss_results = run_xss_scanner(config, xss_targets, callback_url)
    if xss_results.findings:
        for entry in xss_results.findings:
            print(f" - Payload {entry['payload_id']} em {entry['field']}")
    else:
        print(" - Nenhum campo com eco positivo foi identificado.")

    print("\n=== [5/5] Dalfox XSS ===")
    dalfox_result = run_dalfox_scanner(config, xss_targets)
    if dalfox_result.skipped_reason:
        print(f" - {dalfox_result.skipped_reason}")
    elif dalfox_result.findings:
        for finding in dalfox_result.findings:
            status = "VULNERÁVEL" if finding.vulnerable else "OK"
            print(f" - {status} :: {finding.parameter} em {finding.url}")
            if finding.vulnerabilities:
                for vuln in finding.vulnerabilities:
                    payload = vuln.get("payload")
                    poc = vuln.get("poc")
                    if payload:
                        print(f"   Payload: {payload}")
                    if poc:
                        print(f"   PoC: {poc}")
            if finding.error:
                print(f"   Erro: {finding.error}")
    else:
        print(" - Nenhum alvo processado pelo Dalfox.")

    print("\n=== Análise de Acesso ===")
    access_results = run_access_analyzer(config, access_targets)
    if access_results.accessible_urls:
        for url in access_results.accessible_urls:
            print(f" - Acesso permitido: {url}")
    else:
        print(" - Nenhuma URL restrita acessível encontrada.")

    callback_server.stop()


def main() -> None:
    run_cli()


if __name__ == "__main__":
    main()
