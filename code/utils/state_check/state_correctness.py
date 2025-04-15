import subprocess
import re
import json
from utils.utils import remove_comments_and_empty_lines
from config import TARGET_IP

def run_command(cmd: str) -> str:
    try:
        result = subprocess.check_output(cmd.split(), timeout=10).decode()
        return remove_comments_and_empty_lines(result)
    except:
        return ""

def check_port_with_nmap(ip: str, port: str) -> str:
    output = run_command(f"nmap -sV -p {port} {ip}")
    print(f"[DEBUG] nmap output for port {port}:\n{output}")
    for line in output.splitlines():
        match = re.search(rf"{port}/tcp\s+open\s+(\S+)", line)
        if match:
            return match.group(1).lower()
    return ""

def detect_os_from_multiple_tools(ip: str, current_os: str) -> str:
    tools = [
        f"nmap -O {ip}",
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

def verify_web_directories(ip: str, web_dirs: dict) -> dict:
    verified = {code: {} for code in ["200", "401", "403", "404", "503"]}
    for code, entries in web_dirs.items():
        for path in entries:
            full_url = f"http://{ip}{path}"
            try:
                response = subprocess.check_output(
                    ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", full_url],
                    timeout=5
                ).decode().strip()
                if response in verified:
                    verified[response][path] = entries[path]
                else:
                    verified["404"][path] = entries[path]
            except:
                verified["404"][path] = entries[path]
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
    current_os = state["target"].get("os", "Unknown")
    new_os = detect_os_from_multiple_tools(ip, current_os)
    state["target"]["os"] = new_os

    # Web directories
    print(f"[+] Verifying web directories with curl...")
    state["web_directories_status"] = verify_web_directories(ip, state.get("web_directories_status", {}))

    return state
