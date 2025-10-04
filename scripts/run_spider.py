"""Helper script to execute the reconnaissance spider in isolation.

Allows running the crawler against a single URL without invoking the
full CLI pipeline. Useful for quick smoke tests or debugging the
reconnaissance stage.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from owasp_scanner.core.config import load_configuration
from owasp_scanner.recon.crawler_legacy import Spider


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Executa somente o crawler (Spider) em uma URL alvo"
    )
    parser.add_argument(
        "url",
        help="URL base do alvo. Utilize apenas ambientes sob sua autorização",
    )
    parser.add_argument(
        "--report",
        default="relatorio_spider.json",
        help="Arquivo de saída do relatório (JSON). Padrão: relatorio_spider.json",
    )
    parser.add_argument(
        "--headless",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Força execução headless (padrão vem de .env/variáveis de ambiente)",
    )
    parser.add_argument(
        "--session-cookie",
        help="Cookie de sessão para reutilizar uma conta autenticada",
    )
    parser.add_argument(
        "--email",
        help="E-mail para login automático (substitui EMAIL_LOGIN do .env se fornecido)",
    )
    parser.add_argument(
        "--password",
        help="Senha para login automático (substitui PASSWORD_LOGIN do .env se fornecido)",
    )
    return parser.parse_args()


def override_if_provided(current: Optional[str], new: Optional[str]) -> Optional[str]:
    return new if new else current


def count_collection(obj, *attribute_names: str) -> int:
    for name in attribute_names:
        if hasattr(obj, name):
            collection = getattr(obj, name)
            if collection is None:
                return 0
            try:
                return len(collection)
            except TypeError:
                return 0
    return 0


def main() -> None:
    args = parse_arguments()

    config = load_configuration(
        target_url=args.url,
        report_name=args.report,
    )

    if args.headless is not None:
        config.headless = args.headless
    config.session_cookie = override_if_provided(config.session_cookie, args.session_cookie)
    config.auth_email = override_if_provided(config.auth_email, args.email)
    config.auth_password = override_if_provided(config.auth_password, args.password)

    spider = Spider(config)

    print(f"[*] Iniciando crawler para {config.target_url}")
    try:
        report = spider.run()
    except KeyboardInterrupt:
        print("[!] Execução interrompida pelo usuário")
        return

    report_path = Path(config.report_path)
    report.save(report_path)

    print(f"[+] Relatório salvo em {report_path}")
    urls_count = count_collection(report, "discovered_urls", "urls_descobertas")
    xss_count = count_collection(report, "xss_forms", "alvos_para_xss")
    sql_count = count_collection(report, "sqli_targets", "alvos_para_sqli")
    access_count = count_collection(report, "access_targets", "alvos_para_access")
    cookies_count = count_collection(report, "cookies")

    print(f"    URLs descobertas        : {urls_count}")
    print(f"    Formulários para XSS    : {xss_count}")
    print(f"    Alvos para SQL Injection: {sql_count}")
    print(f"    Alvos para Access Ctrl  : {access_count}")
    print(f"    Cookies capturados      : {cookies_count}")


if __name__ == "__main__":
    main()
