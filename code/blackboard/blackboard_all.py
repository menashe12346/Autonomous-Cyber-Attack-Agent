def initialize_blackboard():
    return {
        "attack_id": "",
        "target": {
            "ip": "",
            "os": "",
            "services": []
        },
        "exploit_metadata": {
            "exploit_id": None,
            "exploit_title": "",
            "exploit_language": None,
            "exploit_type": "",
            "source": "",
            "exploit_path": None
        },
        "exploit_code_raw": None,
        "code_static_features": {
            "functions": [],
            "syscalls_used": [],
            "payload_type": "",
            "encoding_methods": [],
            "obfuscation_level": "",
            "external_dependencies": [],
            "exploit_technique": ""
        },
        "connections_summary": {
            "total_connections": None,
            "total_packets": None,
            "protocols": [],
            "ports_involved": [],
            "flags_observed": [],
            "data_transferred_bytes": None,
            "sessions": []
        },
        "payload_analysis": [],
        "runtime_behavior": {
            "shell_opened": {
                "shell_type": "",
                "session_type": "",
                "shell_access_level": "",
                "authentication_method": "",
                "shell_session": {
                    "commands_run": []
                }
            }
        },
        "timestamps": {
            "first_packet": None,
            "last_packet": None
        },
        "attack_impact": {
            "success": None,
            "access_level": "",
            "shell_opened": None,
            "shell_type": "",
            "authentication_required": None,
            "persistence_achieved": None,
            "data_exfiltrated": [],
            "sensitive_info_exposed": [],
            "log_files_modified": [],
            "detected_by_defenses": None,
            "quality_score": None
        },
        "actions_log": [],
        "errors": [],
        "reward_log": [],
        "exploits_attempted": [],
        "explanation_of_attack": "",
        "exploit_analysis_detailed": []
    }

