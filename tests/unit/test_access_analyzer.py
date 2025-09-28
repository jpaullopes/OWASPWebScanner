from tests.helpers.owasp_imports import ReconReport, ScannerConfig, analyzer


def make_config(tmp_path):
    return ScannerConfig(
        target_url="https://example.com",
        session_cookie=None,
        report_path=tmp_path / "report.json",
    )


def test_run_access_analyzer_returns_accessible_urls(monkeypatch, tmp_path):
    report = ReconReport(access_targets={"https://example.com/admin", "https://example.com/profile"})

    calls = []

    monkeypatch.setattr(analyzer, "_prepare_session", lambda _: "session")

    def fake_check(session, url):
        calls.append((session, url))
        return url if url.endswith("/admin") else None

    monkeypatch.setattr(analyzer, "_check_url", fake_check)

    result = analyzer.run_access_analyzer(make_config(tmp_path), report)

    assert result == ["https://example.com/admin"]
    assert {call[1] for call in calls} == {
        "https://example.com/admin",
        "https://example.com/profile",
    }


def test_run_access_analyzer_returns_empty_when_no_targets(tmp_path):
    report = ReconReport()

    assert analyzer.run_access_analyzer(make_config(tmp_path), report) == []
