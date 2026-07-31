# backend/src/utils/schema_validation.py
"""Structural validation for user-authored extraction schemas.

Why this exists: the two sides of an extraction read a schema differently.

* Grammar-constrained decoding (vLLM/xgrammar, OpenAI structured outputs)
  builds its automaton from ``properties`` and **silently ignores** a
  ``required`` entry naming a property the object never defines — the provider
  happily returns output it considers conformant.
* ``validate_against_schema`` in ``utils/info_extraction.py`` enforces
  ``required`` unconditionally.

A schema carrying such a stale entry (typical after renaming a property, or
after hand-editing the JSON) therefore passes at the provider and fails locally
for *every* document with ``'<name>' is a required property``. Validating at
save time turns a silently-burned trial into an inline form error.
"""

import difflib
from typing import Any

import jsonschema
from jsonschema import validators

from .api_errors import api_error

# Cap the report so a pathological schema can't produce a megabyte of detail.
MAX_PROBLEMS = 20

# Keywords that can supply properties from somewhere other than this node's own
# ``properties`` map. When one is present we cannot decide locally whether a
# ``required`` name is satisfiable, so we stay quiet rather than reject a valid
# composed schema.
_COMPOSITION_KEYWORDS = (
    "$ref",
    "$dynamicRef",
    "allOf",
    "anyOf",
    "oneOf",
    "not",
    "if",
    "then",
    "else",
    "patternProperties",
    "dependentSchemas",
)

# Keys whose value is a single subschema.
_SUBSCHEMA_KEYS = (
    "items",
    "contains",
    "not",
    "if",
    "then",
    "else",
    "propertyNames",
    "additionalItems",
    "unevaluatedItems",
    "additionalProperties",
    "unevaluatedProperties",
)

# Keys whose value is a mapping of name -> subschema.
_SCHEMA_MAP_KEYS = (
    "properties",
    "$defs",
    "definitions",
    "patternProperties",
    "dependentSchemas",
)

# Keys whose value is a list of subschemas.
_SCHEMA_LIST_KEYS = ("allOf", "anyOf", "oneOf", "prefixItems")


def _walk(node: Any, path: str = "#"):
    """Yield ``(json_pointer, subschema)`` for every schema node, depth-first."""
    if not isinstance(node, dict):
        return
    yield path, node

    for key in _SCHEMA_MAP_KEYS:
        sub = node.get(key)
        if isinstance(sub, dict):
            for name, child in sub.items():
                yield from _walk(child, f"{path}/{key}/{name}")

    for key in _SCHEMA_LIST_KEYS:
        sub = node.get(key)
        if isinstance(sub, list):
            for index, child in enumerate(sub):
                yield from _walk(child, f"{path}/{key}/{index}")

    for key in _SUBSCHEMA_KEYS:
        sub = node.get(key)
        if isinstance(sub, dict):
            yield from _walk(sub, f"{path}/{key}")
        elif isinstance(sub, list):
            # draft-04 tuple form: "items": [ {...}, {...} ]
            for index, child in enumerate(sub):
                yield from _walk(child, f"{path}/{key}/{index}")


def _defines_properties_elsewhere(node: dict) -> bool:
    """True if this node may gain properties from something other than ``properties``."""
    if any(key in node for key in _COMPOSITION_KEYWORDS):
        return True
    # A *schema* (not a bool) for additional/unevaluated properties means the
    # author deliberately modelled free-form keys, so a required name that is
    # not in ``properties`` is still meaningful.
    return any(
        isinstance(node.get(key), dict)
        for key in ("additionalProperties", "unevaluatedProperties")
    )


def find_schema_problems(schema_definition: Any) -> list[dict[str, Any]]:
    """Return structural problems that would make an extraction schema unusable.

    Each problem is ``{"code", "path", "message"}`` plus, for
    ``required_without_property``, the offending ``field`` and a possible
    ``suggestion``. An empty list means the schema is fine.
    """
    if not isinstance(schema_definition, dict):
        return [
            {
                "code": "not_an_object",
                "path": "#",
                "message": "Schema definition must be a JSON object.",
            }
        ]

    # 1. Is it valid JSON Schema at all?
    try:
        validator_cls = validators.validator_for(
            schema_definition, default=validators.Draft202012Validator
        )
        validator_cls.check_schema(schema_definition)
    except jsonschema.SchemaError as exc:
        pointer = "#" + "".join(f"/{part}" for part in exc.absolute_path)
        return [
            {"code": "invalid_json_schema", "path": pointer, "message": exc.message}
        ]
    except Exception as exc:  # unknown $schema dialect, recursion limits, …
        return [
            {
                "code": "invalid_json_schema",
                "path": "#",
                "message": f"{type(exc).__name__}: {exc}",
            }
        ]

    # 2. `required` entries that nothing can ever produce.
    problems: list[dict[str, Any]] = []
    for path, node in _walk(schema_definition):
        required = node.get("required")
        if not isinstance(required, list) or _defines_properties_elsewhere(node):
            continue
        properties = node.get("properties")
        property_names = list(properties) if isinstance(properties, dict) else []

        for name in required:
            if not isinstance(name, str) or name in property_names:
                continue
            suggestion = next(
                iter(difflib.get_close_matches(name, property_names, n=1, cutoff=0.6)),
                None,
            )
            problems.append(
                {
                    "code": "required_without_property",
                    "path": path,
                    "field": name,
                    "suggestion": suggestion,
                    "message": (
                        f"'{name}' is listed in 'required' but is not defined in "
                        f"'properties' at {path}."
                    ),
                }
            )
            if len(problems) >= MAX_PROBLEMS:
                return problems

    return problems


def format_problems(problems: list[dict[str, Any]]) -> str:
    """Render problems as one compact, user-facing sentence fragment."""
    parts: list[str] = []
    for problem in problems:
        if problem.get("code") == "required_without_property":
            part = f"'{problem['field']}' at {problem['path']}"
            if problem.get("suggestion"):
                part += f" (did you mean '{problem['suggestion']}'?)"
        else:
            part = f"{problem['message']} at {problem['path']}"
        parts.append(part)
    return "; ".join(parts)


def raise_for_schema_problems(schema_definition: Any, *, code_prefix: str) -> None:
    """Validate an extraction schema, raising a localizable 400 on any problem.

    Args:
        schema_definition: The user-supplied JSON Schema.
        code_prefix: Error-code domain for the frontend catalog
            (``"schemas"`` or ``"trials"``).
    """
    problems = find_schema_problems(schema_definition)
    if not problems:
        return

    details = format_problems(problems)
    if problems[0]["code"] == "required_without_property":
        raise api_error(
            f"{code_prefix}.required_without_property",
            400,
            "Schema lists required field(s) that are not defined in properties. "
            "The model can never return them, so every document would fail "
            f"validation: {details}",
            details=details,
        )
    raise api_error(
        f"{code_prefix}.schema_definition_invalid",
        400,
        f"Schema definition is not valid JSON Schema: {details}",
        details=details,
    )
