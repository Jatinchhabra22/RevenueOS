"""Parse and validate LLM JSON without executing model output."""

from __future__ import annotations

import json
import re
from typing import Any, TypeVar, Union, get_args, get_origin

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


class LLMError(RuntimeError):
    pass


def parse_json_object(text: str) -> dict[str, Any]:
    raw = (text or "").strip()
    if not raw:
        raise LLMError("empty LLM response")
    fenced = _FENCE.search(raw)
    if fenced:
        raw = fenced.group(1).strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end <= start:
        raise LLMError("LLM did not return a JSON object")
    try:
        parsed = json.loads(raw[start : end + 1])
    except json.JSONDecodeError as exc:
        raise LLMError("invalid JSON") from exc
    if not isinstance(parsed, dict):
        raise LLMError("LLM did not return a JSON object")
    return parsed


def _is_list_annotation(annotation: Any) -> bool:
    origin = get_origin(annotation)
    if origin is list:
        return True
    if origin is Union:
        return any(_is_list_annotation(arg) for arg in get_args(annotation))
    return False


def _stringify_scalar(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
            else:
                parts.append(json.dumps(item, default=str))
        return "; ".join(part.strip() for part in parts if str(part).strip())
    if isinstance(value, dict):
        return json.dumps(value, default=str)
    return str(value)


def coerce_structured_payload(schema: type[BaseModel], payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize common 3B JSON shape mistakes. Does not invent enum values or actions."""
    repaired = dict(payload)
    for name, field in schema.model_fields.items():
        if name not in repaired:
            continue
        value = repaired[name]
        if _is_list_annotation(field.annotation):
            if value in ("", None):
                repaired[name] = []
            elif isinstance(value, str):
                repaired[name] = [value]
            continue
        if value is None:
            continue
        if isinstance(value, (list, dict)) or not isinstance(value, str):
            if name == "confidence":
                try:
                    repaired[name] = float(value)
                except (TypeError, ValueError):
                    pass
                continue
            if isinstance(value, (list, dict, int, float, bool)):
                repaired[name] = _stringify_scalar(value)
        elif name == "confidence":
            try:
                repaired[name] = float(value)
            except ValueError:
                pass
    return repaired


def invoke_structured(
    llm: Any,
    *,
    schema: type[T],
    system: str,
    user: str,
    schema_name: str | None = None,
    extra: dict[str, Any] | None = None,
) -> T:
    name = schema_name or schema.__name__
    required = list(schema.model_json_schema().get("required") or [])
    hint = (
        f"{system}\nReturn a flat JSON object for {name}. "
        f"Required keys: {', '.join(required)}. "
        "Any list field must be a JSON array of strings, never an empty string."
    )
    payload = llm.generate_structured(system=hint, user=user, schema_name=name)
    if not isinstance(payload, dict):
        raise LLMError("LLM did not return a JSON object")
    nested = payload.get(name) or payload.get(name[0].lower() + name[1:])
    if isinstance(nested, dict):
        payload = nested
    merged = coerce_structured_payload(schema, {**payload, **(extra or {})})
    try:
        return schema.model_validate(merged)
    except ValidationError as exc:
        raise LLMError("structured output failed validation") from exc
