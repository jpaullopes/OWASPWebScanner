from pathlib import Path

from owasp_scanner.core.config import ScannerConfig
from owasp_scanner.recon.crawler_legacy import Spider


def _build_spider() -> Spider:
    config = ScannerConfig(
        target_url="http://example.com",
        session_cookie=None,
        report_path=Path("report.json"),
    )
    return Spider(config)


def test_field_info_prefers_placeholder_over_dynamic_id():
    spider = _build_spider()
    field_info = spider._build_field_info_from_values(
        name=None,
        element_id="mat-input-0",
        aria="Search",
        placeholder="Search for products",
        data_testid=None,
        field_type="text",
        tag="input",
    )

    assert field_info is not None
    assert field_info["identifier"] == "placeholder::Search for products"
    assert field_info["attributes"]["id"] == "mat-input-0"


def test_field_info_falls_back_to_id_when_no_preferred_attributes():
    spider = _build_spider()
    field_info = spider._build_field_info_from_values(
        name=None,
        element_id="unique-id-123",
        aria=None,
        placeholder=None,
        data_testid=None,
        field_type="text",
        tag="input",
    )

    assert field_info is not None
    assert field_info["identifier"] == "id::unique-id-123"
