import re
import copy
import json

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


from config import EXPECTED_STATUS_CODES, STATE_SCHEMA
from blackboard.blackboard import initialize_blackboard

DEFAULT_STATE_STRUCTURE = initialize_blackboard()

def recursive_setdefault(base: dict, default: dict):
    """
    משלים רקורסיבית ערכים חסרים במילון base לפי מבנה default.
    """
    for key, default_value in default.items():
        if key not in base:
            base[key] = copy.deepcopy(default_value)
        elif isinstance(default_value, dict) and isinstance(base[key], dict):
            recursive_setdefault(base[key], default_value)

def clean_list_entries_by_template(actual_list, template_list):
    """
    מנקה איברים לא חוקיים מתוך actual_list על פי המבנה הצפוי ב-template_list.
    כרגע תומך רק בניקוי services לפי port/protocol/service.
    """
    if not template_list or not isinstance(template_list[0], dict):
        return actual_list  # אין תבנית להשוואה
    expected_keys = set(template_list[0].keys())
    return [
        item for item in actual_list
        if isinstance(item, dict) and
           all(k in item and item[k] for k in expected_keys)
    ]

def recursive_clean(base: dict, default: dict):
    """
    מבצע ניקוי מותאם לפי התבנית:
    אם יש רשימה כמו 'services', היא תסונן לפי המבנה שב-template.
    """
    for key, default_value in default.items():
        if isinstance(default_value, dict) and isinstance(base.get(key), dict):
            recursive_clean(base[key], default_value)
        elif isinstance(default_value, list) and isinstance(base.get(key), list):
            base[key] = clean_list_entries_by_template(base[key], default_value)

def ensure_structure(state: dict) -> dict:
    """
    מבטיח שמבנה ה־state תואם בדיוק ל־DEFAULT_STATE_STRUCTURE לפי config בלבד.
    אין שימוש במחרוזות קשיחוֹת.
    """
    recursive_setdefault(state, DEFAULT_STATE_STRUCTURE)
    recursive_clean(state, DEFAULT_STATE_STRUCTURE)
    return state

def is_valid_type(value: str, expected_type: str) -> bool:
    if not isinstance(value, str):
        return False

    if expected_type == "string":
        return True

    elif expected_type == "int":
        return value.isdigit()

    elif expected_type in ("float", "double"):
        try:
            float(value)
            return True
        except ValueError:
            return False

    elif expected_type == "dict":
        try:
            parsed = json.loads(value)
            return isinstance(parsed, dict)
        except (ValueError, TypeError):
            return False

    elif expected_type == "list":
        try:
            parsed = json.loads(value)
            return isinstance(parsed, list)
        except (ValueError, TypeError):
            return False

    return False

def validate_categories_types(data: dict, schema: dict, schema_prefix="") -> dict:
    fixed = {}

    for key, value in data.items():
        full_key = f"{schema_prefix}.{key}" if schema_prefix else key

        # Try exact match
        schema_entry = schema.get(full_key)

        # Handle list item notation (e.g., target.services[].port)
        if schema_entry is None:
            list_key_parts = full_key.split(".")
            for i in range(len(list_key_parts), 0, -1):
                candidate = ".".join(list_key_parts[:i]) + "[]"
                tail = ".".join(list_key_parts[i:])
                test_key = f"{candidate}.{tail}" if tail else candidate
                if test_key in schema:
                    schema_entry = schema[test_key]
                    break

        # Default to unknown type
        expected_type = schema_entry["type"] if schema_entry and "type" in schema_entry else "string"

        if isinstance(value, dict):
            fixed[key] = validate_categories_types(value, schema, full_key)
        elif isinstance(value, list):
            fixed[key] = []
            for item in value:
                if isinstance(item, dict):
                    fixed[key].append(validate_categories_types(item, schema, full_key + "[]"))
                else:
                    fixed_value = str(item)
                    if is_valid_type(fixed_value, expected_type):
                        fixed[key].append(fixed_value)
                    else:
                        fixed[key].append("")
        else:
            fixed_value = str(value)
            fixed[key] = fixed_value if is_valid_type(fixed_value, expected_type) else ""

    return fixed


def validate_state(state: dict) -> dict:
    """
    הפונקציה הראשית שמוודאת שה־state במבנה נכון ובעל ערכים תקניים.
    """
    state = validate_categories_types(state, STATE_SCHEMA)
    state = ensure_structure(state)

    return state
