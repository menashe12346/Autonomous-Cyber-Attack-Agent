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

Fill the "target" object based on all available scan data.
For each section below, do not omit any keys. If a value is missing or unknown, set it explicitly to "" for strings or [] for lists.
Ensure every array contains at least one object with all its keys.

For the detected operating system, fill the "os" object:

    name: general OS name (e.g. "Linux", "Windows")

    distribution name: OS distribution (e.g. "Ubuntu", "Debian")

    distribution version: version string (e.g. "20.04", "11")

    distribution architecture: architecture (e.g. "x86_64", "aarch64")

    kernel: kernel version string (e.g. "5.15.0-75-generic"); if unknown, use ""

For each identified network service, add an object in "services":

    port: numeric port (e.g. 22, 80)

    protocol: either "tcp" or "udp"

    service: service name (e.g. "ssh", "http")

    server_type: software name (e.g. "OpenSSH", "Apache")

    server_version: version string (e.g. "7.2p2", "2.4.18")

    supported_protocols: list of protocol strings (e.g. ["SSH-2.0"]); use [] if unknown

    softwares: list of software objects like:
    {{"name": "mod_ssl", "version": "2.4.6"}} — if none, use [{{"name": "", "version": ""}}]

For each discovered RPC service, fill an object in "rpc_services":

    program_number: numeric ID (e.g. 100003)

    version: version number (e.g. 3)

    protocol: "tcp" or "udp"

    port: numeric port (e.g. 2049)

    service_name: service name (e.g. "nfs", "mountd"); if unknown, use ""

For each discovered DNS record, add an object to "dns_records":

    type: record type (e.g. "A", "MX", "TXT")

    value: record value (e.g. IP address, domain, or text)

For each network interface found, fill an object in "network_interfaces":

    name: interface name (e.g. "eth0", "wlan0")

    ip_address: IP address (e.g. "192.168.1.100")

    mac_address: MAC address (e.g. "00:11:22:33:44:55")

    netmask: netmask (e.g. "255.255.255.0")

    gateway: default gateway (e.g. "192.168.1.1")

If geolocation information is available, fill the "geo_location" object:

    country: country name (e.g. "United States")

    region: region or state (e.g. "California")

    city: city name (e.g. "San Francisco")

If SSL/TLS was detected, fill the "ssl" object:

    issuer: name of the certificate issuer (e.g. "Let's Encrypt")

    protocols: list of supported TLS versions (e.g. ["TLSv1.2", "TLSv1.3"]); use [] if unknown

If a web server was discovered, fill the "http" object:

    headers: fill each if available:

        "Server": server type/version (e.g. "Apache/2.4.6")

        "X-Powered-By": platform (e.g. "PHP/7.4.3")

        "Content-Type": MIME type (e.g. "text/html")

    title: web page title (e.g. "Welcome to nginx!")

    robots_txt: contents of /robots.txt as raw text (or "")

    powered_by: other evidence of frameworks/platforms (e.g. "WordPress")

If any trust relationships (e.g., Windows domain trusts) are discovered, fill "trust_relationships" with one object per trust:

    source: the trusting domain/system

    target: the trusted domain/system

    type: type of trust (e.g. "one-way", "transitive")

    direction: "inbound" or "outbound"

    auth_type: authentication method (e.g. "Kerberos")

For each discovered user, add an object to "users":

    username: account username

    group: group name (e.g. "Administrators")

    domain: associated domain (e.g. "WORKGROUP")

If group names are discovered, add them to the "groups" array as strings (e.g. "Administrators", "Users").
Even if none are found, the list should still be included as [""].
omit any of these keys. If you can’t find a value, set it to "" or [] explicitly.

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