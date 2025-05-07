import subprocess
import re
import json
import inspect
import builtins
import copy
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config import TARGET_IP, EXPECTED_STATUS_CODES, OS_LINUX_DATASET, OS_LINUX_KERNEL_DATASET, STATE_SCHEMA, TARGET_IP
from utils.utils import run_command, load_dataset
from utils.state_check.correctness_cache import CorrectnessCache
from blackboard.blackboard import initialize_blackboard

DEFAULT_STATE_STRUCTURE = initialize_blackboard()
cache = CorrectnessCache()

def correct_port(ip: str, port: str) -> tuple[str, str]:
    key = f"port_open:{ip}:{port}"
    cached_result = cache.get(key)
    if cached_result is not None:
        return cached_result, "unknown"

    output = run_command(f"nmap -sV -p {port} {ip}")
    print(f"[DEBUG] Nmap output for {ip}:{port}:\n{output}")

    for line in output.splitlines():
        if re.match(rf"^{port}/\w+\s+open", line):
            match = re.match(rf"^{port}/(\w+)\s+open\s+(\S+)", line)
            if match:
                protocol = match.group(1).lower()
                service = match.group(2).lower()
            else:
                protocol = "unknown"
                service = "unknown"

            print(f"[+] Detected open port {port}/{protocol} → service: {service}")
            cache.set(key, service)
            return service, protocol

    print(f"[!] Port {port} is not open on {ip} — skipping.")
    cache.set(key, None)
    return None, None

"""
def correct_services(ip: str, services: list[dict]) -> list[dict]:
    print(f"[+] Verifying declared services individually on {ip}...")
    verified_services = []

    for s in services:
        port = s.get("port", "")
        declared_protocol = s.get("protocol", "").lower()
        declared_service = s.get("service", "").lower()

        service, protocol = correct_port(ip, port)
        if service:
            verified_services.append({
                "port": port,
                "protocol": protocol,
                "service": service
            })

    return verified_services
"""

def correct_os(
    ip: str,
    current_os: dict,
    linux_dataset: dict,
    kernel_versions: list
) -> dict:
    """
    1) Lowercase & split OS name + distribution name into words.
       If 'linux' in OS-words or distribution-words, corrected['name']='linux'.
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

    # detect 'linux' in OS name or dist name
    if "linux" in os_name_words or "linux" in dist_name_words:
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
            # אם הנתיב לא מתחיל ב־'/', נכין לו גם גרסה מתוקנת
            paths_to_check = [path]
            if not path.startswith("/"):
                corrected = "/" + path
                paths_to_check.append(corrected)

            for p in paths_to_check:
                # ודא שבכל מקרה הנתיב מתחיל '/'
                if not p.startswith("/"):
                    p = "/" + p

                if not is_valid_url_path(p):
                    print(f"[WARNING] Skipping invalid path: {p!r}")
                    continue

                full_url = f"http://{ip}{p}"
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
                    # שמירה במפתח העיקרי p (המתוקן או המקורי)
                    verified[status_code][p] = reason

    return verified

def correct_state(*, state: dict, schema: dict = None, base_path: str = "", **kwargs) -> dict:
    """
    Recursively corrects the state using correction_func from the schema.
    All arguments must be passed by name (keyword-only).
    
    Args:
        state (dict): The input state to correct.
        schema (dict): The schema definition. If None, loads STATE_SCHEMA from config.
        base_path (str): Internal path used for recursion.
        **kwargs: Named external arguments passed to correction functions (e.g. os_linux_dataset).

    Returns:
        dict: A corrected version of the input state.
    """
    if schema is None:
        from config import STATE_SCHEMA
        schema = STATE_SCHEMA

    if not isinstance(schema, dict):
        raise TypeError(f"[correct_state] Expected 'schema' to be a dict, got {type(schema).__name__}")

    corrected = copy.deepcopy(state)

    for key, entry in schema.items():
        full_path = f"{base_path}.{key}" if base_path else key

        if isinstance(entry, dict) and "correction_func" in entry:
            func_name = entry["correction_func"]
            correction_func = globals().get(func_name)

            if not callable(correction_func):
                print(f"[WARNING] Correction function '{func_name}' not found for '{full_path}'")
                continue

            # Navigate to target field
            parts = full_path.split(".")
            target = corrected
            for part in parts[:-1]:
                part = part.replace("[]", "")
                target = target.get(part, {})

            last_part = parts[-1].replace("[]", "")
            if last_part in target:
                try:
                    value = target[last_part]
                    ip = corrected.get("target", {}).get("ip", "")

                    # Build args from function signature
                    sig = inspect.signature(correction_func)
                    call_args = {}
                    for param in sig.parameters.values():
                        pname = param.name

                        if pname == "ip":
                            call_args[pname] = ip
                        elif pname in kwargs:
                            call_args[pname] = kwargs[pname]
                        elif pname in corrected:
                            call_args[pname] = corrected[pname]
                        else:
                            # ניגש לערך הנוכחי אם הוא נדרש (למשל 'current_os' או 'services')
                            value = target.get(last_part, None)
                            if value is not None:
                                call_args[pname] = value


                    print(f"[INFO] Running {func_name} on '{full_path}'")
                    result = correction_func(**call_args)
                    target[last_part] = result

                except Exception as e:
                    print(f"[ERROR] Correction '{func_name}' failed on '{full_path}': {e}")

        elif isinstance(entry, dict):
            corrected = correct_state(
                state=corrected,
                schema=entry,
                base_path=full_path,
                **kwargs
            )

    return corrected


def clean_state(state: dict, structure: dict) -> dict:
    """
    Recursively traverses the state based on DEFAULT_STATE_STRUCTURE and:
    1. For any list of dicts: removes dicts where all fields are empty.
    2. If the final list is empty: adds one template item (with all empty fields).
    3. For dict-of-dicts (e.g., web_directories_status): removes "" keys with "" values.

    Args:
        state: The actual state dict to be cleaned.
        structure: The DEFAULT_STATE_STRUCTURE that defines the template.

    Returns:
        A cleaned state dict with invalid list entries removed and empty templates preserved.
    """
    cleaned = copy.deepcopy(state)

    for key, expected_value in structure.items():
        if key not in cleaned:
            continue

        if isinstance(expected_value, list) and isinstance(cleaned[key], list):
            template_item = expected_value[0] if expected_value else {}
            # Remove dicts with all fields empty
            cleaned_list = [
                item for item in cleaned[key]
                if any(v != "" for v in item.values())
            ]
            # If empty after cleaning, insert one blank template
            if not cleaned_list:
                cleaned_list = [copy.deepcopy(template_item)]
            cleaned[key] = cleaned_list

        elif isinstance(expected_value, dict) and isinstance(cleaned[key], dict):
            # Special case for web_directories_status-like dicts of dicts
            inner_dict = cleaned[key]
            for subkey, subdict in inner_dict.items():
                if isinstance(subdict, dict):
                    inner_dict[subkey] = {
                        k: v for k, v in subdict.items() if k != "" or v != ""
                    }
                    # If nothing left, ensure one empty entry
                    if not inner_dict[subkey]:
                        inner_dict[subkey] = {"": ""}
            # Continue recursive cleaning
            cleaned[key] = clean_state(cleaned[key], expected_value)

    return cleaned

def merge_state(state: dict) -> dict:
    """
    Merge entries in the state for:
      - target.services: group by 'port' and combine fields across entries
      - target.rpc_services: remove duplicate dicts
    Returns a new state dict with services merged by port and rpc_services deduped.
    """
    import copy

    merged = copy.deepcopy(state)

    # 1) Merge target.services by port
    services = merged.get("target", {}).get("services", [])
    by_port = {}
    order = []
    for svc in services:
        port = svc.get("port")
        if port not in by_port:
            by_port[port] = copy.deepcopy(svc)
            order.append(port)
        else:
            existing = by_port[port]
            for key, value in svc.items():
                if key == "port":
                    continue
                # Merge strings: keep existing if present, else use new
                if isinstance(value, str):
                    if not existing.get(key) and value:
                        existing[key] = value
                # Merge lists: union while preserving order
                elif isinstance(value, list):
                    merged_list = existing.get(key, [])[:]
                    for item in value:
                        if item not in merged_list:
                            merged_list.append(item)
                    existing[key] = merged_list
                # Merge dicts: take non-empty values from new
                elif isinstance(value, dict):
                    merged_dict = existing.get(key, {}).copy()
                    for subk, subv in value.items():
                        if not merged_dict.get(subk) and subv:
                            merged_dict[subk] = subv
                    existing[key] = merged_dict
                # Other types: only set if missing
                else:
                    if not existing.get(key) and value is not None:
                        existing[key] = value
    merged_services = [by_port[p] for p in order]
    if "target" in merged:
        merged["target"]["services"] = merged_services

    # 2) Deduplicate target.rpc_services if present
    if "target" in merged and isinstance(merged["target"].get("rpc_services"), list):
        rpc_list = merged["target"]["rpc_services"]
        seen = set()
        unique_rpc = []
        for rpc in rpc_list:
            key = tuple(sorted(rpc.items()))
            if key not in seen:
                seen.add(key)
                unique_rpc.append(rpc)
        merged["target"]["rpc_services"] = unique_rpc

    return merged

if __name__ == "__main__":
    state = {'target': {'ip': '192.168.56.101', 'os': {'name': '', 'distribution': {'name': '', 'version': ''}, 'kernel': '', 'architecture': ''}, 'services': []}, 'web_directories_status': {'200': {'/index.php': '', '/phpinfo.php': '', '/phpinfo': '', '/index': ''}, '301': {'/dav/': '', '/phpMyAdmin/': '', '/test/': '', '/twiki/': ''}, '302': {'': ''}, '307': {'': ''}, '401': {'': ''}, '403': {'/.htaccess': '', '/cgi-bin/': '', '/server-status': '', '/test/': '', '/twiki/': '', '/': ''}, '500': {'': ''}, '502': {'': ''}, '503': {'': ''}, '504': {'': ''}}, 'actions_history': [], 'cpes': [], 'vulnerabilities_found': []}
    os_linux_dataset = load_dataset(OS_LINUX_DATASET)
    print(f"✅ OS Linux dataset Loaded Successfully")

    os_linux_kernel_dataset = load_dataset(OS_LINUX_KERNEL_DATASET)
    print(f"✅ OS Linux Kernel dataset Loaded Successfully")

    #final_state = correct_state(state, os_linux_dataset, os_linux_kernel_dataset)

    #print(final_state)