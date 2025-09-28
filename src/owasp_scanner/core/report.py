"""Utilities to manage the shared reconnaissance report."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Set


@dataclass
class ReconReport:
    """Structured data produced by the crawler phase."""

    sqli_targets: Set[str] = field(default_factory=set)
    xss_forms: List[Dict[str, Any]] = field(default_factory=list)
    access_targets: Set[str] = field(default_factory=set)
    cookies: List[Dict[str, Any]] = field(default_factory=list)

    def to_json(self) -> str:
        data = {
            "alvos_para_sqli": sorted(self.sqli_targets),
            "alvos_para_xss": self.xss_forms,
            "alvos_para_access": sorted(self.access_targets),
            "cookies": self.cookies,
        }
        return json.dumps(data, indent=4)

    def save(self, path: Path) -> None:
        path.write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "ReconReport":
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            sqli_targets=set(raw.get("alvos_para_sqli", [])),
            xss_forms=list(raw.get("alvos_para_xss", [])),
            access_targets=set(raw.get("alvos_para_access", [])),
            cookies=list(raw.get("cookies", [])),
        )
