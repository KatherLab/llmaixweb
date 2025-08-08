import base64
import io
import json
from datetime import datetime, timezone
from typing import Any

import requests
from fastapi import HTTPException
from PIL import Image

from backend.src import schemas



def extract_leaf_paths_from_dict(data, parent=""):
    """Recursively extracts all leaf field paths from a nested dict using dot notation."""
    fields = []
    if isinstance(data, dict):
        for k, v in data.items():
            new_parent = f"{parent}.{k}" if parent else k
            if isinstance(v, dict):
                fields.extend(extract_leaf_paths_from_dict(v, new_parent))
            else:
                fields.append(new_parent)
    elif isinstance(data, list):
        # List: treat as array, add [*] to path (optionally)
        for i, item in enumerate(data):
            new_parent = f"{parent}[{i}]"
            fields.extend(extract_leaf_paths_from_dict(item, new_parent))
    return fields

def extract_required_fields_from_schema(
    schema_def: dict, prefix: str = ""
) -> list[str]:
    """Extract required fields from JSON schema using dot notation."""
    required = []

    if "properties" in schema_def:
        # Get fields marked as required at this level
        required_at_level = schema_def.get("required", [])

        for prop, prop_def in schema_def["properties"].items():
            field_path = f"{prefix}.{prop}" if prefix else prop

            # Check if this field is required
            if prop in required_at_level:
                required.append(field_path)

            # Recurse for nested objects
            if prop_def.get("type") == "object":
                required.extend(
                    extract_required_fields_from_schema(prop_def, field_path)
                )

            # Handle arrays of objects
            elif (
                prop_def.get("type") == "array"
                and prop_def.get("items", {}).get("type") == "object"
            ):
                # For arrays, we check the items schema
                required.extend(
                    extract_required_fields_from_schema(
                        prop_def["items"], f"{field_path}[]"
                    )
                )

    return required


def check_missing_fields_nested(
    data: dict, required_fields: list[str], prefix: str = ""
) -> list[str]:
    """Check for missing required fields in nested structure using dot notation."""
    missing = []

    for field_path in required_fields:
        # Skip array notation for now
        if "[]" in field_path:
            continue

        keys = field_path.split(".")
        current = data
        found = True

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                found = False
                break

        if not found:
            missing.append(field_path)

    return missing


def find_extra_fields_nested(
    data: dict, schema_def: dict, prefix: str = ""
) -> list[str]:
    """Find fields in data that aren't in schema."""
    extra = []

    # Special fields to ignore
    ignore_fields = {"id", "document_id", "_id"}

    def get_schema_fields(schema: dict, prefix: str = "") -> set[str]:
        """Extract all field paths from schema."""
        fields = set()

        if "properties" in schema:
            for prop, prop_def in schema["properties"].items():
                field_path = f"{prefix}.{prop}" if prefix else prop
                fields.add(field_path)

                # Recurse for nested objects
                if prop_def.get("type") == "object":
                    fields.update(get_schema_fields(prop_def, field_path))

        return fields

    # Get all schema fields
    schema_fields = get_schema_fields(schema_def)

    def check_data_fields(data: dict, prefix: str = ""):
        """Check data fields against schema."""
        for key, value in data.items():
            if key in ignore_fields:
                continue

            field_path = f"{prefix}.{key}" if prefix else key

            if field_path not in schema_fields:
                extra.append(field_path)
            elif isinstance(value, dict):
                # Recurse for nested objects
                check_data_fields(value, field_path)

    check_data_fields(data)
    return extra

def check_field_types(data: dict, schema_def: dict, prefix: str = "") -> list[str]:
    """Check if data types in the JSON match the schema definition."""
    type_errors = []

    if "properties" in schema_def:
        for prop, prop_def in schema_def["properties"].items():
            field_path = f"{prefix}.{prop}" if prefix else prop

            # Check if field exists in data
            if prop not in data:
                continue  # Missing fields are handled separately

            value = data[prop]
            expected_type = prop_def.get("type")

            # Check type compatibility
            if expected_type:
                type_error = check_value_type(value, expected_type, field_path)
                if type_error:
                    type_errors.append(type_error)

            # Recurse for nested objects
            if expected_type == "object" and isinstance(value, dict):
                nested_errors = check_field_types(value, prop_def, field_path)
                type_errors.extend(nested_errors)

            # Handle arrays
            elif expected_type == "array" and isinstance(value, list):
                items_schema = prop_def.get("items", {})
                for i, item in enumerate(value):
                    if items_schema.get("type") == "object":
                        nested_errors = check_field_types(
                            item, items_schema, f"{field_path}[{i}]"
                        )
                        type_errors.extend(nested_errors)

    return type_errors


def check_value_type(value: Any, expected_type: str, field_path: str) -> str | None:
    """Check if a value matches the expected JSON schema type."""
    if value is None:
        return None  # Null values are generally acceptable

    type_mapping = {
        "string": str,
        "number": (int, float),
        "integer": int,
        "boolean": bool,
        "array": list,
        "object": dict,
    }

    expected_python_type = type_mapping.get(expected_type)

    if expected_python_type is None:
        return None  # Unknown type, skip validation

    if not isinstance(value, expected_python_type):
        # Special handling for numbers
        if expected_type == "number" and isinstance(value, (int, float)):
            return None  # Both int and float are acceptable for number

        # Special handling for integer vs float
        if (
            expected_type == "integer"
            and isinstance(value, float)
            and value.is_integer()
        ):
            return None  # Float with no decimal part is acceptable as integer

        # Generate user-friendly error message
        actual_type = type(value).__name__

        # Make error messages more intuitive
        if isinstance(value, str) and expected_type in ["number", "integer"]:
            return f"Field '{field_path}' expects a {expected_type} but got text '{value}'. Please use a numeric value without quotes."
        elif isinstance(value, (int, float)) and expected_type == "string":
            return f"Field '{field_path}' expects text but got number {value}. Please wrap the value in quotes."
        elif expected_type == "boolean":
            return f"Field '{field_path}' expects true/false but got {actual_type} '{value}'. Use true or false without quotes."
        else:
            return f"Field '{field_path}' expects {expected_type} but got {actual_type}"

    return None


def find_extra_fields(data: dict, schema_def: dict) -> list[str]:
    """Find fields in data that aren't defined in the schema."""
    extra = []

    # Use the existing find_extra_fields_nested function
    extra_fields = find_extra_fields_nested(data, schema_def)

    return extra_fields


def make_naive_fields_timezone_aware(value: Any) -> Any:
    # Only process datetime instances that are naive
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        # Optional: normalize to UTC if already tz-aware but not UTC
        # return value.astimezone(timezone.utc)
    return value


def validate_prompt(prompt: schemas.PromptCreate | schemas.PromptUpdate) -> None:
    """Validate that the prompt contains the required placeholder and at least one prompt is present."""
    placeholder = "{document_content}"

    # Check that at least one prompt is provided
    if not prompt.system_prompt and not prompt.user_prompt:
        raise HTTPException(
            status_code=400,
            detail="At least one of system_prompt or user_prompt must be provided",
        )

    # Check that the placeholder exists in at least one of the prompts
    has_placeholder = False
    if prompt.system_prompt and placeholder in prompt.system_prompt:
        has_placeholder = True
    if prompt.user_prompt and placeholder in prompt.user_prompt:
        has_placeholder = True

    if not has_placeholder:
        raise HTTPException(
            status_code=400,
            detail=f"The placeholder '{placeholder}' must be present in either system_prompt or user_prompt",
        )


def flatten_dict(d, parent_key="", sep="."):
    """Flatten dictionary with dot notation for nested fields."""
    flat_dict = {}
    if isinstance(d, dict):
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                flat_dict.update(flatten_dict(v, new_key, sep))
            elif isinstance(v, list):
                # Recursively flatten lists of dicts
                for i, item in enumerate(v):
                    flat_dict.update(flatten_dict(item, f"{new_key}[{i}]", sep))
            else:
                flat_dict[new_key] = v
    else:
        flat_dict[parent_key] = d
    return flat_dict


def extract_field_types_from_schema(schema_def: dict, result: dict, prefix: str = ""):
    """Extract all field types from a JSON schema as dot notation (leaf paths)."""
    if "properties" in schema_def:
        for prop_name, prop_def in schema_def["properties"].items():
            full_path = f"{prefix}.{prop_name}" if prefix else prop_name

            if prop_def.get("type") == "object" and "properties" in prop_def:
                extract_field_types_from_schema(prop_def, result, full_path)
            elif prop_def.get("type") == "array" and "items" in prop_def:
                if prop_def["items"].get("type") == "object":
                    # For arrays of objects, list the full path with []
                    extract_field_types_from_schema(
                        prop_def["items"], result, f"{full_path}[]"
                    )
                else:
                    result[full_path + "[]"] = prop_def["items"].get("type", "string")
            else:
                # Primitive type or enum
                if "enum" in prop_def:
                    result[full_path] = "category"
                else:
                    type_mapping = {
                        "boolean": "boolean",
                        "integer": "number",
                        "number": "number",
                        "string": "string",
                    }
                    result[full_path] = type_mapping.get(prop_def.get("type", "string"), "string")

            if prop_def.get("format") in ["date", "date-time"]:
                result[full_path] = "date"



# As sqlite does not support timezone-aware datetimes, we have to do this manually.
# Make extra-sure that all datetimes are timezone-aware to utc before saving to the database!
def _make_aware(dt):
    """Make a datetime timezone-aware, assuming UTC if naive."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def test_remote_image_support(api_url: str, model: str, api_key: str) -> bool:
    img = Image.new("RGB", (1, 1), color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe this image in one word."},
                    {"type": "image_url", "image_url": f"data:image/png;base64,{b64}"},
                ],
            }
        ],
        "max_tokens": 3,
    }
    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=10)
        data = response.json()
        if not response.ok or "choices" not in data:
            return False
        reply = data["choices"][0].get("message", {}).get("content", "").lower()
        # You may want to adjust the check below based on expected behavior
        if (
            "white" in reply
            or "blank" in reply
            or "cannot" in reply
            or "empty" in reply
        ):
            return True
        return False
    except Exception:
        return False
