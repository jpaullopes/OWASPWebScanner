"""Manual helper to run the new access analyzer against an existing report."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

access_module = importlib.import_module("owasp_scanner.access.analyzer")
config_module = importlib.import_module("owasp_scanner.core.config")
report_module = importlib.import_module("owasp_scanner.core.report")

run_access_analyzer = getattr(access_module, "run_access_analyzer")
load_configuration = getattr(config_module, "load_configuration")
ReconReport = getattr(report_module, "ReconReport")


TARGET_URL = "http://localhost:3000"
REPORT_PATH = PROJECT_ROOT / "relatorio_spider.json"


def run_test() -> None:
    print("\n--- Iniciando teste manual do Access Analyzer ---")
    print(f"Alvo: {TARGET_URL}")
    print(f"Relatório: {REPORT_PATH}")

    if not REPORT_PATH.exists():
        print("[!] O relatório não foi encontrado. Execute o crawler antes deste teste.")
        return

    config = load_configuration(TARGET_URL, str(REPORT_PATH))
    report = ReconReport.load(REPORT_PATH)

    try:
        accessible = run_access_analyzer(config, report)
    except Exception as exc:  # pragma: no cover - helper script
        print(f"[!] Erro ao executar analisador: {exc}")
        return

    if not accessible:
        print("[-] Nenhuma URL restrita acessível foi identificada.")
    else:
        print("[+] URLs acessíveis sem permissão adequada:")
        for url in accessible:
            print(f"    - {url}")


if __name__ == "__main__":
    run_test()
