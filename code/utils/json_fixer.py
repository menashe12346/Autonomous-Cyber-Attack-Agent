import re
import json
import os
import sys
import ast

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import EXPECTED_STATUS_CODES, DEFAULT_STATE_STRUCTURE
from blackboard.blackboard import initialize_blackboard

EXPECTED_STRUCTURE = initialize_blackboard()
EXPECTED_STRUCTURE["target"].pop("ip",None)
import re
from config import EXPECTED_STATUS_CODES, DEFAULT_STATE_STRUCTURE


def extract_value_after_key(text, key_name, next_keys=None):
    key_pos = text.find(key_name)
    if key_pos == -1:
        return None, len(key_name)

    after_key = text[key_pos + len(key_name):].lstrip()

    while after_key and after_key[0] in [':', ' ', '\'', '"', '{', '}']:
        after_key = after_key[1:]

    value = ''
    idx = 0
    while idx < len(after_key):
        subtext = after_key[idx:]

        if next_keys:
            for k in next_keys:
                if subtext.startswith(k):
                    return value.strip(), key_pos + len(key_name) + idx

        c = after_key[idx]
        if c.isalnum() or c in ['-', '.', '/']:
            value += c
            idx += 1
        else:
            break

    return value.strip(), key_pos + len(key_name) + idx


def cut_text_until_word(text, stop_word):
    collected = ''
    idx = 0
    while idx < len(text):
        if stop_word and text[idx:].startswith(stop_word):
            break
        collected += text[idx]
        idx += 1
    return collected


def find_missing_categories(parsed_data: dict, expected_structure: dict, path="") -> dict:
    missing = {}

    for key, expected_value in expected_structure.items():
        full_path = f"{path}.{key}" if path else key

        if key not in parsed_data:
            missing[full_path] = "missing key"
        else:
            actual_value = parsed_data[key]

            if isinstance(expected_value, dict):
                if not isinstance(actual_value, dict):
                    missing[full_path] = f"expected dict, got {type(actual_value).__name__}"
                else:
                    sub_missing = find_missing_categories(actual_value, expected_value, full_path)
                    missing.update(sub_missing)

            elif isinstance(expected_value, list) and expected_value and isinstance(expected_value[0], dict):
                if not isinstance(actual_value, list):
                    missing[full_path] = f"expected list, got {type(actual_value).__name__}"
                else:
                    for i, item in enumerate(actual_value):
                        if not isinstance(item, dict):
                            missing[f"{full_path}[{i}]"] = f"expected dict, got {type(item).__name__}"
                        else:
                            sub_missing = find_missing_categories(item, expected_value[0], f"{full_path}[{i}]")
                            missing.update(sub_missing)

    return missing


def extract_status_block(text_after_status, status_code):
    print(f"[DEBUG] Extracting block for status: {status_code}")
    after_status = text_after_status[len(status_code):].lstrip()

    while after_status and after_status[0] in [':', '{', ' ', '\'', '"']:
        after_status = after_status[1:]

    directories = {}
    pos = 0
    status_codes = EXPECTED_STATUS_CODES
    inside_block = True

    while pos < len(after_status) and inside_block:
        while pos < len(after_status) and after_status[pos] in [':', ' ', '\'', '"', ',']:
            pos += 1

        if pos >= len(after_status):
            break

        for code in status_codes:
            if after_status[pos:].startswith(code):
                inside_block = False
                break
        if not inside_block:
            break

        if after_status[pos] == '}':
            inside_block = False
            break

        path = ''
        while pos < len(after_status):
            if any(after_status[pos:].startswith(code) for code in status_codes):
                inside_block = False
                break
            c = after_status[pos]
            if c == ':':
                pos += 1
                break
            if c not in ['\'', '"', ',', '{', '}']:
                path += c
            pos += 1
        path = path.strip()

        while pos < len(after_status) and after_status[pos] in [' ', ':', '\'', '"', '{']:
            pos += 1

        value = ''
        while pos < len(after_status):
            if any(after_status[pos:].startswith(code) for code in status_codes):
                inside_block = False
                break
            if after_status[pos] in [',', '}', '\'', '"', ':']:
                break
            value += after_status[pos]
            pos += 1
        value = value.strip()

        if path:
            print(f"[DEBUG] Found path: {path} -> {value}")
            directories[path] = value

        while pos < len(after_status) and after_status[pos] in [' ', ',', ':', '\'', '"']:
            pos += 1
        if pos < len(after_status) and after_status[pos] == '}':
            inside_block = False
            break

    return directories if directories else {"": ""}


def extract_json_parts_recursive(text: str, structure: dict) -> tuple[dict, dict]:
    parts = {}
    text = text.replace('\n', ' ').replace('\r', ' ').strip()
    keys = list(structure.keys())

    pos = 0
    while pos < len(text):
        for i, key in enumerate(keys):
            if text[pos:].startswith(key):
                after_key_text = text[pos + len(key):]
                next_keys = keys[i + 1:]
                next_stop = next((k for k in next_keys if k in text[pos + len(key):]), "")
                block_text = cut_text_until_word(after_key_text, next_stop)

                expected_type = structure[key]

                if isinstance(expected_type, dict) and all(k.isdigit() for k in expected_type.keys()):
                    sub_result = {}
                    for code in expected_type.keys():
                        if code in block_text:
                            code_start = block_text.find(code)
                            subtext = block_text[code_start:]
                            sub_result[code] = extract_status_block(subtext, code)
                        else:
                            sub_result[code] = {"": ""}
                    parts[key] = sub_result

                elif isinstance(expected_type, dict):
                    sub_result, _ = extract_json_parts_recursive(block_text, expected_type)
                    parts[key] = sub_result

                elif isinstance(expected_type, list) and expected_type and isinstance(expected_type[0], dict):
                    list_result = []
                    item_structure = expected_type[0]
                    item_pos = 0
                    current_item = {}

                    while item_pos < len(block_text):
                        subtext = block_text[item_pos:]
                        matched = False
                        for field in item_structure:
                            if subtext.startswith(field):
                                val, jump = extract_value_after_key(subtext, field, next_keys=list(item_structure.keys()))
                                if val:
                                    current_item[field] = val
                                item_pos += jump
                                matched = True
                                break
                        if matched:
                            if all(k in current_item for k in item_structure):
                                list_result.append(current_item)
                                current_item = {}
                        else:
                            item_pos += 1
                    parts[key] = list_result

                else:
                    cleaned = block_text.strip(': "{}')
                    parts[key] = cleaned if cleaned else ""

                pos += len(key)
                break
        pos += 1

    for key in structure:
        if key not in parts:
            expected_type = structure[key]
            if isinstance(expected_type, dict):
                parts[key] = extract_json_parts_recursive("", expected_type)[0]
            elif isinstance(expected_type, list) and expected_type and isinstance(expected_type[0], dict):
                parts[key] = []
            elif isinstance(expected_type, dict) and all(k.isdigit() for k in expected_type.keys()):
                parts[key] = {code: {"": ""} for code in expected_type.keys()}
            else:
                parts[key] = ""

    missing = find_missing_categories(parts, structure)
    return parts, missing

def fill_json_structure(template_json, extracted_parts):
    target = template_json.get("target", {})

    if "target" in extracted_parts:
        target_data = extracted_parts["target"]
        if "ip" in target_data and target_data["ip"] and not target.get("ip"):
            target["ip"] = target_data["ip"]
        if "os" in target_data and target_data["os"] and not target.get("os"):
            target["os"] = target_data["os"]
        if "services" in target_data and target_data["services"]:
            existing_services = {
                (s["port"], s["protocol"], s["service"]) for s in target.get("services", [])
            }
            for service in target_data["services"]:
                if not service.get("port") or not service.get("protocol") or not service.get("service"):
                    continue
                service_tuple = (service["port"], service["protocol"], service["service"])
                if service_tuple not in existing_services:
                    target.setdefault("services", []).append(service)

    template_json["target"] = target

    web_directories_status = template_json.get("web_directories_status", {})

    if "web_directories_status" in extracted_parts:
        wds_data = extracted_parts["web_directories_status"]
        for status, directories in wds_data.items():
            if status not in web_directories_status:
                web_directories_status[status] = {}
            for directory, value in directories.items():
                directory = directory.strip('"')
                value = value.strip('"')
                if directory and directory not in web_directories_status[status]:
                    web_directories_status[status][directory] = value

    template_json["web_directories_status"] = web_directories_status

    for section in ["target", "web_directories_status"]:
        if section == "target" and not template_json["target"].get("services"):
            template_json["target"]["services"] = [{"port": "", "protocol": "", "service": ""}]
        if section == "web_directories_status":
            for status in EXPECTED_STATUS_CODES:
                if status not in template_json["web_directories_status"]:
                    template_json["web_directories_status"][status] = {}

    final_json = remove_empty_services(template_json)
    final_json = clean_empty_directories_status(final_json)

    return final_json

def remove_empty_services(template_json):
    if "target" in template_json and "services" in template_json["target"]:
        template_json["target"]["services"] = [
            service for service in template_json["target"]["services"]
            if service.get("port") and service.get("protocol") and service.get("service")
        ]
    return template_json

def clean_empty_directories_status(json_data):
    if "web_directories_status" in json_data:
        web_directories_status = json_data["web_directories_status"]
        for status, directories in web_directories_status.items():
            if "" in directories:
                del directories[""]
            if not directories:
                directories[""] = ""
    return json_data


def print_json_parts(parts):
    def print_dict(d, indent=0):
        for key, value in d.items():
            if isinstance(value, dict):
                print(' ' * indent + f"{key}:")
                print_dict(value, indent + 2)
            elif isinstance(value, list):
                print(' ' * indent + f"{key}:")
                for i, item in enumerate(value):
                    print(f"{' ' * (indent + 2)}Item {i + 1}:")
                    print_dict(item, indent + 4)
            else:
                print(f"{' ' * indent}{key}: {value}")

    print_dict(parts)


def fix_json(state: dict, new_data):
    parts, missing = extract_json_parts_recursive(new_data, DEFAULT_STATE_STRUCTURE)
    if parts:
        print("✅ JSON extracted successfully.")
        print_json_parts(parts)
    else:
        print("❌ Failed to extract valid JSON.")
    
    if missing:
        print("❗ Missing categories/subfields detected:")
        print(json.dumps(missing, indent=2))

    filled_json = fill_json_structure(state, parts)
    print(json.dumps(filled_json, indent=2))
    return filled_json

if __name__ == "__main__":

    state = """
        {
        "target": {
            "ip": "192.168.56.101",
            "os": {
                "name": "",
                "distribution": {
                    "name": "", "version": ""
                },
                "kernel": "",
                "architecture": ""
            },
            "services": [
            {
                "port": "",
                "protocol": "",
                "service": ""
            },
            {
                "port": "",
                "protocol": "",
                "service": ""
            },
            {
                "port": "",
                "protocol": "",
                "service": ""
            }
            ]
        },
        "web_directories_status": {
            "404": {
            "": ""
            },
            "200": {
            "": ""
            },
            "403": {
            "": ""
            },
            "401": {
            "zxcv": "n"
            },
            "503": {
            "": "u"
            }
        },
        "actions_history": [],
        "cpes": [],
        "vulnerabilities_found": [],
        "failed_CVEs": []
        }
        """

    new_data = """
    
    "target": {
        "ip": "192.168.56.101",
        "os": {
            "name": "Linux",
            "distribution": {
                "name": "ubunto", "version": "1.0"
            },
            "kernel": "",
            "architecture": "19"
        },
        "services": [
        {"port": "21", "protocol": "tcp", "service": "ftp"},
        {"port": "22", "protocol": "tcp", "service": "ssh"},
        {"port": "23", "protocol": "tcp", "service": "telnet"},
        {"port": "25", "protocol": "tcp", "service": "smtp"},
        {"port": "53", "protocol": "tcp", "service": "domain"},
        {"port": "80", "protocol": "tcp", "service": "http"},
        {"port": "111", "protocol": "tcp", "service": "rpcbind"},
        {"port": "139", "protocol": "tcp", "service": "netbios-ssn"},
        {"port": "445", "protocol": "tcp", "service": "microsoft-ds"},
        {"port": "512", "protocol": "tcp", "service": "exec"},
        port513", "protocol": "tcp", "servicelogin
        {"port": "1099", "protocol": "tcp", "service": "rmiregistry"},
        {"port": "1524", "protocol": "tcp", "service": "ingreslock"},
        {"port": "2049", "protocol": "tcp", "service": "nfs"},
        {"port": "2121", "protocol": "tcp", "service": "ccproxy-ftp"},
        {"port": "3306", "protocol": "tcp", "service": "mysql"},
        {"port": "5432", "protocol": "tcp", "service": "postgresql"},
        {"port": "5900", "protocol": "tcp", "service": "vnc"},
        {"port": "6000", "protocol": "tcp", "service": "X11"},
        {"port": "6667", "protocol": "tcp", "service": "irc"},
        {"port": "8009", "protocol": "tcp", "service": "ajp13"},
        {"port": "8180", "protocol": "tcp", "service": "unknown"}
        ]
    },
    "web_directories_status": {
        "200": {
        "/": "",
        "/admin": "",
        "/login": "",
        "/public": ""
        },
        "400": {
        "": ""
        },
        "401": {
        "": ""
        },
        "403": {
        "": ""
        },
        "404": {
        "": ""
        },
        "500": {
        "": ""
        },
        "503": {
        "b": "sdf"
        }
    }
    }
    """
    fix_json(json.loads(state), new_data)
