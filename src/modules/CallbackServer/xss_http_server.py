"""Compat layer for the legacy callback server module.

All logic now lives in ``owasp_scanner.callback.server``; the helper functions here
keep backwards compatibility with the earlier API used in the repository.
"""

from __future__ import annotations

from typing import Dict, Optional

from owasp_scanner.callback.server import CallbackServer, register_payload, tracker

__all__ = [
    "iniciar_servidor_ouvinte",
    "registrar_payload_injetado",
    "obter_payloads_injetados",
    "obter_payloads_recebidos",
    "obter_payloads_executados",
    "obter_status_tracking",
    "obter_relatorio_detalhado",
    "limpar_tracking",
]


_CURRENT_SERVER: Optional[CallbackServer] = None


def iniciar_servidor_ouvinte(porta: int) -> CallbackServer:
    """Inicia o servidor de callback de Blind XSS e retorna a instância."""

    global _CURRENT_SERVER

    if _CURRENT_SERVER is None:
        _CURRENT_SERVER = CallbackServer(porta, tracker)
        _CURRENT_SERVER.start()
    return _CURRENT_SERVER


def registrar_payload_injetado(campo_id: str | None, campo_name: str | None, payload: str, url_origem: str) -> str:
    return register_payload(campo_id, campo_name, payload, url_origem)


def obter_payloads_injetados() -> Dict[str, object]:
    return tracker.injected.copy()


def obter_payloads_recebidos() -> Dict[str, object]:
    return tracker.received.copy()


def obter_payloads_executados() -> Dict[str, object]:
    return {k: v for k, v in tracker.injected.items() if v.status == "executed"}


def obter_status_tracking() -> Dict[str, int]:
    executados = sum(1 for info in tracker.injected.values() if info.status == "executed")
    return {
        "total_injetados": len(tracker.injected),
        "total_recebidos": len(tracker.received),
        "total_executados": executados,
    }


def obter_relatorio_detalhado() -> Dict[str, object]:
    executados = obter_payloads_executados()
    campos = {info.field_name for info in executados.values() if info.field_name}
    return {
        "resumo": obter_status_tracking(),
        "payloads_injetados": obter_payloads_injetados(),
        "callbacks_recebidos": obter_payloads_recebidos(),
        "payloads_executados": executados,
        "campos_vulneraveis": sorted(campos),
    }


def limpar_tracking() -> None:
    tracker.injected.clear()
    tracker.received.clear()
    global _CURRENT_SERVER
    if _CURRENT_SERVER is not None:
        _CURRENT_SERVER.stop()
        _CURRENT_SERVER = None
