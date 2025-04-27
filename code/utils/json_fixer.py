import re
import json
import os
import sys
import ast

EXPECTED_STRUCTURE = {
    "target": {
        "os": None,
        "services": None
    },
    "web_directories_status": {
        "200": None,
        "401": None,
        "403": None,
        "404": None,
        "503": None
    }
}

def find_missing_categories(parsed_parts, expected_structure):
    missing = {}

    for key, subfields in expected_structure.items():
        if key not in parsed_parts:
            missing[key] = "entire category missing"
        else:
            if isinstance(subfields, dict):
                for subkey in subfields:
                    if subkey not in parsed_parts[key]:
                        missing.setdefault(key, []).append(subkey)

    return missing

def extract_json_parts(new_data):
    """
    Scans the text and extracts parts starting when encountering 'target' or 'web_directories_status'.
    Passes only the specific block after each key to its extractor.
    """
    parts = {}

    text = new_data.replace('\n', ' ').replace('\r', ' ').strip()

    pos = 0
    while pos < len(text):
        # Search for target
        if text[pos:].startswith('target'):
            target_after = text[pos + len('target'):]
            target_text = cut_text_until_word(target_after, 'web_directories_status')
            parts['target'] = extract_target_data(target_text)
            pos += len('target')
            break
        pos += 1  # move forward character by character

    pos = 0
    while pos < len(target_after):
        # Search for web_directories_status
        if target_after[pos:].startswith('web_directories_status'):
            wds_text = target_after[pos + len('web_directories_status'):]
            parts['web_directories_status'] = extract_web_directories_status(wds_text)
            pos += len('web_directories_status')
            break
        pos += 1  # move forward character by character

    missing = find_missing_categories(parts, EXPECTED_STRUCTURE)
    return parts, missing


def extract_target_data(target_text):
    #print(target_text)
    target_data = {}

    pos = 0
    while pos < len(target_text):
        if target_text[pos:].startswith('os'):
            after_os = target_text[pos + len('os'):]
            os_text = cut_text_until_word(after_os, 'services')  # משתמשים בפונקציה החכמה
            os_data = extract_os_from_target(os_text)
            if os_data:
                target_data['os'] = os_data
            pos += len('os')
            break
        pos += 1

    pos = 0
    while pos < len(after_os):
        if after_os[pos:].startswith('services'):
            services_data = extract_services_from_target(after_os[pos + len('services'):])
            if services_data:
                target_data['services'] = services_data
            pos += len('services')
            break
        pos += 1

    return target_data

def extract_web_directories_status(text_after_web):
    """
    Extracts the web_directories_status section.
    Scans for status codes like 200, 401, 403, 404, 503, and collects their associated directories.
    """
    wds = {}
    pos = 0

    while pos < len(text_after_web):
        subtext = text_after_web[pos:]

        # Look for each possible HTTP status code
        for status_code in ['200', '401', '403', '404', '503']:
            if subtext.startswith(status_code):
                status_block = extract_status_block(subtext, status_code)
                if status_block is not None:
                    wds[status_code] = status_block
                pos += len(status_code)
                break  # found a match, restart checking
        else:
            pos += 1  # if no status matched, move forward

    return wds
def extract_os_from_target(text):
    """
    Extracts OS from a clean piece of text (already trimmed at services).
    Accepts only letters, digits, spaces, dots, dashes.
    """
    print(text)
    after_os = text.lstrip()

    os_value = ''
    idx = 0
    while idx < len(after_os):
        c = after_os[idx]
        if c.isalnum() or c in [' ', '.', '-']:
            os_value += c
            idx += 1
        else:
            break  # ברגע שמגיעים לתו לא חוקי - עוצרים
    return os_value.strip() if os_value else None

def cut_text_until_word(text, stop_word):
    """
    Scans character by character through 'text', and stops exactly when 'stop_word' starts.
    
    Args:
        text (str): The input text to scan.
        stop_word (str): The word that signals to stop collecting.

    Returns:
        str: The collected text up until (but not including) the stop_word.
    """
    collected = ''
    idx = 0
    while idx < len(text):
        if text[idx:].startswith(stop_word):
            break
        collected += text[idx]
        idx += 1
    return collected


def extract_services_from_target(text_after_services):
    """
    Extracts the services from the text after 'services'.
    Finds sequential triplets of (port, protocol, service) even if messy.
    """
    services = []
    pos = 0
    current_service = {}

    while pos < len(text_after_services):
        subtext = text_after_services[pos:]

        # Find port
        if subtext.startswith('port'):
            port_value, jump = extract_value_after_key(subtext, 'port', next_keys=['protocol', 'service'])
            if port_value:
                current_service['port'] = port_value
            pos += jump
            continue

        # Find protocol
        if subtext.startswith('protocol'):
            protocol_value, jump = extract_value_after_key(subtext, 'protocol', next_keys=['port', 'service'])
            if protocol_value:
                current_service['protocol'] = protocol_value
            pos += jump
            continue

        # Find service
        if subtext.startswith('service'):
            service_value, jump = extract_value_after_key(subtext, 'service', next_keys=['port', 'protocol'])
            if service_value:
                current_service['service'] = service_value

            # אחרי שהשגנו את שלושתם -> הוסף
            if all(k in current_service for k in ('port', 'protocol', 'service')):
                services.append(current_service)
                current_service = {}

            pos += jump
            continue

        pos += 1

    return services

def extract_value_after_key(text, key_name, next_keys=None):
    """
    Extracts the value after a key, stopping immediately if a next key starts.
    """
    key_pos = text.find(key_name)
    if key_pos == -1:
        return None, len(key_name)

    after_key = text[key_pos + len(key_name):].lstrip()

    # דילג על רעשים
    while after_key and after_key[0] in [':', ' ', '\'', '"', '{', '}']:
        after_key = after_key[1:]

    value = ''
    idx = 0
    while idx < len(after_key):
        subtext = after_key[idx:]

        # ❗ בדוק כל הזמן אם התחלנו מילת next_key
        if next_keys:
            for k in next_keys:
                if subtext.startswith(k):
                    return value.strip(), key_pos + len(key_name) + idx

        c = after_key[idx]
        if c.isalnum() or c in ['-', '.', '/']:
            value += c
            idx += 1
        else:
            break  # פיסוק - עצור

    return value.strip(), key_pos + len(key_name) + idx

def extract_status_block(text_after_status, status_code):
    """
    Extracts all directories and their statuses after a given HTTP status code.
    Stops when '}' or a new status code appears.
    """
    after_status = text_after_status[len(status_code):].lstrip()

    while after_status and after_status[0] in [':', '{', ' ', '\'', '"']:
        after_status = after_status[1:]

    directories = {}
    pos = 0
    inside_block = True
    status_codes = ['200', '401', '403', '404', '503']

    while pos < len(after_status) and inside_block:
        while pos < len(after_status) and after_status[pos] in [':', ' ', '\'', '"', ',']:
            pos += 1
        
        if pos >= len(after_status):
            break

        # בדוק אם מתחיל קוד סטטוס חדש
        for code in status_codes:
            if after_status[pos:].startswith(code):
                inside_block = False
                break
        if not inside_block:
            break

        if after_status[pos] == '}':
            inside_block = False
            break

        # קריאת path
        path = ''
        while pos < len(after_status):
            subtext = after_status[pos:]
            if any(subtext.startswith(code) for code in status_codes):
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

        # ⬇️⬇️⬇️ עכשיו מייד אחרי path — קוראים את value!!

        # דלג על רווחים וגרשיים
        while pos < len(after_status) and after_status[pos] in [' ', ':', '\'', '"', '{']:
            pos += 1

        # קריאת value
        value = ''
        while pos < len(after_status):
            subtext = after_status[pos:]
            if any(subtext.startswith(code) for code in status_codes):
                inside_block = False
                break
            if after_status[pos] in [',', '}', '\'', '"', ':']:
                break
            value += after_status[pos]
            pos += 1
        value = value.strip()

        if path:
            directories[path] = value

        # דילוג אחרי value
        while pos < len(after_status) and after_status[pos] in [' ', ',', ':', '\'', '"']:
            pos += 1
        if pos < len(after_status) and after_status[pos] == '}':
            inside_block = False
            break

    if not directories:
        return {"": ""}
    return directories

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
            for status in ["200", "401", "403", "404", "503"]:
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


def fix_json(state: dict, new_data):
    parts, missing = extract_json_parts(new_data)
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

state = """
{
  "target": {
    "ip": "192.168.56.101",
    "os": "",
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
      "": ""
    },
    "503": {
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
target'''osLinuxservices' 'port '21, 'protocoltcp', 'service': 'ftpport': '22', 'protocol': 'tcp', 'service': 'ssh'}, {'port': '23', 'protocol': 'tcp', 'service': 'telnet'}, {'port': '25', 'protocol': 'tcp', 'service': 'smtp'}, {'port': '53', 'protocol': 'tcp', 'service': 'domain'}, {'port': '80', 'protocol': 'tcp', 'service': 'http'}, {'port': '111', 'protocol': 'tcp', 'service': 'rpcbind'}, {'port': '445', 'protocol': 'tcp', 'service': 'netbios-ssn'}, {'port': '512', 'protocol': 'tcp', 'service': 'exec'}, {'port': '513', 'protocol': 'tcp', 'service': 'login'}, {'port': '1099', 'protocol': 'tcp', 'service': 'java-rmi'}, {'port': '1524', 'protocol': 'tcp', 'service': 'bindshell'}, {'port': '2049', 'protocol': 'tcp', 'service': 'nfs'}, {'port': '2121', 'protocol': 'tcp', 'service': 'ftp'}, {'port': '3306', 'protocol': 'tcp', 'service': 'mysql'}, {'port': '5432', 'protocol': 'tcp', 'service': 'postgresql'}, {'port': '5900', 'protocol': 'tcp', 'service': 'vnc'}, {'port': '6000', 'protocol': 'tcp', 'service': 'x11'}, {'port': '6667', 'protocol': 'tcp', 'service': 'ircweb_directories_status': {'200': {'abc': '123'}, '401': {'aaa': '111403': {'': ''},  ''}, '503': {'nn': 'dfg
"""

if __name__ == "__main__":
    fix_json(json.loads(state), new_data)
