from datetime import timezone


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
