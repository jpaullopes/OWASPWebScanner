"""Blind XSS callback server utilities."""

from __future__ import annotations

import http.server
import socketserver
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional
from urllib.parse import parse_qs, urlparse


@dataclass
class PayloadInfo:
    payload_id: str
    timestamp: str
    field_id: str | None
    field_name: str | None
    payload: str
    origin_url: str
    status: str = "injected"
    callback_id: str | None = None
    executed_at: str | None = None


@dataclass
class CallbackInfo:
    callback_id: str
    timestamp: str
    payload_id: str | None
    client_ip: str
    client_port: int
    path: str
    query: dict
    full_path: str
    user_agent: str
    referer: str


@dataclass
class PayloadTracker:
    injected: Dict[str, PayloadInfo] = field(default_factory=dict)
    received: Dict[str, CallbackInfo] = field(default_factory=dict)

    def register_payload(
        self,
        field_id: str | None,
        field_name: str | None,
        payload: str,
        origin_url: str,
    ) -> str:
        payload_id = str(uuid.uuid4())[:8]
        info = PayloadInfo(
            payload_id=payload_id,
            timestamp=datetime.now().isoformat(),
            field_id=field_id,
            field_name=field_name,
            payload=payload,
            origin_url=origin_url,
        )
        self.injected[payload_id] = info
        return payload_id

    def register_callback(
        self,
        payload_id: Optional[str],
        request_handler: http.server.BaseHTTPRequestHandler,
    ) -> CallbackInfo:
        callback_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().isoformat()
        parsed = urlparse(request_handler.path)
        query_params = parse_qs(parsed.query)

        info = CallbackInfo(
            callback_id=callback_id,
            timestamp=timestamp,
            payload_id=payload_id,
            client_ip=request_handler.client_address[0],
            client_port=request_handler.client_address[1],
            path=parsed.path,
            query=query_params,
            full_path=request_handler.path,
            user_agent=request_handler.headers.get("User-Agent", "Unknown"),
            referer=request_handler.headers.get("Referer", "Unknown"),
        )
        self.received[callback_id] = info

        if payload_id and payload_id in self.injected:
            payload_info = self.injected[payload_id]
            payload_info.status = "executed"
            payload_info.callback_id = callback_id
            payload_info.executed_at = timestamp

        return info


def _handler_factory(tracker: PayloadTracker):
    class RequestHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # type: ignore[override]
            payload_id = None
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            if "id" in params:
                payload_id = params["id"][0]

            tracker.register_callback(payload_id, self)

            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")

        def log_message(self, format: str, *args) -> None:  # pragma: no cover - silence default logging
            return

    return RequestHandler


@dataclass
class CallbackServer:
    port: int
    tracker: PayloadTracker
    _server: socketserver.TCPServer | None = None
    _thread: threading.Thread | None = None

    def start(self) -> None:
        if self._server:
            return
        handler = _handler_factory(self.tracker)
        self._server = socketserver.TCPServer(("", self.port), handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if not self._server:
            return
        self._server.shutdown()
        self._server.server_close()
        self._server = None
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None


tracker = PayloadTracker()


def register_payload(field_id: str | None, field_name: str | None, payload: str, origin_url: str) -> str:
    return tracker.register_payload(field_id, field_name, payload, origin_url)
