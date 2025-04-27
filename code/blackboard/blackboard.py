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
            #"is_up": "",
            #"hostname": "",
            "os": "",
            #"kernel_version": "",
            "services": [
                {"port": "", "protocol": "", "service": ""},
                {"port": "", "protocol": "", "service": ""},
                {"port": "", "protocol": "", "service": ""}
            ],
            #"dns_records": []
        },
        "web_directories_status": {
            "200": {
            "": ""
            },
            "401": {
            "": ""
            },
            "403": {
            "": ""
            },
            "404": {
            "": ""
            },
            "503": {
            "": ""
            }
        },
        "actions_history": [],
        "cpes": [],
        "vulnerabilities_found": [],
        "failed_CVEs": []
    }

         """
            "200": { "": "" },
            "301": { "": "" },
            "302": { "": "" },
            "307": { "": "" },
            "401": { "": "" },
            "403": { "": "" },
            "404": { "": "" },
            "500": { "": "" }
            "502": { "": "" }
            "503": { "": "" }
            "504": { "": "" }
            """