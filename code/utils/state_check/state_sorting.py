import json

def sort_state(state: dict) -> dict:
    """
    Sorts services:
      - First by port number (ascending) for services with a valid port.
      - Then services with missing/invalid ports sorted alphabetically by service name.
    Also sorts web directories alphabetically.
    Removes duplicates based on (port, protocol, service, version).
    Ignores empty services (where port, protocol, and service are all empty).
    """

    def service_sort_key(service):
        port = service.get("port", "")
        service_name = service.get("service", "")
        
        if port.isdigit():
            return (0, int(port))  # פורט תקין - קבוצה 0 לפי מספר
        else:
            return (1, service_name.lower())  # ללא פורט - קבוצה 1 לפי שם שירות

    # Remove duplicate services, ignore empty entries, and sort
    seen_services = set()
    sorted_services = []
    services = state.get("target", {}).get("services", [])

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

    if "target" in state:
        state["target"]["services"] = sorted_services

    # Sort web directories inside each HTTP status code
    for code, entries in state.get("web_directories_status", {}).items():
        if isinstance(entries, dict):
            sorted_entries = dict(sorted(entries.items()))
            state["web_directories_status"][code] = sorted_entries

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
