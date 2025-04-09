from typing import List

COMMAND_TEMPLATES = {
    "ping": [
        "ping -c 1 {ip}"
    ],
    "nmap_fast": [
        "nmap -F {ip}"
    ],
    "nmap_os": [
        "nmap -O {ip}"
    ],
    "nmap_services": [
        "nmap {ip}"
    ],
    "curl_headers": [
        "curl -I http://{ip}"
    ],
    "curl_index": [
        "curl http://{ip}/"
    ],
    "wget_index": [
        "wget http://{ip} -O -"
    ],
    "dns_lookup": [
        "nslookup {ip}"
    ],
    "whois": [
        "whois {ip}"
    ],
    "traceroute": [
        "traceroute {ip}"
    ],
    "web_tech": [
        "whatweb http://{ip}"
    ],
    "dirb_scan": [
        "dirb http://{ip}"
    ],
    "gobuster_scan": [
        "gobuster dir -u http://{ip} -w /mnt/linux-data/wordlists/SecLists/Discovery/Web-Content/common.txt"
    ]
}

TOOLS = list(COMMAND_TEMPLATES.keys())

def build_action_space(ip: str) -> List[str]:
    """
    בונה את כל הפקודות האפשריות עם כתובת ה-IP שניתנה.
    """
    actions = []
    for tool, templates in COMMAND_TEMPLATES.items():
        for cmd in templates:
            actions.append(cmd.format(ip=ip))
    return actions

def get_commands_for_agent(agent_type: str, ip: str) -> List[str]:
    """
    מחזיר רשימת פקודות בהתאם לסוג הסוכן.
    
    כרגע, כל סוג הסוכן משתמש בפונקציה build_action_space,
    אך בעתיד ניתן להרחיב ולסנן פקודות לפי agent_type.
    """
    # דוגמה: אם הסוכן Recon, נשתמש בכל הפקודות המהירות
    if agent_type.lower() == "recon":
        return build_action_space(ip)
    # אפשר להוסיף תנאים נוספים עבור סוגי סוכנים אחרים (access, exec וכו')
    return build_action_space(ip)

if __name__ == "__main__":
    target_ip = "192.168.56.101"
    cmds = get_commands_for_agent("recon", target_ip)
    for cmd in cmds:
        print(cmd)
