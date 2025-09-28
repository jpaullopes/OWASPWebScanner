import json

from tests.helpers.owasp_imports import ReconReport


def test_report_to_json_sorted_lists():
    report = ReconReport(
        sqli_targets={"b", "a"},
        xss_forms=[{"url": "https://app/form", "campos": ["q"]}],
        access_targets={"/admin", "/profile"},
        cookies=[{"name": "session", "value": "abc"}],
    )

    data = json.loads(report.to_json())

    assert data["alvos_para_sqli"] == ["a", "b"]
    assert data["alvos_para_access"] == ["/admin", "/profile"]
    assert data["cookies"] == [{"name": "session", "value": "abc"}]


def test_report_save_and_load(tmp_path):
    report = ReconReport(
        sqli_targets={"https://app/items?id=1"},
        xss_forms=[{"url_de_envio": "https://app/form", "campos": ["name"]}],
        access_targets={"https://app/admin"},
        cookies=[{"name": "session", "value": "token", "domain": "app"}],
    )

    path = tmp_path / "report.json"
    report.save(path)

    loaded = ReconReport.load(path)
    assert loaded == report
