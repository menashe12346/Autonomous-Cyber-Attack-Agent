import subprocess
import re
import json
from utils.utils import remove_comments_and_empty_lines
from config import TARGET_IP
from utils.state_check.state_validator import clean_web_directories

def run_command(cmd: str) -> str:
    try:
        result = subprocess.check_output(cmd.split(), timeout=10).decode()
        return remove_comments_and_empty_lines(result)
    except:
        return ""

def check_port_with_nmap(ip: str, port: str) -> str:
    output = run_command(f"nmap -sV -p {port} {ip}")
    #print(f"[DEBUG] nmap output for port {port}:\n{output}")

    for line in output.splitlines():
        # בדוק שהפורט פתוח, גם אם אין שם שירות
        if re.match(rf"^{port}/tcp\s+open", line):
            match = re.match(rf"^{port}/tcp\s+open\s+(\S+)", line)
            if match:
                return match.group(1).lower()
            else:
                print(f"[!] Could not determine service on open port {port}/tcp — marking as 'unknown'")
                return "unknown"

    print(f"[!] Port {port}/tcp is not open — skipping.")
    return None

def detect_os_from_multiple_tools(ip: str, current_os: str) -> str:
    tools = [
        f"whatweb http://{ip}",
        f"curl -I http://{ip}",
        f"wget http://{ip} -O -"
    ]

    os_candidates = []

    for cmd in tools:
        output = run_command(cmd)
        if "linux" in output.lower():
            os_candidates.append("Linux")
        elif "windows" in output.lower():
            os_candidates.append("Windows")
        elif "ubuntu" in output.lower():
            os_candidates.append("Linux")
        elif "iis" in output.lower():
            os_candidates.append("Windows")
        elif "apache" in output.lower() or "nginx" in output.lower():
            os_candidates.append("Linux")

    if os_candidates:
        if "Linux" in os_candidates:
            return "Linux"
        return os_candidates[0]

    return current_os

EXPECTED_CODES = ["200", "401", "403", "404", "503"]

def verify_web_directories(ip: str, web_dirs: dict) -> dict:
    """
    מאמת נתיבי Web מול השרת וממקם כל נתיב בקטגוריית הסטטוס האמיתית בלבד.
    בנוסף, מסיר "" ריקים אם קיימים נתיבים תקניים.
    """
    verified = {code: {} for code in EXPECTED_CODES}

    for code, entries in web_dirs.items():
        for path in entries:
            full_url = f"http://{ip}{path}"
            try:
                response = subprocess.check_output(
                    ["curl", "-i", "-s", full_url],
                    timeout=5
                ).decode()

                # מציאת שורת ה־HTTP
                first_line = next((line for line in response.splitlines() if line.startswith("HTTP/")), "")
                parts = first_line.strip().split(" ", 2)
                status_code = parts[1] if len(parts) > 1 else "404"
                reason = parts[2] if len(parts) > 2 else ""

                # ניקוי הקוד
                status_code = status_code.strip()
                reason = reason.strip()

                if status_code in verified:
                    verified[status_code][path] = reason
                else:
                    verified["404"][path] = reason or "Unknown"

            except Exception:
                verified["404"][path] = "Error or Timeout"

    # הסרת "" מיותר ויישור סופי של המבנה
    verified = clean_web_directories(verified)
    return verified

def correct_state(state: dict) -> dict:
    ip = TARGET_IP

    print(f"[+] Verifying declared services individually on {ip}...")

    verified_services = []
    for s in state.get("target", {}).get("services", []):
        port = s.get("port", "")
        protocol = s.get("protocol", "").lower()
        declared_service = s.get("service", "").lower()

        if not port or not protocol or protocol != "tcp":
            continue  # מדלגים על שורות פגומות או שאינן TCP

        actual_service = check_port_with_nmap(ip, port)
        if actual_service:
            verified_services.append({
                "port": port,
                "protocol": "tcp",
                "service": actual_service  # יכול להיות שונה מהצהרה
            })
        else:
            print(f"[!] Port {port}/tcp is not open — removing.")

    state["target"]["services"] = verified_services

    # OS detection
    current_os = state["target"].get("os", "")
    new_os = detect_os_from_multiple_tools(ip, current_os)
    state["target"]["os"] = new_os

    # Web directories
    print(f"[+] Verifying web directories with curl...")
    raw_web_dirs = verify_web_directories(ip, state.get("web_directories_status", {}))
    state["web_directories_status"] = clean_web_directories(raw_web_dirs)

    return state
