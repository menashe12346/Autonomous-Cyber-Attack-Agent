import json
import re

def extract_json_block(text_input):
    """
    מקבלת טקסט (או רשימה של טקסטים), ומחזירה את בלוק ה־JSON התקני הכי גדול שמצאה כ־dict.
    """
    if isinstance(text_input, list):
        text = "\n".join(text_input)
    else:
        text = str(text_input)

    # ניקוי escape codes (כמו \x1b[0m)
    text = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)

    # חיפוש כל הבלוקים שמתחילים ונגמרים בסוגריים מסולסלים
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
                    candidate = text[start:i+1]
                    matches.append(candidate)

    # נסה לפרסר כל אחד ולבחור את הכי גדול
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

    # בחר את המחרוזת הכי ארוכה (כ־string)
    best_candidate = max(valid_jsons, key=lambda pair: len(pair[0]))
    return best_candidate[1]  # מחזיר את ה־dict

def fix_malformed_json(text: str) -> str:
    """
    מנקה JSON שמכיל פסיקים מיותרים לפני סוגרים או תווים לא חוקיים,
    ומחזיר מחרוזת JSON תקנית ככל האפשר.
    """
    # מסיר תווי ANSI escape (כמו \x1b[0m)
    text = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)

    # מסיר פסיקים לפני סוגרי dict או list
    text = re.sub(r',\s*}', '}', text)
    text = re.sub(r',\s*]', ']', text)

    # מסיר כפילויות של סוגרים מסולסלים
    text = re.sub(r'}\s*}', '}}', text)
    text = re.sub(r']\s*]', ']]', text)

    # מוודא שהמחרוזת מתחילה ונגמרת עם סוגר מסולסל
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1:
        text = text[start:end + 1]

    return text



def remove_comments_and_empty_lines(text: str) -> str:
    """
    מוחקת את כל השורות שמתחילות ב־# ואת כל השורות הריקות מתוך הטקסט.
    """
    cleaned_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def main():
    text_input = [
        '[I will memorize the provided JSON structure exactly as-is:\n\n{\n  "target": {\n    "ip": "",\n    "os": "Unknown",\n    "services": [\n      {"port": "", "protocol": "", "service": ""},\n      {"port": "", "protocol": "", "service": ""},\n      {"port": "", "protocol": "", "service": ""}\n    ]\n  },\n  "web_directories_status": {\n    "404": { "": "" },\n    "200": { "": "" },\n    "403": { "": "" },\n    "401": { "": "" },\n    "503": { "": "" }\n  }\n}\x1b[0m\n',
        '{\n  "target": {\n    "ip": "",\n    "os": "Unknown",\n    "services": [\n      {"port": "", "protocol": "", "service": ""},\n      {"port": "", "protocol": "", "service": ""},\n      {"port": "", "protocol": "", "service": ""}\n    ]\n  },\n  "web_directories_status": {\n    "404": { "": "" },\n    "200": { "": "" },\n    "403": { "": "" },\n    "401": { "": "" },\n    "503": { "": "" }\n  }\n}\x1b[0m\n]'
    ]

    result = extract_json_block(text_input)
    print("✅ Extracted JSON:")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()