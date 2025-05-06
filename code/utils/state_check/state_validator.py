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
    מסיר רק את הפריט הריק המייצג placeholder (התבנית), ומשאיר כל שאר השירותים.
    """
    # אם אין תבנית או שהתבנית אינה dict — אין מה לנקות
    if not template_list or not isinstance(template_list[0], dict):
        return actual_list

    default_template = template_list[0]
    cleaned = []
    for item in actual_list:
        # נשמור כל פריט שאינו זהה במלואו לתבנית
        if not (isinstance(item, dict) and item == default_template):
            cleaned.append(item)
    return cleaned

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


if __name__ == "__main__":

    state = """
{
  "target": {
    "ip": "192.168.56.101",
    "os": {
      "name": "Linux",
      "distribution": {
        "name": "",
        "version": "",
        "architecture": ""
      },
      "kernel": ""
    },
    "services": [
      {
        "port": "",
        "protocol": "",
        "service": "",
        "server_type": "",
        "server_version": "",
        "supported_protocols": [
          ""
        ],
        "softwares": [
          {
            "name": "",
            "version": ""
          }
        ]
      },
      {
        "port": "21",
        "protocol": "",
        "service": "",
        "server_type": "",
        "server_version": "",
        "supported_protocols": "",
        "softwares": ""
      },
      {
        "port": "22",
        "protocol": "tcp",
        "service": "ftp",
        "server_type": "",
        "server_version": "",
        "supported_protocols": "",
        "softwares": ""
      },
      {
        "port": "23",
        "protocol": "tcp",
        "service": "ssh",
        "server_type": "",
        "server_version": "",
        "supported_protocols": "",
        "softwares": ""
      },
      {
        "port": "25",
        "protocol": "tcp",
        "service": "telnet",
        "server_type": "",
        "server_version": "",
        "supported_protocols": "",
        "softwares": ""
      },
      {
        "port": "53",
        "protocol": "tcp",
        "service": "smtp",
        "server_type": "",
        "server_version": "",
        "supported_protocols": "",
        "softwares": ""
      },
      {
        "port": "80",
        "protocol": "tcp",
        "service": "domain",
        "server_type": "",
        "server_version": "",
        "supported_protocols": "",
        "softwares": ""
      },
      {
        "port": "111",
        "protocol": "tcp",
        "service": "http",
        "server_type": "",
        "server_version": "",
        "supported_protocols": "",
        "softwares": ""
      },
      {
        "port": "139",
        "protocol": "tcp",
        "service": "rpcbind",
        "server_type": "",
        "server_version": "",
        "supported_protocols": "",
        "softwares": ""
      },
      {
        "port": "445",
        "protocol": "tcp",
        "service": "netbios-ssn",
        "server_type": "",
        "server_version": "",
        "supported_protocols": "",
        "softwares": ""
      },
      {
        "port": "512",
        "protocol": "tcp",
        "service": "microsoft-ds",
        "server_type": "",
        "server_version": "",
        "supported_protocols": "",
        "softwares": ""
      },
      {
        "port": "513",
        "protocol": "tcp",
        "service": "exec",
        "server_type": "",
        "server_version": "",
        "supported_protocols": "",
        "softwares": ""
      },
      {
        "port": "1099",
        "protocol": "tcp",
        "service": "login",
        "server_type": "",
        "server_version": "",
        "supported_protocols": "",
        "softwares": ""
      },
      {
        "port": "1524",
        "protocol": "tcp",
        "service": "rmiregistry",
        "server_type": "",
        "server_version": "",
        "supported_protocols": "",
        "softwares": ""
      },
      {
        "port": "2049",
        "protocol": "tcp",
        "service": "ingreslock",
        "server_type": "",
        "server_version": "",
        "supported_protocols": "",
        "softwares": ""
      },
      {
        "port": "2121",
        "protocol": "tcp",
        "service": "nfs",
        "server_type": "",
        "server_version": "",
        "supported_protocols": "",
        "softwares": ""
      },
      {
        "port": "3306",
        "protocol": "tcp",
        "service": "ccproxy-ftp",
        "server_type": "",
        "server_version": "",
        "supported_protocols": "",
        "softwares": ""
      },
      {
        "port": "5432",
        "protocol": "tcp",
        "service": "mysql",
        "server_type": "",
        "server_version": "",
        "supported_protocols": "",
        "softwares": ""
      },
      {
        "port": "5900",
        "protocol": "tcp",
        "service": "postgresql",
        "server_type": "",
        "server_version": "",
        "supported_protocols": "",
        "softwares": ""
      },
      {
        "port": "6000",
        "protocol": "tcp",
        "service": "vnc",
        "server_type": "",
        "server_version": "",
        "supported_protocols": "",
        "softwares": ""
      },
      {
        "port": "6667",
        "protocol": "tcp",
        "service": "X11",
        "server_type": "",
        "server_version": "",
        "supported_protocols": "",
        "softwares": ""
      },
      {
        "port": "8009",
        "protocol": "tcp",
        "service": "irc",
        "server_type": "",
        "server_version": "",
        "supported_protocols": "",
        "softwares": ""
      }
    ]
  },
  "web_directories_status": {
    "200": {},
    "301": {},
    "302": {},
    "307": {},
    "401": {},
    "403": {},
    "500": {},
    "502": {},
    "503": {},
    "504": {}
  },
  "actions_history": [],
  "cpes": [],
  "vulnerabilities_found": []
}
    """
    state_dict = json.loads(state)
    print(validate_state(state_dict))
