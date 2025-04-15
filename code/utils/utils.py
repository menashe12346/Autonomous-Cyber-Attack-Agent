import json
import re

def extract_json_block(text_input):
    """
    Extracts the largest and most complete JSON block from a noisy text input.
    Handles malformed JSON, stray text, markdown fences, escape codes, and unbalanced braces.
    
    Parameters:
        text_input (str or List[str])
    
    Returns:
        dict or None
    """
    if isinstance(text_input, list):
        text = "\n".join(text_input)
    else:
        text = str(text_input)

    # 1. Remove ANSI escape codes
    text = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)

    # 2. Remove Markdown-style ```json ... ``` wrappers
    text = re.sub(r"```(?:json)?\s*({.*?})\s*```", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)

    # 3. Remove non-JSON explanation blocks (e.g., "The JSON structure provided is:")
    text = re.sub(r"The JSON structure provided.*?```", "", text, flags=re.DOTALL)

    # 4. Remove repeated explanations of the structure
    text = re.sub(r"(?i)(you were previously given|here is the structure|return ONLY ONE JSON).*?{", "{", text, flags=re.DOTALL)

    # 5. Remove trailing commas before } or ]
    text = re.sub(r",\s*([\]}])", r"\1", text)

    # 6. Attempt to find all top-level {...} blocks with balanced braces
    matches = []
    stack = []
    start = None

    for i, char in enumerate(text):
        if char == '{':
            if not stack:
                start = i
            stack.append('{')
        elif char == '}':
            if stack:
                stack.pop()
                if not stack and start is not None:
                    candidate = text[start:i + 1]
                    matches.append(candidate)

    # 7. Try parsing candidates
    valid_jsons = []
    for candidate in matches:
        try:
            obj = json.loads(candidate)
            valid_jsons.append((candidate, obj))
        except json.JSONDecodeError:
            # Try to auto-fix
            try:
                fixed = fix_malformed_json(candidate)
                obj = json.loads(fixed)
                valid_jsons.append((fixed, obj))
            except:
                continue

    if not valid_jsons:
        print("❌ No valid JSON found.")
        return None

    # 8. Return the one with the longest valid content
    best_candidate = max(valid_jsons, key=lambda pair: len(json.dumps(pair[1])))
    is_valid, validation_errors = validate_json_structure(best_candidate[1])
    if not is_valid:
        print("❌ Invalid JSON structure:")
        for e in validation_errors:
            print(" -", e)
    return best_candidate[1]

def fix_malformed_json(text):
    """
    Attempts to fix common JSON syntax problems.
    """
    # Remove ANSI escape codes
    text = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)

    # Fix extra commas before brackets
    text = re.sub(r",\s*}", "}", text)
    text = re.sub(r",\s*]", "]", text)

    # Fix nested closing brackets
    text = re.sub(r"}\s*}", "}}", text)
    text = re.sub(r"]\s*]", "]]", text)

    # Trim outside garbage
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1:
        text = text[start:end+1]

    # Auto-balance unclosed brackets
    open_count = text.count('{')
    close_count = text.count('}')
    if open_count > close_count:
        text += '}' * (open_count - close_count)

    return text

EXPECTED_TOP_KEYS = {"target", "web_directories_status"}
EXPECTED_SERVICE_KEYS = {"port", "protocol", "service"}
EXPECTED_STATUS_CODES = {"200", "401", "403", "404", "503"}

def validate_json_structure(obj):
    """
    Validates that the object matches the strict schema for the penetration AI system.
    Returns (bool, list_of_errors)
    """
    errors = []

    if not isinstance(obj, dict):
        return False, ["Top-level is not a dictionary"]

    # Check top-level keys
    extra_keys = set(obj.keys()) - EXPECTED_TOP_KEYS
    missing_keys = EXPECTED_TOP_KEYS - set(obj.keys())
    if extra_keys:
        errors.append(f"Unexpected top-level keys: {extra_keys}")
    if missing_keys:
        errors.append(f"Missing top-level keys: {missing_keys}")

    # Validate "target"
    target = obj.get("target", {})
    if not isinstance(target, dict):
        errors.append("'target' must be a dictionary")
    else:
        if "ip" not in target or not isinstance(target["ip"], str):
            errors.append("Missing or invalid 'target.ip'")
        if "os" not in target or not isinstance(target["os"], str):
            errors.append("Missing or invalid 'target.os'")

        services = target.get("services", [])
        if not isinstance(services, list):
            errors.append("'target.services' must be a list")
        else:
            for i, service in enumerate(services):
                if not isinstance(service, dict):
                    errors.append(f"Service #{i} is not a dict")
                    continue
                keys = set(service.keys())
                if keys != EXPECTED_SERVICE_KEYS:
                    errors.append(f"Service #{i} has invalid keys: {keys}")

    # Validate "web_directories_status"
    wds = obj.get("web_directories_status", {})
    if not isinstance(wds, dict):
        errors.append("'web_directories_status' must be a dictionary")
    else:
        for status in EXPECTED_STATUS_CODES:
            if status not in wds:
                errors.append(f"Missing status code {status} in web_directories_status")
            elif not isinstance(wds[status], dict):
                errors.append(f"Status code {status} value is not a dictionary")

    return len(errors) == 0, errors

def remove_comments_and_empty_lines(text: str) -> str:
    """
    Removes comment lines (starting with '#') and empty lines from a multiline string.

    Parameters:
        text (str): Multiline string.

    Returns:
        str: Cleaned text.
    """
    cleaned_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            cleaned_lines.append(line)
    return "\n".join(cleaned_lines)

def one_line(text: str) -> str:
    """
    Convert a multi-line string into a clean single line.
    """
    return ' '.join(line.strip() for line in text.strip().splitlines() if line).replace('  ', ' ')


# Example debug run
def main():
    text_input = [
        '[Some prompt text\n\n{\n  "target": {\n    "ip": "",\n    "os": "Unknown"\n  }\n}\x1b[0m\n',
        '{\n  "target": {\n    "ip": "",\n    "os": "Unknown"\n  }\n}\x1b[0m\n'
    ]

    result = extract_json_block(text_input)
    print("✅ Extracted JSON:")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
