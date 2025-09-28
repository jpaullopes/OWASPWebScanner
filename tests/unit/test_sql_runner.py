import subprocess as real_subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from owasp_scanner.core.report import ReconReport  # type: ignore[import]
from owasp_scanner.scanners.sql import runner as sql_runner  # type: ignore[import]


def test_run_sql_scanner_marks_vulnerable(monkeypatch):
    report = ReconReport(
        sqli_targets={"https://example.com/items?id=1"},
        cookies=[{"name": "session", "value": "abc"}],
    )

    commands = []

    def fake_run(command, capture_output, text, timeout):
        commands.append(command)
        return real_subprocess.CompletedProcess(command, 0, stdout="the back-end DBMS is MySQL", stderr="")

    namespace = SimpleNamespace(run=fake_run, TimeoutExpired=real_subprocess.TimeoutExpired)
    monkeypatch.setattr(sql_runner, "subprocess", namespace)

    results = sql_runner.run_sql_scanner(report)

    assert len(results) == 1
    assert results[0].vulnerable is True
    assert any("--cookie" in command for command in commands)
    assert any("session=abc" in command for command in commands)


def test_run_sql_scanner_handles_timeout(monkeypatch):
    report = ReconReport(sqli_targets={"https://example.com/items?id=1"})

    def fake_run(command, capture_output, text, timeout):  # noqa: ARG001
        raise real_subprocess.TimeoutExpired(cmd=command, timeout=timeout)

    namespace = SimpleNamespace(run=fake_run, TimeoutExpired=real_subprocess.TimeoutExpired)
    monkeypatch.setattr(sql_runner, "subprocess", namespace)

    results = sql_runner.run_sql_scanner(report)

    assert len(results) == 1
    assert results[0].vulnerable is False
    assert results[0].raw_output == "Timeout"
