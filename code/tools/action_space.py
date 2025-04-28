from typing import List, Dict

from config import WORDLISTS

# Mapping of tool categories to their command templates
COMMAND_TEMPLATES: Dict[str, Dict[str, List[str]]] = {
    "recon": {
        "ping": [
            #"ping -c 1 {ip}"
        ],
        "nmap": [
            "nmap -F {ip}",
            "nmap {ip}"
        ],
        "curl": [
          #  "curl -I http://{ip}",
            #"curl http://{ip}/"
        ],
        "wget": [
            #"wget http://{ip} -O -"
        ],
        "traceroute": [
          #  "traceroute {ip}"
        ],
        "whatweb": [
            #"whatweb http://{ip}"
        ],
        "gobuster": [
            "gobuster dir -u http://{ip} -w /mnt/linux-data/wordlists/SecLists/Discovery/Web-Content/common.txt"
        ]
    },

    # Example future support:
    # "exploit": {
    #     "manual_exploit": [
    #         "python3 /path/to/exploit.py {ip}"
    #     ]
    # }
}

def build_action_space(agent_type: str, ip: str) -> List[str]:
    """
    Builds a list of actions for the given agent type and target IP address.

    Args:
        agent_type (str): Type of the agent (e.g., "recon", "exploit").
        ip (str): Target IP address.

    Returns:
        List[str]: List of formatted commands.
    """
    actions = []
    agent_type = agent_type.lower()

    if agent_type not in COMMAND_TEMPLATES:
        raise ValueError(f"Unknown agent type: '{agent_type}'")

    for tool, templates in COMMAND_TEMPLATES[agent_type].items():
        for cmd in templates:
            actions.append(cmd.format(ip=ip))

    return actions


def get_commands_for_agent(agent_type: str, ip: str) -> List[str]:
    """
    Retrieves a list of commands for a specific agent.

    Args:
        agent_type (str): Agent category ("recon", etc).
        ip (str): Target IP.

    Returns:
        List[str]: List of formatted commands.
    """
    return build_action_space(agent_type, ip)


if __name__ == "__main__":
    # Debug output of commands for a given IP and agent type
    target_ip = "192.168.56.101"
    commands = get_commands_for_agent("recon", target_ip)
    for cmd in commands:
        print(cmd)