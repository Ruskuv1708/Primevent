from __future__ import annotations

import copy
import re


_CYRILLIC_TO_LATIN = str.maketrans(
    {
        "а": "a",
        "б": "b",
        "в": "v",
        "г": "g",
        "д": "d",
        "е": "e",
        "ё": "e",
        "ж": "zh",
        "з": "z",
        "и": "i",
        "й": "y",
        "к": "k",
        "л": "l",
        "м": "m",
        "н": "n",
        "о": "o",
        "п": "p",
        "р": "r",
        "с": "s",
        "т": "t",
        "у": "u",
        "ф": "f",
        "х": "h",
        "ц": "ts",
        "ч": "ch",
        "ш": "sh",
        "щ": "sch",
        "ъ": "",
        "ы": "y",
        "ь": "",
        "э": "e",
        "ю": "yu",
        "я": "ya",
    }
)


def _normalized(value: str) -> str:
    return re.sub(r"[^0-9a-zа-яё]+", "", value.casefold())


def _field_key(label: str, used_keys: set[str]) -> str:
    base = label.casefold().translate(_CYRILLIC_TO_LATIN)
    base = re.sub(r"[^a-z0-9]+", "_", base).strip("_") or "field"
    if base[0].isdigit():
        base = f"field_{base}"

    key = base
    index = 2
    while key in used_keys:
        key = f"{base}_{index}"
        index += 1
    used_keys.add(key)
    return key


def _field_type(label: str) -> str:
    normalized = label.casefold()
    if any(token in normalized for token in ("дата", "date", "deadline", "срок")):
        return "date"
    if any(token in normalized for token in ("сумма", "стоимость", "цена", "количество", "amount", "cost", "price", "total")):
        return "number"
    if any(token in normalized for token in ("да/нет", "boolean", "оплачен", "активен")):
        return "boolean"
    return "text"


def _field_list_tail(message: str) -> str:
    patterns = (
        r"(?:полями|поля|полей|fields?)\s*[:：-]\s*(.+)$",
        r"(?:следующие поля|такие поля)\s*[:：-]\s*(.+)$",
    )
    for pattern in patterns:
        match = re.search(pattern, message, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1)
    return ""


def extract_requested_form_schema(message: str) -> list[dict]:
    tail = _field_list_tail(message)
    if not tail:
        return []

    tail = re.split(r"\n\s*\n", tail, maxsplit=1)[0]
    tail = re.sub(r"\n\s*[-*•]\s*", "\n", tail)
    parts = re.split(r"[,;\n]+", tail)
    labels: list[str] = []
    seen_labels: set[str] = set()

    for part in parts:
        label = re.sub(r"^\s*(?:[-*•]|\d+[\).:-]?)\s*", "", part).strip()
        label = label.strip(" \t\r\n\"'`«»“”().")
        if not label:
            continue
        normalized = _normalized(label)
        if not normalized or normalized in seen_labels:
            continue
        seen_labels.add(normalized)
        labels.append(label)

    used_keys: set[str] = set()
    return [
        {
            "key": _field_key(label, used_keys),
            "label": label,
            "type": _field_type(label),
            "required": False,
        }
        for label in labels
    ]


def _existing_field_map(schema: list[dict]) -> dict[str, dict]:
    fields = {}
    for field in schema:
        if not isinstance(field, dict):
            continue
        for value in (field.get("label"), field.get("key")):
            if isinstance(value, str) and value.strip():
                fields[_normalized(value)] = field
    return fields


def _replace_with_requested_schema(existing_schema: list[dict], requested_schema: list[dict]) -> list[dict]:
    existing_by_name = _existing_field_map(existing_schema)
    result = []
    used_keys: set[str] = set()
    for requested in requested_schema:
        existing = existing_by_name.get(_normalized(requested["label"])) or existing_by_name.get(_normalized(requested["key"]))
        field = {**requested, **(existing or {})}
        field["label"] = requested["label"]
        if not field.get("key") or field["key"] in used_keys:
            field["key"] = _field_key(field["label"], used_keys)
        else:
            used_keys.add(field["key"])
        field["type"] = field.get("type") or requested["type"]
        field["required"] = bool(field.get("required", requested["required"]))
        result.append(field)
    return result


def _merge_requested_schema(existing_schema: list[dict], requested_schema: list[dict]) -> list[dict]:
    result = [field for field in existing_schema if isinstance(field, dict)]
    existing_by_name = _existing_field_map(result)
    used_keys = {str(field.get("key")) for field in result if field.get("key")}
    for requested in requested_schema:
        if _normalized(requested["label"]) in existing_by_name or _normalized(requested["key"]) in existing_by_name:
            continue
        field = dict(requested)
        if field["key"] in used_keys:
            field["key"] = _field_key(field["label"], used_keys)
        else:
            used_keys.add(field["key"])
        result.append(field)
    return result


def reinforce_requested_form_fields(payload: dict, message: str) -> dict:
    requested_schema = extract_requested_form_schema(message)
    if not requested_schema or payload.get("kind") == "clarification" or payload.get("proposal_type") != "forms":
        return payload

    guarded = copy.deepcopy(payload)
    if guarded.get("operation") == "create":
        for artifact in guarded.get("generated_artifacts") or []:
            if artifact.get("type") != "form":
                continue
            artifact["schema_structure"] = _replace_with_requested_schema(
                artifact.get("schema_structure") or [],
                requested_schema,
            )
        return guarded

    if guarded.get("operation") == "update":
        after_state = guarded.setdefault("after_state", {})
        if isinstance(after_state.get("schema_structure"), list):
            after_state["schema_structure"] = _merge_requested_schema(after_state["schema_structure"], requested_schema)
    return guarded
