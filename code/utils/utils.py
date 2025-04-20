import subprocess
import re
import json
from utils.state_check.state_validator import validate_state

def extract_json_block(text_input):
    """
    Extracts the largest and most complete valid JSON block from noisy text.
    It cleans the input, finds all JSON-like blocks, parses them, validates them,
    and returns the best candidate.
    """

    # === Step 1: Convert input to string ===
    if isinstance(text_input, list):
        text = "\n".join(text_input)
    else:
        text = str(text_input)

    # === Step 2: Initial cleaning (remove ANSI codes, markdown, LLM artifacts) ===
    text = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)  # ANSI colors
    text = re.sub(r"```(?:json)?\s*({.*?})\s*```", r"\1", text, flags=re.DOTALL)  # strip ```json
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)  # strip any code blocks
    text = re.sub(r"(The given JSON structure is:|Here is the structure:|You were previously given.*?)\n", "", text, flags=re.IGNORECASE)
    text = re.sub(r"The JSON structure provided.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"(?i)(you were previously given|return ONLY ONE JSON).*?{", "{", text, flags=re.DOTALL)
    text = re.sub(r",\s*([\]}])", r"\1", text)  # remove trailing commas

    # === Step 3: Find candidate JSON blocks using brace matching ===
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

    # === Step 4: Attempt to parse each candidate JSON block ===
    valid_jsons = []

    for candidate in matches:
        candidate = candidate.strip()
        try:
            obj = json.loads(candidate)
            obj = one_line(obj)  # flatten
            valid_jsons.append((json.dumps(obj), obj))
        except json.JSONDecodeError as e:
            print(f"[!] JSONDecodeError: {e} — attempting to fix...")
            try:
                fixed = fix_malformed_json(candidate)
                obj = json.loads(validate_state(fixed))
                obj = one_line(obj)  # flatten
                valid_jsons.append((json.dumps(obj), obj))
            except Exception as e_inner:
                print(f"[!] Failed to fix JSON — {type(e_inner).__name__}: {e_inner}")
                continue
        except Exception as e:
            print(f"[!] Unexpected error — {type(e).__name__}: {e}")
            continue

        # Try to flatten the JSON into one line (optional visual clean-up)
        try:
            obj = one_line(obj)
        except:
            pass

        valid_jsons.append((json.dumps(obj), obj))
    
    if not valid_jsons:
        print("❌ No valid JSON found.")
        return None


    # === Step 5: Return the best valid JSON candidate ===

    # Select the largest (most complete) candidate
    best_candidate = max(valid_jsons, key=lambda pair: len(pair[0]))

    # === Step 6: Validate the JSON structure ===
    is_valid, validation_errors = validate_json_structure(best_candidate[1])
    if not is_valid:
        print("❌ Invalid JSON structure:")
        for e in validation_errors:
            print(" -", e)

    return best_candidate[1]

def fix_malformed_json(text):
    """
    Attempts to fix common JSON syntax problems carefully.
    Fixes only known issues to avoid breaking valid JSONs.
    """
    import re

    # Remove ANSI escape codes
    text = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)

    # Remove stray broken key-value pairs like '"" : ""' with no comma
    text = re.sub(r'"\s*"\s*:\s*"\s*"\s*(?!,)', '"": "",', text)

    # Remove duplicate JSON blocks without comma between
    text = re.sub(r'}\s*{', '}, {', text)

    # Fix extra commas before closing
    text = re.sub(r",\s*([\]}])", r"\1", text)

    # Fix lines like "/path/: Status" → "/path/": "Status"
    def fix_key_value_line(match):
        key = match.group(1).strip()
        value = match.group(2).strip()
        if key and value and not key.endswith('"') and not value.startswith('"'):
            return f'"{key}": "{value}"'
        return match.group(0)  # leave unchanged

    text = re.sub(r'"(/[^"]*?):\s*([^"]+?)"', fix_key_value_line, text)

    # Trim garbage outside JSON
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1:
        text = text[start:end+1]

    # Auto-balance braces
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

def run_command(cmd: str) -> str:
    try:
        result = subprocess.check_output(cmd.split(), timeout=10).decode()
        return result
    except:
        return ""


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
