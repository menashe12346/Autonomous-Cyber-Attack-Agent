import subprocess
import re
import json
import os
import orjson
import csv
import shutil

def get_first_word(s: str) -> str:
    """
    Returns the first word in the string.
    A word is defined as a sequence of non-space characters.
    """
    return s.strip().split()[0] if s.strip() else ""


def does_not_contain_brackets_or_exploit_warning(s: str) -> bool:
    """
    Returns True if the string does NOT contain '[-]' and also does NOT contain
    'Exploit completed, but no session was created.'
    """
    return '[-]' not in s and 'Exploit completed, but no session was created.' not in s

def get_nested(d: dict, path: str):
    """
    Retrieves a nested value from a dictionary using dot notation.

    Example:
        get_nested(data, "target.os.name") 
        will return data["target"]["os"]["name"] if it exists, otherwise None.

    Args:
        d (dict): The dictionary to traverse.
        path (str): The dot-separated key path.

    Returns:
        The value at the specified nested path, or None if any key is missing.
    """
    keys = path.split(".")
    for k in keys:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d

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

# 1) ANSI CSI 
_CSI_RE = re.compile(r'\x1b\[[0-9;]*[@-~]')

# 2) Punctuation characters
_PUNCT_CHARS = r'\.,:;\'"\-\–—_/\\\?\>\<\(\)\[\]\{\}'
_PUNCT_AFTER  = re.compile(rf'([{_PUNCT_CHARS}])\s+')
_PUNCT_BEFORE = re.compile(rf'\s+([{_PUNCT_CHARS}])')

def clean_command_output(text: str) -> str:
    """
    Cleans terminal command output by removing ANSI escape codes, long formatting sequences,
    excess whitespace, and line breaks.

    Parameters:
        text (str): Raw multiline output from a terminal command.

    Returns:
        str: A cleaned, single-line version of the output.
    """
    # 1) Remove ANSI escape codes
    text = _CSI_RE.sub('', text)

    # 2) Replace repeated =, -, or space characters (20 or more) with '. '
    text = re.sub(r'(?s)[=\-\s]{20,}', '. ', text)

    # 3) Collapse multiple spaces into one
    text = re.sub(r' {2,}', ' ', text)

    # 4) Flatten to a single line, removing empty or whitespace-only lines
    merged = ' '.join(line.strip() for line in text.splitlines() if line.strip())

    return merged

def clean_prompt(text: str) -> str:
    """
    Cleans a prompt string by removing unnecessary spaces around punctuation,
    collapsing repeated spaces, and flattening the text into a single line.

    Parameters:
        text (str): The input prompt string, possibly multiline and noisy.

    Returns:
        str: A cleaned, single-line version of the prompt.
    """
    # 1) Remove spaces after punctuation characters
    text = _PUNCT_AFTER.sub(r'\1', text)

    # 2) Remove spaces before punctuation characters
    text = _PUNCT_BEFORE.sub(r'\1', text)

    # 3) Collapse multiple spaces into one
    text = re.sub(r' {2,}', ' ', text)

    # 4) Flatten to a single line, removing empty or whitespace-only lines
    merged = ' '.join(line.strip() for line in text.splitlines() if line.strip())

    return merged

def check_file_exists(file_path, min_size_gb=None):
    """
    Verifies that the file exists and is at least a minimum size in gigabytes.

    Parameters:
        file_path (str): Path to the file.
        min_size_gb (int): Minimum required file size in GB.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is smaller than the specified minimum size.
    """

    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"❌ File not found: {file_path}.")

    size_bytes = os.path.getsize(file_path)
    size_gb = size_bytes / (1024 ** 3)

    if min_size_gb is not None:
        if size_gb < min_size_gb:
            raise ValueError(f"❌ Size of file is lower then {min_size_gb}GB ({size_gb:.2f}GB): {model_path}, maybe corrupted, remove the file and run program again.")
        
    print(f"✅ File {os.path.basename(file_path)} ({size_gb:.2f}GB) exists")

def run_command(cmd: str) -> str:
    """
    Executes a shell command and returns its output as a string.

    Parameters:
        cmd (str): The command to execute, as a single string.

    Returns:
        str: The decoded command output, or an empty string if execution fails.
    """
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

def delete_directory(path: str) -> None:
    """
    Deletes the directory at `path` and all its contents.
    """
    if not os.path.exists(path):
        print(f"[!] Directory '{path}' does not exist.")
        return
    if not os.path.isdir(path):
        print(f"[!] Path '{path}' is not a directory.")
        return

    try:
        shutil.rmtree(path)
        print(f"[✓] Directory '{path}' removed successfully.")
    except Exception as e:
        print(f"[✗] Failed to remove '{path}': {e}")

# [DEBUG]:
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