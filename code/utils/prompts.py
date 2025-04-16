def PROMPT_1(current_state: str) -> str:
  return f""" You are about to receive a specific JSON structure. You must remember it exactly as-is.

Do not explain, summarize, or transform it in any way.
Just memorize it internally — you will be asked to use it later.
All response should be one line.

Here is the structure:
{current_state}
"""

def PROMPT_2(command_output: str, Custom_prompt: str) -> str:
  return f"""You were previously given a specific JSON structure. You MUST now return ONLY that same structure, filled correctly. Do NOT rename fields, add another keys, nest or restructure fileds, remove or replace any part of the format, guess or invent values, capitalize protocol or service names (use lowercase only). You MUST return JSON with exactly two top-level keys: "target" and "web_directories_status". Include all real fileds found, with no limit each status key must exist with {{"": ""}} if empty Do not change "ip" — always leave it as-is. Fill "os" only if the OS is clearly mentioned (e.g. "Linux", "Ubuntu", "Windows"). In "services", add an entry for each service found: "port": numeric (e.g. 22, 80) "protocol": "tcp" or "udp" (lowercase) "service": service name (e.g. http, ssh) — lowercase If missing, leave value as "". In "web_directories_status", for each status (200, 401, 403, 404, 503): Map any discovered paths (like "/admin") to their message (or use "" if no message). All five keys must appear, even if empty. If none found, keep {{ "": "" }}. Do not invent or guess data. Do not rename, add, or remove any fields. Return only the completed JSON. No extra text or formatting. Return only one-line compact JSON with same structure, no newlines, no indentations. All response should be one line. Instructions for this specific command: {Custom_prompt} Here is the new data: {command_output} Before returning your answer: Compare it to the original structure character by character Return ONLY ONE JSON — no explanation, no formatting, no comments"""

"""
You were previously given a specific JSON structure. You MUST now return ONLY that same structure, filled correctly.
Do NOT rename fields, add another keys, nest or restructure fileds, remove or replace any part of the format, guess or invent values, capitalize protocol or service names (use lowercase only).
You MUST return JSON with exactly two top-level keys: "target" and "web_directories_status".
Include all real fileds found, with no limit
each status key must exist with {{"": ""}} if empty
Do not change "ip" — always leave it as-is.
Fill "os" only if the OS is clearly mentioned (e.g. "Linux", "Ubuntu", "Windows").
In "services", add an entry for each service found:
"port": numeric (e.g. 22, 80)
"protocol": "tcp" or "udp" (lowercase)
"service": service name (e.g. http, ssh) — lowercase
If missing, leave value as "".
In "web_directories_status", for each status (200, 401, 403, 404, 503):
Map any discovered paths (like "/admin") to their message (or use "" if no message).
All five keys must appear, even if empty. If none found, keep {{ "": "" }}.
Do not invent or guess data.
Do not rename, add, or remove any fields.
Return only the completed JSON. No extra text or formatting.
Return only one-line compact JSON with same structure, no newlines, no indentations.
All response should be one line.
Instructions for this specific command:
{Custom_prompt}
Here is the new data:
{command_output}
Before returning your answer:
Compare it to the original structure character by character
Return ONLY ONE JSON — no explanation, no formatting, no comments
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

Very importent - It should be maximux 60 words!!!
No emojis!!
✏️ Return only a clear and focused list of extraction instructions based on the data in this output.
"""