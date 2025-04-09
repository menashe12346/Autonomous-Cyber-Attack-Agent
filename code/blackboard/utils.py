import json
import re

def extract_json(text: str):
    """
    מחלץ את מבנה ה-JSON התקני האחרון מתוך טקסט (ללא שימוש ב-?R).
    """
    # נחפש בלוקים שיכולים להיות JSON (מהתווים { ... })
    json_like_blocks = re.findall(r"{[\s\S]*?}", text)

    for block in reversed(json_like_blocks):  # נתחיל מהסוף
        try:
            return json.loads(block)
        except json.JSONDecodeError:
            continue

    raise ValueError(f"❌ Failed to extract valid JSON from:\n{text}")
