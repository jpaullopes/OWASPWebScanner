import json

from tests.helpers.owasp_imports import ReconReport


def test_report_to_json_sorted_lists():
    report = ReconReport(
        seed_url="https://app",
        discovered_urls={"https://app", "https://app/form"},
        sqli_targets={"b", "a"},
        xss_forms=[
            {
                "url_de_envio": "https://app/form",
                "campos": [
                    {
                        "identifier": "q",
                        "attributes": {
                            "name": "q",
                            "type": "text",
                            "tag": "input",
                        },
                    }
                ],
            }
        ],
        access_targets={"/admin", "/profile"},
        cookies=[{"name": "session", "value": "abc"}],
    )

    data = json.loads(report.to_json())

    assert data["seed_url"] == "https://app"
    assert data["urls_descobertas"] == ["https://app", "https://app/form"]
    assert data["alvos_para_sqli"] == ["a", "b"]
    assert data["alvos_para_access"] == ["/admin", "/profile"]
    assert data["cookies"] == [{"name": "session", "value": "abc"}]


def test_report_save_and_load(tmp_path):
    report = ReconReport(
        seed_url="https://app",
        discovered_urls={"https://app", "https://app/admin"},
        sqli_targets={"https://app/items?id=1"},
        xss_forms=[
            {
                "url_de_envio": "https://app/form",
                "campos": [
                    {
                        "identifier": "name",
                        "attributes": {
                            "name": "name",
                            "id": "input-name",
                            "aria_label": "Name",
                            "placeholder": "Name",
                            "type": "text",
                            "tag": "input",
                        },
                    }
                ],
            }
        ],
        access_targets={"https://app/admin"},
        cookies=[{"name": "session", "value": "token", "domain": "app"}],
    )

    path = tmp_path / "report.json"
    report.save(path)

    loaded = ReconReport.load(path)
    assert loaded == report
