PROMPT_1 = """ You are about to receive a specific JSON structure. You must remember it exactly as-is.

 Do not explain, summarize, or transform it in any way.
Just memorize it internally — you will be asked to use it later.

Here is the structure:
{
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
  }
}
"""

def PROMPT_2(command_output: str) -> str:
  return f"""
    You were previously given a specific JSON structure. You MUST now return ONLY that same structure, filled correctly.

    🛑 Do NOT:
    - Change or rename any fields
    - Add new keys like "network_services", "port_state", or "service_name"
    - Nest data inside services or add arrays like "web_directories"
    - Remove or replace any part of the original structure
    - GUESS or INVENT any values that were not explicitly provided
    - Capitalize service or protocol names — always use lowercase only
    - Fill "ip" unless it is clearly the target machine
    - Use vague messages like "Active" — only real messages are allowed

    ✅ You MUST:
    - Return a JSON with the following two root-level keys only: "target" and "web_directories_status"
    - Inside "target", include: "ip" (string), "os" (string), and "services" (array of {{\"port\", \"protocol\", \"service\"}})
    - Inside "web_directories_status", keep ONLY the keys: "200", "401", "403", "404", "503" — each must be a dictionary mapping directory paths (e.g., "admin/") to messages

    🚫 If no IP, OS, or web directories were provided, leave them exactly as-is:
    - "ip": ""
    - "os": "Unknown"
    - web_directories_status must keep: {{"": ""}} for each status code key

    ❗ Each entry in the "services" array MUST be a JSON object with:
    - "port": number
    - "protocol": string (lowercase only)
    - "service": string (lowercase only)

    Here is the new data:

    {command_output}

    🧪 Before returning your answer:
    - Compare it to the original structure character by character
    - Return ONLY the JSON — no explanation, no formatting, no comments
    """

def clean_output_prompt(raw_output: str) -> str:
    return f"""
You are given raw output from a network-related command.

🎯 Your task is to extract only the **critical technical reconnaissance data** relevant to identifying, fingerprinting, or mapping a **target system**.

❗ You do **NOT** know which command was used — it could be `whois`, `dig`, `nmap`, `nslookup`, `curl -I`, or any other.

✅ KEEP only the following:
- IP ranges, CIDRs, hostnames, domain names
- Open ports and services (e.g., "80/tcp open http")
- Server headers and fingerprinting info (e.g., Apache, nginx, PHP, IIS, versions)
- WHOIS identifiers: NetName, NetHandle, NetType, CIDR
- RFC references and technical timestamps (RegDate, Updated)
- Technical metadata directly describing network blocks or infrastructure

🛑 REMOVE everything else, including:
- Organization identity fields: `OrgName`, `OrgId`, `OrgTechName`, `OrgAbuseName`, etc.
- Geographical location: `City`, `Country`, `PostalCode`, `Address`
- Abuse or tech contact details: `OrgAbuseEmail`, `OrgTechEmail`, `Phone numbers`
- Legal disclaimers or registry policy messages (ARIN/RIPE/IANA)
- Any general comments, public notices, usage suggestions, or boilerplate text
- Duplicate fields or references (e.g., "Ref:", "Parent:")
- Empty fields, formatting headers, decorative characters

⚠️ DO NOT:
- Rephrase anything
- Add explanations or summaries
- Invent missing values

Return ONLY the cleaned, relevant technical output that a **penetration tester or AI agent** could use to understand the target system.

---

Here is the raw output:
---
{raw_output}
---

Return ONLY the cleaned output. No explanations, no formatting.
"""
  // import re

def clean_output(raw_output: str) -> str:
    lines = raw_output.splitlines()
    keep_patterns = [
        r'\b\d{1,3}(?:\.\d{1,3}){3}(?:/\d{1,2})?\b',      # IP or CIDR
        r'\b\d+/(tcp|udp)\s+open\b',                      # open ports
        r'Server:\s+.*',                                  # server header
        r'(Apache|nginx|IIS|PHP|OpenSSH|PostgreSQL|MySQL).*',  # common services
        r'NetName|NetHandle|NetType|CIDR|RegDate|Updated'
    ]
    
    cleaned_lines = []
    for line in lines:
        if any(re.search(p, line, re.IGNORECASE) for p in keep_patterns):
            cleaned_lines.append(line.strip())
    return '\n'.join(cleaned_lines)

// import re
import json

def extract_json_from_output(raw_output: str) -> dict:
    # Default structure
    result = {
        "target": {
            "ip": "",
            "os": "Unknown",
            "services": []
        },
        "web_directories_status": {
            "404": {"": ""},
            "200": {"": ""},
            "403": {"": ""},
            "401": {"": ""},
            "503": {"": ""}
        }
    }

    # Extract IP address (first one found)
    ip_match = re.search(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', raw_output)
    if ip_match:
        result["target"]["ip"] = ip_match.group()

    # Extract services (e.g. 80/tcp open http)
    service_lines = re.findall(r'(\d+)/(\w+)\s+open\s+([\w\-]+)', raw_output, re.IGNORECASE)
    for port, protocol, service in service_lines:
        result["target"]["services"].append({
            "port": int(port),
            "protocol": protocol.lower(),
            "service": service.lower()
        })

    # Extract common web directory status codes
    for code in ["200", "401", "403", "404", "503"]:
        matches = re.findall(rf'\b{code}\b\s+(/[^\s]*)', raw_output)
        for path in matches:
            result["web_directories_status"][code][path.strip('/')] = f"{code} found"

    return result

