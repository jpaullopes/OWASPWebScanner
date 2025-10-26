"""Access control checks based on reconnaissance results."""

from __future__ import annotations

import concurrent.futures
from typing import Iterable, List

import requests

from ..core.config import ScannerConfig
from ..core.report import AccessAnalysisArtifact, AccessTargetsArtifact, ReconReport

MAX_THREADS = 15


def _prepare_session(cookies: Iterable[dict]) -> requests.Session:
    session = requests.Session()
    for cookie in cookies:
        name = cookie.get("name")
        value = cookie.get("value")
        domain = cookie.get("domain")
        if name and value:
            session.cookies.set(name, value, domain=domain)
    return session


def _check_url(session: requests.Session, url: str) -> str | None:
    try:
        response = session.get(url, timeout=6, allow_redirects=False, stream=True)
        if response.status_code == 200:
            return url
    except requests.RequestException:
        return None
    return None


def run_access_analyzer(
    config: ScannerConfig,  # noqa: ARG001 - config reserved for future use
    targets: AccessTargetsArtifact | ReconReport,
) -> AccessAnalysisArtifact:
    """Executes the broken access control checks."""

    artifact = targets.as_access_targets() if isinstance(targets, ReconReport) else targets

    if not artifact.urls:
        return AccessAnalysisArtifact(checked_urls=(), accessible_urls=[])

    session = _prepare_session(artifact.cookies)
    accessible: List[str] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        futures = {executor.submit(_check_url, session, url): url for url in artifact.urls}
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                accessible.append(result)

    return AccessAnalysisArtifact(checked_urls=artifact.urls, accessible_urls=sorted(accessible))
