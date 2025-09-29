from pathlib import Path
from typing import List

from owasp_scanner.core.config import ScannerConfig
from owasp_scanner.core.report import ReconReport
from owasp_scanner.scanners.xssstrike.runner import (
    XSSStrikeRunResult,
    XSSStrikeTarget,
    XSSSTRIKE_PARAM_VALUE,
    _build_target_url,
    _build_targets,
    _normalize_action_url,
    _resolve_parameter_name,
    run_xssstrike_scanner,
)


def _build_report(forms: List[dict]) -> ReconReport:
    return ReconReport(xss_forms=forms)


def _build_config() -> ScannerConfig:
    return ScannerConfig(
        target_url="https://target.test",
        session_cookie=None,
        report_path=Path("/tmp/report.json"),
        headless=True,
    )


def test_normalize_action_url_strips_fragment_paths():
    assert _normalize_action_url("https://target.test/#/login") == "https://target.test/login"


def test_resolve_parameter_name_prefers_name_field():
    field = {
        "identifier": "form::username",
        "attributes": {"name": "username", "placeholder": "user", "label": "Login"},
    }
    assert _resolve_parameter_name(field) == "username"


def test_build_target_url_appends_payload():
    url = _build_target_url("https://target.test/login", "username")
    assert url == f"https://target.test/login?username={XSSSTRIKE_PARAM_VALUE}"


def test_build_targets_generates_unique_entries():
    report = _build_report(
        [
            {
                "url_de_envio": "https://target.test/login",
                "campos": [
                    {
                        "identifier": "form::username",
                        "attributes": {"name": "username"},
                    },
                    {
                        "identifier": "form::token",
                        "attributes": {"placeholder": "Token"},
                    },
                    {
                        "identifier": "form::token",
                        "attributes": {"placeholder": "Token"},
                    },
                ],
            }
        ]
    )

    targets = _build_targets(report.xss_forms)
    assert len(targets) == 2
    assert targets[0] == XSSStrikeTarget(
        target_url=f"https://target.test/login?username={XSSSTRIKE_PARAM_VALUE}",
        field_identifier="form::username",
        parameter="username",
    )
    assert targets[1] == XSSStrikeTarget(
        target_url=f"https://target.test/login?Token={XSSSTRIKE_PARAM_VALUE}",
        field_identifier="form::token",
        parameter="Token",
    )


def test_run_xssstrike_scanner_skips_when_binary_missing(monkeypatch):
    report = _build_report(
        [
            {
                "url_de_envio": "https://target.test/login",
                "campos": [
                    {
                        "identifier": "form::username",
                        "attributes": {"name": "username"},
                    }
                ],
            }
        ]
    )
    monkeypatch.setattr(
        "owasp_scanner.scanners.xssstrike.runner.shutil.which", lambda executable: None
    )

    result = run_xssstrike_scanner(_build_config(), report)
    assert isinstance(result, XSSStrikeRunResult)
    assert result.skipped_reason == "xssstrike não encontrado no PATH."


def test_run_xssstrike_scanner_collects_output(monkeypatch):
    report = _build_report(
        [
            {
                "url_de_envio": "https://target.test/login",
                "campos": [
                    {
                        "identifier": "form::token",
                        "attributes": {"name": "token"},
                    }
                ],
            }
        ]
    )

    monkeypatch.setattr(
        "owasp_scanner.scanners.xssstrike.runner.shutil.which", lambda executable: "/usr/bin/xssstrike"
    )

    executed_commands = []

    class DummyCompletedProcess:
        def __init__(self, url: str):
            self.stdout = f"[INF] Testing {url}...\n[VUL] Reflected XSS discovered -- vulnerable"
            self.stderr = ""
            self.returncode = 0

    def fake_run(command, *, capture_output, text, timeout, check):
        executed_commands.append(command)
        return DummyCompletedProcess(command[-1])

    monkeypatch.setattr(
        "owasp_scanner.scanners.xssstrike.runner.subprocess.run", fake_run
    )

    result = run_xssstrike_scanner(_build_config(), report, timeout=15)

    assert result.skipped_reason is None
    assert len(result.results) == 1
    payload_record = result.results[0]
    assert payload_record["parameter"] == "token"
    assert payload_record["vulnerable"] is True
    assert "Reflected XSS" in payload_record["output"]
    assert executed_commands and executed_commands[0][0] == "/usr/bin/xssstrike"


def test_run_xssstrike_scanner_reports_no_skip_when_binary_exists(monkeypatch):
    monkeypatch.setattr(
        "owasp_scanner.scanners.xssstrike.runner.shutil.which", lambda executable: "/usr/bin/xssstrike"
    )

    result = run_xssstrike_scanner(_build_config(), _build_report([]))
    assert isinstance(result, XSSStrikeRunResult)
    assert result.skipped_reason is None