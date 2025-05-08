import json
import os
import sys
from utils.utils import clean_command_output, clean_prompt

from config import EXPECTED_STATUS_CODES, DEFAULT_STATE_STRUCTURE, STATE_SCHEMA

def PROMPT(command_output: str, Custom_prompt: str) -> str:
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

For the detected operating system, fill the "os" object with the following fields
- name: OS name (e.g. "Linux", "Windows")
- distribution name: distribution name (e.g. "Ubuntu", "Debian")
- distribution version: version string (e.g. "20.04", "11")
- distribution architecture: architecture string (e.g. "x86_64", "aarch64")
- kernel: kernel version string (e.g. "5.15.0-75-generic") – if unknown, use ""

For each line of the scan, fill one object in the "services" array.  
- port: numeric (e.g. 22)  
- protocol: "tcp" or "udp"  
- service: service name (e.g. "ssh")  
- server_type: software name (e.g. "OpenSSH", "Apache")  
- server_version: version string (e.g. "7.2p2", "2.4.18")  
- supported_protocols: list of strings (e.g. ["SSH-2.0", "HTTP/1.1"]) – if unknown, use []  
- softwares: list of objects like {{"name": ..., "version": ...}} – if none, use []

For each discovered RPC program, fill one object in the "rpc_services" array
- program_number: numeric program identifier (e.g. 100003)
- version: version number (e.g. 3)
- protocol: "tcp" or "udp"
- port: port number (e.g. 2049)
- service_name: service name (e.g. "nfs", "mountd") – if unknown, use ""

**Do not** omit any of these keys. If you can’t find a value, set it to "" or [] explicitly.

In "web_directories_status", for each status ({clean_prompt(json.dumps(EXPECTED_STATUS_CODES, indent=4, separators=(',',':')))}): Map any discovered paths (like "/admin") to their message (or use "" if no message) like this pattern {{ "{{" }}"": ""{{ }}" }}.

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

# [DEBUG]
if __name__ == "__main__":
  print("""
For each line of the scan, fill one object in the "services" array.  
- port: numeric (e.g. 22)  
- protocol: "tcp" or "udp"  
- service: service name (e.g. "ssh")  
- server_type: software name (e.g. "OpenSSH", "Apache")  
- server_version: version string (e.g. "7.2p2", "2.4.18")  
- supported_protocols: list of strings (e.g. ["SSH-2.0", "HTTP/1.1"]) – if unknown, use []  
- softwares: list of objects like {{"name": ..., "version": ...}} – if none, use []
""")