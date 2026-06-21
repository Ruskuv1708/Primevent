from __future__ import annotations

from collections.abc import Iterable
from typing import Any

DANGEROUS_SPREADSHEET_PREFIXES = ("=", "+", "-", "@")


def safe_spreadsheet_cell(value: Any) -> Any:
    if isinstance(value, str) and value.startswith(DANGEROUS_SPREADSHEET_PREFIXES):
        return f"'{value}"
    return value


def safe_spreadsheet_row(values: Iterable[Any]) -> list[Any]:
    return [safe_spreadsheet_cell(value) for value in values]
