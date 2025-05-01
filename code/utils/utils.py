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

def one_line(text: str) -> str:
    # 0) הסרת ANSI
    text = _CSI_RE.sub('', text)

    # 1) הסרת באנרים “inline” שגם אם יש בהם טקסט:
    #    [=\-\s]{10,}  = עשרה תווים או יותר של '=' או '-' או רווח
    #    .*?           = הכי מעט תווים של טקסט בינהם
    #    [=\-\s]{10,}  = שוב עשרה תווים או יותר של '=', '-' או רווח
    #  (?s) מאפשר ל־. לגעת גם ב־'\n' (במקרה שבאנרים יחצו שורות)
    text = re.sub(r'(?s)[=\-\s]{10,}.*?[=\-\s]{10,}', '', text)

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
    sample = """You are about to receive a specific JSON structure.You must remember it exactly as-is.Do not explain,summarize,or transform it in any way.Just memorize it internally—you will be asked to use it later.All response should be one line.Here is the structure:{"target":{"ip":"","os":{"name":"","distribution":{"name":"","version":""},"kernel":"","architecture":""},"services":[{"port":"","protocol":"","service":""},{"port":"","protocol":"","service":""},{"port":"","protocol":"","service":""}]},"web_directories_status":{"200":{"":""},"301":{"":""},"302":{"":""},"307":{"":""},"401":{"":""},"403":{"":""},"500":{"":""},"502":{"":""},"503":{"":""},"504":{"":""}}}.You were previously given a specific JSON structure.You MUST now return ONLY that same structure,filled correctly.Do NOT rename fields,add another keys,nest or restructure fileds,remove or replace any part of the format,guess or invent values,capitalize protocol or service names(use lowercase only).You MUST return JSON with exactly two top-level keys:"target"and"web_directories_status".Include all real fileds found.with no limit each status key must exist with{"{"}"":""{}"}.The"os"field includes name(e.g."Linux"),distribution with name(e.g."Ubuntu")and version(e.g."20.04"),kernel(e.g."5.15.0-85-generic"),and architecture(e.g."x86_64")In"services",add an entry for each service found:"port":numeric(e.g.22,80),"protocol":"tcp"or"udp"(lowercase),"service":service name(e.g.http,ssh)—lowercase,If missing,leave value as"".In"web_directories_status",for each status(["200","301","302","307","401","403","500","502","503","504"]):Map any discovered paths(like"/admin")to their message(or use""if no message).All 10 keys must appear,even if empty.Do not invent or guess data.Do not rename,add,or remove any fields.Return only the completed JSON.No extra text or formatting.Return only one-line compact JSON with same structure,no newlines,no indentations.All response should be one line.Instructions for this specific command:Extract the following fields from the given output:1.Target URL 2.HTTP method 3.Number of threads 4.Wordlist path 5.Status codes 6.User agent 7.Timeout value 8.Found directory or file(with corresponding status code and size)Instructions:1.Target URL:Extract the URL after\'[+]Url:\'in the first line.In this case,it is\'http://192.168.56.101\'.2.HTTP method:Locate the text after\'[+]Method:\'in the second line.It is\'GET\'.3.Number of threads:Find the text after\'[+]Threads:\'in the third line.The number is\'10\'.4.Wordlist path:Look for the text following\'[+]Wordlist:\'and ending with a line break.The path is\'/mnt/linux-data/wordlists/SecLists/Discovery/Web-Content/common.txt\'.5.Status codes:Identify the lines starting with a timestamp(\'[\'and\']\'),a status code(e.g.,\'200\',\'403\',or\'301\'),and a size(if available).The status code precedes the size or the direction arrow(\'-->\')within square brackets.Extract the status codes in these lines.In this case,the status codes found are\'403\',\'200\',\'200\',\'301\',\'200\',\'403\',\'403\',\'301\',and\'301\'.6.User agent:Locate the text following\'[+]User Agent:\'and ending with a line break.The user agent is\'gobuster/3.6\'.7.Timeout value:Find the text after\'[+]Timeout:\'in the same line as the user agent.The timeout value is\'10s\'.8.Found directories or files(with corresponding status codes,sizes,and directions):Identify the lines starting with a timestamp(\'[\'and\']\'),a status code(e.g.,\'200\',\'403\',or\'301\'),a size(if available),and a direction arrow(\'-->\')within square brackets.The line structure consists of the found directory/file name,status code,size(if available),and direction arrow within square brackets.Extract this information in each line.In this case,the found directories/files and their corresponding details are as follows:-.hta:Status-403,Size-291-.htaccess:Status-403,Size-296-.htpasswd:Status-403,Size-296-cgi-bin:Status-403,Size-295-phpMyAdmin:Status-301,Direction-\'-->http://192.168.56.101/phpMyAdmin/\'-phpinfo:Status-200,Size-48002-phpinfo.php:Status-200,Size-48014-server-status:Status-403,Size-300-test:Status-301,Direction-\'-->http://192.168.56.101/test/\'-twiki:Status-301,Direction-\'-->http://192.168.56.101/twiki/\'.Here is the new data:=============================================================== Gobuster v3.6 by OJ Reeves(@TheColonial)& Christian Mehlmauer(@firefart)===============================================================[+]Url:http://192.168.56.101[+]Method:GET[+]Threads:10[+]Wordlist:/mnt/linux-data/wordlists/SecLists/Discovery/Web-Content/common.txt[+]Negative Status codes:404[+]User Agent:gobuster/3.6[+]Timeout:10s =============================================================== Starting gobuster in directory enumeration mode =============================================================== \x1b[2K/.hta(Status:403)[Size:291]\x1b[2K/.htaccess(Status:403)[Size:296]\x1b[2K/.htpasswd(Status:403)[Size:296]\x1b[2K/cgi-bin/(Status:403)[Size:295]\x1b[2K/dav(Status:301)[Size:319][-->http://192.168.56.101/dav/]\x1b[2K/index.php(Status:200)[Size:891]\x1b[2K/index(Status:200)[Size:891]\x1b[2K/phpMyAdmin(Status:301)[Size:326][-->http://192.168.56.101/phpMyAdmin/]\x1b[2K/phpinfo(Status:200)[Size:48002]\x1b[2K/phpinfo.php(Status:200)[Size:48014]\x1b[2K/server-status(Status:403)[Size:300]\x1b[2K/test(Status:301)[Size:320][-->http://192.168.56.101/test/]\x1b[2K/twiki(Status:301)[Size:321][-->http://192.168.56.101/twiki/]=============================================================== Finished ===============================================================.Before returning your answer:Compare it to the original json structure character by character.Return ONLY ONE JSON—no explanation,no formatting,no comments."""
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