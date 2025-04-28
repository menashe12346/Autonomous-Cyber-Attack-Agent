import json

def sort_state(state: dict) -> dict:
    """
    Sorts the services list by port number and
    sorts the web directories alphabetically inside each HTTP status code.
    Also removes duplicate entries.
    Assumes state is already validated and well-formed.
    """

    # Sort services by port number and remove duplicates
    seen_ports = set()
    sorted_services = []
    for service in sorted(state.get("target", {}).get("services", []), key=lambda x: int(x.get("port", 0))):
        port = service.get("port")
        protocol = service.get("protocol")
        service_name = service.get("service")
        version = service.get("version", None)
        
        service_key = (port, protocol, service_name, version)
        if service_key not in seen_ports:
            seen_ports.add(service_key)
            sorted_services.append(service)

    if "target" in state:
        state["target"]["services"] = sorted_services

    # Sort web directories paths alphabetically and remove duplicates
    for code, entries in state.get("web_directories_status", {}).items():
        if isinstance(entries, dict):
            unique_paths = {}
            for path in sorted(entries.keys()):
                label = entries[path]
                if path not in unique_paths:
                    unique_paths[path] = label
            state["web_directories_status"][code] = unique_paths

    return state



if __name__ == "__main__":
    # Example usage
    example_state = {
        "target": {
            "services": [
                {"port": "80", "protocol": "tcp", "service": "http"},
                {"port": "22", "protocol": "tcp", "service": "ssh"},
                {"port": "80", "protocol": "tcp", "service": "http"}  # duplicate
            ]
        },
        "web_directories_status": {
            "200": {"/admin": "", "/login": "", "/admin": "duplicate"},
            "404": {"/notfound": "", "/missing": ""}
        }
    }
