"""SQL Injection scanning built on top of sqlmap."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import List

from ...core.report import ReconReport
from ...recon.utils import build_cookie_header

SQLMAP_TIMEOUT = 300


@dataclass(slots=True)
class SqlScanResult:
    target: str
    vulnerable: bool
    raw_output: str


def run_sql_scanner(report: ReconReport) -> List[SqlScanResult]:
    """Runs sqlmap for each target stored in the report."""

    if not report.sqli_targets:
        return []

    cookie_header = build_cookie_header(report.cookies)
    results: List[SqlScanResult] = []

    for target in sorted(report.sqli_targets):
        command = [
            "sqlmap",
            "-u",
            target,
            "--batch",
            "--level",
            "5",
            "--risk",
            "3",
        ]
        if cookie_header:
            command.extend(["--cookie", cookie_header])

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=SQLMAP_TIMEOUT,
            )
            stdout = completed.stdout or ""
        except subprocess.TimeoutExpired:
            results.append(SqlScanResult(target, False, "Timeout"))
            continue

        vulnerable = "the back-end DBMS is" in stdout or "is vulnerable" in stdout
        results.append(SqlScanResult(target, vulnerable, stdout))

    return results
