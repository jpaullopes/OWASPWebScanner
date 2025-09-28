"""Compat package para o antigo módulo de callback."""

from __future__ import annotations

from .xss_http_server import (
    iniciar_servidor_ouvinte,
    limpar_tracking,
    obter_payloads_executados,
    obter_payloads_injetados,
    obter_payloads_recebidos,
    obter_relatorio_detalhado,
    obter_status_tracking,
    registrar_payload_injetado,
)

__all__ = [
    "iniciar_servidor_ouvinte",
    "limpar_tracking",
    "obter_payloads_executados",
    "obter_payloads_injetados",
    "obter_payloads_recebidos",
    "obter_relatorio_detalhado",
    "obter_status_tracking",
    "registrar_payload_injetado",
]