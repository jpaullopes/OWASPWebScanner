import subprocess as real_subprocess
from types import SimpleNamespace

from tests.helpers.pytest_import import pytest
from tests.helpers.owasp_imports import dependencies


def test_check_tool_returns_false_when_missing(monkeypatch):
    monkeypatch.setattr(dependencies.shutil, "which", lambda _: None)

    assert dependencies.check_tool(["sqlmap"]) is False


def test_verify_dependencies_handles_success(monkeypatch):
    commands = []

    monkeypatch.setattr(dependencies.shutil, "which", lambda _: "/usr/bin/fake")

    def fake_run(command, capture_output, text, check):
        commands.append(command)
        return real_subprocess.CompletedProcess(command, 0)

    namespace = SimpleNamespace(
        run=fake_run,
        CalledProcessError=real_subprocess.CalledProcessError,
    )
    monkeypatch.setattr(dependencies, "subprocess", namespace)

    results = dependencies.verify_dependencies()

    assert all(results.values())
    assert commands
    for command in commands:
        assert command[0] in {tool[0] for tool in dependencies.REQUIRED_TOOLS}


def test_verify_dependencies_handles_failure(monkeypatch):
    monkeypatch.setattr(dependencies.shutil, "which", lambda _: "/usr/bin/fake")

    def fake_run(command, capture_output, text, check):
        raise real_subprocess.CalledProcessError(returncode=1, cmd=command)

    namespace = SimpleNamespace(
        run=fake_run,
        CalledProcessError=real_subprocess.CalledProcessError,
    )
    monkeypatch.setattr(dependencies, "subprocess", namespace)

    results = dependencies.verify_dependencies()

    assert any(result is False for result in results.values())
