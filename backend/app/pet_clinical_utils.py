from __future__ import annotations

from typing import Any


def _split_text_lines(value: str) -> list[str]:
    separators = ["\n", ";", ","]
    items = [value]
    for separator in separators:
        next_items: list[str] = []
        for item in items:
            next_items.extend(item.split(separator))
        items = next_items
    return items


def normalize_clinical_list(value: Any) -> list[str]:
    if value is None:
        return []

    if isinstance(value, str):
        raw_items = _split_text_lines(value)
    elif isinstance(value, list):
        raw_items = value
    else:
        raw_items = [value]

    normalized: list[str] = []
    seen: set[str] = set()

    for item in raw_items:
        text = str(item or "").strip()
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(text)

    return normalized


def clinical_list_to_text(items: list[str]) -> str | None:
    if not items:
        return None
    return "\n".join(items)


def normalize_pet_clinical_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)

    field_mapping = {
        "alergias_lista": "alergias",
        "condicoes_cronicas_lista": "doencas_cronicas",
        "medicamentos_continuos_lista": "medicamentos_continuos",
    }

    for list_field, legacy_field in field_mapping.items():
        list_sent = list_field in normalized
        legacy_sent = legacy_field in normalized

        list_items = normalize_clinical_list(normalized.get(list_field)) if list_sent else None
        legacy_items = normalize_clinical_list(normalized.get(legacy_field)) if legacy_sent else None

        merged_items = list_items if list_items is not None else legacy_items
        if merged_items is None:
            continue

        normalized[list_field] = merged_items
        normalized[legacy_field] = clinical_list_to_text(merged_items)

    if "restricoes_alimentares_lista" in normalized:
        normalized["restricoes_alimentares_lista"] = normalize_clinical_list(
            normalized.get("restricoes_alimentares_lista")
        )

    return normalized
