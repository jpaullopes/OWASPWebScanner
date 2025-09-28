"""Manual helper to exercise the XSS scanner and callback server."""

from __future__ import annotations

import importlib
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

callback_module = importlib.import_module("owasp_scanner.callback.server")
config_module = importlib.import_module("owasp_scanner.core.config")
report_module = importlib.import_module("owasp_scanner.core.report")
xss_module = importlib.import_module("owasp_scanner.scanners.xss.runner")

CallbackServer = getattr(callback_module, "CallbackServer")
tracker = getattr(callback_module, "tracker")
load_configuration = getattr(config_module, "load_configuration")
ReconReport = getattr(report_module, "ReconReport")
run_xss_scanner = getattr(xss_module, "run_xss_scanner")


TARGET_URL = "http://localhost:3000"
CALLBACK_PORT = 8000
REPORT_PATH = PROJECT_ROOT / "relatorio_spider.json"


def run_test() -> None:
    print("\n--- Executando teste manual do XSS Scanner ---")
    print(f"Alvo: {TARGET_URL}")
    print(f"Relatório: {REPORT_PATH}")
    print(f"Callback: http://localhost:{CALLBACK_PORT}")

    if not REPORT_PATH.exists():
        print("[!] O relatório não foi encontrado. Execute o crawler antes deste teste.")
        return

    config = load_configuration(TARGET_URL, str(REPORT_PATH))
    report = ReconReport.load(REPORT_PATH)

    if not report.xss_forms:
        print("[-] Nenhum formulário registrado no relatório.")
        return

    callback_server = CallbackServer(CALLBACK_PORT, tracker)
    callback_server.start()

    print("[*] Servidor de callback iniciado. Aguardando injeções...")

    try:
        results = run_xss_scanner(config, report, f"http://localhost:{CALLBACK_PORT}")
        if not results:
            print("[-] Nenhuma injeção foi realizada (nenhum campo com eco positivo).")
        else:
            print(f"[+] {len(results)} payload(s) injetados. Aguardando callbacks...")
            time.sleep(15)

            received = tracker.received
            if not received:
                print("[-] Nenhum callback recebido até o momento.")
            else:
                print("[+] Callbacks recebidos:")
                for cb_id, info in received.items():
                    print(f"    - {cb_id} :: payload={info.payload_id} from {info.client_ip}")
    except Exception as exc:  # pragma: no cover - helper script
        print(f"[!] Erro ao executar scanner de XSS: {exc}")
    finally:
        callback_server.stop()
        print("[*] Servidor de callback finalizado.")


if __name__ == "__main__":
    run_test()
