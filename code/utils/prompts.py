import json
import os
import sys
from utils.utils import clean_command_output, clean_prompt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
from config import EXPECTED_STATUS_CODES, DEFAULT_STATE_STRUCTURE, STATE_SCHEMA

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
{clean_prompt(json.dumps(DEFAULT_STATE_STRUCTURE, indent=4, separators=(',',':')))}.

You were previously given a specific JSON structure. 
You MUST now return ONLY that same structure, filled correctly. 
Do NOT rename fields, add another keys, nest or restructure fileds, remove or replace any part of the format, guess or invent values, capitalize fields or names. 
You MUST return JSON with exactly {len(top_level_keys)} top-level keys: {top_level_keys_string}. 
Include all and only real fileds found.

The "os" field includes name (e.g. "Linux"), distribution with name (e.g. "Ubuntu"), version (e.g. "20.04") and architecture (e.g. "x86_64"), kernel (e.g. "5.15.0-85-generic").The name of the os can be only Linux and the name of the distribution is the type of linux like ubunto or arch and etc.

For each line of the scan, fill one object in the "services" array.  
- port: numeric (e.g. 22)  
- protocol: "tcp" or "udp"  
- service: service name (e.g. "ssh")  
- server_type: software name (e.g. "OpenSSH", "Apache")  
- server_version: version string (e.g. "7.2p2", "2.4.18")  
- supported_protocols: list of strings (e.g. ["SSH-2.0", "HTTP/1.1"]) – if unknown, use []  
- softwares: list of objects like {{"name": ..., "version": ...}} – if none, use []

**Do not** omit any of these keys. If you can’t find a value, set it to "" or [] explicitly.

In "web_directories_status", for each status ({json.dumps(EXPECTED_STATUS_CODES, indent=4, separators=(',',':'))}): Map any discovered paths (like "/admin") to their message (or use "" if no message) like this pattern {{ "{{" }}"": ""{{ }}" }}.

Do not invent or guess data.
Do not rename, add, or remove any fields. 
Return only the completed JSON. No extra text or formatting. Return only one-line compact JSON with same structure, no newlines, no indentations. Response must be one line.
Instructions for this specific command:
"""

  part_2 = f""" {Custom_prompt}."""

  part_3 = f"""Here is the new data:"""

  part_4 = f"""{command_output}."""

  part_5 = f"""Before returning your answer: Compare it to the original json structure character by character. Return ONLY ONE JSON — no explanation, no formatting, no comments"""

  final_prompt = part_1 + part_2 + part_3 + part_4 + part_5

  return final_prompt

def PROMPT_2_real(command_output: str, Custom_prompt: str) -> str:
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
Do NOT rename fields, add another keys, nest or restructure fileds, remove or replace any part of the format, guess or invent values, capitalize fields or names. 
You MUST return JSON with exactly {len(top_level_keys)} top-level keys: {top_level_keys_string}. 
Include all and only real fileds found.

The "os" field includes name (e.g. "Linux"), distribution with name (e.g. "Ubuntu"), version (e.g. "20.04") and architecture (e.g. "x86_64"), kernel (e.g. "5.15.0-85-generic").The name of the os can be only Linux and the name of the distribution is the type of linux like ubunto or arch and etc.
In "services", add an entry for each service found: "port": numeric (e.g. 22, 80), "protocol": "tcp" or "udp", "service": service name (e.g. http, ssh), "server_type": software name (e.g. Apache, nginx), "server_version": version string (e.g. 2.2.8), "supported_protocols": list of strings (e.g. ["HTTP/1.1", "DAV"]). Also include a "softwares" list with entries of the form {{"name": software name, "version": version string}}. If any value is missing, use "" or empty list as appropriate.
In "web_directories_status", for each status ({json.dumps(EXPECTED_STATUS_CODES, indent=4, separators=(',',':'))}): Map any discovered paths (like "/admin") to their message (or use "" if no message) like this pattern {{ "{{" }}"": ""{{ }}" }}.

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
from collections import defaultdict

def build_state_explanation(schema: dict, default_structure: dict) -> str:
    """
    Builds explanation sentences per top-level field.
    - Fully recursive.
    - Supports suppressing a container if its llm_prompt is False, promoting its children to top-level.
    - Uses schema-provided prompts for both dict and list fields.
    """
    lines = []

    # Determine effective top-level entries, handling suppressed containers
    entries = []  # List of tuples: (label, struct, parent_prefix)
    for key, value in default_structure.items():
        top_prompt = schema.get(key, {}).get("llm_prompt", None)
        if top_prompt is False and isinstance(value, dict):
            # suppress this container, promote its children
            for child_key, child_val in value.items():
                entries.append((child_key, child_val, key))
        else:
            entries.append((key, value, None))

    def recurse_collect(struct, path=""):
        group_fields = defaultdict(list)
        if isinstance(struct, dict):
            for k, v in struct.items():
                full_key = f"{path}.{k}" if path else k
                prompt = schema.get(full_key, {}).get("llm_prompt", "").strip()
                if isinstance(v, dict):
                    sub = recurse_collect(v, full_key)
                    if prompt:
                        group_fields[k].append(("__parent_prompt__", prompt))
                    if sub:
                        group_fields[k].append(("__nested__", sub))
                elif isinstance(v, list) and v and isinstance(v[0], dict):
                    # child list-of-dicts inside dict
                    if prompt:
                        group_fields[k].append(("__parent_prompt__", prompt))
                    for subk in v[0]:
                        list_key = f"{full_key}[].{subk}"
                        sub_prompt = schema.get(list_key, {}).get("llm_prompt", "").strip()
                        if sub_prompt:
                            group_fields[k].append((subk, sub_prompt))
                else:
                    if prompt:
                        group_fields[""].append((k, prompt))
        return group_fields

    def format_group(group):
        segments = []
        for key, fields in group.items():
            parent_p = None
            nested_items = []
            for name, val in fields:
                if name == "__parent_prompt__":
                    parent_p = f"{key} field includes {val}:" if key else val
                elif name == "__nested__":
                    nested_items.append(format_group(val))
                else:
                    nested_items.append(f"{name} ({val})")
            if nested_items:
                inner = nested_items[0] if len(nested_items) == 1 else ", ".join(nested_items[:-1]) + f" and {nested_items[-1]}"
                if parent_p:
                    segments.append(f"{parent_p} {inner}")
                elif key:
                    segments.append(f"{key} with {inner}")
                else:
                    segments.append(inner)
            elif parent_p:
                segments.append(parent_p)
        return ", ".join(segments)

    for label, struct, parent in entries:
        # build schema path
        path = f"{parent}.{label}" if parent else label
        top_prompt_raw = schema.get(path, {}).get("llm_prompt", None)
        top_prompt = top_prompt_raw.strip().rstrip('.') if isinstance(top_prompt_raw, str) else None

        # Handle list-of-dict top-level fields using schema prompt
        if isinstance(struct, list) and struct and isinstance(struct[0], dict):
            # collect child prompts
            items = []
            for subk in struct[0]:
                list_key = f"{path}[].{subk}"
                sub_prompt = schema.get(list_key, {}).get("llm_prompt", "").strip()
                if sub_prompt:
                    items.append(f"{subk} ({sub_prompt})")
            if items:
                inner = items[0] if len(items) == 1 else ", ".join(items[:-1]) + f" and {items[-1]}"
                if top_prompt:
                    prefix = f'In "{label}", {top_prompt}:'
                else:
                    singular = label[:-1] if label.endswith('s') else label
                    prefix = f'In "{label}", add an entry for each {singular} found:'
                lines.append(f"{prefix} {inner}.")
            continue

        # General dict or suppressed-case handling
        group = recurse_collect(struct, path)
        if group:
            # prefix for dict fields
            if isinstance(struct, list):
                # fallback if non-dict list without schema prompt
                singular = label[:-1] if label.endswith('s') else label
                prefix = f'In "{label}", add an entry for each {singular} found:'
            else:
                prefix = f'The "{label}" field includes'
            sentence = f"{prefix} {format_group(group)}."
            if top_prompt:
                sentence += f" {top_prompt}."
            lines.append(sentence)
        elif isinstance(top_prompt_raw, str) and top_prompt:
            # only top-level prompt
            if top_prompt.lower().startswith('for each'):
                lines.append(f"In \"{label}\", {top_prompt}.")
            else:
                lines.append(f"The \"{label}\" field includes {top_prompt}.")

    return "\n".join(lines).strip()


def PROMPT_22(command_output: str, Custom_prompt: str) -> str:
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

Use these field explanations to build the state JSON:
{build_state_explanation(STATE_SCHEMA, DEFAULT_STATE_STRUCTURE)}

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

if __name__ == "__main__":
  print("""In "services", add an entry for each service found: "port": numeric (e.g. 22, 80), "protocol": "tcp" or "udp", "service": service name (e.g. http, ssh), "server_type": software name (e.g. Apache, nginx), "server_version": version string (e.g. 2.2.8), "supported_protocols": list of strings (e.g. ["HTTP/1.1", "DAV"]). Also include a "softwares" list with entries of the form {{"name": software name, "version": version string}}. If any value is missing, use "" or empty list as appropriate.""")