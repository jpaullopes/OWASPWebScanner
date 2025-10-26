"""Helper utilities used by recon modules."""

from __future__ import annotations

from typing import Iterable, Optional, Tuple

from ..core.models import FieldAttributes, FieldInfo


def build_cookie_header(cookies: Optional[Iterable[dict]]) -> str:
    if not cookies:
        return ""
    pieces = []
    for cookie in cookies:
        name = cookie.get("name")
        value = cookie.get("value")
        if name and value:
            pieces.append(f"{name}={value}")
    return "; ".join(pieces)


def choose_field_identifier(
    *,
    name: Optional[str],
    element_id: Optional[str],
    aria: Optional[str],
    placeholder: Optional[str],
    data_testid: Optional[str],
) -> Optional[str]:
    """Best-effort identifier for an input field."""

    if name:
        return name

    priority_attributes: Tuple[Tuple[Optional[str], str], ...] = (
        (data_testid, "data-testid::"),
        (placeholder, "placeholder::"),
        (aria, "aria::"),
    )
    for value, prefix in priority_attributes:
        if value:
            return f"{prefix}{value}"

    if element_id:
        return f"id::{element_id}"

    return None


def build_field_info_from_values(
    *,
    name: Optional[str],
    element_id: Optional[str],
    aria: Optional[str],
    placeholder: Optional[str],
    data_testid: Optional[str],
    field_type: Optional[str] = None,
    tag: Optional[str] = None,
) -> Optional[FieldInfo]:
    """Creates a :class:`FieldInfo` dictionary from raw tag attributes."""

    identifier = choose_field_identifier(
        name=name,
        element_id=element_id,
        aria=aria,
        placeholder=placeholder,
        data_testid=data_testid,
    )
    if not identifier:
        return None

    attributes: FieldAttributes = {}
    if name is not None:
        attributes["name"] = name
    if element_id is not None:
        attributes["id"] = element_id
    if aria is not None:
        attributes["aria_label"] = aria
    if placeholder is not None:
        attributes["placeholder"] = placeholder
    if data_testid is not None:
        attributes["data_testid"] = data_testid
    if field_type:
        attributes["type"] = field_type.lower()
    if tag:
        attributes["tag"] = tag.lower()

    return {"identifier": identifier, "attributes": attributes}
