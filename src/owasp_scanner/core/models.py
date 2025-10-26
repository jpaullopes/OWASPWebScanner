"""Shared data structures used across scanners."""

from __future__ import annotations

from typing import Optional, TypedDict


class FieldAttributes(TypedDict, total=False):
    """Describes identifying attributes for an input field."""

    name: Optional[str]
    id: Optional[str]
    aria_label: Optional[str]
    placeholder: Optional[str]
    data_testid: Optional[str]
    type: Optional[str]
    tag: Optional[str]


class FieldInfo(TypedDict):
    """Represents a single input field discovered by the crawler."""

    identifier: str
    attributes: FieldAttributes
