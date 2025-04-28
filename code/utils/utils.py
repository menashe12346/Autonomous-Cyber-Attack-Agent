import subprocess
import re
import json
import os
import orjson
import csv

from utils.state_check.state_validator import validate_state

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

def load_dataset(cve_path: str):
    """
    Loads and normalizes the dataset. Supports both JSON (via orjson) and CSV (via csv.DictReader).

    Args:
        cve_path (str): Path to the dataset file (JSON or CSV)

    Returns:
        List[dict]: Loaded dataset
    """
    ext = os.path.splitext(cve_path)[-1].lower()

    if ext == ".json":
        with open(cve_path, "rb") as f:
            content = f.read()
            if not content.strip():
                raise ValueError(f"[!] Dataset file is empty: {cve_path}")
            return orjson.loads(content)

    elif ext == ".csv":
        with open(cve_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)

    else:
        raise ValueError(f"[!] Unsupported file extension: {ext}")