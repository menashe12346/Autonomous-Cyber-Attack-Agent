import subprocess
import re
import json
import os
import orjson
import csv

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

import re

""" HARD FOR THE MODEL TO UNDERSTEND:
def one_line(text: str) -> str:
    # 1) איחוד שורות
    s = ' '.join(line.strip() for line in text.strip().splitlines() if line.strip())
    # 2) הסרת רווחים סביב כל punctuation (כולל dot,comma,colon וכו׳)
    s = re.sub(r'\s*([.,:;!?\)\]\{\}\[\]])\s*', r'\1', s)
    # 3) דחיסת ריבוי רווחים
    s = re.sub(r'\s{2,}', ' ', s)
    return s
"""

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

def load_dataset(path: str):
    """
    Loads and normalizes the dataset. Supports both JSON (via orjson) and CSV (via csv.DictReader).

    Args:
        path (str): Path to the dataset file (JSON or CSV)

    Returns:
        List[dict]: Loaded dataset
    """
    ext = os.path.splitext(path)[-1].lower()

    if ext == ".json":
        with open(path, "rb") as f:
            content = f.read()
            if not content.strip():
                raise ValueError(f"[!] Dataset file is empty: {path}")
            return orjson.loads(content)

    elif ext == ".csv":
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)

    else:
        raise ValueError(f"[!] Unsupported file extension: {ext}")