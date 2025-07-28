import base64
import io
from datetime import timezone

import requests
from PIL import Image
from fastapi import HTTPException

from backend.src import schemas


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


def flatten_dict(d: dict, parent_key: str = "", sep: str = "_") -> dict:
    """Flatten a nested dictionary."""
    items = {}
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.update(flatten_dict(v, new_key, sep=sep))
        elif isinstance(v, list):
            # Handle lists by converting to string representation
            items[new_key] = str(v)
        else:
            items[new_key] = v
    return items


def extract_field_types_from_schema(schema_def: dict, result: dict, prefix: str = ""):
    """Extract field types from JSON schema."""
    if "properties" in schema_def:
        for prop_name, prop_def in schema_def["properties"].items():
            full_path = f"{prefix}_{prop_name}" if prefix else prop_name

            if "type" in prop_def:
                if prop_def["type"] == "object" and "properties" in prop_def:
                    extract_field_types_from_schema(prop_def, result, full_path)
                elif prop_def["type"] == "array" and "items" in prop_def:
                    if "type" in prop_def["items"]:
                        result[full_path] = f"array[{prop_def['items']['type']}]"
                    else:
                        result[full_path] = "array"
                else:
                    if "enum" in prop_def:
                        result[full_path] = "category"
                    else:
                        type_mapping = {
                            "boolean": "boolean",
                            "integer": "number",
                            "number": "number",
                            "string": "string",
                        }
                        result[full_path] = type_mapping.get(prop_def["type"], "string")

            if "format" in prop_def:
                if prop_def["format"] in ["date", "date-time"]:
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
                    {"type": "image_url", "image_url": f"data:image/png;base64,{b64}"}
                ]
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
        if "white" in reply or "blank" in reply or "cannot" in reply or "empty" in reply:
            return True
        return False
    except Exception:
        return False