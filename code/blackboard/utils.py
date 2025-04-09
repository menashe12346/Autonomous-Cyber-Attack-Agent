import json
import re

def extract_json(text: str) -> dict:
    """
    מחלץ את ה־JSON התקין מתוך טקסט חופשי (כמו פלט של מודל).
    מניח שה־JSON מתחיל ב־{ ונגמר ב־}.
    """
    try:
        match = re.search(r"{.*}", text, re.DOTALL)
        if not match:
            raise ValueError("❌ JSON block not found in model output.")
        return json.loads(match.group())
    except Exception as e:
        raise ValueError(f"❌ Failed to extract valid JSON:\n{text}\n\nError: {e}")
