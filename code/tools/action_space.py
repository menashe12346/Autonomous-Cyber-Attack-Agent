from typing import List, Dict

from config import WORDLISTS, TARGET_IP

# Mapping of tool categories to their command templates
COMMAND_TEMPLATES1: Dict[str, Dict[str, List[str]]] = {
    "recon": {
        "ping": [
            "ping -c 1 {ip}"
        ],
        "hping3": [
            #"sudo hping3 -S -p 80 -c 1 {ip}"
        ],
        "httpx": [
            "httpx http://192.168.56.101",
        ],
        "nikto": [
            "nikto -h {ip}"
        ],
        "sslscan": [
            "sslscan {ip}"
        ],
        "nmap": [
            "nmap -F {ip}",
            "nmap {ip}",
            "nmap -sV {ip}",
            #"nmap -A {ip}",
            "nmap -p 80,443 --script=http-title,http-headers,http-methods {ip}",
            #"nmap -O {ip}",  # זיהוי מערכת הפעלה
            "nmap -sS -A {ip}",  # includes OS, version, script scan, traceroute
            "nmap --script=vuln {ip}",
            "nmap -p 88 --script=krb5-enum-users  {ip}",
            #"nmap -sV --script=banner {ip}",
            #"sudo nmap -O -Pn --traceroute {ip}",
        ],
        "nmap_ssh": [
            "nmap -p 22 --script ssh-hostkey {ip}",
            "nmap -p 22 --script sshv1 {ip}"
        ],
        "nmap_ftp": [
            "nmap -p 21 --script ftp-anon {ip}",
            "nmap -p 21 --script ftp-bounce {ip}"
        ],

        "smbmap": [
            "smbmap -H {ip}"
        ],
        "rpcinfo": [
            "rpcinfo -p {ip}"
        ],
        "nc": [
            #"nc -vz {ip} 1-65535"
        ],
        "curl": [
            "curl -I http://{ip}",
            "curl -k -v http://{ip}"
            "curl http://{ip}/",
        ],
        "wget": [
            "wget http://{ip} -O -",
        ],
        "dig": [
            "dig -x {ip}",
        ],
        "traceroute": [
            "traceroute {ip}",
        ],
        "nbtscan": [
            "nbtscan {ip}"
        ],
        "whatweb": [
            "whatweb http://{ip}"
        ],
        "gobuster": [
            #"gobuster dir -u http://{ip} -w /mnt/linux-data/wordlists/SecLists/Discovery/Web-Content/common.txt"
        ],
        "whois": [
            "whois {ip}"
        ],
        "dirb": [
            #"dirb http://{ip}/ /mnt/linux-data/wordlists/SecLists/Discovery/Web-Content/common.txt"
        ],
        "metasploit": [
            #"""msfconsole -q -x 'use exploit/unix/ftp/vsftpd_234_backdoor; set PAYLOAD payload/cmd/unix/interact; set RHOST 192.168.56.101; set RPORT 21; run -z; sessions 1 -i; sessions -K; exit -y'"""
        ]
    },
}

# [DEBUG] For Debugging
COMMAND_TEMPLATES: Dict[str, Dict[str, List[str]]] = {
    "recon": {
        "nmap": [
            "nmap -F {ip}",
           # "nmap {ip}",
            #"nbtscan {ip}",
            #"httpx http://192.168.56.101",
            #"nikto -h {ip}"
        ],
        "sslscan": [
            #"sslscan {ip}"
        ],
    },
}

def build_action_space(agent_type: str) -> List[str]:
    """
    Builds a list of actions for the given agent type and target IP address.

    Args:
        agent_type (str): Type of the agent (e.g., "recon", "exploit").

    Returns:
        List[str]: List of formatted commands.
    """
    actions = []
    agent_type = agent_type.lower()

    if agent_type not in COMMAND_TEMPLATES:
        raise ValueError(f"Unknown agent type: '{agent_type}'")

    for tool, templates in COMMAND_TEMPLATES[agent_type].items():
        for cmd in templates:
            actions.append(cmd.format(ip=TARGET_IP))

    return actions

def get_commands_for_agent(agent_type: str) -> List[str]:
    """
    Retrieves a list of commands for a specific agent.

    Args:
        agent_type (str): Agent category ("recon", etc).

    Returns:
        List[str]: List of formatted commands.
    """
    return build_action_space(agent_type)

# [DEBUG]
if __name__ == "__main__":
    target_ip = "192.168.56.101"
    commands = get_commands_for_agent("recon", target_ip)
    for cmd in commands:
        print(cmd)