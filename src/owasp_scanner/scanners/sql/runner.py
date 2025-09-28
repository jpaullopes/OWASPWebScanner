"""SQL Injection scanning built on top of sqlmap."""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from typing import List

from ...core.report import ReconReport
from ...recon.utils import build_cookie_header

DEFAULT_SQLMAP_TIMEOUT = 120


def _stream_sqlmap(command: list[str], timeout: int) -> tuple[str, str]:
    process = subprocess.Popen(  # type: ignore[arg-type]
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    assert process.stdout is not None

    output_lines: list[str] = []
    deadline = time.monotonic() + timeout

    try:
        while True:
            if time.monotonic() > deadline:
                process.kill()
                raise subprocess.TimeoutExpired(command, timeout)

            line = process.stdout.readline()
            if line:
                print(line, end="")
                output_lines.append(line)
                continue

            if process.poll() is not None:
                # ensure we consume any trailing data
                remainder = process.stdout.read()
                if remainder:
                    print(remainder, end="")
                    output_lines.append(remainder)
                break

            time.sleep(0.1)
    finally:
        process.stdout.close()
        process.wait()

    return ("".join(output_lines), "")


@dataclass(slots=True)
class SqlScanResult:
    target: str
    vulnerable: bool
    raw_output: str


def run_sql_scanner(
    report: ReconReport,
    *,
    verbose: bool = False,
    timeout: int = DEFAULT_SQLMAP_TIMEOUT,
) -> List[SqlScanResult]:
    """Runs sqlmap for each target stored in the report."""

    if not report.sqli_targets:
        return []

    cookie_header = build_cookie_header(report.cookies)
    results: List[SqlScanResult] = []
    targets = sorted(report.sqli_targets)
    total = len(targets)

    print(f" - {total} alvo(s) de SQL Injection identificados (timeout {timeout}s).")
    for index, target in enumerate(targets, start=1):
        print(f"   > [{index}/{total}] Executando sqlmap contra {target}")
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
            if verbose:
                print("[sqlmap] comando:", " ".join(command))
                stdout, stderr = _stream_sqlmap(command, timeout)
            else:
                completed = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
                stdout = completed.stdout or ""
                stderr = completed.stderr or ""
        except subprocess.TimeoutExpired:
            results.append(SqlScanResult(target, False, "Timeout"))
            print(f"     - Timeout após {timeout}s")
            continue

        vulnerable = "the back-end DBMS is" in stdout or "is vulnerable" in stdout
        results.append(SqlScanResult(target, vulnerable, stdout))
        if verbose and stderr:
            print(stderr)
        print("     - Finalizado")

    return results
