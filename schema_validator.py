"""
Faz 12 P1 — Data Quality Validator: JSON Schema Validation
CPO-693: Validate API responses against JSON Schema definitions in schemas/
"""

import json
import os
import logging
import jsonschema

logger = logging.getLogger(__name__)

_SCHEMAS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schemas")
_schema_cache: dict = {}


def _load_schema(name):
    """Load and cache a JSON schema from schemas/<name>.json."""
    if name not in _schema_cache:
        path = os.path.join(_SCHEMAS_DIR, f"{name}.json")
        with open(path, encoding="utf-8") as f:
            _schema_cache[name] = json.load(f)
    return _schema_cache[name]


def validate_schema(data, schema_name):
    """
    Validate data against a named schema.

    Returns: {"ok": True, "schema": schema_name}
          or {"ok": False, "flag": "SCHEMA_ERROR", "schema": schema_name, "errors": [...]}
    """
    try:
        schema = _load_schema(schema_name)
    except FileNotFoundError:
        return {
            "ok": False, "flag": "SCHEMA_FILE_NOT_FOUND",
            "schema": schema_name, "errors": [{"message": f"Schema file not found: {schema_name}.json"}],
        }

    validator = jsonschema.Draft7Validator(schema)
    errors = [
        {"path": list(err.path) if err.path else [], "message": err.message}
        for err in validator.iter_errors(data)
    ]
    if errors:
        logger.warning(
            "SCHEMA_ERROR %s: %d validation error(s): %s",
            schema_name, len(errors), [e["message"] for e in errors[:3]],
        )
        return {"ok": False, "flag": "SCHEMA_ERROR", "schema": schema_name, "errors": errors}

    return {"ok": True, "schema": schema_name}


def validate_api_data(data):
    """Validate /api/data response against api_data schema."""
    return validate_schema(data, "api_data")


def validate_api_macro(data):
    """Validate /api/macro response against api_macro schema."""
    return validate_schema(data, "api_macro")


def validate_api_hisse_chart(data):
    """Validate /api/hisse/<ticker>/chart response against api_hisse_chart schema."""
    return validate_schema(data, "api_hisse_chart")
