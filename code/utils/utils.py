# utils/utils.py

import json
import re

def extract_json_block(text_input):
    """
    Extracts the largest valid JSON block from the given text input (or list of texts).
    It looks for well-formed curly braces and attempts to parse candidates as JSON.
    
    Parameters:
        text_input (str or List[str]): Raw output possibly containing JSON.
    
    Returns:
        dict or None: The best parsed JSON object, or None if no valid JSON found.
    """
    if isinstance(text_input, list):
        text = "\n".join(text_input)
    else:
        text = str(text_input)

    # Remove ANSI escape codes (e.g., \x1b[0m)
    text = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)

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

    valid_jsons = []
    for candidate in matches:
        try:
            fixed_candidate = fix_malformed_json(candidate)
            obj = json.loads(fixed_candidate)
            valid_jsons.append((fixed_candidate, obj))
        except json.JSONDecodeError:
            continue

    if not valid_jsons:
        print("❌ No valid JSON found.")
        return None

    best_candidate = max(valid_jsons, key=lambda pair: len(pair[0]))
    return best_candidate[1]


def fix_malformed_json(text: str) -> str:
    """
    Attempts to fix common JSON issues such as:
    - Trailing commas
    - ANSI escape codes
    - Incomplete block trimming

    Parameters:
        text (str): Raw JSON-like string.

    Returns:
        str: Cleaned and fixed JSON string.
    """
    text = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)
    text = re.sub(r',\s*}', '}', text)
    text = re.sub(r',\s*]', ']', text)
    text = re.sub(r'}\s*}', '}}', text)
    text = re.sub(r']\s*]', ']]', text)

    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1:
        text = text[start:end + 1]

    return text


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

def one_line(self, text: str) -> str:
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
