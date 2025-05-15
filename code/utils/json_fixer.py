import re
import json
import os
import sys
import ast
import copy

from config import EXPECTED_STATUS_CODES
from blackboard.blackboard import initialize_blackboard, initialize_dict

def normalize_parts(data: any, schema: any):
    if isinstance(schema, dict) and isinstance(data, dict):
        for key, exp in schema.items():
            if key not in data:
                continue
            normalize_parts(data[key], exp)
        return

    # Case: schema is a list (either of scalars or of dicts)
    if isinstance(schema, list):
        # placeholder for empty or non-list scraped data
        placeholder = None
        if schema and isinstance(schema[0], dict):
            import copy
            placeholder = [copy.deepcopy(schema[0])]
        else:
            placeholder = [schema[0]] if schema else []

        # if scraped value isn't a list, or is an empty list, return placeholder
        if not isinstance(data, list) or len(data) == 0:
            return placeholder

        # now data is a non-empty list
        if schema and isinstance(schema[0], dict):
            return [
                normalize_parts(item, schema[0]) if isinstance(item, dict) else item
                for item in data
            ]
        # list-of-scalars: assume scraped list is fine
        return data

    return

def split_items_on_repeat(text: str, field_keys: list[str]) -> list[str]:
    """
    Splits a text blob into one chunk per occurrence of the first schema field.
    Matches the field as a whole word (\b…\b), no quotes required.
    """
    if not field_keys:
        return [text]

    first = field_keys[0]
    pattern = re.compile(rf'\b{re.escape(first)}\b')
    positions = [m.start() for m in pattern.finditer(text)]
    if not positions:
        return []

    chunks = []

    for idx, start in enumerate(positions):
        end = positions[idx + 1] if idx + 1 < len(positions) else len(text)
        chunk = text[start:end].strip(" \t\n\r,")
        chunks.append(chunk)

    return chunks


def clean_input_string(s: str, preserve_prefix: int = 0) -> str:
    if not isinstance(s, str):
        return s
    s = s.strip()

    prefix = s[:preserve_prefix]
    rest = s[preserve_prefix:]

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
    try:
        text_snippet = json.dumps(text, default=str)[:80]
    except Exception:
        text_snippet = str(text)[:80]

    print(f"[DEBUG] extract_json_parts_recursive(type={type(text).__name__}, snippet={text_snippet!r}, keys={list(structure.keys())})")
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

                # Dynamic status-code dict
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

                # Nested object
                elif isinstance(expected_type, dict):
                    is_status_mapping = all(str(k).isdigit() for k in expected_type.keys())
                    if not is_status_mapping:
                        print(f"[DEBUG] Recursing into object key={key!r}")
                        print(f"[DEBUG]   raw block_text for {key!r}: {block_text!r}")
                    cleaned_block = block_text.lstrip(': {\'\"')
                    if not is_status_mapping:
                        print(f"[DEBUG]   cleaned block_text for {key!r}: {cleaned_block!r}")
                    sub_result, _ = extract_json_parts_recursive(cleaned_block, expected_type)
                    if not is_status_mapping:
                        print(f"[DEBUG]   result for {key!r}: {sub_result!r}")
                    parts[key] = sub_result

                elif isinstance(expected_type, list) and expected_type and isinstance(expected_type[0], dict):
                    # grab the one‐item schema so we don’t clobber the outer `keys`
                    item_struct = expected_type[0]
                    item_keys   = list(item_struct.keys())

                    # split into raw text chunks whenever the first field repeats
                    raw_items = split_items_on_repeat(block_text, [item_keys[0]])
                    print(f"[DEBUG] raw_items splits: {raw_items}")

                    list_result = []

                    for raw in raw_items:
                        current = {k: "" for k in item_keys}
                        stop_fields = set(structure.keys()) - set(item_keys)
                        
                        for field in item_keys:
                            val, offset = extract_value_after_key(raw, field, next_keys=item_keys)
                            current[field] = clean_input_string(val or "")
                        
                        for word in stop_fields:
                            if re.search(rf'\b{re.escape(word)}\b\s*:', raw):
                                print(f"[WARNING] Skipping irrelevant field inside block: {word}")
                                break

                        if current.get(item_keys[0], ""):
                            list_result.append(current)

                    parts[key] = list_result

                # Scalar value
                else:
                    parts[key] = clean_input_string(block_text)

                pos += len(key)
                break
        pos += 1

    # Ensure all expected keys exist
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
    - Lists of dicts: append any item that has a non-empty 'port'.
    """
    for key, expected in expected_structure.items():
        if key not in extracted_parts:
            continue

        # Dynamic status–code dicts (כל המקשים ספרות) – נשאר איך שהיה
        if isinstance(expected, dict) and all(str(k).isdigit() for k in expected.keys()):
            merged = {
                code: dirs
                for code, dirs in template_json.get(key, {}).items()
                if code
            }
            for code, dirs in extracted_parts[key].items():
                if not isinstance(dirs, dict):
                    continue
                real = {d: v for d, v in dirs.items() if d}
                if real:
                    merged.setdefault(code, {}).update(real)
                else:
                    merged.setdefault(code, {})[""] = ""
            template_json[key] = merged
            continue

        value = extracted_parts[key]

        # 1) Scalar
        if not isinstance(expected, (dict, list)):
            if value and not template_json.get(key):
                template_json[key] = value
            continue

        # 2) Nested dict
        if isinstance(expected, dict):
            sub_template = template_json.get(key, {})
            if not isinstance(sub_template, dict):
                sub_template = {}
            template_json[key] = fill_json_structure(
                sub_template,
                value if isinstance(value, dict) else {},
                expected
            )
            continue

        # 3) List-of-dicts (services ועוד) – נשמור כל אייטם עם 'port'
        if isinstance(expected, list) and expected and isinstance(expected[0], dict):
            sub_template_list = template_json.get(key, [])
            if not isinstance(sub_template_list, list):
                sub_template_list = []

            for item in value:
                if not isinstance(item, dict):
                    continue

                if not item.get('port'):
                    continue

                if item not in sub_template_list:
                    sub_template_list.append(item)

            template_json[key] = sub_template_list
            continue

    return template_json

def remove_empty_fields(json_data: dict, expected_structure: dict) -> dict:
    print(f"[DEBUG] expected_structure: {expected_structure}")
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
            continue

        # 2) dynamic dict-of-dicts (status codes)
        if isinstance(expected, dict) and all(str(k).isdigit() for k in expected.keys()):
            if isinstance(val, dict):
                for code, dirs in val.items():
                    if isinstance(dirs, dict):
                        dirs.pop("", None)
            continue

        # 3) nested dict
        if isinstance(expected, dict):
            if isinstance(val, dict):
                json_data[key] = remove_empty_fields(val, expected)
            continue

    return json_data

def build_state_from_parts(extracted_parts: dict, expected_structure: dict) -> dict:
    """
    Returns a new dict based on expected_structure, with extracted_parts merged in.
    Uses the same merging rules as fill_json_structure.
    """
    state = copy.deepcopy(expected_structure)

    for key, expected in expected_structure.items():
        if key not in extracted_parts:
            continue

        parts = extracted_parts[key]

        if isinstance(expected, dict) and all(str(k).isdigit() for k in expected):
            merged = {
                code: dirs
                for code, dirs in state.get(key, {}).items()
                if code
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

        if not isinstance(expected, (dict, list)):
            if parts and not state.get(key):
                state[key] = parts
            continue

        if isinstance(expected, dict):
            sub = state.get(key, {})
            if not isinstance(sub, dict):
                sub = {}
            state[key] = build_state_from_parts(parts if isinstance(parts, dict) else {}, expected)
            continue

        if isinstance(expected, list) and expected and isinstance(expected[0], dict):
            lst = state.get(key, [])
            if not isinstance(lst, list):
                lst = []
            for item in parts:
                if not isinstance(item, dict):
                    continue
                if item not in lst:
                    lst.append(item)
            state[key] = lst

    return state

def print_json_parts(parts):
    def print_dict(d, indent=0):
        if not isinstance(d, dict):
            print(' ' * indent + str(d))
            return

        for key, value in d.items():
            if isinstance(value, dict):
                print(' ' * indent + f"{key}:")
                print_dict(value, indent + 2)

            elif isinstance(value, list):
                print(' ' * indent + f"{key}:")
                for i, item in enumerate(value):
                    print(f"{' ' * (indent + 2)}Item {i + 1}:")
                    if isinstance(item, dict):
                        print_dict(item, indent + 4)
                    else:
                        print(' ' * (indent + 4) + str(item))

            else:
                print(f"{' ' * indent}{key}: {value}")

    print_dict(parts)


def fix_json(state: dict, new_data: str, Dict) -> dict:
    # 1) Extract parts and report
    extracted_parts, missing = extract_json_parts_recursive(new_data, initialize_dict(Dict))

    def _apply_normalization(parts, schema):

        if isinstance(schema, list) and schema and isinstance(schema[0], dict):
            if not isinstance(parts, list):
                return []
            for idx, itm in enumerate(parts):
                if isinstance(itm, dict):
                    parts[idx] = _apply_normalization(itm, schema[0])
            return parts
        elif isinstance(schema, dict) and isinstance(parts, dict):
            for k, exp in schema.items():
                if k in parts:
                    parts[k] = _apply_normalization(parts[k], exp)
            return parts
        else:
            return parts
        
    if extracted_parts:
        print("✅ JSON extracted successfully.")
        print_json_parts(extracted_parts)
    else:
        print("❌ Failed to extract valid JSON.")

    extracted_parts = _apply_normalization(extracted_parts, initialize_dict(Dict))  

    if missing:
        missing = {
            path: err 
            for path, err in missing.items()
        }
        print("❗ Missing categories/subfields detected:")
        print(json.dumps(missing, indent=2))
    
    data_for_cache = build_state_from_parts(extracted_parts, initialize_dict(Dict))

    state = copy.deepcopy(state)

    # 2) Merge into the original state using the expected schema
    filled = fill_json_structure(state, extracted_parts, initialize_dict(Dict))

    # 3) Run our generic cleanup (services, status‐codes, etc.)
    final_json = remove_empty_fields(filled, initialize_dict(Dict))

    # 4) Show and return
    print("🧹 Final cleaned JSON:")
    print(json.dumps(final_json, indent=2))
    return final_json, data_for_cache

# [DEBUG]
if __name__ == "__main__":

    state = """
        {
        "target": {
            "os": {
            "distribution": {
                "name": "",
                "version": "",
                "architecture": ""
            },
            "kernel": "",
            "name": "Linux"
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
            }
            ]
        },
        "web_directories_status": {
            "200": {
            "": ""
            },
            "301": {
            "": ""
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
            "": ""
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
        }
        }
        """

    new_data = """
    {"target":{"ip":"192.168.56.101","os":{"name":"Linux","distribution":{},"kernel":""},"services":[{"port":"21","protocol":"tcp","service":"ftp","server_type":"","server_version":"","supported_protocols":[],"softwares":[]},{"port":"22","protocol":"tcp","service":"ssh","server_type":"","server_version":"","supported_protocols":[],"softwares":[]},{"port":"23","protocol":"tcp","service":"telnet","server_type":"","server_version":"","supported_protocols":[],"softwares":[]},{"port":"25","protocol":"tcp","service":"smtp","server_type":"","server_version":"","supported_protocols":[],"softwares":[]},{"port":"53","protocol":"tcp","service":"domain","server_type":"","server_version":"","supported_protocols":[],"softwares":[]},{"port":"80","protocol":"tcp","service":"http","server_type":"","server_version":"","supported_protocols":[],"softwares":[]},{"port":"111","protocol":"tcp","service":"rpcbind","server_type":"","server_version":"","supported_protocols":[],"softwares":[]},{"port":"139","protocol":"tcp","service":"netbios-ssn","server_type":"","server_version":"","supported_protocols":[],"softwares":[]},{"port":"445","protocol":"tcp","service":"microsoft-ds","server_type":"","server_version":"","supported_protocols":[],"softwares":[]},{"port":"512","protocol":"tcp","service":"exec","server_type":"","server_version":"","supported_protocols":[],"softwares":[]},{"port":"513","protocol":"tcp","service":"login","server_type":"","server_version":"","supported_protocols":[],"softwares":[]},{"port":"514","protocol":"tcp","service":"shell","server_type":"","server_version":"","supported_protocols":[],"softwares":[]},{"port":"1099","protocol":"tcp","service":"rmiregistry","server_type":"","server_version":"","supported_protocols":[],"softwares":[]},{"port":"1524","protocol":"tcp","service":"ingreslock","server_type":"","server_version":"","supported_protocols":[],"softwares":[]},{"port":"2049","protocol":"tcp","service":"nfs","server_type":"","server_version":"","supported_protocols":[],"softwares":[]},{"port":"2121","protocol":"tcp","service":"ccproxy-ftp","server_type":"","server_version":"","supported_protocols":[],"softwares":[]},{"port":"3306","protocol":"tcp","service":"mysql","server_type":"","server_version":"","supported_protocols":[],"softwares":[]},{"port":"5432","protocol":"tcp","service":"postgresql","server_type":"","server_version":"","supported_protocols":[],"softwares":[]},{"port":"5900","protocol":"tcp","service":"vnc","server_type":"","server_version":"","supported_protocols":[],"softwares":[]},{"port":"6000","protocol":"tcp","service":"X11","server_type":"","server_version":"","supported_protocols":[],"softwares":[]},{"port":"6667","protocol":"tcp","service":"irc","server_type":"","server_version":"","supported_protocols":[],"softwares":[]},{"port":"8009","protocol":"tcp","service":"ajp13","server_type":"","server_version":"","supported_protocols":[],"softwares":[]},{"port":"","protocol":"","service":"","server_type":"","server_version":"","supported_protocols":[],"softwares":[]}],"web_directories_status":{"200":{},"301":{},"302":{},"307":{},"401":{},"403":{},"500":{},"502":{},"503":{},"504":{}}}.
[DEBUG] extract_json_parts_recursive(text_snippet='{"target":{"ip":"192.168.56.101","os":{"name":"Linux","distribution":{},"kernel"', keys=['target', 'web_directories_status'])
    """
    state_dict = json.loads(state)
    print(fix_json(state_dict, new_data))