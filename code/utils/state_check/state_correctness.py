import subprocess
import re
import json
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config import TARGET_IP, EXPECTED_STATUS_CODES, OS_LINUX_DATASET, OS_LINUX_KERNEL_DATASET
from utils.utils import run_command, load_dataset
from utils.state_check.correctness_cache import CorrectnessCache
from utils.state_check.state_validator import validate_web_directories

from blackboard.blackboard import initialize_blackboard
DEFAULT_STATE_STRUCTURE = initialize_blackboard()

cache = CorrectnessCache()

def correct_port(ip: str, port: str) -> str:
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

def correct_os(
    ip: str,
    current_os: dict,
    linux_dataset: dict,
    kernel_versions: list
) -> dict:
    """
    1) Lowercase & split OS name + distribution name into words.
       If 'linux' in OS-words, corrected['name']='linux'.
    2) Try to match (in order):
         a) concat(OS words)
         b) concat(dist words)
         c) each OS word
         d) each dist word
       against lowercase linux_dataset keys.
       If found → set corrected['distribution']['name'] and corrected['name']='linux'.
       Else → clear only the three distribution fields.
    3) Independently validate corrected['distribution']['version'] and
       corrected['distribution']['architecture'] against that distro’s dataset entry,
       clearing only the field that doesn’t match.
    4) Validate kernel (lowercase) against kernel_versions.
    5) Cache under "os_detection:{ip}" and return.
    """
    cache_key = f"os_detection:{ip}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # 1) pull & lowercase
    raw_os_name   = current_os.get("name", "").lower()
    raw_dist_name = current_os.get("distribution", {})\
                               .get("name", "")\
                               .lower()
    raw_version   = current_os.get("distribution", {})\
                               .get("version", "")\
                               .lower()
    raw_arch      = current_os.get("distribution", {})\
                               .get("architecture", "")\
                               .lower()
    raw_kernel    = current_os.get("kernel", "").lower()

    os_name_words   = raw_os_name.split()
    dist_name_words = raw_dist_name.split()

    # init corrected (all lowercase)
    corrected = {
        "name": "",
        "distribution": {
            "name":         "",
            "version":      raw_version,
            "architecture": raw_arch,
        },
        "kernel": raw_kernel,
    }

    # detect 'linux' in OS name
    if "linux" in os_name_words:
        corrected["name"] = "linux"

    # 2) match distro key
    lc_dataset = {k.lower(): k for k in linux_dataset}
    matched_key = None

    # a) combo of OS words
    combo_os = "".join(os_name_words)
    if combo_os in lc_dataset:
        matched_key = lc_dataset[combo_os]

    # b) combo of dist words
    if not matched_key:
        combo_dist = "".join(dist_name_words)
        if combo_dist in lc_dataset:
            matched_key = lc_dataset[combo_dist]

    # c) each OS word
    if not matched_key:
        for w in os_name_words:
            if w in lc_dataset:
                matched_key = lc_dataset[w]
                break

    # d) each dist word
    if not matched_key:
        for w in dist_name_words:
            if w in lc_dataset:
                matched_key = lc_dataset[w]
                break

    if matched_key:
        # set canonical distro name
        corrected["distribution"]["name"] = matched_key.lower()
        corrected["name"] = "linux"

        # 3a) validate version independently
        valid_versions = {v.lower() for v in linux_dataset[matched_key].get("versions", [])}
        if raw_version not in valid_versions:
            corrected["distribution"]["version"] = ""
        # else leave corrected['distribution']['version'] == raw_version

        # 3b) validate architecture independently
        valid_archs = {a.lower() for a in linux_dataset[matched_key].get("architecture", [])}
        if raw_arch not in valid_archs:
            corrected["distribution"]["architecture"] = ""
        # else leave corrected['distribution']['architecture'] == raw_arch

    else:
        # no distro match → clear only distribution fields
        corrected["distribution"]["name"]         = ""
        corrected["distribution"]["version"]      = ""
        corrected["distribution"]["architecture"] = ""

    # 4) validate kernel
    valid_kernels = {k.lower() for k in kernel_versions}
    if raw_kernel not in valid_kernels:
        corrected["kernel"] = ""
    else:
        corrected["kernel"] = raw_kernel

    # 5) cache & return
    cache.set(cache_key, corrected)
    return corrected

# תווים מותרים ב־URL path לפי RFC 3986 (unreserved characters)
ALLOWED_PATH_CHARS_REGEX = re.compile(r'^[A-Za-z0-9\-._~/]*$')

def is_valid_url_path(path: str) -> bool:
    """
    בודק אם הנתיב מורכב אך ורק מהתווים המותרים ב־URL לפי התקן:
    A–Z, a–z, 0–9, -, ., _, ~, /
    """
    return isinstance(path, str) and bool(ALLOWED_PATH_CHARS_REGEX.fullmatch(path))


def correct_web_directories(ip: str, web_dirs: dict) -> dict:
    verified = {code: {} for code in EXPECTED_STATUS_CODES}

    for code, entries in web_dirs.items():
        for path in entries:

            if not is_valid_url_path(path):
                print(f"[WARNING] Skipping invalid path: {path!r}")
                continue

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
                
    return validate_web_directories(verified)
    
def correct_state(state: dict, linux_dataset: dict, kernel_versions: list) -> dict:

    print(f"[+] Verifying declared services individually on {TARGET_IP}...")

    verified_services = []
    for s in state.get("target", {}).get("services", []):
        port = s.get("port", "")
        protocol = s.get("protocol", "").lower()
        declared_service = s.get("service", "").lower()

        actual_service = correct_port(TARGET_IP, port)
        if actual_service:
            verified_services.append({
                "port": port,
                "protocol": "tcp",
                "service": actual_service
            })
        else:
            print(f"[!] Port {port}/tcp is not open — removing.")

    state["target"]["services"] = verified_services

    # תיקון OS
    current_os = state["target"].get("os", DEFAULT_STATE_STRUCTURE["target"]["os"])
    if isinstance(current_os, dict):
        new_os = correct_os(TARGET_IP, current_os, linux_dataset, kernel_versions)
        state["target"]["os"] = new_os
    else:
        print("[!] OS field is not in expected dict format — skipping.")

    # תיקון web directories
    print(f"[+] Verifying web directories with curl...")
    state["web_directories_status"] = correct_web_directories(TARGET_IP, state.get("web_directories_status", DEFAULT_STATE_STRUCTURE["web_directories_status"]))
    return state

if __name__ == "__main__":
    state = {'target': {'ip': '192.168.56.101', 'os': {'name': '', 'distribution': {'name': '', 'version': ''}, 'kernel': '', 'architecture': ''}, 'services': []}, 'web_directories_status': {'200': {'/index.php': '', '/phpinfo.php': '', '/phpinfo': '', '/index': ''}, '301': {'/dav/': '', '/phpMyAdmin/': '', '/test/': '', '/twiki/': ''}, '302': {'': ''}, '307': {'': ''}, '401': {'': ''}, '403': {'/.htaccess': '', '/cgi-bin/': '', '/server-status': '', '/test/': '', '/twiki/': '', '/': ''}, '500': {'': ''}, '502': {'': ''}, '503': {'': ''}, '504': {'': ''}}, 'actions_history': [], 'cpes': [], 'vulnerabilities_found': []}
    os_linux_dataset = load_dataset(OS_LINUX_DATASET)
    print(f"✅ OS Linux dataset Loaded Successfully")

    os_linux_kernel_dataset = load_dataset(OS_LINUX_KERNEL_DATASET)
    print(f"✅ OS Linux Kernel dataset Loaded Successfully")

    final_state = correct_state(state, os_linux_dataset, os_linux_kernel_dataset)

    print(final_state)