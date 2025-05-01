import json
from copy import deepcopy
from config import EXPECTED_STATUS_CODES


def sort_services(services: list) -> list:
    """
    Sorts and deduplicates service entries.
    - First by port number (ascending) if port is valid.
    - Then by service name (alphabetically) if port is missing/invalid.
    - Ignores completely empty entries.
    - Removes duplicates based on (port, protocol, service, version).
    """

    def service_sort_key(service):
        port = service.get("port", "")
        service_name = service.get("service", "")
        if port.isdigit():
            return (0, int(port))
        else:
            return (1, service_name.lower())

    seen_services = set()
    sorted_services = []

    for service in sorted(services, key=service_sort_key):
        port = service.get("port", "")
        protocol = service.get("protocol", "")
        service_name = service.get("service", "")
        version = service.get("version", None)

        # Ignore completely empty services
        if port == "" and protocol == "" and service_name == "":
            continue

        service_key = (port, protocol, service_name, version)
        if service_key not in seen_services:
            seen_services.add(service_key)
            sorted_services.append(service)

    return sorted_services


def sort_web_directories(web_dirs: dict) -> dict:
    """
    Sorts web directory paths alphabetically within each HTTP status code.
    """
    sorted_result = {}
    for code, entries in web_dirs.items():
        if isinstance(entries, dict):
            sorted_result[code] = dict(sorted(entries.items()))
        else:
            sorted_result[code] = entries  # keep as-is if not a dict
    return sorted_result

def sort_state(state: dict) -> dict:
    """
    Delegates sorting of services and web directories.
    """
    if "target" in state:
        services = state["target"].get("services", [])
        state["target"]["services"] = sort_services(services)

    if "web_directories_status" in state:
        web_dirs = state.get("web_directories_status", {})
        state["web_directories_status"] = sort_web_directories(web_dirs)

    return state

if __name__ == "__main__":
    # Example usage
    example_state = {
        "target": {
            "services": [
                {"port": "80", "protocol": "tcp", "service": "http"},
                {"port": "22", "protocol": "tcp", "service": "ssh"},
                {"port": "", "protocol": "", "service": ""},  # Should be ignored
                {"port": "80", "protocol": "tcp", "service": "http"}  # duplicate
            ]
        },
        "web_directories_status": {
            "200": {"/admin": "", "/login": "", "/admin": "duplicate"},
            "404": {"/notfound": "", "/missing": ""}
        }
    }
    sorted_state = sort_state(example_state)
    print(json.dumps(sorted_state, indent=2))
