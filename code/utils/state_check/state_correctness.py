import subprocess
import re
import json
from utils.utils import remove_comments_and_empty_lines
from config import TARGET_IP, EXPECTED_STATUS_CODES
from utils.state_check.state_validator import clean_web_directories
from utils.utils import run_command
from utils.state_check.correctness_cache import CorrectnessCache

cache = CorrectnessCache()

def check_port_with_nmap(ip: str, port: str) -> str:
    key = f"port_open:{ip}:{port}"
    cached_result = cache.get(key)
    if cached_result is not None:
        return cached_result

    output = run_command(f"nmap -sV -p {port} {ip}")
    print(f"[DEBUG] nmap output for port {port}:\n{output}")

    for line in output.splitlines():
        if re.match(rf"^{port}/tcp\s+open", line):
            match = re.match(rf"^{port}/tcp\s+open\s+(\S+)", line)
            service = match.group(1).lower() if match else "unknown"
            cache.set(key, service)
            return service

    print(f"[!] Port {port}/tcp is not open — skipping.")
    cache.set(key, None)
    return None

def detect_os_from_multiple_tools(ip: str, current_os: str) -> str:
    key = f"os_detection:{ip}"
    cached_result = cache.get(key)
    if cached_result is not None:
        return cached_result

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
        final_os = "Linux" if "Linux" in os_candidates else os_candidates[0]
    else:
        final_os = current_os

    cache.set(key, final_os)
    return final_os

EXPECTED_CODES = EXPECTED_STATUS_CODES
def verify_web_directories(ip: str, web_dirs: dict) -> dict:
    verified = {code: {} for code in EXPECTED_CODES}

    for code, entries in web_dirs.items():
        for path in entries:
            full_url = f"http://{ip}{path}"
            key = f"url_check:{full_url}"
            cached_result = cache.get(key)

            if cached_result is None:
                try:
                    response = subprocess.check_output(
                        ["curl", "-i", "-s", full_url],
                        timeout=5
                    ).decode()

                    first_line = next((line for line in response.splitlines() if line.startswith("HTTP/")), "")
                    parts = first_line.strip().split(" ", 2)
                    status_code = parts[1] if len(parts) > 1 else "404"
                    reason = parts[2] if len(parts) > 2 else ""

                    cached_result = (status_code.strip(), reason.strip())
                except Exception:
                    cached_result = ("404", "Error or Timeout")

                cache.set(key, cached_result)

            status_code, reason = cached_result
            if status_code in verified:
                verified[status_code][path] = reason
            else:
                verified["404"][path] = reason or "Unknown"

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
