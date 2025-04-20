import re
import json

from blackboard.blackboard import initialize_blackboard

def fix_malformed_json(text):
    """
    Attempts to fix common JSON syntax problems carefully.
    Fixes only known issues to avoid breaking valid JSONs.
    """
    # Remove ANSI escape codes (if any)
    text = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)

    # Fix cases where the status code key is missing quotation marks (e.g., "200": {/": "OK"})
    text = re.sub(r'"(\d{3})"\s*{(/\s*":\s*")', r'"\1": {"\2', text)

    # Fix missing closing quotation mark and colon for some cases like:
    # "200": /": "OK", --> "200": {"/": "OK"}
    text = re.sub(r'"/\s*":\s*([a-zA-Z0-9\s]+)"', r'"/": "\1"', text)

    # Handle cases where missing quotation marks or incorrect symbols
    text = re.sub(r'(\d{3}):\s*{/\s*":\s*', r'"\1": {"', text)

    # Ensure that strings have quotes (add if missing)
    text = re.sub(r'([a-zA-Z0-9_\-/]+)\s*:', r'"\1":', text)

    # Fix lines like "/path/: Status" → "/path/": "Status"
    def fix_key_value_line(match):
        key = match.group(1).strip()
        value = match.group(2).strip()
        if key and value and not key.endswith('"') and not value.startswith('"'):
            return f'"{key}": "{value}"'
        return match.group(0)  # leave unchanged

    text = re.sub(r'"(/[^"]*?):\s*([^"]+?)"', fix_key_value_line, text)

    # Remove stray broken key-value pairs like '"" : ""' with no comma
    text = re.sub(r'"\s*"\s*:\s*"\s*"\s*(?!,)', '"": "",', text)

    # Remove duplicate JSON blocks without comma between
    text = re.sub(r'}\s*{', '}, {', text)

    # Fix extra commas before closing
    text = re.sub(r",\s*([\]}])", r"\1", text)

    # Trim garbage outside JSON
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1:
        text = text[start:end+1]

    # Auto-balance braces if needed
    open_count = text.count('{')
    close_count = text.count('}')
    if open_count > close_count:
        text += '}' * (open_count - close_count)

    return text

def extract_json_parts(noisy_text):
    """
    Extracts the different parts of the JSON structure from the noisy text.
    It finds specific values under 'target', 'os', 'ip', and 'web_directories_status' structure.
    :param noisy_text: The noisy text to extract information from.
    :return: A dictionary with extracted parts.
    """
    # First, fix any malformed JSON
    fixed_text = fix_malformed_json(noisy_text)
    
    parts = {}

    # Extracting "target" -> "ip"
    ip = extract_value_from_text(fixed_text, "ip", value_type="number")
    if ip:
        parts["target"] = {"ip": ip}

    # Extracting "target" -> "os"
    os = extract_value_from_text(fixed_text, "os", value_type="string")
    if os:
        if "target" not in parts:
            parts["target"] = {}
        parts["target"]["os"] = os

    # Extracting "target" -> "services"
    services = []
    service_matches = re.findall(r'"port": "(.*?)", "protocol": "(.*?)", "service": "(.*?)"', fixed_text)
    for match in service_matches:
        port, protocol, service = match
        services.append({"port": port, "protocol": protocol, "service": service})

    if services:
        if "target" not in parts:
            parts["target"] = {}
        parts["target"]["services"] = services

    # Extracting "web_directories_status"
    web_directories_status = {}
    status_matches = re.findall(r'"(\d{3})": {(.*?)}', fixed_text)
    for status, directories in status_matches:
        directories_dict = {}
        directories_list = re.findall(r'"(/.*?)": "(.*?)"', directories)
        for dir_path, status_text in directories_list:
            # Fixing missing " or :
            if not dir_path.startswith('"'):
                dir_path = '"' + dir_path
            if not dir_path.endswith('"'):
                dir_path = dir_path + '"'
            if not status_text.startswith('"'):
                status_text = '"' + status_text
            if not status_text.endswith('"'):
                status_text = status_text + '"'
            directories_dict[dir_path] = status_text
        web_directories_status[status] = directories_dict

    if web_directories_status:
        parts["web_directories_status"] = web_directories_status

    return parts

def extract_value_from_text(text, start_keyword, value_type="string"):
    """
    Extracts value after a keyword in the text.
    :param text: The input text to search in.
    :param start_keyword: The keyword to search for.
    :param value_type: Type of value to extract ("string", "number").
    :return: Extracted value.
    """
    pattern = re.compile(rf"{start_keyword}[^a-zA-Z0-9]*([a-zA-Z0-9\s\.]*)")
    match = re.search(pattern, text)
    if match:
        value = match.group(1).strip()
        if value_type == "number":
            # Extract the number only
            number_match = re.match(r"[\d.]+", value)
            if number_match:
                return number_match.group(0)
            else:
                return None
        return value
    return None

def print_json_parts(parts):
    """
    Recursively prints the contents of the JSON parts dictionary in a structured way.
    """
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
    """
    Fills the provided JSON template with extracted parts data, ensuring no overwriting of existing data
    and handling edge cases (e.g., malformed JSON, missing values).

    Arguments:
    template_json -- The initial JSON structure to be filled
    extracted_parts -- The dictionary containing the extracted parts data

    Returns:
    A filled and corrected JSON structure
    """
    # Initialize a clean template for the JSON (or use the existing one)
    if not template_json:
        template_json = initialize_blackboard()

    # === Step 1: Fill "target" section ===
    target = template_json.get("target", {})

    if "target" in extracted_parts:
        target_data = extracted_parts["target"]

        # Fill IP only if it's not already present and not empty
        if "ip" in target_data and target_data["ip"] and not target.get("ip"):
            target["ip"] = target_data["ip"]

        # Fill OS only if it's not already present and not empty
        if "os" in target_data and target_data["os"] and not target.get("os"):
            target["os"] = target_data["os"]

        # Ensure all the services in the extracted data are added
        if "services" in target_data and target_data["services"]:
            existing_services = {
                (s["port"], s["protocol"], s["service"]) for s in target.get("services", [])
            }
            for service in target_data["services"]:
                if not service.get("port") or not service.get("protocol") or not service.get("service"):
                    continue  # skip incomplete or empty services
                service_tuple = (service["port"], service["protocol"], service["service"])
                if service_tuple not in existing_services:
                    target.setdefault("services", []).append(service)

    template_json["target"] = target

    # === Step 2: Fill "web_directories_status" section ===
    web_directories_status = template_json.get("web_directories_status", {})

    if "web_directories_status" in extracted_parts:
        wds_data = extracted_parts["web_directories_status"]

        for status, directories in wds_data.items():
            if status not in web_directories_status:
                web_directories_status[status] = {}
            for directory, value in directories.items():
                # Remove unnecessary escape characters like ""/admin""
                directory = directory.strip('"')
                value = value.strip('"')

                # Add directory only if it doesn't already exist
                if directory and directory not in web_directories_status[status]:
                    web_directories_status[status][directory] = value

    template_json["web_directories_status"] = web_directories_status

    # === Step 3: Correct malformed structures (handling edge cases) ===
    for section in ["target", "web_directories_status"]:
        if section in template_json:
            if section == "target":
                if not template_json["target"].get("services"):
                    template_json["target"]["services"] = [{"port": "", "protocol": "", "service": ""}]
            if section == "web_directories_status":
                for status in ["200", "401", "403", "404", "503"]:
                    if status not in template_json["web_directories_status"]:
                        template_json["web_directories_status"][status] = {}

    # === Step 4: Remove empty services and empty directories ===
    final_json = remove_empty_services(template_json)
    final_json = clean_empty_directories_status(final_json)

    return final_json

def remove_empty_services(template_json):
    """
    Removes any services with empty values in the "services" list inside "target".
    
    Arguments:
    template_json -- The JSON structure that contains the "target" section
    
    Returns:
    The updated JSON structure with empty services removed
    """
    # Check if the 'target' and 'services' keys exist
    if "target" in template_json and "services" in template_json["target"]:
        # Filter out any service where any of the fields are empty
        template_json["target"]["services"] = [
            service for service in template_json["target"]["services"]
            if service.get("port") and service.get("protocol") and service.get("service")
        ]
    
    return template_json

def clean_empty_directories_status(json_data):
    """
    This function checks the 'web_directories_status' section in the full JSON data.
    If there are no directories (empty dictionary), it ensures that the entry with an empty key (": "") is present.
    If there are directories, it removes the entry with the empty key if it exists, and removes any additional occurrences of it.
    
    Arguments:
    json_data -- The full JSON data containing 'web_directories_status' among other parts
    
    Returns:
    json_data -- The updated JSON data with cleaned 'web_directories_status'
    """
    
    # Check if 'web_directories_status' exists in the json_data
    if "web_directories_status" in json_data:
        web_directories_status = json_data["web_directories_status"]
        
        # Loop over each status in web_directories_status
        for status, directories in web_directories_status.items():
            # Remove any occurrences of "": "" from the directories
            if "" in directories:
                del directories[""]  # Remove the empty key entry

            # If the status contains directories, we don't need to add an empty key
            if not directories:  # If no directories exist
                # Ensure that the empty key "" is present if no directories
                directories[""] = ""  # Add the empty key with empty value
    
    return json_data

def fix_json(state: dict, new_data):
    parts = extract_json_parts(new_data)
    if parts:
        print("✅ JSON extracted successfully.")
        print_json_parts(parts)
    else:
        print("❌ Failed to extract valid JSON.")
    
    # Fill the JSON structure
    filled_json = fill_json_structure(state, parts)

    # Print result
    print(json.dumps(filled_json, indent=2))

    return filled_json