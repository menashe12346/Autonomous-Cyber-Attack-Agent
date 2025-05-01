import re
import json
import os
import sys
import ast
import copy
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import EXPECTED_STATUS_CODES
from blackboard.blackboard import initialize_blackboard

EXPECTED_STRUCTURE = initialize_blackboard()
EXPECTED_STRUCTURE["target"].pop("ip",None)

import re

def clean_input_string(s: str, preserve_prefix: int = 0) -> str:
    """
    מנקה מחרוזת מתווים לא רצויים, עם אפשרות לשמר N תווים מההתחלה (למשל '/', './').
    - מסיר תווים כמו , : " ' ( ) [ ] { } < > .
    - מבצע strip לתווי קצה כמו רווחים, נקודותיים, גרשיים וכו'.
    """
    if not isinstance(s, str):
        return s
    s = s.strip()

    # חלק לשימור בתחילת המחרוזת
    prefix = s[:preserve_prefix]
    rest = s[preserve_prefix:]

    # ניקוי שאר המחרוזת
    cleaned_rest = re.sub(r"[,:\"'()\[\]{}<>]", "", rest)
    cleaned_rest = cleaned_rest.strip(' :{},"\n\r\'')

    return prefix + cleaned_rest

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
        path = clean_input_string(path)

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
        value = clean_input_string(value)

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
                                cleaned_item = {f: clean_input_string(current_item[f]) for f in item_structure}
                                list_result.append(cleaned_item)
                                current_item = {}
                        else:
                            item_pos += 1
                    parts[key] = list_result

                else:
                    # strip surrounding punctuation, quotes, commas, braces and whitespace
                    parts[key] = clean_input_string(block_text)


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

def fill_json_structure(template_json: dict,
                        extracted_parts: dict,
                        expected_structure: dict) -> dict:
    """
    Recursively merge extracted_parts into template_json based on expected_structure.
    - Scalars: only set if template_json[key] is empty.
    - Dicts: recurse into sub-dicts.
    - Lists of dicts: append any item not already present (by full-item equality).
    """
    print(f"template_json: {template_json}")
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
def remove_empty_fields(json_data: dict, expected_structure: dict) -> dict:
    """
    מסיר רק placeholders דינמיים בתוך json_data לפי expected_structure:
      - list of dicts: drop items שכל השדות שלהם == ""
      - dict-of-dicts with digit keys: pop("") בלבד
      - nested dicts: recurse
    לא מוסיף placeholder חדש, לא מוחק מפתחות סקימטיים.
    """
    print(f"expected_structure: {expected_structure}")
    for key, expected in expected_structure.items():
        if key not in json_data:
            continue

        val = json_data[key]

        # 1) list-of-dicts (e.g. services)
        if isinstance(expected, list) and expected and isinstance(expected[0], dict):
            item_struct = expected[0]
            if isinstance(val, list):
                json_data[key] = [
                    item for item in val
                    if any(item.get(field) for field in item_struct.keys())
                ]
            # else: לא נוגעים
            continue

        # 2) dynamic dict-of-dicts (status codes)
        if isinstance(expected, dict) and all(str(k).isdigit() for k in expected.keys()):
            if isinstance(val, dict):
                for code, dirs in val.items():
                    if isinstance(dirs, dict):
                        dirs.pop("", None)
            # else: לא נוגעים
            continue

        # 3) nested dict
        if isinstance(expected, dict):
            if isinstance(val, dict):
                json_data[key] = remove_empty_fields(val, expected)
            # else: לא נוגעים
            continue

    return json_data

import copy

def build_state_from_parts(extracted_parts: dict, expected_structure: dict) -> dict:
    """
    Returns a new dict based on expected_structure, with extracted_parts merged in.
    Uses the same merging rules as fill_json_structure.
    """
    # 1) יוצרים עותק עמוק של המבנה
    state = copy.deepcopy(expected_structure)

    # 2) ממזגים פנימה
    for key, expected in expected_structure.items():
        if key not in extracted_parts:
            continue

        parts = extracted_parts[key]

        # מצב־קוד דינמי (כל המפתחות ספרות)
        if isinstance(expected, dict) and all(str(k).isdigit() for k in expected):
            merged = {
                code: dirs
                for code, dirs in state.get(key, {}).items()
                if code  # שומרים רק קודים לא ריקים
            }
            for code, dirs in parts.items():
                if not isinstance(dirs, dict):
                    continue
                real = {p: v for p, v in dirs.items() if p}
                if real:
                    merged.setdefault(code, {}).update(real)
                else:
                    merged.setdefault(code, {})[""] = ""
            state[key] = merged
            continue

        # שדה סקלרי
        if not isinstance(expected, (dict, list)):
            if parts and not state.get(key):
                state[key] = parts
            continue

        # dict מקונן
        if isinstance(expected, dict):
            sub = state.get(key, {})
            if not isinstance(sub, dict):
                sub = {}
            state[key] = build_state_from_parts(parts if isinstance(parts, dict) else {}, expected)
            continue

        # list של dicts
        if isinstance(expected, list) and expected and isinstance(expected[0], dict):
            lst = state.get(key, [])
            if not isinstance(lst, list):
                lst = []
            for item in parts:
                if not isinstance(item, dict):
                    continue
                # סינון פריטים ריקים
                if any(not item.get(f) for f in expected[0].keys()):
                    continue
                if item not in lst:
                    lst.append(item)
            state[key] = lst

    return state

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
    EXPECTED_STRUCTURE=initialize_blackboard()
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
    
    state = copy.deepcopy(state)

    EXPECTED_STRUCTURE=initialize_blackboard()
    data_for_cache = build_state_from_parts(extracted_parts, EXPECTED_STRUCTURE)

    EXPECTED_STRUCTURE=initialize_blackboard()
    # 2) Merge into the original state using the expected schema
    filled = fill_json_structure(state, extracted_parts, EXPECTED_STRUCTURE)

    EXPECTED_STRUCTURE=initialize_blackboard()
    # 3) Run our generic cleanup (services, status‐codes, etc.)
    final_json = remove_empty_fields(filled, EXPECTED_STRUCTURE)

    # 4) Show and return
    print("🧹 Final cleaned JSON:")
    print(json.dumps(final_json, indent=2))
    return final_json, data_for_cache


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
    extracted_parts, missing = extract_json_parts_recursive(new_data, EXPECTED_STRUCTURE)
    data_for_cache = build_state_from_parts(extracted_parts, EXPECTED_STRUCTURE)
    print(data_for_cache)
