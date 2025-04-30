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
    # ── DEBUG: entering recursion, show a snippet of the text and the keys we expect ──
    print(f"[DEBUG] extract_json_parts_recursive(text_snippet={text[:80]!r}, keys={list(structure.keys())})")
    parts: dict = {} 
    text = text.replace('\n', ' ').replace('\r', ' ').strip()
    keys = list(structure.keys())

    pos = 0
    while pos < len(text):
        for i, key in enumerate(keys):
            #── DEBUG: disable skipping duplicates so 'os' always matches ──
            if key in parts:
                continue
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
                            # detect “status‐code” dicts (all keys are digits) and skip debug for those
                            is_status_mapping = all(str(k).isdigit() for k in expected_type.keys())
                
                            if not is_status_mapping:
                                # — only for real object‐like fields (e.g. os, distribution, target…) —
                                print(f"[DEBUG] Recursing into object key={key!r}")
                                print(f"[DEBUG]   raw block_text for {key!r}: {block_text!r}")
                            # strip leading punctuation so inner keys line up
                            cleaned_block = block_text.lstrip(': {\'"')
                            if not is_status_mapping:
                                print(f"[DEBUG]   cleaned block_text for {key!r}: {cleaned_block!r}")
                            # recurse
                            sub_result, _ = extract_json_parts_recursive(cleaned_block, expected_type)
                            if not is_status_mapping:
                                print(f"[DEBUG]   result for {key!r}: {sub_result!r}")
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
                    # strip surrounding punctuation, quotes, commas, braces and whitespace
                    cleaned = block_text.strip(' :{},"\n\r,')
                    parts[key] = cleaned


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

def fill_json_structure(template_json: dict,
                        extracted_parts: dict,
                        expected_structure: dict) -> dict:
    """
    Recursively merge extracted_parts into template_json based on expected_structure.
    - Scalars: only set if template_json[key] is empty.
    - Dicts: recurse into sub-dicts.
    - Lists of dicts: append any item not already present (by full-item equality).
    """
    for key, expected in expected_structure.items():
        # אם לא הוצא כלום – דילוג
        if key not in extracted_parts:
            continue

        # ── Branch for dynamic status–code dicts (כל המקשים הם ספרות) ──
        if isinstance(expected, dict) and all(str(k).isdigit() for k in expected.keys()):
            # קח עותק של המצב הקיים, בלי placeholder:
            merged = {
                code: dirs
                for code, dirs in template_json.get(key, {}).items()
                if code  # רק אם הקוד לא ריק
            }
            print(f"[DEBUG] before merge status={key}: {merged!r}")
            # וננדס איך שהתקבלו ב־extracted_parts
            for code, dirs in extracted_parts[key].items():
                if not isinstance(dirs, dict):
                    continue
                # מחשב רק התיקיות האמיתיות מתוך extracted
                real = {d: v for d, v in dirs.items() if d}
                if real:
                    merged.setdefault(code, {}).update(real)
                else:
                    # אין ערכים אמיתיים -> שמור placeholder
                    merged.setdefault(code, {})[""] = ""
            print(f"[DEBUG] after  merge status={key}: {merged!r}")
            template_json[key] = merged
            # המשך ללולאה מבלי לגרום לרקורסיה הרגילה
            continue
        value = extracted_parts[key]
        # 1) Scalar field
        if not isinstance(expected, (dict, list)):
            if value and not template_json.get(key):
                template_json[key] = value
            continue

        # 2) Nested dict
        if isinstance(expected, dict):
            # get or init a dict in the template
            sub_template = template_json.get(key, {})
            if not isinstance(sub_template, dict):
                sub_template = {}
            # recurse
            template_json[key] = fill_json_structure(
                sub_template,
                value if isinstance(value, dict) else {},
                expected
            )
            continue

        # 3) List-of-dicts
        if isinstance(expected, list) and expected and isinstance(expected[0], dict):
            # get or init a list in the template
            sub_template_list = template_json.get(key, [])
            if not isinstance(sub_template_list, list):
                sub_template_list = []

            # each item in `value` should be a dict matching expected[0]
            for item in value:
                if not isinstance(item, dict):
                    continue
                # drop any empty items
                if any(not item.get(f) for f in expected[0].keys()):
                    continue
                # append if not already there
                if item not in sub_template_list:
                    sub_template_list.append(item)

            template_json[key] = sub_template_list

    return template_json

def clean_after_fill(json_data: dict, expected_structure: dict) -> dict:
    """
    לנקות אחרי מיזוג:
    1. לכל מפתח שהוא list של dicts — הסרת פריטים שלא מלאים בכל השדות.
       אם List ריק בסוף, יוצרים פריט ריק עם כל השדות כמחרוזת ריקה.
    2. לכל מפתח שהוא dict של dicts עם מפתחות ספרתיים (status codes) — 
       הסרת המפתח "" ולהוספתו אם מערך הערכים ריק.
    3. לכל מפתח שהוא dict רגיל — רק לחזור פנימה.
    """
    for key, expected in expected_structure.items():
        if key not in json_data:
            continue

        val = json_data[key]

        # 1) List-of-dicts
        if isinstance(expected, list) and expected and isinstance(expected[0], dict):
            item_struct = expected[0]
            cleaned_list = []
            for item in val if isinstance(val, list) else []:
                # נשמור פריט רק אם כל השדות שלו מלאים
                if all(item.get(field) for field in item_struct):
                    cleaned_list.append(item)
            # אם אין פריטים — נשים פריט ריק
            if not cleaned_list:
                cleaned_list = [{field: "" for field in item_struct}]
            json_data[key] = cleaned_list
            continue

        # 2) Dynamic dict-of-dicts (status codes)
        if isinstance(expected, dict) and all(str(k).isdigit() for k in expected.keys()):
            block = val if isinstance(val, dict) else {}
            # הסרת מפתח ריק
            block.pop("", None)
            # אם אין ערכים — נחזיר {"": ""}
            if not block:
                block[""] = ""
            json_data[key] = block
            continue

        # 3) Nested dict — נקרא רקורסיבית
        if isinstance(expected, dict):
            sub = val if isinstance(val, dict) else {}
            json_data[key] = clean_after_fill(sub, expected)

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

def fix_json(state: dict, new_data: str) -> dict:
    # 1) Extract parts and report (use EXPECTED_STRUCTURE)
    extracted_parts, missing = extract_json_parts_recursive(new_data, EXPECTED_STRUCTURE)
    if extracted_parts:
        print("✅ JSON extracted successfully.")
        print_json_parts(extracted_parts)
    else:
        print("❌ Failed to extract valid JSON.")

    if missing:
        # ── drop any “missing” שנוצר עבור web_directories_status.<code>. ──
        missing = {
            path: err 
            for path, err in missing.items()
            if not path.startswith("web_directories_status.") or path == "web_directories_status"
        }
        print("❗ Missing categories/subfields detected:")
        print(json.dumps(missing, indent=2))

    # 2) Merge into the original state using the expected schema
    filled = fill_json_structure(state, extracted_parts, EXPECTED_STRUCTURE)

    # 3) Run our generic cleanup (services, status‐codes, etc.)
    final_cleaned = clean_after_fill(filled, EXPECTED_STRUCTURE)

    # 4) Show and return
    print("🧹 Final cleaned JSON:")
    print(json.dumps(final_cleaned, indent=2))
    return final_cleaned


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
            "200": {
                "": "",
                "/dav/": "OK",
                "/index": "OK",
                "/index.php": "OK",
                "/phpinfo": "OK",
                "/phpinfo.php": "OK",
                "/test/": "OK",
                "/twiki/": "OK"
            },
            "301": {
                "": "",
                "/dav": "Moved Permanently",
                "/phpMyAdmin": "Moved Permanently"
            },
            "302": {
                "": ""
            },
            "307": {
                "": ""
            },
            "401": {
                "": ""
            },
            "403": {
                "": "",
                "/.hta": "Forbidden",
                "/.htaccess": "Forbidden",
                "/.htpasswd": "Forbidden",
                "/cgi-bin/": "Forbidden",
                "/server-status": "Forbidden"
            },
            "500": {
                "": ""
            },
            "502": {
                "": ""
            },
            "503": {
                "": ""
            },
            "504": {
                "": ""
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
        "os": 
            "name": "Linux
distributionname": "ubunto", "version": "1.0"
            
            "kernel76543garchitecture": "19
        },
        "services

        {"port": "139", "protocol": "tcp", "service": "netbios-ssn"},
        {"port": "445", "protocol": "tcp", "service": "microsoft-ds"}port": "512", "protocol": "tcp", "service": "exec"},
        port513", "protocol": "tcp", "servicelogin

        {"port": "8180", "protocol": "tcp", "service": "unknown"}
        ]
    },
    "web_directories_status200": {
        "/": "",
        "/admin": "",
        "/login": ""public": ""
        },
        "400
        "": "
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
        "503
        "b": "sdf"
        }
    }
    }
    """
    fix_json(json.loads(state), new_data)
