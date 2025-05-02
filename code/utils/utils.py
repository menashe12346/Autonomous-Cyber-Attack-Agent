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

# 1) הסרת כל קודי ANSI CSI (כולל m, K, J, H וכו')
_CSI_RE = re.compile(r'\x1b\[[0-9;]*[@-~]')

# 2) תווים של פיסוק (כבר יש לך אותם)
_PUNCT_CHARS = r'\.,:;\'"\-\–—_/\\\?\>\<\(\)\[\]\{\}'
_PUNCT_AFTER  = re.compile(rf'([{_PUNCT_CHARS}])\s+')
_PUNCT_BEFORE = re.compile(rf'\s+([{_PUNCT_CHARS}])')

def clean_command_output(text: str) -> str:
    # 0) הסרת ANSI
    text = _CSI_RE.sub('', text)

    # 1) הסרת באנרים “inline” שגם אם יש בהם טקסט:
    #    [=\-\s]{30,}  = עשרה תווים או יותר של '=' או '-' או רווח
    #  (?s) מאפשר ל־. לגעת גם ב־'\n' (במקרה שבאנרים יחצו שורות)
    text = re.sub(r'(?s)[=\-\s]{20,}', '. ', text)

    # 2) מסיר רווחים אחרי פיסוק
    #text = _PUNCT_AFTER.sub(r'\1', text)
    # 3) מסיר רווחים לפני פיסוק
    #text = _PUNCT_BEFORE.sub(r'\1', text)

    # 4) מצמצם 2+ רווחים לרווח יחיד
    text = re.sub(r' {2,}', ' ', text)

    # 5) מאחד כל שורה לשורה אחת
    merged = ' '.join(line.strip() for line in text.splitlines() if line.strip())
    return merged

def clean_prompt(text: str) -> str:

    # 2) מסיר רווחים אחרי פיסוק
    text = _PUNCT_AFTER.sub(r'\1', text)
    # 3) מסיר רווחים לפני פיסוק
    text = _PUNCT_BEFORE.sub(r'\1', text)

    # 4) מצמצם 2+ רווחים לרווח יחיד
    text = re.sub(r' {2,}', ' ', text)

    # 5) מאחד כל שורה לשורה אחת
    merged = ' '.join(line.strip() for line in text.splitlines() if line.strip())
    return merged

# Example:
if __name__ == "__main__":
    sample = """===============================================================
Gobuster v3.6
by OJ Reeves (@TheColonial) & Christian Mehlmauer (@firefart)
===============================================================
[+] Url:                     http://192.168.56.101
[+] Method:                  GET
[+] Threads:                 10
[+] Wordlist:                /mnt/linux-data/wordlists/SecLists/Discovery/Web-Content/common.txt
[+] Negative Status codes:   404
[+] User Agent:              gobuster/3.6
[+] Timeout:                 10s
===============================================================
Starting gobuster in directory enumeration mode
===============================================================
/.htaccess            (Status: 403) [Size: 296]
/.hta                 (Status: 403) [Size: 291]
/.htpasswd            (Status: 403) [Size: 296]
/cgi-bin/             (Status: 403) [Size: 295]
/dav                  (Status: 301) [Size: 319] [--> http://192.168.56.101/dav/]
/index.php            (Status: 200) [Size: 891]
/index                (Status: 200) [Size: 891]
/phpMyAdmin           (Status: 301) [Size: 326] [--> http://192.168.56.101/phpMyAdmin/]
/phpinfo              (Status: 200) [Size: 48002]
/phpinfo.php          (Status: 200) [Size: 48014]
/server-status        (Status: 403) [Size: 300]
/test                 (Status: 301) [Size: 320] [--> http://192.168.56.101/test/]
/twiki                (Status: 301) [Size: 321] [--> http://192.168.56.101/twiki/]
===============================================================
Finished
==============================================================="""
    print(one_line(sample))


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