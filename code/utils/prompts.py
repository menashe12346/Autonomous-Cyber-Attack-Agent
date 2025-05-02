from config import EXPECTED_STATUS_CODES, DEFAULT_STATE_STRUCTURE
import json
from utils.utils import clean_command_output, clean_prompt

def PROMPT_1(current_state: str) -> str:
  return f""" You are about to receive a specific JSON structure. You must remember it exactly as-is.

Do not explain, summarize, or transform it in any way.
Just memorize it internally — you will be asked to use it later.
All response should be one line.

Here is the structure:
{current_state}
"""
def PROMPT_2(command_output: str, Custom_prompt: str) -> str:
  top_level_keys = list(DEFAULT_STATE_STRUCTURE.keys())
  
  if len(top_level_keys) == 1:
      top_level_keys_string = top_level_keys[0]
  elif len(top_level_keys) == 2:
      top_level_keys_string = " and ".join(top_level_keys)
  else:
      top_level_keys_string = ", ".join(top_level_keys[:-1]) + ", and " + top_level_keys[-1]

  part_1 = f"""
You are about to receive a specific JSON structure.

You must remember it exactly as-is. Do not explain, summarize, or transform it in any way. 
Just memorize it internally — you will be asked to use it later.

Here is the structure: 
{json.dumps(DEFAULT_STATE_STRUCTURE, indent=4, separators=(',',':'))}.

You were previously given a specific JSON structure. 
You MUST now return ONLY that same structure, filled correctly. 
Do NOT rename fields, add another keys, nest or restructure fileds, remove or replace any part of the format, guess or invent values, capitalize fields or names (use lowercase only). 
You MUST return JSON with exactly {len(top_level_keys)} top-level keys: {top_level_keys_string}. 
Include all and only real fileds found.

The "os" field includes name (e.g. "Linux"), distribution with name (e.g. "Ubuntu"), version (e.g. "20.04") and architecture (e.g. "x86_64"), kernel (e.g. "5.15.0-85-generic").The name of the os can be only Linux and the name of the distribution is the type of linux like ubunto or arch and etc.
In "services", add an entry for each service found: "port": numeric (e.g. 22, 80), "protocol": "tcp" or "udp" (lowercase), "service": service name (e.g. http, ssh) — lowercase, If missing, leave value as "". 
In "web_directories_status", for each status ({json.dumps(EXPECTED_STATUS_CODES, indent=4, separators=(',',':'))}): Map any discovered paths (like "/admin") to their message (or use "" if no message) like this pattern {{ "{{" }}"": ""{{ }}" }}. All {len(EXPECTED_STATUS_CODES)} keys must appear, even if empty.

Do not invent or guess data.
Do not rename, add, or remove any fields. 
Return only the completed JSON. No extra text or formatting. Return only one-line compact JSON with same structure, no newlines, no indentations. Response must be one line.
Instructions for this specific command:
"""
  part_1 = clean_prompt(part_1)

  part_2 = f""" {Custom_prompt}."""
  part_2 = clean_command_output(part_2)

  part_3 = f"""Here is the new data:"""
  part_3 = clean_prompt(part_3)

  part_4 = f"""{command_output}."""
  part_4 = clean_command_output(part_4)

  part_5 = f"""Before returning your answer: Compare it to the original json structure character by character. Return ONLY ONE JSON — no explanation, no formatting, no comments"""
  part_5 = clean_prompt(part_5)

  final_prompt = part_1 + part_2 + part_3 + part_4 + part_5

  return final_prompt

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
  part_1 = f"""
Very importent - your output must be maximux 60 words!!!
You are an LLM tasked with analyzing raw output from a reconnaissance command.

Your job is to generate **precise instructions** that guide another LLM on how to extract technical information from this specific output.  
🛠 The instructions must describe **how to interpret the output**, **what patterns to look for**, and **what information is relevant**.

🎯 Your output must:
- Identify the type of information present (e.g., IP, OS, ports, services).
- Specify **how to locate that data** (e.g., line structure, keywords, formats).
- Describe each relevant field that should be extracted.
- Be tailored **specifically to this output** — not generic.

❌ Do **NOT** include:
- Any example JSON structure.
- Any explanations, summaries, or assumptions.
- Any formatting instructions or extra commentary.

📥 Here is the raw output to analyze:
"""
  part_2 =f"""{raw_output}."""

  part_3 = f"""
No emojis!!
✏️ Return only a clear and focused list of extraction instructions based on the data in this output.
"""
  part_1 = clean_prompt(part_1)
  part_2 = clean_command_output(part_2)
  part_3 = clean_prompt(part_3)

  final_prompt = part_1 + part_2 + part_3

  return final_prompt