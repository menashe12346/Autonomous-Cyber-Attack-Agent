import re
import json
import os
import sys
import ast

# sys.path.append(...) if needed for blackboard (commented now)

def fix_malformed_json(text):
    text = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)
    text = re.sub(r'"(\d{3})"\s*{(/\s*":\s*")', r'"\1": {"\2', text)
    text = re.sub(r'"/\s*":\s*([a-zA-Z0-9\s]+)"', r'"/": "\1"', text)
    text = re.sub(r'(\d{3}):\s*{/\s*":\s*', r'"\1": {"', text)
    text = re.sub(r'([a-zA-Z0-9_\-/]+)\s*:', r'"\1":', text)

    def fix_key_value_line(match):
        key = match.group(1).strip()
        value = match.group(2).strip()
        if key and value and not key.endswith('"') and not value.startswith('"'):
            return f'"{key}": "{value}"'
        return match.group(0)

    text = re.sub(r'"(/[^"]*?):\s*([^"]+?)"', fix_key_value_line, text)
    text = re.sub(r'"\s*"\s*:\s*"\s*"\s*(?!,)', '"": "",', text)
    text = re.sub(r'}\s*{', '}, {', text)
    text = re.sub(r",\s*([\]}])", r"\1", text)

    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1:
        text = text[start:end+1]

    open_count = text.count('{')
    close_count = text.count('}')
    if open_count > close_count:
        text += '}' * (open_count - close_count)

    return text
def extract_json_parts(raw_text):
    parts = {}

    text = raw_text.replace('\n', ' ').replace('\r', ' ').strip()

    if 'target' not in text:
        return parts

    target_start = text.find('target')
    target_text = text[target_start:]

    parts["target"] = {}

    # 1. Extract ip
    if 'ip' in target_text:
        ip_start = target_text.find('ip')
        ip_value = extract_simple_value(target_text[ip_start:], key_name="ip")
        if ip_value:
            parts["target"]["ip"] = ip_value

    # 2. Extract os
    if 'os' in target_text:
        os_start = target_text.find('os')
        os_value = extract_os_value(target_text[os_start + len('os'):])
        if os_value:
            parts["target"]["os"] = os_value

    # 3. Extract services
    if 'services' in target_text:
        services_start = target_text.find('services')
        services_list = extract_services_block(target_text[services_start:])
        if services_list:
            parts["target"]["services"] = services_list

    # 4. Extract web_directories_status
    if 'web_directories_status' in text:
        wds_start = text.find('web_directories_status')
        wds_block = extract_dict_block(text[wds_start:])
        if wds_block:
            parts["web_directories_status"] = wds_block

    return parts

def extract_simple_value(text_after_key, key_name=None):
    """
    Extracts letters and digits immediately after a key.
    Stops at the first character that is not a letter or a digit.
    Example: osLinux' --> returns Linux
    """
    key_pos = text_after_key.find(key_name)
    if key_pos == -1:
        return None

    after_key = text_after_key[key_pos + len(key_name):].lstrip()

    # Skip colon if exists
    if after_key.startswith(':'):
        after_key = after_key[1:].lstrip()

    value = ''
    for c in after_key:
        if c.isalnum():  # only letters or numbers
            value += c
        else:
            break  # stop immediately at the first non-letter/non-digit

    return value if value else None

def extract_os_value(text_after_os):
    """
    After finding 'os', extracts everything until the word 'services'.
    """
    start = 0
    # Skip possible colon or quote after os
    while start < len(text_after_os) and text_after_os[start] in [':', ' ', '\'', '"']:
        start += 1

    # Start extracting until you hit the word 'services'
    services_index = text_after_os.find('services')
    if services_index == -1:
        services_index = len(text_after_os)

    os_block = text_after_os[start:services_index]

    # Clean trailing unwanted characters
    os_block = os_block.strip(" ,:'\"{}[]")

    return os_block.strip()

def extract_services_block(text_after_services):
    """
    After finding 'services', extract the list block safely.
    Works even if closing ']' is missing.
    """
    start = text_after_services.find('[')
    if start == -1:
        return []  # No list found

    after_list = text_after_services[start+1:]

    end = after_list.find(']')
    if end == -1:
        list_content = after_list  # no closing bracket, take everything
    else:
        list_content = after_list[:end]

    list_text = '[' + list_content.strip() + ']'

    try:
        services_list = ast.literal_eval(list_text)
        return services_list
    except Exception:
        return []

def extract_list_block(text_after_key):
    """
    Extracts a list block from raw text.
    """
    start = text_after_key.find('[')
    end = text_after_key.find(']')
    if start == -1 or end == -1:
        return []
    list_text = text_after_key[start:end+1]
    try:
        return ast.literal_eval(list_text)
    except Exception:
        return []


def extract_dict_block(text_after_key):
    """
    Extracts a dictionary block from raw text.
    """
    start = text_after_key.find('{')
    end = text_after_key.find('}')
    if start == -1 or end == -1:
        return {}
    dict_text = text_after_key[start:end+1]
    try:
        return ast.literal_eval(dict_text)
    except Exception:
        return {}

def clean_value(val):
    """
    Cleans unwanted characters from a value block.
    """
    val = val.strip()
    # Remove leading colon if exists
    if val.startswith(':'):
        val = val[1:].strip()
    # Remove starting and ending quotes if exists
    if val.startswith("'") or val.startswith('"'):
        val = val[1:]
    if val.endswith("'") or val.endswith('"'):
        val = val[:-1]
    return val.strip()



def extract_value_from_text(text, start_keyword, value_type="string"):
    pattern = re.compile(rf"{start_keyword}[^a-zA-Z0-9]*([a-zA-Z0-9\s\.]*)")
    match = re.search(pattern, text)
    if match:
        value = match.group(1).strip()
        if value_type == "number":
            number_match = re.match(r"[\d.]+", value)
            if number_match:
                return number_match.group(0)
            else:
                return None
        return value
    return None

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
    parts = extract_json_parts(new_data)
    if parts:
        print("✅ JSON extracted successfully.")
        print_json_parts(parts)
    else:
        print("❌ Failed to extract valid JSON.")
    
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
target'''osLinuxservices' {'port': '21', 'protocol': 'tcp', 'service': 'ftp'}, {'port': '22', 'protocol': 'tcp', 'service': 'ssh'}, {'port': '23', 'protocol': 'tcp', 'service': 'telnet'}, {'port': '25', 'protocol': 'tcp', 'service': 'smtp'}, {'port': '53', 'protocol': 'tcp', 'service': 'domain'}, {'port': '80', 'protocol': 'tcp', 'service': 'http'}, {'port': '111', 'protocol': 'tcp', 'service': 'rpcbind'}, {'port': '445', 'protocol': 'tcp', 'service': 'netbios-ssn'}, {'port': '512', 'protocol': 'tcp', 'service': 'exec'}, {'port': '513', 'protocol': 'tcp', 'service': 'login'}, {'port': '1099', 'protocol': 'tcp', 'service': 'java-rmi'}, {'port': '1524', 'protocol': 'tcp', 'service': 'bindshell'}, {'port': '2049', 'protocol': 'tcp', 'service': 'nfs'}, {'port': '2121', 'protocol': 'tcp', 'service': 'ftp'}, {'port': '3306', 'protocol': 'tcp', 'service': 'mysql'}, {'port': '5432', 'protocol': 'tcp', 'service': 'postgresql'}, {'port': '5900', 'protocol': 'tcp', 'service': 'vnc'}, {'port': '6000', 'protocol': 'tcp', 'service': 'x11'}, {'port': '6667', 'protocol': 'tcp', 'service': 'irc'}]}, 'web_directories_status': {'200': {'': ''}, '401': {'': ''}, '403': {'': ''}, '404': {'': ''}, '503': {'': ''}}, 'actions_history': [], 'cpes': [], 'vulnerabilities_found': [], 'failed_CVEs': [], 'attack_impact': {'success': 'False', 'shell_opened': 'False'}}
"""

if __name__ == "__main__":
    fix_json(json.loads(state), new_data)
