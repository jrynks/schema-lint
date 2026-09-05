"""Read JSON-LD properties without inventing missing values."""

from __future__ import annotations

from typing import Any


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def text_of(value: Any) -> str | None:
    """Best-effort textual value. Returns None when nothing was published."""
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, str):
        s = value.strip()
        return s or None
    if isinstance(value, list):
        for item in value:
            t = text_of(item)
            if t:
                return t
        return None
    if isinstance(value, dict):
        for key in ("@value", "text", "name", "value", "caption", "description"):
            if key in value:
                t = text_of(value[key])
                if t:
                    return t
        return None
    return None


def first_node(value: Any) -> Any:
    items = as_list(value)
    return items[0] if items else None


def getp(node: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in node:
            return node[key]
    return None


def has_text(node: dict[str, Any], *keys: str) -> bool:
    return text_of(getp(node, *keys)) is not None


def nonempty(value: Any) -> bool:
    if value is None:
        return False
    if value == "" or value == [] or value == {}:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    return True
