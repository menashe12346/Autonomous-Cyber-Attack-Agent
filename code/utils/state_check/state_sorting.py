import json
from copy import deepcopy
import sys
import os

# allow import of project modules
toplevel = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if toplevel not in sys.path:
    sys.path.append(toplevel)

from config import STATE_SCHEMA

def _make_hashable(v):
    """
    Convert lists and dicts into hashable tuples for use in deduplication keys.
    """
    if isinstance(v, list):
        return tuple(_make_hashable(x) for x in v)
    if isinstance(v, dict):
        # sort dict items to ensure deterministic order
        return tuple((k, _make_hashable(w)) for k, w in sorted(v.items()))
    return v

def _generic_sort_list(raw_key: str, items: list) -> list:
    """
    Deduplicate & sort a list of dicts according to the schema:
      - Remove exact duplicates (by tuple of all defined child fields).
      - Sort by numeric fields first, then lexicographically by string fields.
    """
    # Find all child field names for this list in STATE_SCHEMA
    child_fields = [
        k.split("[]", 1)[1].lstrip('.')
        for k, info in STATE_SCHEMA.items()
        if k.startswith(raw_key + "[]")
    ]

    # Deduplicate
    seen = set()
    unique = []
    for item in items:
        if not isinstance(item, dict):
            continue
        # build hashable key
        key = tuple(_make_hashable(item.get(f, "")) for f in child_fields)
        if key not in seen:
            seen.add(key)
            unique.append(item)

    # Sort
    def sort_key(item):
        parts = []
        for f in child_fields:
            v = item.get(f, "")
            if isinstance(v, str) and v.isdigit():
                parts.append((0, int(v)))
            else:
                parts.append((1, str(v).lower()))
        return tuple(parts)

    return sorted(unique, key=sort_key)


def _sort_recursive(obj, prefix=""):
    """
    Recursively sort & dedupe according to STATE_SCHEMA:
      - If prefix in schema as list → apply _generic_sort_list
      - If prefix in schema as dict → sort dict keys
      - Then recurse into any dict values or list items
    """
    # 1) list-level sorting
    if prefix in STATE_SCHEMA and STATE_SCHEMA[prefix].get("type") == "list" and isinstance(obj, list):
        obj = _generic_sort_list(prefix, obj)

    # 2) dict-level sorting
    if prefix in STATE_SCHEMA and STATE_SCHEMA[prefix].get("type") == "dict" and isinstance(obj, dict):
        obj = dict(sorted(obj.items()))

    # 3) recurse
    if isinstance(obj, dict):
        new = {}
        for k, v in obj.items():
            child_prefix = f"{prefix}.{k}" if prefix else k
            new[k] = _sort_recursive(v, child_prefix)
        return new

    if isinstance(obj, list):
        child_prefix = f"{prefix}[]" if prefix else "[]"
        return [_sort_recursive(item, child_prefix) for item in obj]

    # base case (neither dict nor list)
    return obj


def sort_state(state: dict) -> dict:
    """
    Deep-copies `state`, then applies recursive sorting/deduplication
    guided entirely by STATE_SCHEMA.
    """
    return _sort_recursive(deepcopy(state))

# Example usage
if __name__ == "__main__":
    example = {
        "target": {
            "services": [
                {"port": "80", "protocol": "tcp", "service": "http"},
                {"port": "22", "protocol": "tcp", "service": "ssh"},
                {"port": "80", "protocol": "tcp", "service": "http"},  # dup
            ]
        },
        "web_directories_status": {
            "200": {"/admin": ""},
            "404": {"/x": "", "/y": ""}
        }
    }

    sorted_state = sort_state(example)
    print(json.dumps(sorted_state, indent=2))
