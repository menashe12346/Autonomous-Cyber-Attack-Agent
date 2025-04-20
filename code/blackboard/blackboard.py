def initialize_blackboard():
    """
    Returns a new initialized blackboard dictionary with empty/default values.

    Structure includes:
    - target information (IP, OS, services)
    - web directory status categorized by HTTP status codes
    - action history (agent logs, to be extended by API)

    Returns:
        dict: Initialized blackboard structure
    """
    return {
        "target": {
            "ip": "",
            "os": "",
            "services": [
                {"port": "", "protocol": "", "service": ""},
                {"port": "", "protocol": "", "service": ""},
                {"port": "", "protocol": "", "service": ""}
            ]
        },
        "web_directories_status": {
            "404": { "": "" },
            "200": { "": "" },
            "403": { "": "" },
            "401": { "": "" },
            "503": { "": "" }
        },

        "actions_history": [],
        "cpes": [],
        "vulnerabilities_found": [],
        "failed CVEs": []
    }