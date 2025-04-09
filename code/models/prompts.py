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