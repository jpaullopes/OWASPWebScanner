from pathlib import Path
from typing import List

from owasp_scanner.core.config import ScannerConfig
from owasp_scanner.core.report import ReconReport
from owasp_scanner.scanners.dalfox.runner import (
    DALFOX_PLACEHOLDER,
    DalfoxFinding,
    DalfoxRunResult,
    DalfoxTarget,
    _build_target_url,
    _build_targets,
    _normalize_action_url,
    _resolve_parameter_name,
    run_dalfox_scanner,
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


def test_build_target_url_appends_placeholder():
    url = _build_target_url("https://target.test/login", "username")
    assert url == f"https://target.test/login?username={DALFOX_PLACEHOLDER}"


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
    assert targets[0] == DalfoxTarget(
        url=f"https://target.test/login?username={DALFOX_PLACEHOLDER}",
        field_identifier="form::username",
        parameter="username",
    )
    assert targets[1] == DalfoxTarget(
        url=f"https://target.test/login?Token={DALFOX_PLACEHOLDER}",
        field_identifier="form::token",
        parameter="Token",
    )


def test_run_dalfox_scanner_skips_when_binary_missing(monkeypatch):
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
        "owasp_scanner.scanners.dalfox.runner.shutil.which", lambda executable: None
    )

    result = run_dalfox_scanner(_build_config(), report)
    assert isinstance(result, DalfoxRunResult)
    assert result.skipped_reason == "dalfox não encontrado no PATH."
    assert result.findings == []


def test_run_dalfox_scanner_collects_vulnerabilities(monkeypatch):
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
        "owasp_scanner.scanners.dalfox.runner.shutil.which", lambda executable: "/usr/bin/dalfox"
    )

    executed_commands = []

    class DummyCompletedProcess:
        def __init__(self, url: str):
            self.stdout = (
                "[\n"
                "  {\n"
                "    \"param\": \"token\",\n"
                "    \"payload\": \"<img src=x onerror=alert(1)>\",\n"
                "    \"poc\": \"https://target.test/login?token=...\"\n"
                "  }\n"
                "]"
            )
            self.stderr = ""
            self.returncode = 0

    def fake_run(command, *, timeout):
        executed_commands.append((command, timeout))
        return DummyCompletedProcess(command[2])

    monkeypatch.setattr(
        "owasp_scanner.scanners.dalfox.runner._execute_dalfox", fake_run
    )

    result = run_dalfox_scanner(_build_config(), report, timeout=30)

    assert result.skipped_reason is None
    assert len(result.findings) == 1

    finding = result.findings[0]
    assert isinstance(finding, DalfoxFinding)
    assert finding.parameter == "token"
    assert finding.vulnerable is True
    assert finding.vulnerabilities[0]["payload"] == "<img src=x onerror=alert(1)>"
    assert executed_commands[0][0][0] == "/usr/bin/dalfox"
    assert executed_commands[0][1] == 30


def test_run_dalfox_scanner_handles_empty_output(monkeypatch):
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
        "owasp_scanner.scanners.dalfox.runner.shutil.which", lambda executable: "/usr/bin/dalfox"
    )

    def fake_run(command, *, timeout):
        class DummyCompletedProcess:
            stdout = ""
            stderr = ""
            returncode = 0

        return DummyCompletedProcess()

    monkeypatch.setattr(
        "owasp_scanner.scanners.dalfox.runner._execute_dalfox", fake_run
    )

    result = run_dalfox_scanner(_build_config(), report)

    assert result.skipped_reason is None
    assert len(result.findings) == 1
    assert result.findings[0].vulnerable is False
    assert result.findings[0].vulnerabilities == ()
