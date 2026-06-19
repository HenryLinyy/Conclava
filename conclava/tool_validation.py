"""Validate model-selected tool calls against client-provided tool specs."""

from __future__ import annotations

from dataclasses import is_dataclass
from typing import Any


def parse_tool_arguments(raw: Any) -> tuple[dict | None, str | None]:
    """Normalize OpenAI tool-call arguments into a dict."""
    if raw is None:
        return {}, None
    if isinstance(raw, dict):
        return raw, None
    if isinstance(raw, str):
        import json

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            return None, f"tool arguments are not valid JSON: {exc.msg}"
        if not isinstance(parsed, dict):
            return None, "tool arguments JSON must decode to an object"
        return parsed, None
    return None, "tool arguments must be an object or JSON object string"


def validate_tool_call(
    tool_name: str | None,
    tool_input: dict | None,
    tools: list[Any] | None,
) -> tuple[bool, str | None]:
    """Return whether a tool call is allowed by the provided tool specs."""
    if not tools:
        return True, None
    if not tool_name:
        return False, "tool name is missing"

    tool_map = _tool_schema_map(tools)
    if tool_name not in tool_map:
        return False, f"tool '{tool_name}' was not provided by the client"

    schema = tool_map[tool_name] or {}
    payload = tool_input or {}
    return _validate_schema(payload, schema)


def _tool_schema_map(tools: list[Any]) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for tool in tools:
        name, schema = _extract_tool_name_schema(tool)
        if name:
            result[name] = schema or {}
    return result


def _extract_tool_name_schema(tool: Any) -> tuple[str | None, dict]:
    if is_dataclass(tool):
        name = getattr(tool, "name", None)
        schema = getattr(tool, "input_schema", None) or {}
        return name, schema

    if not isinstance(tool, dict):
        return None, {}

    if tool.get("type") == "function":
        func = tool.get("function", tool)
        if not isinstance(func, dict):
            return None, {}
        return (
            func.get("name") or tool.get("name"),
            func.get("parameters") or tool.get("parameters") or {},
        )

    return tool.get("name"), tool.get("input_schema") or tool.get("parameters") or {}


def _validate_schema(payload: dict, schema: dict) -> tuple[bool, str | None]:
    try:
        from jsonschema import Draft202012Validator, exceptions
    except ImportError:
        return _validate_schema_minimal(payload, schema)

    try:
        Draft202012Validator.check_schema(schema)
        errors = sorted(Draft202012Validator(schema).iter_errors(payload), key=str)
    except exceptions.SchemaError as exc:
        return False, f"tool schema is invalid: {exc.message}"

    if errors:
        return False, errors[0].message
    return True, None


def _validate_schema_minimal(payload: dict, schema: dict) -> tuple[bool, str | None]:
    if schema.get("type") not in (None, "object"):
        return False, "tool schema root type must be object"
    if not isinstance(payload, dict):
        return False, "tool input must be an object"

    for key in schema.get("required", []):
        if key not in payload:
            return False, f"'{key}' is a required property"

    properties = schema.get("properties", {})
    if isinstance(properties, dict):
        for key, value in payload.items():
            prop_schema = properties.get(key)
            if isinstance(prop_schema, dict):
                ok, error = _validate_type(value, prop_schema.get("type"), key)
                if not ok:
                    return False, error

    if schema.get("additionalProperties") is False and isinstance(properties, dict):
        extras = sorted(set(payload) - set(properties))
        if extras:
            return False, f"unexpected property '{extras[0]}'"

    return True, None


def _validate_type(value: Any, expected: Any, key: str) -> tuple[bool, str | None]:
    if expected is None:
        return True, None
    if isinstance(expected, list):
        for item in expected:
            ok, _ = _validate_type(value, item, key)
            if ok:
                return True, None
        return False, f"'{key}' does not match any allowed type"

    type_map = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "object": dict,
        "array": list,
    }
    expected_type = type_map.get(expected)
    if expected_type is None:
        return True, None
    if expected == "integer" and isinstance(value, bool):
        return False, f"'{key}' must be integer"
    if expected == "number" and isinstance(value, bool):
        return False, f"'{key}' must be number"
    if not isinstance(value, expected_type):
        return False, f"'{key}' must be {expected}"
    return True, None
