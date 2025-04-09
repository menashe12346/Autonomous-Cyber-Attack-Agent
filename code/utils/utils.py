import json
import re

def extract_final_json(parsed_info_list):
    for text in reversed(parsed_info_list):
        try:
            # ננסה לאתר JSON חוקי
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                json_part = text[start:end + 1]
                return json.loads(json_part)
        except json.JSONDecodeError:
            continue
    return {}  # אם אף אחד לא תקין


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
