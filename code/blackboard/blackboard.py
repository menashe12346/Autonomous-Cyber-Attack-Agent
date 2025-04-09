def initialize_blackboard():
    return {
        "target": {
            "ip": "",
            "os": "Unknown",
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
        "actions_history": {}
    }

