import re
from pathlib import Path

def extract_usage_arguments(usage_line: str):
    usage_line = usage_line.strip()
    match = re.match(r'^(\S+)\s+(.*)$', usage_line)
    if not match:
        return []

    args_part = match.group(2)
    required_args = re.findall(r'<([^>]+)>', args_part)
    optional_args = re.findall(r'\[([^\]]+)\]', args_part)

    all_args = [arg.strip() for arg in required_args + optional_args]
    return all_args

def find_first_usage_line(code: str):
    for line in code.splitlines():
        if "usage" in line.lower() and ("<" in line or "[" in line):
            match = re.search(r'"(.*?usage:.*?)"', line)
            if match:
                return match.group(1).replace('\\n', '').replace('"', '').strip()
            else:
                return line.strip()
    return None

def analyze_all_c_files(directory: str):
    base_path = Path(directory)
    for file_path in base_path.rglob("*.c"):
        try:
            code = file_path.read_text(errors="ignore")
            usage_line = find_first_usage_line(code)
            if usage_line:
                args = extract_usage_arguments(usage_line)
                if args:
                    print(", ".join([arg for arg in args if arg != "0"]), end=",")
        except Exception as e:
            print(f"[!] Failed on file {file_path}: {e}")

if __name__ == "__main__":
    analyze_all_c_files("/mnt/linux-data/project/code/datasets/exploitdb/exploits")
