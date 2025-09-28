"""Manual helper to run the SQL injection scanner using the consolidated report."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

report_module = importlib.import_module("owasp_scanner.core.report")
sql_module = importlib.import_module("owasp_scanner.scanners.sql.runner")

ReconReport = getattr(report_module, "ReconReport")
run_sql_scanner = getattr(sql_module, "run_sql_scanner")
SqlScanResult = getattr(sql_module, "SqlScanResult")

REPORT_PATH = PROJECT_ROOT / "relatorio_spider.json"


def run_sql_injection_test() -> None:
    print("\n--- Executando teste manual do SQL Injection Scanner ---")
    print(f"Relatório: {REPORT_PATH}")

    if not REPORT_PATH.exists():
        print("[!] O relatório não foi encontrado. Execute o crawler antes deste teste.")
        return

    report = ReconReport.load(REPORT_PATH)

    if not report.sqli_targets:
        print("[-] Nenhum alvo SQLi registrado no relatório.")
        return

    results = run_sql_scanner(report)
    if not results:
        print("[-] Nenhuma análise foi executada.")
        return

    for result in results:
        status = "VULNERÁVEL" if getattr(result, "vulnerable", False) else "OK"
        print(f" - {status} :: {result.target}")


if __name__ == "__main__":
    run_sql_injection_test()