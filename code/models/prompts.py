PROMPT_1 = """ You are about to receive a specific JSON structure. You must remember it exactly as-is.

Do not explain, summarize, or transform it in any way.
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
  },
}
"""

def PROMPT_1(current_state: str) -> str:
  return f""" You are about to receive a specific JSON structure. You must remember it exactly as-is.

Do not explain, summarize, or transform it in any way.
Just memorize it internally — you will be asked to use it later.

Here is the structure:
{current_state}
"""

def PROMPT_2(command_output: str, Custom_prompt: str) -> str:
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
    - You MUST include ALL valid services found in the data.
    - There is NO limit on how many services can be returned.
    - Even if the example structure had 3 entries — return as many as needed.

    🚫 If no IP, OS, or web directories were provided, leave them exactly as-is:
    - "ip": ""
    - "os": "Unknown"
    - web_directories_status must include exactly these keys: "200", "401", "403", "404", "503"
    - If no web directory paths are available for a status, use: {{ "": "" }} as its value

    ❗ Each entry in the "services" array MUST be a JSON object with:
    - "port": number
    - "protocol": string (lowercase only)
    - "service": string (lowercase only)

    Instructions for this spesific command:

    {Custom_prompt}

    Here is the new data:

    {command_output}

    🧪 Before returning your answer:
    - Compare it to the original structure character by character
    - Return ONLY ONE JSON — no explanation, no formatting, no comments
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

def PROMPT_FOR_A_PROMPT(raw_output: str) -> str:
    return f"""
You are an LLM tasked with analyzing raw output from a reconnaissance command.

Your job is to generate **precise instructions** that guide another LLM on how to extract technical information from this specific output.  
🛠 The instructions must describe **how to interpret the output**, **what patterns to look for**, and **what information is relevant**.

🎯 Your output must:
- Identify the type of information present (e.g., IP, OS, ports, services)
- Specify **how to locate that data** (e.g., line structure, keywords, formats)
- Describe each relevant field that should be extracted
- Be tailored **specifically to this output** — not generic

❌ Do **NOT** include:
- Any example JSON structure
- Any explanations, summaries, or assumptions
- Any formatting instructions or extra commentary

📥 Here is the raw output to analyze:

{raw_output}

✏️ Return only a clear and focused list of extraction instructions based on the data in this output.
"""
