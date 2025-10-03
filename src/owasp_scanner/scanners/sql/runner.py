"""SQL Injection scanning built on top of sqlmap."""

from __future__ import annotations

import subprocess
import time

from ...core.report import (
    ReconReport,
    SqlScanArtifact,
    SqlScanResult,
    SqlTargetsArtifact,
)
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


def run_sql_scanner(
    targets: SqlTargetsArtifact | ReconReport,
    *,
    verbose: bool = False,
    timeout: int = DEFAULT_SQLMAP_TIMEOUT,
) -> SqlScanArtifact:
    """Runs sqlmap for each provided target and returns a structured artifact."""

    artifact = targets.as_sql_targets() if isinstance(targets, ReconReport) else targets

    if not artifact.targets:
        return SqlScanArtifact(targets=(), results=[])

    cookie_header = build_cookie_header(artifact.cookies)
    results: list[SqlScanResult] = []
    total = len(artifact.targets)

    print(f" - {total} alvo(s) de SQL Injection identificados (timeout {timeout}s).")
    for index, target in enumerate(artifact.targets, start=1):
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
            results.append(SqlScanResult(target=target, vulnerable=False, raw_output="Timeout"))
            print(f"     - Timeout após {timeout}s")
            continue

        vulnerable = "the back-end DBMS is" in stdout or "is vulnerable" in stdout
        results.append(SqlScanResult(target=target, vulnerable=vulnerable, raw_output=stdout))
        if verbose and stderr:
            print(stderr)
        print("     - Finalizado")

    return SqlScanArtifact(targets=artifact.targets, results=results)
